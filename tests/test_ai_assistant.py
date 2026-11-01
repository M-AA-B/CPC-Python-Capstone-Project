"""S3 - AI assistant, OpenAI wrapper and AI pages. OpenAI is always mocked."""
import json
from datetime import date

import openai
import pytest

from app.ai_assistant.services import FALLBACK_MESSAGE, AIAssistant, AIUnavailable
from app.extensions import db
from app.models.ai_request import AIRequest
from app.models.chat_message import ChatMessage
from app.models.recommendation import Recommendation, Status
from app.user_access.services import AuthService
from s3_helpers import (  # noqa: F401
    app, demo, demo_data, fake_openai, get_department, get_user, login, month_start, no_api_key, post,
)

TIPS_JSON = json.dumps({"recommendations": [
    {"title": "Electric vans", "description": "Replace two diesel vans.",
     "est_saving_kg": 1200, "est_cost_eur": 50000, "effort": "high"},
    {"title": "Eco-driving training", "description": "Train drivers.",
     "est_saving_kg": 300, "est_cost_eur": 800, "effort": "low"},
]})


def count(model):
    return db.session.scalar(db.select(db.func.count()).select_from(model))


def timeout_error():
    # The real error carries the HTTP request; the tests never send one
    return openai.APITimeoutError(request=None)


def ask(email, question="Hi"):
    return AIAssistant.from_app().ask(get_user(email), question)


# --- OpenAI wrapper --------------------------------------------------------

def test_without_api_key_assistant_explains_setup(demo):
    with pytest.raises(AIUnavailable, match="OPENAI_API_KEY"):
        ask("manager@demo.de")


def test_model_and_token_limit_come_from_config(app, demo, fake_openai):
    app.config.update(OPENAI_MODEL="test-model", AI_MAX_TOKENS=123)
    ask("manager@demo.de")
    call = fake_openai.calls[0]
    assert call["model"] == "test-model"
    assert call["max_completion_tokens"] == 123


def test_default_model(demo, fake_openai):
    ask("manager@demo.de")
    assert fake_openai.calls[0]["model"] == "gpt-4o-mini"


def test_api_failure_gives_fallback_message_and_is_logged(demo, fake_openai):
    fake_openai.error = timeout_error()
    with pytest.raises(AIUnavailable, match=FALLBACK_MESSAGE):
        ask("manager@demo.de")
    log = db.session.scalar(db.select(AIRequest))
    assert log.kind == "chat" and log.succeeded is False


def test_empty_answer_gives_fallback_message(demo, fake_openai):
    fake_openai.replies = ["   "]
    with pytest.raises(AIUnavailable, match=FALLBACK_MESSAGE):
        ask("manager@demo.de")


def test_successful_request_is_logged_with_tokens(demo, fake_openai):
    ask("manager@demo.de")
    log = db.session.scalar(db.select(AIRequest))
    assert log.succeeded is True and log.total_tokens == 42


def test_daily_limit_per_company(app, demo, fake_openai):
    app.config["AI_DAILY_REQUEST_LIMIT"] = 2
    ask("manager@demo.de", "one")
    ask("employee@demo.de", "two")  # same company
    with pytest.raises(AIUnavailable, match="limit"):
        ask("manager@demo.de", "three")
    assert len(fake_openai.calls) == 2

    # another company still has its own limit
    AuthService.register("Other AG", "boss@other.de", "secret123")
    ask("boss@other.de", "hello")
    assert len(fake_openai.calls) == 3


# --- chat ------------------------------------------------------------------

def test_ask_saves_question_and_answer(demo_data, fake_openai):
    fake_openai.replies = ["Logistics emits the most: 750 kg CO2e."]
    reply = ask("manager@demo.de", "  Which department emits most?  ")
    assert reply.content == "Logistics emits the most: 750 kg CO2e."
    messages = db.session.scalars(db.select(ChatMessage).order_by(ChatMessage.created_at)).all()
    assert [m.content for m in messages] == ["Which department emits most?", reply.content]


def test_ask_sends_real_company_figures(demo_data, fake_openai):
    ask("manager@demo.de")
    system = fake_openai.calls[0]["messages"][0]["content"]
    assert '"total_kg": 1300.0' in system
    assert '"Logistics": 750.0' in system


def test_failed_answer_saves_nothing(demo, fake_openai):
    fake_openai.error = timeout_error()
    with pytest.raises(AIUnavailable):
        ask("manager@demo.de")
    assert count(ChatMessage) == 0


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_invalid_questions_never_reach_openai(demo, fake_openai, question):
    with pytest.raises(ValueError):
        ask("manager@demo.de", question)
    assert fake_openai.calls == []


def test_follow_up_question_includes_history(demo, fake_openai):
    ask("manager@demo.de", "first question")
    ask("manager@demo.de", "second question")
    contents = [m["content"] for m in fake_openai.calls[1]["messages"]]
    assert contents[-3:] == ["first question", "Sample answer.", "second question"]


def test_history_is_per_user(demo, fake_openai):
    ask("manager@demo.de", "manager question")
    ask("employee@demo.de", "employee question")
    contents = [m["content"] for m in fake_openai.calls[1]["messages"]]
    assert "manager question" not in contents


# --- recommendations -------------------------------------------------------

def test_recommend_saves_validated_tips(demo_data, fake_openai):
    fake_openai.replies = [TIPS_JSON]
    tips = AIAssistant.from_app().recommend(demo_data.company_id, get_department("Logistics").id)
    assert [t.title for t in tips] == ["Electric vans", "Eco-driving training"]
    assert all(t.status == Status.PROPOSED for t in tips)
    assert fake_openai.calls[0]["response_format"] == {"type": "json_object"}
    # Logistics: 750 kg in 3 months = 3000 kg per year, the upper limit for a saving
    assert "between 0 and 3000" in fake_openai.calls[0]["messages"][1]["content"]


def test_recommend_with_unusable_answer_saves_nothing(demo_data, fake_openai):
    fake_openai.replies = ["Sorry, I can't help with that."]
    with pytest.raises(AIUnavailable, match="unusable"):
        AIAssistant.from_app().recommend(demo_data.company_id, get_department("Logistics").id)
    assert count(Recommendation) == 0


def test_recommend_rejects_other_companys_department(demo_data, fake_openai):
    other = AuthService.register("Other AG", "boss@other.de", "secret123")
    with pytest.raises(ValueError, match="Unknown department"):
        AIAssistant.from_app().recommend(other.company_id, get_department("Logistics").id)
    assert fake_openai.calls == []


def test_recommend_without_emission_data(demo, fake_openai):
    with pytest.raises(AIUnavailable, match="no emission data"):
        AIAssistant.from_app().recommend(demo.company_id, get_department("Office").id)
    assert fake_openai.calls == []


def test_recommendation_status_methods():
    tip = Recommendation(title="t", description="d", est_saving_kg=1, effort="low")
    tip.accept()
    assert tip.status == Status.ACCEPTED
    tip.mark_done()
    assert tip.status == Status.DONE
    tip.reject()
    assert tip.status == Status.REJECTED


# --- monthly summary -------------------------------------------------------

def test_summary_covers_month_and_previous_month(demo_data, fake_openai):
    fake_openai.replies = ["Emissions rose by 22 %."]
    month = month_start(0)
    text = AIAssistant.from_app().summarise(demo_data.company_id, month)
    assert text == "Emissions rose by 22 %."
    system, instruction = (m["content"] for m in fake_openai.calls[0]["messages"])
    assert month.strftime("%B %Y") in instruction
    assert f'"period_start": "{month_start(1).isoformat()}"' in system
    assert '"latest_month_change_pct": 22.2' in system


# --- pages -----------------------------------------------------------------

def test_assistant_page_for_guests_and_users(demo, client):
    assert b"Log in" in client.get("/assistant/").data
    login(client, "employee@demo.de")
    assert b'id="chat-form"' in client.get("/assistant/").data


def test_chat_endpoint_returns_answer(demo, fake_openai, client):
    login(client, "employee@demo.de")
    response = post(client, "/assistant/ask", json={"question": "How are we doing?"})
    assert response.status_code == 200
    assert response.get_json()["message"]["content"] == "Sample answer."
    assert b"Sample answer." in client.get("/assistant/").data  # shown in the history


def test_chat_endpoint_needs_csrf_token(demo, fake_openai, client):
    login(client, "employee@demo.de")
    response = post(client, "/assistant/ask", json={"question": "Hi"}, token="wrong")
    assert response.status_code == 400
    assert fake_openai.calls == []


def test_chat_endpoint_fallback(demo, fake_openai, client):
    fake_openai.error = timeout_error()
    login(client, "employee@demo.de")
    response = post(client, "/assistant/ask", json={"question": "Hi"})
    assert response.status_code == 503
    assert response.get_json() == {"ok": False, "error": FALLBACK_MESSAGE}


def test_chat_endpoint_needs_login(client):
    assert post(client, "/assistant/ask", json={"question": "Hi"}).status_code == 302


def test_manager_generates_and_accepts_tips(demo_data, fake_openai, client):
    fake_openai.replies = [TIPS_JSON]
    login(client, "manager@demo.de")
    post(client, "/assistant/recommendations/generate", {"department_id": get_department("Logistics").id})
    page = client.get("/assistant/recommendations").data
    assert b"Electric vans" in page and b"1,200" in page

    tip = db.session.scalar(db.select(Recommendation).filter_by(title="Electric vans"))
    post(client, f"/assistant/recommendations/{tip.id}/accept")
    db.session.refresh(tip)
    assert tip.status == Status.ACCEPTED


def test_employee_cannot_generate_tips(demo_data, fake_openai, client):
    login(client, "employee@demo.de")
    response = post(client, "/assistant/recommendations/generate",
                    {"department_id": get_department("Office").id})
    assert response.status_code == 403
    assert fake_openai.calls == []


def test_employee_sees_only_own_department_tips(demo, client):
    for name in ("Office", "Logistics"):
        db.session.add(Recommendation(company_id=demo.company_id, department_id=get_department(name).id,
                                      title=f"Tip for {name}", description="d", est_saving_kg=1, effort="low"))
    db.session.commit()

    login(client, "employee@demo.de")  # works in Office
    page = client.get("/assistant/recommendations").data
    assert b"Tip for Office" in page
    assert b"Tip for Logistics" not in page


def test_cannot_change_other_companys_tip(demo, client):
    other = AuthService.register("Other AG", "boss@other.de", "secret123", ["Sales"])
    tip = Recommendation(company_id=other.company_id, department_id=get_department("Sales").id,
                         title="t", description="d", est_saving_kg=1, effort="low")
    db.session.add(tip)
    db.session.commit()

    login(client, "manager@demo.de")
    assert post(client, f"/assistant/recommendations/{tip.id}/reject").status_code == 404
    db.session.refresh(tip)
    assert tip.status == Status.PROPOSED


def test_summary_page(demo_data, fake_openai, client):
    fake_openai.replies = ["Emissions fell in March."]
    login(client, "employee@demo.de")
    response = post(client, "/assistant/summary", {"month": "2026-03"})
    assert b"Emissions fell in March." in response.data
    assert b"March 2026" in response.data


def test_summary_page_without_api_key_shows_message(demo, client):
    login(client, "employee@demo.de")
    response = post(client, "/assistant/summary", {"month": "2026-03"})
    assert b"missing OPENAI_API_KEY" in response.data
