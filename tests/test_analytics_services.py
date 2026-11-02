from datetime import date

import pytest

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.company import Company
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.user import User
from app.analytics.services import (
    get_emissions_summary,
    get_emissions_by_category,
    get_monthly_emissions,
)


@pytest.fixture()
def analytics_data(client):
    with client.application.app_context():
        db.session.add_all([
            Company(id="company-a", name="Company A"),
            Company(id="company-b", name="Company B"),
            User(id="test-user", email="analytics@example.com"),
            EmissionFactor(
                id=1,
                category="electricity",
                kg_co2e_per_unit=1,
                unit="kWh",
                scope=2,
                valid_year=2026,
            ),
        ])
        db.session.flush()

        db.session.add_all([
            Department(
                id="dept-a",
                company_id="company-a",
                name="Department A",
            ),
            Department(
                id="dept-b",
                company_id="company-b",
                name="Department B",
            ),
        ])
        db.session.flush()

        rows = [
            ("a1", "dept-a", date(2026, 3, 1), "electricity", 42),
            ("a2", "dept-a", date(2026, 4, 1), "transport", 60),
            ("a3", "dept-a", date(2026, 4, 30), " electricity ", 18),
            ("a4", "dept-a", None, "", 5),
            ("b1", "dept-b", date(2026, 3, 1), "electricity", 900),
        ]

        for record_id, department_id, start, category, emissions in rows:
            db.session.add(ActivityRecord(
                id=record_id,
                department_id=department_id,
                factor_id=1,
                period_start=start,
                period_end=start,
                category=category,
                quantity=emissions,
                unit="kWh",
                co2e_kg=emissions,
                scope=2,
                created_by="test-user",
            ))

        db.session.commit()
        yield


def test_summary_is_isolated_by_company(analytics_data):
    result = get_emissions_summary("company-a")

    assert result["record_count"] == 4
    assert result["total_emissions"] == pytest.approx(125)

    other = get_emissions_summary("company-b")
    assert other["record_count"] == 1
    assert other["total_emissions"] == pytest.approx(900)


def test_date_boundaries_are_inclusive(analytics_data):
    result = get_emissions_summary(
        "company-a",
        date(2026, 4, 1),
        date(2026, 4, 30),
    )

    assert result["record_count"] == 2
    assert result["total_emissions"] == pytest.approx(78)


def test_category_filter_normalises_whitespace(analytics_data):
    result = get_emissions_summary(
        "company-a",
        category="electricity",
    )

    assert result["record_count"] == 2
    assert result["total_emissions"] == pytest.approx(60)


def test_combined_date_and_category_filters(analytics_data):
    result = get_emissions_summary(
        "company-a",
        date(2026, 4, 1),
        date(2026, 4, 30),
        "electricity",
    )

    assert result["record_count"] == 1
    assert result["total_emissions"] == pytest.approx(18)


def test_category_totals_match_summary(analytics_data):
    categories = get_emissions_by_category("company-a")
    totals = {
        item["category"]: item["total_emissions"]
        for item in categories
    }

    assert totals == {
        "electricity": 60,
        "transport": 60,
        "Uncategorised": 5,
    }
    assert sum(totals.values()) == pytest.approx(
        get_emissions_summary("company-a")["total_emissions"]
    )


def test_monthly_totals_exclude_undated_records(analytics_data):
    result = get_monthly_emissions("company-a")

    assert result == [
        {"month": "2026-03", "total_emissions": 42},
        {"month": "2026-04", "total_emissions": 78},
    ]


def test_monthly_totals_respect_category_filter(analytics_data):
    result = get_monthly_emissions(
        "company-a",
        category="electricity",
    )

    assert result == [
        {"month": "2026-03", "total_emissions": 42},
        {"month": "2026-04", "total_emissions": 18},
    ]


def test_empty_company_results(analytics_data):
    assert get_emissions_summary("missing-company") == {
        "record_count": 0,
        "total_emissions": 0.0,
    }
    assert get_emissions_by_category("missing-company") == []
    assert get_monthly_emissions("missing-company") == []


def test_queries_do_not_change_records(analytics_data):
    before = [
        record.to_dict()
        for record in db.session.execute(
            db.select(ActivityRecord).order_by(ActivityRecord.id)
        ).scalars()
    ]

    get_emissions_summary("company-a")
    get_emissions_by_category("company-a")
    get_monthly_emissions("company-a")

    db.session.expire_all()

    after = [
        record.to_dict()
        for record in db.session.execute(
            db.select(ActivityRecord).order_by(ActivityRecord.id)
        ).scalars()
    ]

    assert after == before