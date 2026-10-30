"""S2 — Analytics & Dashboard. Owner: Vanessa. Add business logic here."""
from sqlalchemy import func, select

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department


"""S2 — Analytics & Dashboard. Owner: Vanessa."""

from sqlalchemy import func, select

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department


def get_emissions_summary(company_id):
    """Calculate total emissions for one company's departments."""
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

    record_count, total_emissions = db.session.execute(statement).one()

    return {
        "record_count": record_count,
        "total_emissions": float(total_emissions),
    }


def get_emissions_by_category(company_id):
    """Group one company's saved emissions by category."""
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

    results = db.session.execute(statement).all()

    return [
        {
            "category": row.category,
            "total_emissions": float(row.total_emissions),
        }
        for row in results
    ]