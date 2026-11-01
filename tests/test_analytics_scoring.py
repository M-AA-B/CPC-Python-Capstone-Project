from datetime import date

import pytest

from app.analytics.scoring import calculate_target_progress
from app.analytics.services import compare_latest_months
from app.analytics.targets import validate_target_form


@pytest.mark.parametrize(
    "current, expected_score, target_met",
    [
        (90, 50, False),
        (80, 100, True),
        (70, 100, True),
        (100, 0, False),
        (120, 0, False),
    ],
)
def test_target_progress(current, expected_score, target_met):
    result = calculate_target_progress(
        100, current, 20, data_complete=True
    )

    assert result["available"] is True
    assert result["score"] == pytest.approx(expected_score)
    assert result["target_met"] is target_met


@pytest.mark.parametrize(
    "baseline, current, reduction",
    [
        (0, 80, 20),
        (100, -1, 20),
        (100, 80, 0),
        (100, 80, 101),
        (float("nan"), 80, 20),
        (100, float("inf"), 20),
        (100, 80, "invalid"),
    ],
)
def test_invalid_scoring_values_are_unavailable(
    baseline, current, reduction
):
    result = calculate_target_progress(
        baseline, current, reduction, data_complete=True
    )

    assert result["available"] is False
    assert result["score"] is None


def test_unconfirmed_completeness_has_no_score():
    result = calculate_target_progress(100, 80, 20)

    assert result["available"] is False
    assert result["score"] is None


def test_monthly_comparison_across_year_boundary():
    result = compare_latest_months([
        {"month": "2025-12", "total_emissions": 100},
        {"month": "2026-01", "total_emissions": 80},
    ])

    assert result["available"] is True
    assert result["difference"] == pytest.approx(-20)
    assert result["percentage"] == pytest.approx(-20)


def test_monthly_comparison_with_zero_previous_total():
    result = compare_latest_months([
        {"month": "2026-01", "total_emissions": 0},
        {"month": "2026-02", "total_emissions": 80},
    ])

    assert result["available"] is True
    assert result["difference"] == pytest.approx(80)
    assert result["percentage"] is None


@pytest.mark.parametrize(
    "months",
    [
        [],
        [{"month": "2026-03", "total_emissions": 42}],
        [
            {"month": "2026-03", "total_emissions": 42},
            {"month": "2026-10", "total_emissions": 420},
        ],
    ],
)
def test_missing_or_nonconsecutive_months_are_unavailable(months):
    assert compare_latest_months(months)["available"] is False


def valid_target_form():
    return {
        "baseline_start": "2020-01-01",
        "baseline_end": "2020-01-31",
        "period_start": "2020-03-01",
        "period_end": "2020-03-31",
        "reduction_percent": "20",
        "data_complete": "on",
    }


def test_valid_target_form():
    result = validate_target_form(valid_target_form())

    assert result["baseline_start"] == date(2020, 1, 1)
    assert result["reduction_percent"] == 20
    assert result["data_complete"] is True


@pytest.mark.parametrize(
    "changes",
    [
        {"baseline_start": "invalid"},
        {"baseline_start": "2020-02-01"},
        {"period_start": "2020-01-01"},
        {"period_start": "2020-03-02"},
        {"period_end": "2020-03-30"},
        {"period_end": "2020-04-30"},
        {"reduction_percent": "0"},
        {"reduction_percent": "nan"},
        {
            "period_start": "2999-03-01",
            "period_end": "2999-03-31",
        },
    ],
)
def test_invalid_target_form_is_rejected(changes):
    form = valid_target_form()
    form.update(changes)

    with pytest.raises(ValueError):
        validate_target_form(form)