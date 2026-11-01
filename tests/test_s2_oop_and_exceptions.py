"""Tests for Hometask 1 OOP encapsulation and Hometask 4 custom exceptions in Subsystem 2."""
from datetime import date

import pytest

from app.analytics.exceptions import (
    AnalyticsAccessError,
    AnalyticsError,
    InvalidFilterError,
    TargetValidationError,
)
from app.analytics.report import DashboardReport
from app.analytics.routes import handle_analytics_error
from app.analytics.scoring import CarbonScorer
from app.analytics.services import AnalyticsService
from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.company import Company
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.target import ReductionTarget, Target
from app.models.user import User


def test_s2_exception_hierarchy():
    assert issubclass(InvalidFilterError, (AnalyticsError, ValueError))
    assert issubclass(TargetValidationError, (AnalyticsError, ValueError))
    assert issubclass(AnalyticsAccessError, (AnalyticsError, PermissionError))

    err = InvalidFilterError("Bad date filter")
    assert err.status_code == 400
    assert err.to_dict() == {"error": "Bad date filter"}

    forbidden = AnalyticsAccessError()
    assert forbidden.status_code == 403


def test_s2_blueprint_error_handler(client):
    with client.application.test_request_context("/analytics/"):
        response, status = handle_analytics_error(TargetValidationError("Custom S2 error"))
        assert status == 400
        assert response.get_json() == {"error": "Custom S2 error"}


def test_reduction_target_oop_methods():
    target = ReductionTarget(
        company_id="comp-1",
        baseline_start=date(2025, 1, 1),
        baseline_end=date(2025, 1, 31),
        period_start=date(2025, 3, 1),
        period_end=date(2025, 3, 31),
        reduction_percent=15.0,
    )
    assert isinstance(target, Target)
    assert target.get_target() == 15.0
    assert target.is_data_complete() is False

    target.set_target(25.5)
    assert target.get_target() == 25.5

    target.set_data_complete(True)
    assert target.is_data_complete() is True

    target.configure_periods(
        date(2025, 2, 1),
        date(2025, 2, 28),
        date(2025, 4, 1),
        date(2025, 4, 30),
    )
    assert target.baseline_start == date(2025, 2, 1)
    assert target.period_end == date(2025, 4, 30)

    with pytest.raises(TargetValidationError):
        target.set_target(0)

    with pytest.raises(TargetValidationError):
        target.configure_periods(
            date(2025, 5, 1),
            date(2025, 4, 1),
            date(2025, 6, 1),
            date(2025, 6, 30),
        )


def test_analytics_service_oop_and_encapsulation(client):
    with client.application.app_context():
        comp = Company(id="oop-comp", name="OOP Corp")
        dept = Department(id="oop-dept", company_id="oop-comp", name="R&D")
        user = User(id="oop-user", company_id="oop-comp", email="oop@corp.de")
        factor = EmissionFactor(
            id=77, category="electricity", kg_co2e_per_unit=0.5, unit="kWh", scope=2, valid_year=2026
        )
        db.session.add_all([comp, dept, user, factor])
        db.session.flush()
        db.session.add(
            ActivityRecord(
                id="oop-rec-1",
                company_id="oop-comp",
                department_id="oop-dept",
                factor_id=77,
                period_start=date(2026, 3, 10),
                period_end=date(2026, 3, 10),
                category="electricity",
                quantity=200.0,
                unit="kWh",
                co2e_kg=100.0,
                scope=2,
                created_by="oop-user",
            )
        )
        db.session.commit()

        service = AnalyticsService(company_id="oop-comp")
        assert service.company_id == "oop-comp"
        assert service.calculate_total() == pytest.approx(100.0)
        assert service.group_by_category() == [{"category": "electricity", "total_emissions": 100.0}]

        service.configure_filters(
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            category=" electricity ",
        )
        assert service.category == "electricity"
        assert service.calculate_total() == pytest.approx(100.0)

        with pytest.raises(InvalidFilterError):
            service.configure_filters(
                start_date=date(2026, 4, 30),
                end_date=date(2026, 4, 1),
            )

        service.reset_filters()
        assert service.start_date is None and service.end_date is None and service.category is None

        score = service.calculate_score(100.0, 90.0, 20.0, data_complete=True)
        assert score["score"] == pytest.approx(50.0)


def test_dashboard_report_oop():
    report = DashboardReport(
        summary={"record_count": 2, "total_emissions": 150.0},
        category_totals=[{"category": "electricity", "total_emissions": 150.0}],
        monthly_totals=[
            {"month": "2026-02", "total_emissions": 100.0},
            {"month": "2026-03", "total_emissions": 50.0},
        ],
    )
    assert report.filename == "emissions-analytics.csv"
    report.filename = "custom-report.csv"
    assert report.filename == "custom-report.csv"

    with pytest.raises(AnalyticsError):
        report.filename = "not-a-csv.txt"

    charts = report.generate_charts()
    assert charts["monthly_chart"] is not None
    assert charts["category_chart"] is not None

    info = report.display_summary()
    assert info["highest_category"] == "electricity"
    assert info["comparison"]["available"] is True

    csv_text = report.export_CSV()
    assert "Total emissions,150.00,2" in csv_text


def test_carbon_scorer_oop():
    scorer = CarbonScorer(min_score=0.0, max_score=100.0)
    assert scorer.min_score == 0.0 and scorer.max_score == 100.0
    scorer.max_score = 120.0
    assert scorer.max_score == 120.0

    with pytest.raises(AnalyticsError):
        scorer.min_score = 150.0

    scorer.reset_defaults()
    assert scorer.max_score == 100.0

