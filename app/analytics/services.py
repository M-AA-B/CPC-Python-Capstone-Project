"""S2 — Analytics & Dashboard. Owner: Vanessa. Add business logic here."""
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