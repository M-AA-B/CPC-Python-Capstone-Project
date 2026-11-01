"""S3 - the AI only gets aggregated data, and AI output is validated before saving."""
import json
from datetime import date

import pytest

from app.ai_assistant import data
from app.ai_assistant.prompts import PromptBuilder, default_period
from app.ai_assistant.services import InvalidAIOutput, parse_recommendations
from app.models.chat_message import ChatMessage, Sender
from s3_helpers import app, demo, demo_data, month_start, no_api_key  # noqa: F401


@pytest.fixture()
def summary(demo_data):
    return PromptBuilder.build_context(demo_data.company_id, month_start(2), date.today())


# --- aggregated company data -----------------------------------------------

def test_summary_totals(summary):
    assert summary["total_kg"] == 1300.0
    assert summary["by_department"] == {"Logistics": 750.0, "Office": 550.0}
    assert summary["by_category"] == {"Fuel": 750.0, "Electricity": 450.0, "Business Travel": 100.0}
    assert summary["by_scope"] == {"Scope 1": 750.0, "Scope 2": 450.0, "Scope 3": 100.0}


def test_summary_by_month_oldest_first_with_change(summary):
    months = [month_start(n).strftime("%Y-%m") for n in (2, 1, 0)]
    assert summary["by_month"] == {months[0]: 300.0, months[1]: 450.0, months[2]: 550.0}
    assert summary["latest_month_change_pct"] == pytest.approx(22.2)


def test_summary_respects_the_period(demo_data):
    this_month = data.emission_summary(demo_data.company_id, month_start(0), date.today())
    assert this_month["total_kg"] == 550.0
    assert this_month["latest_month_change_pct"] is None  # only one month


def test_summary_only_contains_own_company(demo_data):
    from app.user_access.services import AuthService
    other = AuthService.register("Other AG", "boss@other.de", "secret123", ["Sales"])
    assert data.emission_summary(other.company_id)["total_kg"] == 0.0


@pytest.mark.parametrize("monthly, expected", [
    ({"2026-02": 100.0, "2026-03": 80.0}, -20.0),
    ({"2026-01": 100.0, "2026-03": 80.0}, None),   # not consecutive
    ({"2026-03": 80.0}, None),
    ({"2025-12": 50.0, "2026-01": 100.0}, 100.0),  # across the year boundary
])
def test_latest_month_change(monthly, expected):
    assert data.latest_month_change(monthly) == expected


# --- PromptBuilder ---------------------------------------------------------

def test_prompt_contains_aggregates_but_no_ids_or_emails(summary, demo_data):
    text = json.dumps(PromptBuilder().chat_messages(summary, "How are we doing?"))
    assert "1300.0" in text and "Logistics" in text
    assert demo_data.company_id not in text and demo_data.id not in text
    assert "@" not in text  # no email addresses


def test_system_prompt_forbids_invented_numbers(summary):
    system = PromptBuilder().chat_messages(summary, "Q")[0]
    assert system["role"] == "system"
    assert "ONLY the figures" in system["content"]


def test_chat_history_is_sent_in_order(summary):
    history = [ChatMessage(sender=Sender.USER, content="first question"),
               ChatMessage(sender=Sender.ASSISTANT, content="first answer")]
    messages = PromptBuilder().chat_messages(summary, "follow-up", history)
    assert [(m["role"], m["content"]) for m in messages[1:]] == [
        ("user", "first question"), ("assistant", "first answer"), ("user", "follow-up"),
    ]


def test_hotspots_are_biggest_categories_with_share(summary):
    hotspots = PromptBuilder.hotspots(summary, top=2)
    assert [name for name, _kg, _share in hotspots] == ["Fuel", "Electricity"]
    assert hotspots[0][2] == pytest.approx(750 / 1300 * 100)


def test_advice_prompt_names_department_and_saving_limit(summary):
    text = PromptBuilder().advice_prompt(summary, "Logistics", annual_kg=3000)[1]["content"]
    assert '"Logistics"' in text
    assert "between 0 and 3000" in text
    assert "Fuel (58 %)" in text


@pytest.mark.parametrize("today, expected_start", [
    (date(2026, 11, 1), date(2025, 12, 1)),
    (date(2026, 12, 15), date(2026, 1, 1)),
])
def test_default_period_is_twelve_months(today, expected_start):
    assert default_period(today) == (expected_start, today)


# --- recommendation JSON validation ----------------------------------------

def tip(**overrides):
    item = {"title": "Electric vans", "description": "Replace two diesel vans.",
            "est_saving_kg": 1200, "est_cost_eur": 50000, "effort": "High"}
    item.update(overrides)
    return item


def test_valid_recommendations_are_parsed():
    [result] = parse_recommendations(json.dumps({"recommendations": [tip()]}), max_saving_kg=3000)
    assert result["effort"] == "high"
    assert result["est_saving_kg"] == 1200.0


def test_invalid_items_are_skipped_valid_ones_kept():
    raw = json.dumps({"recommendations": [
        tip(est_saving_kg=999_999),  # more than the department emits
        tip(effort="extreme"),
        tip(est_saving_kg="a lot"),
        tip(title=""),
        tip(est_cost_eur=-5),
        tip(est_saving_kg=True),
        tip(title="Kept", est_cost_eur=None),
    ]})
    result = parse_recommendations(raw, max_saving_kg=3000)
    assert [r["title"] for r in result] == ["Kept"]
    assert result[0]["est_cost_eur"] is None


def test_at_most_five_recommendations():
    raw = json.dumps({"recommendations": [tip(title=f"Tip {n}") for n in range(8)]})
    assert len(parse_recommendations(raw, max_saving_kg=3000)) == 5


@pytest.mark.parametrize("raw", [
    "Here are some tips: ...",               # not JSON
    json.dumps([tip()]),                     # list instead of object
    json.dumps({"tips": [tip()]}),           # wrong key
    json.dumps({"recommendations": []}),     # empty
    json.dumps({"recommendations": [tip(est_saving_kg=-1)]}),  # nothing valid
])
def test_unusable_output_is_rejected(raw):
    with pytest.raises(InvalidAIOutput):
        parse_recommendations(raw, max_saving_kg=3000)
