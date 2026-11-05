"""S3 JSON Web API (Hometask 3) — Owner: Junaid Ahmad · 7222074.

All endpoints live under /api/s3 and answer in JSON, including errors:
S3 errors (app/user_access/exceptions.py) are turned into JSON by S3ErrorHandler.
Login uses the normal session cookie; every request after login is checked
for role and company, and every POST/PATCH needs the X-CSRFToken header
(the token comes back from /login and /me).

    POST  /api/s3/login                    {"email", "password"}
    POST  /api/s3/logout
    GET   /api/s3/me
    GET   /api/s3/users?role=              admin only
    GET   /api/s3/recommendations?status=&department_id=
    GET   /api/s3/recommendations/<id>
    PATCH /api/s3/recommendations/<id>     {"status": "accepted" | "rejected" | "done"}   admin, manager
    GET   /api/s3/chat/history?limit=
    POST  /api/s3/chat                     {"question"}
    GET   /api/s3/ai-usage                 admin only
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app.ai_assistant.repositories import (
    AIRequestRepository,
    ChatMessageRepository,
    RecommendationRepository,
)
from app.ai_assistant.services import AIAssistant, _setting
from app.models.user import Role
from app.user_access.exceptions import InvalidCredentialsError, InvalidInputError, ResourceNotFoundError
from app.user_access.permissions import check_csrf, csrf_token, require_role
from app.user_access.repositories import UserRepository
from app.user_access.services import AuthService

api_bp = Blueprint("s3_api", __name__, url_prefix="/api/s3")

PUBLIC_ENDPOINTS = {"s3_api.login"}
MAX_HISTORY = 100


def _error(status: int, message: str):
    return jsonify(ok=False, error=message), status


def _json_body() -> dict:
    """The request's JSON object; anything else is a 400."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise InvalidInputError("Send a JSON object with Content-Type: application/json.")
    return body


def _http_error(error: HTTPException):
    """abort(403), abort(404) and check_csrf()'s 400 become JSON instead of HTML pages."""
    return _error(error.code, error.description)


# Registered per status code: the app's own 403 page handler would otherwise win.
api_bp.register_error_handler(HTTPException, _http_error)
for _code in (400, 401, 403, 404, 405):
    api_bp.register_error_handler(_code, _http_error)


@api_bp.before_request
def _require_login():
    if request.endpoint not in PUBLIC_ENDPOINTS and not current_user.is_authenticated:
        return _error(401, "Please log in first (POST /api/s3/login).")
    return None


def _user_payload(user) -> dict:
    return {"ok": True, "user": user.to_dict(), "csrf_token": csrf_token()}


# --- user access -------------------------------------------------------------

@api_bp.post("/login")
def login():
    body = _json_body()
    user = AuthService.login(str(body.get("email", "")), str(body.get("password", "")))
    if user is None:
        raise InvalidCredentialsError()
    return jsonify(_user_payload(user))


@api_bp.post("/logout")
def logout():
    check_csrf()
    AuthService.logout()
    return jsonify(ok=True)


@api_bp.get("/me")
def me():
    return jsonify(_user_payload(current_user))


@api_bp.get("/users")
@require_role(Role.ADMIN)
def users():
    items = UserRepository(current_user.company_id).list(role=request.args.get("role") or None)
    return jsonify(ok=True, users=[u.to_dict() for u in items])


# --- recommendations ---------------------------------------------------------

@api_bp.get("/recommendations")
def list_recommendations():
    repo = RecommendationRepository(current_user.company_id)
    items = repo.list_for(current_user, status=request.args.get("status") or None,
                          department_id=request.args.get("department_id") or None)
    return jsonify(ok=True, recommendations=[r.to_dict() for r in items])


@api_bp.get("/recommendations/<recommendation_id>")
def get_recommendation(recommendation_id: str):
    item = RecommendationRepository(current_user.company_id).get_for(current_user, recommendation_id)
    if item is None:
        raise ResourceNotFoundError("Recommendation", recommendation_id)
    return jsonify(ok=True, recommendation=item.to_dict())


@api_bp.patch("/recommendations/<recommendation_id>")
@require_role(Role.ADMIN, Role.MANAGER)
def update_recommendation(recommendation_id: str):
    check_csrf()
    body = _json_body()
    repo = RecommendationRepository(current_user.company_id)
    item = repo.get_for(current_user, recommendation_id)
    if item is None:
        raise ResourceNotFoundError("Recommendation", recommendation_id)
    repo.change_status(item, str(body.get("status", "")))  # WorkflowError -> 409
    return jsonify(ok=True, recommendation=item.to_dict())


# --- chat ----------------------------------------------------------------------

@api_bp.get("/chat/history")
def chat_history():
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        raise InvalidInputError("limit must be a whole number.") from None
    limit = max(1, min(limit, MAX_HISTORY))
    messages = ChatMessageRepository(current_user.company_id).history(current_user.id, limit)
    return jsonify(ok=True, messages=[m.to_dict() for m in messages])


@api_bp.post("/chat")
def chat():
    check_csrf()
    question = str(_json_body().get("question", ""))
    # InvalidQuestionError -> 400, AIRateLimitError -> 429, AIUnavailable -> 503
    reply = AIAssistant.from_app().ask(current_user, question)
    return jsonify(ok=True, message=reply.to_dict())


@api_bp.get("/ai-usage")
@require_role(Role.ADMIN)
def ai_usage():
    repo = AIRequestRepository(current_user.company_id)
    return jsonify(ok=True, requests_today=repo.count_today(), tokens_today=repo.tokens_today(),
                   daily_limit=int(_setting("AI_DAILY_REQUEST_LIMIT")))
