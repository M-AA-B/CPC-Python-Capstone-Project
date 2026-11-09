import secrets
from datetime import date

from flask import (
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from flask_login import current_user
from app.models.user import Role
from app.user_access.permissions import require_role

from app.extensions import db
from app.models.company import Company
from app.models.target import Target

from . import bp
from .exceptions import (
    AnalyticsError,
    InvalidFilterError,
    TargetValidationError,
)
from .report import DashboardReport
from .services import (
    AnalyticsService,
    get_emissions_by_category,
)
from .targets import (
    get_latest_target,
    get_target_progress,
    validate_target_form,
)


@bp.errorhandler(AnalyticsError)
def handle_analytics_error(error: AnalyticsError):
    """Centralized error handler for Subsystem 2 custom exceptions (Hometask 4)."""
    return jsonify(error.to_dict()), error.status_code


@bp.get("/")
@require_role()
def index():
    company = None
    summary = None
    category_totals = []
    categories = []
    monthly_chart = None
    category_chart = None
    comparison = None
    error = None

    filters = {
        "start_date": request.args.get("start_date", "").strip(),
        "end_date": request.args.get("end_date", "").strip(),
        "category": request.args.get("category", "").strip(),
    }

    if not current_user.company_id:
        abort(403)

    company = db.session.get(Company, current_user.company_id)
    if company is None:
        abort(403)

    target = (
        get_latest_target(company.id)
        if company is not None
        else None
    )
    target_progress = get_target_progress(target)

    if company is not None:
        categories = [
            item["category"]
            for item in get_emissions_by_category(company.id)
        ]

        try:
            try:
                start_date = (
                    date.fromisoformat(filters["start_date"])
                    if filters["start_date"]
                    else None
                )
                end_date = (
                    date.fromisoformat(filters["end_date"])
                    if filters["end_date"]
                    else None
                )
            except ValueError:
                raise InvalidFilterError(
                    "Enter valid dates in YYYY-MM-DD format."
                ) from None

            service = AnalyticsService(company_id=company.id)
            service.configure_filters(
                start_date=start_date,
                end_date=end_date,
                category=filters["category"],
            )

            if (
                filters["category"]
                and filters["category"] not in categories
            ):
                raise InvalidFilterError("Select an available category.")

        except InvalidFilterError as exc:
            error = str(exc)
        else:
            summary = service.get_summary()
            category_totals = service.group_by_category()
            monthly_totals = service.get_monthly_totals()

            report = DashboardReport(
                summary=summary,
                category_totals=category_totals,
                monthly_totals=monthly_totals,
            )

            if request.args.get("export") == "csv":
                csv_content = report.export_CSV()

                return Response(
                    "\ufeff" + csv_content,
                    content_type="text/csv; charset=utf-8",
                    headers={
                        "Content-Disposition": (
                            f'attachment; filename="{report.filename}"'
                        ),
                        "Cache-Control": "no-store",
                    },
                )

            comparison = report.display_summary()["comparison"]
            charts = report.generate_charts()
            monthly_chart = charts["monthly_chart"]
            category_chart = charts["category_chart"]

    return render_template(
        "analytics/index.html",
        company=company,
        summary=summary,
        category_totals=category_totals,
        categories=categories,
        filters=filters,
        error=error,
        monthly_chart=monthly_chart,
        category_chart=category_chart,
        comparison=comparison,
        target=target,
        target_progress=target_progress,
    )


@bp.route("/target", methods=["GET", "POST"])
@require_role(Role.ADMIN, Role.MANAGER)
def target_form():
    if not current_user.company_id:
        abort(403)

    company = db.session.get(Company, current_user.company_id)
    if company is None:
        abort(403)

    if "target_form_token" not in session:
        session["target_form_token"] = secrets.token_urlsafe(32)

    error = None

    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(
            submitted_token,
            session["target_form_token"],
        ):
            abort(400)

        try:
            values = validate_target_form(request.form)
        except TargetValidationError as exc:
            error = str(exc)
        else:
            target = Target(company_id=company.id, **values)
            db.session.add(target)
            db.session.commit()
            return redirect(url_for("analytics.index"))

    return render_template(
        "analytics/target_form.html",
        company=company,
        error=error,
        values=request.form,
        csrf_token=session["target_form_token"],
    )