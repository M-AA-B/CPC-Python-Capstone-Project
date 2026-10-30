"""S2 — Analytics & Dashboard. Owner: Vanessa."""

from sqlalchemy import func, select

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department


def apply_filters(
    statement, start_date=None, end_date=None, category=None
):
    """Filter records without changing stored data."""
    if start_date is not None:
        statement = statement.where(
            ActivityRecord.period_start >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            ActivityRecord.period_start <= end_date
        )

    if category:
        normalised_category = func.coalesce(
            func.nullif(func.trim(ActivityRecord.category), ""),
            "Uncategorised",
        )
        statement = statement.where(
            normalised_category == category
        )

    return statement


def get_emissions_summary(
    company_id, start_date=None, end_date=None, category=None
):
    """Calculate filtered emissions for one company's departments."""
    statement = (
        select(
            func.count(ActivityRecord.id),
            func.coalesce(func.sum(ActivityRecord.co2e_kg), 0.0),
        )
        .select_from(ActivityRecord)
        .join(
            Department,
            ActivityRecord.department_id == Department.id,
        )
        .where(Department.company_id == company_id)
    )

    statement = apply_filters(
        statement, start_date, end_date, category
    )

    record_count, total_emissions = db.session.execute(
        statement
    ).one()

    return {
        "record_count": record_count,
        "total_emissions": float(total_emissions),
    }


def get_emissions_by_category(
    company_id, start_date=None, end_date=None, category_filter=None
):
    """Group one company's filtered emissions by category."""
    category = func.coalesce(
        func.nullif(func.trim(ActivityRecord.category), ""),
        "Uncategorised",
    )

    total = func.sum(ActivityRecord.co2e_kg)

    statement = (
        select(
            category.label("category"),
            total.label("total_emissions"),
        )
        .select_from(ActivityRecord)
        .join(
            Department,
            ActivityRecord.department_id == Department.id,
        )
        .where(Department.company_id == company_id)
        .group_by(category)
        .order_by(total.desc(), category)
    )

    statement = apply_filters(
        statement, start_date, end_date, category_filter
    )

    results = db.session.execute(statement).all()

    return [
        {
            "category": row.category,
            "total_emissions": float(row.total_emissions),
        }
        for row in results
    ]


def get_monthly_emissions(
    company_id, start_date=None, end_date=None, category=None
):
    """Group dated activity records by year and month."""
    year = func.extract("year", ActivityRecord.period_start)
    month = func.extract("month", ActivityRecord.period_start)

    statement = (
        select(
            year.label("year"),
            month.label("month"),
            func.sum(ActivityRecord.co2e_kg).label("total_emissions"),
        )
        .select_from(ActivityRecord)
        .join(
            Department,
            ActivityRecord.department_id == Department.id,
        )
        .where(
            Department.company_id == company_id,
            ActivityRecord.period_start.is_not(None),
        )
        .group_by(year, month)
        .order_by(year, month)
    )

    statement = apply_filters(
        statement, start_date, end_date, category
    )

    results = db.session.execute(statement).all()

    return [
        {
            "month": f"{int(row.year):04d}-{int(row.month):02d}",
            "total_emissions": float(row.total_emissions),
        }
        for row in results
    ]   