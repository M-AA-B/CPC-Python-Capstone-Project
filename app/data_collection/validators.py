from datetime import date
from app.data_collection.exceptions import PeriodValidationError, UnitMismatchError


def validate_activity_period(start_date: date, end_date: date) -> bool:
    """Ensures the activity period stays strictly within one calendar month and chronological order."""
    if start_date > end_date:
        raise PeriodValidationError("Start date cannot be after end date.")
    if start_date.year != end_date.year or start_date.month != end_date.month:
        raise PeriodValidationError("Activity period must stay within a single calendar month.")
    return True


def validate_unit_match(activity_unit: str, factor_unit: str) -> bool:
    """Ensures the entry unit matches the emission factor unit."""
    if not activity_unit or not factor_unit:
        raise UnitMismatchError(str(activity_unit), str(factor_unit))
    if activity_unit.strip().lower() != factor_unit.strip().lower():
        raise UnitMismatchError(activity_unit, factor_unit)
    return True
