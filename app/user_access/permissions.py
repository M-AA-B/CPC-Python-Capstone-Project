"""S3 - page protection used by every subsystem. Owner: Junaid.

Roles - only logged-in users with one of the roles may open the page:

    from flask_login import current_user
    from app.models.user import Role
    from app.user_access.permissions import require_role

    @bp.get("/records")
    @require_role(Role.ADMIN, Role.MANAGER)   # no arguments = any logged-in user
    def records():
        company_id = current_user.company_id   # always filter by the user's company

CSRF - a POST form includes the token, the view checks it:

    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    check_csrf()   # first line of the POST branch; answers 400 if the token is wrong
"""
import secrets
from functools import wraps

from flask import abort, request, session
from flask_login import current_user, login_required

CSRF_SESSION_KEY = "csrf_token"


def require_role(*roles: str):
    """Login required; with roles given, the user also needs one of them (else 403)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if roles and not current_user.has_role(*roles):
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def csrf_token() -> str:
    """One random token per browser session, available in templates as csrf_token()."""
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def check_csrf() -> None:
    """Stop the request (400) unless the form (or the X-CSRFToken header for fetch/JSON
    requests) sent the session's token."""
    expected = session.get(CSRF_SESSION_KEY)
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400, "Invalid or missing form token. Please reload the page and try again.")
