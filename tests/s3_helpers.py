"""S3 test helpers and fixtures (import them into an S3 test module). Owner: Junaid."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.user import Role, User
from app.user_access.services import AuthService

PASSWORD = "demo1234"
TOKEN = "test-csrf-token"


def get_user(email):
    return db.session.scalar(db.select(User).filter_by(email=email))


def get_department(name):
    return db.session.scalar(db.select(Department).filter_by(name=name))


def post(client, url, data=None, token=TOKEN, json=None):
    """POST like the browser does: the session holds the CSRF token and the request sends it."""
    with client.session_transaction() as session:
        session["csrf_token"] = TOKEN
    if json is not None:
        return client.post(url, json=json, headers={"X-CSRFToken": token})
    return client.post(url, data={**(data or {}), "csrf_token": token})


def login(client, email, password=PASSWORD):
    return post(client, "/auth/login", {"email": email, "password": password})


def month_start(months_ago: int, today: date | None = None) -> date:
    first = (today or date.today()).replace(day=1)
    for _ in range(months_ago):
        first = (first - timedelta(days=1)).replace(day=1)
    return first


@pytest.fixture()
def app(client):
    return client.application


@pytest.fixture()
def demo(client):
    """Demo GmbH: admin, manager and employee (Office), departments Logistics and Office."""
    admin = AuthService.register("Demo GmbH", "admin@demo.de", PASSWORD, ["Logistics", "Office"])
    office = get_department("Office")
    AuthService.create_user(admin, "manager@demo.de", PASSWORD, Role.MANAGER, office.id)
    AuthService.create_user(admin, "employee@demo.de", PASSWORD, Role.EMPLOYEE, office.id)
    return admin


# (months ago, department, category, scope, kg CO2e)
DEMO_RECORDS = [
    (2, "Logistics", "Fuel", 1, 300.0),
    (1, "Logistics", "Fuel", 1, 250.0),
    (0, "Logistics", "Fuel", 1, 200.0),
    (1, "Office", "Electricity", 2, 200.0),
    (0, "Office", "Electricity", 2, 250.0),
    (0, "Office", "Business Travel", 3, 100.0),
]


@pytest.fixture()
def demo_data(demo):
    """Activity records for the last three months, saved like S1 saves them."""
    factor = EmissionFactor(id=1, category="Fuel", kg_co2e_per_unit=1.0, unit="l", scope=1, valid_year=2026)
    db.session.add(factor)
    for months_ago, department, category, scope, kg in DEMO_RECORDS:
        start = month_start(months_ago)
        db.session.add(ActivityRecord(
            company_id=demo.company_id, department_id=get_department(department).id, factor_id=factor.id,
            category=category, quantity=kg, unit="l", co2e_kg=kg, scope=scope,
            period_start=start, period_end=start + timedelta(days=27), created_by=demo.id,
        ))
    db.session.commit()
    return demo


class FakeOpenAI:
    """Stands in for openai.OpenAI. Set .replies (answers in order) or .error (exception to raise)."""

    def __init__(self):
        self.calls = []
        self.replies = []
        self.error = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        content = self.replies.pop(0) if self.replies else "Sample answer."
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            usage=SimpleNamespace(total_tokens=42),
        )


@pytest.fixture()
def fake_openai(app, monkeypatch):
    """Every OpenAI call in the app goes to a FakeOpenAI instead of the real API."""
    fake = FakeOpenAI()
    app.config["OPENAI_API_KEY"] = "test-key"
    monkeypatch.setattr("app.ai_assistant.services.openai.OpenAI", lambda **_kwargs: fake)
    return fake


@pytest.fixture(autouse=True)
def no_api_key(app, monkeypatch):
    """Runs for every test that imports it: a real OPENAI_API_KEY on this computer is never used."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app.config["OPENAI_API_KEY"] = ""
