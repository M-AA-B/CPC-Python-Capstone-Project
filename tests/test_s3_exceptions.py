"""Hometask 4 — S3 error hierarchy and S3ErrorHandler (Junaid Ahmad · 7222074). OpenAI is always mocked."""
import logging

import pytest

from app.ai_assistant.services import AIAssistant, parse_recommendations
from app.extensions import db
from app.models.recommendation import Recommendation
from app.user_access.exceptions import (
    AIError,
    AINotConfiguredError,
    AIRateLimitError,
    AIUnavailable,
    AccessDeniedError,
    AuthError,
    InvalidAIOutput,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidQuestionError,
    NoEmissionDataError,
    ResourceNotFoundError,
    S3Error,
    S3ErrorHandler,
    UnknownDepartmentError,
    WorkflowError,
)
from app.user_access.services import AuthService
from s3_helpers import (  # noqa: F401
    PASSWORD, app, demo, demo_data, fake_openai, get_department, get_user, no_api_key,
)

ALL_ERRORS = [AuthError, InvalidCredentialsError, AccessDeniedError, InvalidInputError, InvalidQuestionError,
              AIError, AIUnavailable, AINotConfiguredError, AIRateLimitError, InvalidAIOutput]


def api_login(client, email):
    response = client.post("/api/s3/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["csrf_token"]


# --- the hierarchy itself ----------------------------------------------------------

@pytest.mark.parametrize("error_class", ALL_ERRORS)
def test_every_s3_error_has_the_common_base(error_class):
    error = error_class()
    assert isinstance(error, S3Error)
    assert error.message and str(error) == error.message


@pytest.mark.parametrize("error, builtin", [
    (AuthError(), ValueError),
    (AccessDeniedError(), PermissionError),
    (ResourceNotFoundError("User"), LookupError),
    (InvalidQuestionError(), ValueError),
    (AIUnavailable(), RuntimeError),
    (InvalidAIOutput(), ValueError),
    (UnknownDepartmentError("d1"), ValueError),
    (UnknownDepartmentError("d1"), LookupError),
])
def test_errors_still_match_builtin_exceptions(error, builtin):
    """Older `except ValueError:` blocks keep working after Hometask 4."""
    assert isinstance(error, builtin)


@pytest.mark.parametrize("error, status", [
    (AuthError(), 400), (InvalidCredentialsError(), 401), (AccessDeniedError(), 403),
    (ResourceNotFoundError("User"), 404), (WorkflowError("done", "accepted"), 409),
    (NoEmissionDataError("Office"), 422), (AIRateLimitError(), 429),
    (InvalidAIOutput(), 502), (AIUnavailable(), 503), (AINotConfiguredError(), 503),
])
def test_status_codes(error, status):
    assert error.status_code == status


def test_to_dict_is_safe_json():
    error = WorkflowError("done", "accepted")
    assert error.to_dict() == {
        "ok": False,
        "error": "A done recommendation cannot become accepted.",
        "error_type": "WorkflowError",
        "details": {"current": "done", "requested": "accepted"},
    }
    assert "details" not in AccessDeniedError("Nope").to_dict()


def test_custom_message_replaces_default():
    assert AIUnavailable().message.startswith("The AI assistant is not available")
    assert AIUnavailable("Try later").message == "Try later"
    assert UnknownDepartmentError("d1").message == "Unknown department."


# --- raised by the S3 services -----------------------------------------------------

def test_missing_api_key_raises_not_configured(demo):
    with pytest.raises(AINotConfiguredError, match="OPENAI_API_KEY"):
        AIAssistant.from_app().ask(get_user("manager@demo.de"), "Hi")


def test_daily_limit_raises_rate_limit_error(app, demo, fake_openai):
    app.config["AI_DAILY_REQUEST_LIMIT"] = "0"
    with pytest.raises(AIRateLimitError) as caught:
        AIAssistant.from_app().ask(get_user("manager@demo.de"), "Hi")
    assert caught.value.details == {"daily_limit": 0}
    assert fake_openai.calls == []


def test_bad_questions_raise_invalid_question(demo, fake_openai):
    assistant = AIAssistant.from_app()
    with pytest.raises(InvalidQuestionError):
        assistant.ask(get_user("manager@demo.de"), "   ")
    with pytest.raises(InvalidQuestionError, match="under 1000"):
        assistant.ask(get_user("manager@demo.de"), "x" * 1001)


def test_recommend_errors(demo, fake_openai):
    office = get_department("Office")
    with pytest.raises(NoEmissionDataError) as caught:
        AIAssistant.from_app().recommend(demo.company_id, office.id)
    assert caught.value.details == {"department": "Office"}
    other = AuthService.register("Other AG", "boss@other.de", PASSWORD)
    with pytest.raises(UnknownDepartmentError):
        AIAssistant.from_app().recommend(other.company_id, office.id)


def test_invalid_ai_output_from_validation():
    with pytest.raises(InvalidAIOutput) as caught:
        parse_recommendations("not json", max_saving_kg=100)
    assert caught.value.status_code == 502


def test_auth_errors_are_s3_errors(demo):
    with pytest.raises(AuthError) as caught:
        AuthService.register("Demo GmbH", "x@demo.de", PASSWORD)
    assert isinstance(caught.value, S3Error)


# --- S3ErrorHandler ------------------------------------------------------------------

def test_handler_is_installed(app):
    assert isinstance(app.extensions["s3_error_handler"], S3ErrorHandler)


def test_api_errors_become_json(client, demo):
    bad_login = client.post("/api/s3/login", json={"email": "admin@demo.de", "password": "wrong-pass"})
    assert bad_login.status_code == 401
    assert bad_login.get_json()["error_type"] == "InvalidCredentialsError"

    token = api_login(client, "manager@demo.de")
    no_ai = client.post("/api/s3/chat", json={"question": "Hi"}, headers={"X-CSRFToken": token})
    assert no_ai.status_code == 503
    assert no_ai.get_json()["error_type"] == "AINotConfiguredError"

    bad_filter = client.get("/api/s3/recommendations?status=maybe")
    assert (bad_filter.status_code, bad_filter.get_json()["error_type"]) == (400, "InvalidInputError")


def test_workflow_error_through_api(client, demo):
    office = get_department("Office")
    tip = Recommendation(company_id=demo.company_id, department_id=office.id, title="LED", description="d",
                         est_saving_kg=10, effort="low", status="rejected")
    db.session.add(tip)
    db.session.commit()
    token = api_login(client, "manager@demo.de")
    response = client.patch(f"/api/s3/recommendations/{tip.id}", json={"status": "done"},
                            headers={"X-CSRFToken": token})
    assert response.status_code == 409
    assert response.get_json()["details"] == {"current": "rejected", "requested": "done"}
    missing = client.get("/api/s3/recommendations/does-not-exist")
    assert (missing.status_code, missing.get_json()["error_type"]) == (404, "ResourceNotFoundError")


def test_html_pages_get_the_error_page(app, client):
    @app.get("/s3-test-error")
    def raise_access_denied():
        raise AccessDeniedError("Managers only.")

    response = client.get("/s3-test-error")
    assert response.status_code == 403
    assert "text/html" in response.content_type
    assert "Managers only." in response.get_data(as_text=True)


def test_handler_counts_and_logs(app, client, demo, caplog):
    handler = app.extensions["s3_error_handler"]
    token = api_login(client, "manager@demo.de")
    with caplog.at_level(logging.INFO, logger="app.user_access.exceptions"):
        client.post("/api/s3/chat", json={"question": "Hi"}, headers={"X-CSRFToken": token})
        client.post("/api/s3/chat", json={"question": "Hi"}, headers={"X-CSRFToken": token})
    assert handler.handled_counts()["AINotConfiguredError"] == 2
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 2 and "AINotConfiguredError" in errors[0].getMessage()
