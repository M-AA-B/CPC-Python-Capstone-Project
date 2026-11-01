import os
import secrets
from datetime import date

from flask import (
    Response,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import db
from app.models.company import Company
from app.models.target import Target

from . import bp
from .charts import build_monthly_chart, build_category_chart
from .exports import build_analytics_csv
from .services import (
    get_emissions_summary,
    get_emissions_by_category,
    get_monthly_emissions,
    compare_latest_months,
)
from .targets import (
    get_latest_target,
    get_target_progress,
    validate_target_form,
)


@bp.get("/")
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

    # S3 will replace development access with authenticated company access.
    if current_app.debug:
        company_id = os.getenv("ANALYTICS_DEV_COMPANY_ID")
        if company_id:
            company = db.session.get(Company, company_id)

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
            error = "Enter valid dates in YYYY-MM-DD format."
        else:
            if start_date and end_date and start_date > end_date:
                error = "Start date must be on or before end date."
            elif (
                filters["category"]
                and filters["category"] not in categories
            ):
                error = "Select an available category."
            else:
                summary = get_emissions_summary(
                    company.id,
                    start_date,
                    end_date,
                    filters["category"],
                )

                category_totals = get_emissions_by_category(
                    company.id,
                    start_date,
                    end_date,
                    filters["category"],
                )

                monthly_totals = get_monthly_emissions(
                    company.id,
                    start_date,
                    end_date,
                    filters["category"],
                )

                if request.args.get("export") == "csv":
                    csv_content = build_analytics_csv(
                        summary,
                        category_totals,
                        monthly_totals,
                    )

                    return Response(
                        "\ufeff" + csv_content,
                        content_type="text/csv; charset=utf-8",
                        headers={
                            "Content-Disposition": (
                                'attachment; filename="emissions-analytics.csv"'
                            ),
                            "Cache-Control": "no-store",
                        },
                    )

                comparison = compare_latest_months(monthly_totals)
                monthly_chart = build_monthly_chart(monthly_totals)
                category_chart = build_category_chart(category_totals)

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
def target_form():
    # Target editing is restricted to development until S3 adds roles.
    if not current_app.debug:
        abort(403)

    company_id = os.getenv("ANALYTICS_DEV_COMPANY_ID")
    company = (
        db.session.get(Company, company_id)
        if company_id
        else None
    )

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
        except ValueError as exc:
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