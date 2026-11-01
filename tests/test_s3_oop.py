"""Tests for Hometask 1 OOP encapsulation in Subsystem 3 and Company-User integration."""
import pytest

from app.ai_assistant.prompts import SYSTEM_PROMPT, PromptBuilder
from app.ai_assistant.services import HISTORY_LENGTH, AIAssistant, AIClient
from app.extensions import db
from app.models.company import Company
from app.models.user import Role, User


def test_ai_client_encapsulation():
    client = AIClient(api_key="", model="gpt-4o-mini", timeout=10.0, max_tokens=600, daily_limit=200)
    assert client.model == "gpt-4o-mini"

    client.configure(model="gpt-4.1-mini", timeout=15.0, max_tokens=400, daily_limit=50)
    assert client.model == "gpt-4.1-mini"
    assert client.timeout == 15.0
    assert client.max_tokens == 400
    assert client.daily_limit == 50

    with pytest.raises(ValueError):
        client.model = "   "
    with pytest.raises(ValueError):
        client.timeout = 0
    with pytest.raises(ValueError):
        client.max_tokens = 0
    with pytest.raises(ValueError):
        client.daily_limit = -1


def test_prompt_builder_encapsulation():
    builder = PromptBuilder()
    assert builder.max_hotspots == 3

    builder.system_prompt = "Custom coach rules."
    builder.max_hotspots = 5
    assert builder.system_prompt == "Custom coach rules."
    assert builder.max_hotspots == 5

    with pytest.raises(ValueError):
        builder.system_prompt = ""
    with pytest.raises(ValueError):
        builder.max_hotspots = 0

    builder.reset_templates()
    assert builder.system_prompt == SYSTEM_PROMPT
    assert builder.max_hotspots == 3


def test_ai_assistant_encapsulation():
    client = AIClient(api_key="", model="gpt-4o-mini")
    builder = PromptBuilder()
    assistant = AIAssistant(client=client, prompts=builder)

    assert assistant.model == "gpt-4o-mini"
    assistant.model = "gpt-4.1-mini"
    assert client.model == "gpt-4.1-mini"

    assistant.history_limit = 10
    assert assistant.history_limit == 10

    with pytest.raises(ValueError):
        assistant.history_limit = -1
    with pytest.raises(TypeError):
        assistant.client = "not-a-client"  # type: ignore[assignment]
    with pytest.raises(TypeError):
        assistant.prompts = "not-a-builder"  # type: ignore[assignment]

    assistant.reset_defaults()
    assert assistant.history_limit == HISTORY_LENGTH


def test_user_role_encapsulation_and_company_employees(client):
    with client.application.app_context():
        comp = Company(id="s3-oop-comp", name="S3 OOP GmbH")
        u1 = User(id="u1", company_id="s3-oop-comp", email="u1@demo.de")
        assert u1.get_role() == Role.EMPLOYEE

        u1.set_role(Role.MANAGER)
        assert u1.get_role() == Role.MANAGER

        with pytest.raises(ValueError):
            u1.set_role("invalid-role")

        db.session.add_all([comp, u1])
        db.session.commit()
        assert comp.get_total_employees() == 1

