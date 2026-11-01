"""S3 - the company figures the AI assistant is allowed to see.

Only aggregated totals (kg CO2e per category, department, scope and month) leave this
module - never single activity records, user names, emails or IDs.

S2 (Vanessa) owns the analytics. When app/analytics/services.py provides
get_emissions_summary / get_emissions_by_category / get_monthly_emissions /
compare_latest_months, those are used. Until then (and for the breakdowns S2 does not
offer: by department and by scope) the same totals are summed here from the stored
co2e_kg values, filtered exactly like S2 does (by Department.company_id and period_start).
"""
from datetime import date

from sqlalchemy import extract, func, select

from app.analytics import services as analytics
from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department

CATEGORY = func.coalesce(func.nullif(func.trim(ActivityRecord.category), ""), "Uncategorised")


def _from_s2(name: str):
    """S2's function `name`, or None while it does not exist yet."""
    return getattr(analytics, name, None)


def _query(columns, company_id: str, start: date | None, end: date | None):
    statement = (
        select(*columns)
        .select_from(ActivityRecord)
        .join(Department, ActivityRecord.department_id == Department.id)
        .where(Department.company_id == company_id)
    )
    if start is not None:
        statement = statement.where(ActivityRecord.period_start >= start)
    if end is not None:
        statement = statement.where(ActivityRecord.period_start <= end)
    return statement


def _grouped(key, company_id, start, end) -> dict:
    total = func.sum(ActivityRecord.co2e_kg)
    statement = _query([key.label("key"), total.label("kg")], company_id, start, end)
    rows = db.session.execute(statement.group_by(key).order_by(total.desc())).all()
    return {row.key: round(float(row.kg), 1) for row in rows}


def total_kg(company_id, start=None, end=None) -> float:
    s2 = _from_s2("get_emissions_summary")
    if s2:
        return round(s2(company_id, start, end)["total_emissions"], 1)
    statement = _query([func.coalesce(func.sum(ActivityRecord.co2e_kg), 0.0)], company_id, start, end)
    return round(float(db.session.scalar(statement)), 1)


def by_category(company_id, start=None, end=None) -> dict[str, float]:
    s2 = _from_s2("get_emissions_by_category")
    if s2:
        return {row["category"]: round(row["total_emissions"], 1) for row in s2(company_id, start, end)}
    return _grouped(CATEGORY, company_id, start, end)


def by_month(company_id, start=None, end=None) -> dict[str, float]:
    """{"2026-03": kg, ...}, oldest month first."""
    s2 = _from_s2("get_monthly_emissions")
    if s2:
        return {row["month"]: round(row["total_emissions"], 1) for row in s2(company_id, start, end)}
    year = extract("year", ActivityRecord.period_start)
    month = extract("month", ActivityRecord.period_start)
    statement = _query([year.label("y"), month.label("m"), func.sum(ActivityRecord.co2e_kg).label("kg")],
                       company_id, start, end)
    statement = statement.where(ActivityRecord.period_start.is_not(None)).group_by(year, month).order_by(year, month)
    return {f"{int(r.y):04d}-{int(r.m):02d}": round(float(r.kg), 1) for r in db.session.execute(statement)}


def by_department(company_id, start=None, end=None) -> dict[str, float]:
    return _grouped(Department.name, company_id, start, end)


def by_scope(company_id, start=None, end=None) -> dict[str, float]:
    scopes = _grouped(ActivityRecord.scope, company_id, start, end)
    return {f"Scope {scope}" if scope else "Unknown scope": kg for scope, kg in scopes.items()}


def latest_month_change(monthly: dict[str, float]) -> float | None:
    """% change of the latest month against the month before (None if not comparable)."""
    rows = [{"month": m, "total_emissions": kg} for m, kg in monthly.items()]
    s2 = _from_s2("compare_latest_months")
    if s2:
        result = s2(rows)
        return round(result["percentage"], 1) if result.get("available") and result["percentage"] is not None else None
    if len(rows) < 2:
        return None
    (prev_month, prev_kg), (last_month, last_kg) = list(monthly.items())[-2:]
    py, pm = map(int, prev_month.split("-"))
    ly, lm = map(int, last_month.split("-"))
    if (ly * 12 + lm) - (py * 12 + pm) != 1 or prev_kg == 0:
        return None
    return round((last_kg - prev_kg) / prev_kg * 100, 1)


def emission_summary(company_id: str, start: date | None = None, end: date | None = None) -> dict:
    """Everything the AI gets to see about one company, for activities starting in [start, end]."""
    monthly = by_month(company_id, start, end)
    return {
        "period_start": start,
        "period_end": end,
        "total_kg": total_kg(company_id, start, end),
        "by_department": by_department(company_id, start, end),
        "by_category": by_category(company_id, start, end),
        "by_scope": by_scope(company_id, start, end),
        "by_month": monthly,
        "latest_month_change_pct": latest_month_change(monthly),
    }
