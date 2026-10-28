from datetime import datetime, timezone
from app.data_collection.calculations import EmissionCalculator, calculate_emissions, assign_scope as _assign_scope
from app.data_collection.exceptions import (
    CompanyIsolationError,
    RecordOwnershipError,
    ResourceNotFoundError,
    ValidationError,
)
from app.data_collection.validators import validate_activity_period, validate_unit_match
from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department
from app.models.emission_factor import EmissionFactor


def create_activity_record(data: dict, user_id: str | None = None) -> ActivityRecord:
    """Creates a new activity record with full validation and transactional integrity."""
    user_id = user_id or data.get('user_id') or data.get('current_user_id')
    if not user_id:
        raise ValidationError("User ID is required.")

    # 1. Resolve and fetch emission factor
    factor_id = data.get('emission_factor_id') or data.get('factor_id')
    if factor_id is None:
        raise ValidationError("Emission factor ID is required.")
    try:
        factor_id = int(factor_id)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid emission factor ID: {factor_id}")

    factor = db.session.get(EmissionFactor, factor_id)
    if not factor:
        raise ResourceNotFoundError("Emission factor", factor_id)

    # 2. Resolve activity quantity / value
    quantity = data.get('activity_value')
    if quantity is None:
        quantity = data.get('quantity')
    if quantity is None:
        raise ValidationError("Activity value / quantity is required.")
    try:
        quantity = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity: {quantity}")

    # 3. Unit validation
    unit = data.get('unit') or factor.unit
    factor_unit = data.get('factor_unit') or factor.unit
    validate_unit_match(unit, factor_unit)

    # 4. Emission calculation
    factor_kg_co2e = data.get('factor_kg_co2e')
    if factor_kg_co2e is None:
        factor_kg_co2e = factor.kg_co2e_per_unit
    co2e = calculate_emissions(quantity, float(factor_kg_co2e))
    # 5. Period / Date resolution & validation
    period_start = data.get('period_start')
    period_end = data.get('period_end')
    if not period_start and not period_end and data.get('date'):
        period_start = data.get('date')
        period_end = data.get('date')

    if isinstance(period_start, str):
        period_start = datetime.strptime(period_start, '%Y-%m-%d').date()
    elif period_start is None:
        period_start = datetime.now(timezone.utc).date()

    if isinstance(period_end, str):
        period_end = datetime.strptime(period_end, '%Y-%m-%d').date()
    elif period_end is None:
        period_end = period_start

    validate_activity_period(period_start, period_end)

    # 6. Department and company resolution with company isolation check
    department_id = data.get('department_id')
    company_id = data.get('company_id')

    if department_id:
        dept = db.session.get(Department, department_id)
        if dept:
            if company_id and dept.company_id and dept.company_id != company_id:
                raise CompanyIsolationError(department_id, company_id)
            if not company_id:
                company_id = dept.company_id

    # 7. Category & scope resolution
    category = data.get('category') or factor.category
    scope = data.get('scope')
    if scope is not None:
        scope = int(scope)
    elif factor.scope is not None:
        scope = factor.scope
    else:
        scope = _assign_scope(category)

    # 8. Create and persist record
    record = ActivityRecord(
        company_id=company_id,
        department_id=department_id,
        factor_id=factor_id,
        period_start=period_start,
        period_end=period_end,
        category=category,
        quantity=quantity,
        unit=unit,
        co2e_kg=co2e,
        scope=scope,
        created_by=user_id
    )

    db.session.add(record)
    db.session.commit()
    return record


def get_activity_records(filters: dict | None = None) -> list[ActivityRecord]:
    """Retrieves activity records filtered by company, department, category, or date range (S1 FR8)."""
    query = ActivityRecord.query

    if filters:
        if filters.get('company_id'):
            query = query.filter(ActivityRecord.company_id == filters['company_id'])
        if filters.get('department_id'):
            query = query.filter(ActivityRecord.department_id == filters['department_id'])
        if filters.get('category'):
            query = query.filter(ActivityRecord.category == filters['category'])
        if filters.get('scope'):
            query = query.filter(ActivityRecord.scope == int(filters['scope']))
        if filters.get('created_by'):
            query = query.filter(ActivityRecord.created_by == filters['created_by'])
        if filters.get('start_date'):
            query = query.filter(ActivityRecord.period_start >= filters['start_date'])
        if filters.get('end_date'):
            query = query.filter(ActivityRecord.period_end <= filters['end_date'])

        # Sorting
        sort_by = filters.get('sort', 'created_at')
        order = filters.get('order', 'desc')
        if hasattr(ActivityRecord, sort_by):
            col = getattr(ActivityRecord, sort_by)
            query = query.order_by(col.desc() if order == 'desc' else col.asc())
    else:
        query = query.order_by(ActivityRecord.created_at.desc())

    return query.all()


def update_activity_record(record_id: str, data: dict, user_id: str) -> ActivityRecord:
    """Updates an existing activity record with ownership enforcement (S1 FR9)."""
    record = db.session.get(ActivityRecord, record_id)
    if not record:
        raise ResourceNotFoundError("ActivityRecord", record_id)
    if record.created_by != user_id:
        raise RecordOwnershipError("You can only edit your own records.")

    # Update quantity and recalculate emissions if provided
    if 'quantity' in data or 'activity_value' in data:
        new_qty = float(data.get('quantity') or data.get('activity_value'))
        record.quantity = new_qty
        factor = db.session.get(EmissionFactor, record.factor_id)
        if factor:
            record.co2e_kg = calculate_emissions(new_qty, factor.kg_co2e_per_unit)

    # Update unit if provided and valid
    if 'unit' in data:
        factor = db.session.get(EmissionFactor, record.factor_id)
        if factor:
            validate_unit_match(data['unit'], factor.unit)
        record.unit = data['unit']

    # Update dates if provided
    if 'date' in data:
        d = datetime.strptime(data['date'], '%Y-%m-%d').date() if isinstance(data['date'], str) else data['date']
        record.period_start = d
        record.period_end = d

    db.session.commit()
    return record


def delete_activity_record(record_id: str, user_id: str) -> bool:
    """Deletes an activity record with ownership enforcement (S1 FR9)."""
    record = db.session.get(ActivityRecord, record_id)
    if not record:
        raise ResourceNotFoundError("ActivityRecord", record_id)
    if record.created_by != user_id:
        raise RecordOwnershipError("You can only delete your own records.")

    db.session.delete(record)
    db.session.commit()
    return True
