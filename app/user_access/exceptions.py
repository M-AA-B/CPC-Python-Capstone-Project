"""S3 — AI Assistant & User Access: error hierarchy and error handler (Hometask 4).

Owner: Junaid Ahmad · 7222074

    S3Error                                   base of every S3 error (status_code, to_dict)
    ├── AuthError (ValueError)                400  form/account problem the user can fix
    │   └── InvalidCredentialsError           401  wrong email or password
    ├── AccessDeniedError (PermissionError)   403  wrong role, or another company's data
    ├── ResourceNotFoundError (LookupError)   404  unknown id (or hidden by company isolation)
    │   └── UnknownDepartmentError (ValueError)    department missing or of another company
    ├── InvalidInputError (ValueError)        400  bad parameter or request body
    │   └── InvalidQuestionError              400  empty or too long chat question
    ├── WorkflowError (ValueError)            409  recommendation status step not allowed
    └── AIError                                    anything that goes wrong with the AI coach
        ├── AIUnavailable (RuntimeError)      503  no answer from the AI
        │   ├── AINotConfiguredError          503  OPENAI_API_KEY missing
        │   ├── AIRateLimitError              429  company's daily request limit reached
        │   └── NoEmissionDataError           422  nothing to base advice on yet
        └── InvalidAIOutput (ValueError)      502  AI answer failed validation

The second parent class (ValueError, PermissionError, ...) keeps older
`except ValueError:` blocks working while new code can catch the exact error.

S3ErrorHandler turns any S3Error into a response: JSON for /api/ requests,
otherwise the S3 error page. Messages are always safe to show.
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)


class S3Error(Exception):
    """Base error-handling class for Subsystem 3. The message is safe to show to users."""

    status_code = 400
    default_message = "Something went wrong in the AI assistant or user access."

    def __init__(self, message: str | None = None, *, details: dict | None = None):
        self.message = message or self.default_message
        self.details = dict(details or {})
        super().__init__(self.message)

    def to_dict(self) -> dict:
        payload = {"ok": False, "error": self.message, "error_type": type(self).__name__}
        if self.details:
            payload["details"] = self.details
        return payload


# --- user access ----------------------------------------------------------------

class AuthError(S3Error, ValueError):
    """A problem with a form or account the user can fix; shown on the form."""

    status_code = 400
    default_message = "Please check the form and try again."


class InvalidCredentialsError(AuthError):
    status_code = 401
    default_message = "Wrong email or password."


class AccessDeniedError(S3Error, PermissionError):
    status_code = 403
    default_message = "You do not have permission to do this."


class ResourceNotFoundError(S3Error, LookupError):
    status_code = 404
    default_message = "Not found."

    def __init__(self, resource: str = "Item", item_id: str | None = None):
        super().__init__(f"{resource} not found.", details={"id": item_id} if item_id else None)


class UnknownDepartmentError(ResourceNotFoundError, ValueError):
    """Also a ValueError: forms treat it like any other invalid choice."""

    def __init__(self, department_id: str | None = None):
        super().__init__("Department", department_id)
        self.message = "Unknown department."
        self.args = (self.message,)


# --- AI assistant ---------------------------------------------------------------

class InvalidInputError(S3Error, ValueError):
    status_code = 400
    default_message = "Invalid input."


class InvalidQuestionError(InvalidInputError):
    default_message = "Please enter a question."


class WorkflowError(S3Error, ValueError):
    """A recommendation status change that its workflow does not allow."""

    status_code = 409

    def __init__(self, current: str, requested: str):
        super().__init__(f"A {current} recommendation cannot become {requested}.",
                         details={"current": current, "requested": requested})


class AIError(S3Error):
    status_code = 503
    default_message = "The AI assistant is not available right now. Please try again in a few minutes."


class AIUnavailable(AIError, RuntimeError):
    """The AI could not give an answer."""


class AINotConfiguredError(AIUnavailable):
    default_message = "The AI assistant is not set up yet (missing OPENAI_API_KEY)."


class AIRateLimitError(AIUnavailable):
    status_code = 429
    default_message = "Your company has reached today's AI request limit. Please try again tomorrow."


class NoEmissionDataError(AIUnavailable):
    status_code = 422

    def __init__(self, department: str):
        super().__init__(f"There is no emission data for {department} yet.",
                         details={"department": department})


class InvalidAIOutput(AIError, ValueError):
    """The AI's answer did not pass validation (internal; shown as a generic message)."""

    status_code = 502
    default_message = "The AI returned an unusable answer. Please try again."


# --- handler --------------------------------------------------------------------

class S3ErrorHandler:
    """Central error handling for S3: one place that logs errors and builds responses.

        handler = S3ErrorHandler()
        handler.init_app(app)      # done in register_user_access()
    """

    def __init__(self, app=None, error_template: str = "user_access/error.html"):
        self._error_template = error_template
        self._handled: dict[str, int] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app) -> None:
        app.register_error_handler(S3Error, self.handle)
        app.extensions["s3_error_handler"] = self

    def get_error_template(self) -> str:
        return self._error_template

    def handled_counts(self) -> dict[str, int]:
        """How many errors of each type were handled since start-up (for monitoring)."""
        return dict(self._handled)

    @staticmethod
    def wants_json() -> bool:
        return request.path.startswith("/api/") or request.is_json

    def handle(self, error: S3Error):
        name = type(error).__name__
        self._handled[name] = self._handled.get(name, 0) + 1
        level = logging.ERROR if error.status_code >= 500 else logging.INFO
        logger.log(level, "S3 %s (%s) on %s: %s", name, error.status_code, request.path, error.message)

        if self.wants_json():
            return jsonify(error.to_dict()), error.status_code
        return render_template(self._error_template, error=error), error.status_code
