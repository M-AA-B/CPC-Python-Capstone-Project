class DataCollectionError(Exception):
    """Base exception class for Subsystem 1 (Data Collection & Calculation)."""
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict:
        return {"error": self.message}


class ValidationError(DataCollectionError, ValueError):
    """Base error for data validation failures (inherits from ValueError for compatibility)."""
    status_code = 400


class UnitMismatchError(ValidationError):
    """Raised when activity unit does not match emission factor unit."""
    def __init__(self, activity_unit: str, factor_unit: str):
        super().__init__(f"Unit mismatch: expected {factor_unit}, got {activity_unit}.", status_code=400)


class PeriodValidationError(ValidationError):
    """Raised when date range violates calendar month boundaries or chronological order."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class RecordOwnershipError(DataCollectionError, PermissionError):
    """Raised when a user attempts to modify or delete a record they do not own."""
    status_code = 403

    def __init__(self, message: str = "You can only delete your own records."):
        super().__init__(message, status_code=403)


class ResourceNotFoundError(DataCollectionError, ValueError):
    """Raised when a requested resource (record, factor, department) is not found."""
    status_code = 404

    def __init__(self, resource_name: str, resource_id: str | int):
        super().__init__(f"{resource_name} with ID '{resource_id}' not found.", status_code=404)


class CompanyIsolationError(ValidationError):
    """Raised when a department does not belong to the specified company."""
    status_code = 400

    def __init__(self, dept_id: str, comp_id: str):
        super().__init__(f"Department '{dept_id}' does not belong to company '{comp_id}'.", status_code=400)

