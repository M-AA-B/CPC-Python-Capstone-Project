"""S3 - AI chat, reduction tips and monthly summary pages (/assistant/...)."""
from datetime import date

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.ai_assistant.services import MAX_QUESTION_LENGTH, AIAssistant, AIUnavailable
from app.extensions import db
from app.models.recommendation import Recommendation, Status
from app.models.user import Role
from app.user_access.permissions import check_csrf, require_role
from app.user_access.services import AuthService

from . import bp

STATUS_ACTIONS = {
    "accept": Recommendation.accept,
    "reject": Recommendation.reject,
    "done": Recommendation.mark_done,
}


# --- chat ------------------------------------------------------------------

@bp.get("/")
def index():
    """The chat for logged-in users, a short introduction for guests."""
    if not current_user.is_authenticated:
        return render_template("ai_assistant/index.html")
    return render_template("ai_assistant/chat.html", history=AIAssistant.history(current_user.id, 50),
                           max_length=MAX_QUESTION_LENGTH)


@bp.post("/ask")
@require_role()
def ask():
    check_csrf()
    question = str((request.get_json(silent=True) or {}).get("question", ""))
    try:
        reply = AIAssistant.from_app().ask(current_user, question)
    except ValueError as error:
        return jsonify(ok=False, error=str(error)), 400
    except AIUnavailable as error:
        return jsonify(ok=False, error=str(error)), 503
    return jsonify(ok=True, message=reply.to_dict())


# --- reduction tips --------------------------------------------------------

@bp.get("/recommendations")
@require_role()
def recommendations():
    query = db.select(Recommendation).filter_by(company_id=current_user.company_id)
    if current_user.has_role(Role.EMPLOYEE):
        query = query.filter_by(department_id=current_user.department_id)

    status = request.args.get("status")
    if status in Status.ALL:
        query = query.filter_by(status=status)

    items = db.session.scalars(query.order_by(Recommendation.created_at.desc())).all()
    return render_template(
        "ai_assistant/recommendations.html",
        recommendations=items,
        departments=AuthService.company_departments(current_user.company_id),
        statuses=Status.ALL,
        current_status=status,
        can_edit=current_user.has_role(Role.ADMIN, Role.MANAGER),
    )


@bp.post("/recommendations/generate")
@require_role(Role.ADMIN, Role.MANAGER)
def generate_recommendations():
    check_csrf()
    try:
        created = AIAssistant.from_app().recommend(
            current_user.company_id, request.form.get("department_id", ""), current_user.id
        )
    except ValueError:
        flash("Please choose a department.", "danger")
    except AIUnavailable as error:
        flash(str(error), "danger")
    else:
        flash(f"{len(created)} new recommendations added.", "success")
    return redirect(url_for("assistant.recommendations"))


@bp.post("/recommendations/<recommendation_id>/<action>")
@require_role(Role.ADMIN, Role.MANAGER)
def update_recommendation(recommendation_id: str, action: str):
    check_csrf()
    recommendation = db.session.get(Recommendation, recommendation_id)
    if recommendation is None or recommendation.company_id != current_user.company_id:
        abort(404)
    if action not in STATUS_ACTIONS:
        abort(400)
    STATUS_ACTIONS[action](recommendation)
    db.session.commit()
    return redirect(url_for("assistant.recommendations", status=request.args.get("status")))


# --- monthly summary -------------------------------------------------------

@bp.route("/summary", methods=["GET", "POST"])
@require_role()
def summary():
    month_value = request.values.get("month") or date.today().strftime("%Y-%m")
    try:
        month = date.fromisoformat(f"{month_value}-01")
    except ValueError:
        month = date.today().replace(day=1)
        month_value = month.strftime("%Y-%m")

    text = None
    if request.method == "POST":
        check_csrf()
        try:
            text = AIAssistant.from_app().summarise(current_user.company_id, month, current_user.id)
        except AIUnavailable as error:
            flash(str(error), "danger")
    return render_template("ai_assistant/summary.html", month=month, month_value=month_value, text=text)
