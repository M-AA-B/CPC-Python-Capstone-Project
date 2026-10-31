from datetime import date

from sqlalchemy import select

from app.extensions import db
from app.models.target import Target
from .scoring import calculate_target_progress
from .services import get_emissions_summary


def get_latest_target(company_id):
    statement = (
        select(Target)
        .where(Target.company_id == company_id)
        .order_by(Target.created_at.desc(), Target.id.desc())
        .limit(1)
    )
    return db.session.execute(statement).scalar_one_or_none()


def get_target_progress(target):
    if target is None:
        return {
            "available": False,
            "score": None,
            "reason": "No reduction target has been set.",
        }

    if target.period_end >= date.today():
        return {
            "available": False,
            "score": None,
            "reason": "The target period must finish before scoring.",
        }

    baseline = get_emissions_summary(
        target.company_id,
        target.baseline_start,
        target.baseline_end,
    )
    current = get_emissions_summary(
        target.company_id,
        target.period_start,
        target.period_end,
    )

    if baseline["record_count"] == 0 or current["record_count"] == 0:
        return {
            "available": False,
            "score": None,
            "reason": "Both periods need activity records before scoring.",
        }

    return calculate_target_progress(
        baseline["total_emissions"],
        current["total_emissions"],
        target.reduction_percent,
        data_complete=target.data_complete,
    )


def validate_target_form(form):
    from calendar import monthrange
    from math import isfinite

    date_fields = (
        "baseline_start",
        "baseline_end",
        "period_start",
        "period_end",
    )

    try:
        values = {
            field: date.fromisoformat(form.get(field, "").strip())
            for field in date_fields
        }
    except ValueError:
        raise ValueError("Enter valid dates for both reporting periods.")

    try:
        reduction = float(form.get("reduction_percent", ""))
    except (TypeError, ValueError):
        raise ValueError("Enter a valid reduction percentage.")

    if not isfinite(reduction) or not 0 < reduction <= 100:
        raise ValueError("Reduction must be greater than 0% and at most 100%.")

    baseline_start = values["baseline_start"]
    baseline_end = values["baseline_end"]
    period_start = values["period_start"]
    period_end = values["period_end"]

    if baseline_start > baseline_end or period_start > period_end:
        raise ValueError("Each start date must be on or before its end date.")

    if baseline_end >= period_start:
        raise ValueError("The baseline must finish before the target period.")

    for start, end in (
        (baseline_start, baseline_end),
        (period_start, period_end),
    ):
        last_day = monthrange(end.year, end.month)[1]
        if start.day != 1 or end.day != last_day:
            raise ValueError("Select complete calendar months for both periods.")

    baseline_months = (
        (baseline_end.year - baseline_start.year) * 12
        + baseline_end.month - baseline_start.month + 1
    )
    target_months = (
        (period_end.year - period_start.year) * 12
        + period_end.month - period_start.month + 1
    )

    if baseline_months != target_months:
        raise ValueError("Both periods must contain the same number of months.")

    data_complete = form.get("data_complete") == "on"

    if data_complete and period_end >= date.today():
        raise ValueError(
            "Completeness can only be confirmed after the target period ends."
        )

    values["reduction_percent"] = reduction
    values["data_complete"] = data_complete
    return values