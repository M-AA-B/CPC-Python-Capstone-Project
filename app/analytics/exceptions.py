"""S2 — Analytics & Dashboard custom domain exceptions (Hometask 4)."""


class AnalyticsError(Exception):
    """Base error-handling class for Subsystem 2 (Analytics & Dashboard)."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> dict:
        return {"error": self.message}


class InvalidFilterError(AnalyticsError, ValueError):
    """Raised when dashboard date or category filters are invalid."""

    status_code = 400


class TargetValidationError(AnalyticsError, ValueError):
    """Raised when carbon reduction target parameters violate reporting rules."""

    status_code = 400


class AnalyticsAccessError(AnalyticsError, PermissionError):
    """Raised when analytics or target modification is not permitted."""

    status_code = 403

    def __init__(self, message: str = "Access to analytics target configuration is forbidden."):
        super().__init__(message, status_code=403)

