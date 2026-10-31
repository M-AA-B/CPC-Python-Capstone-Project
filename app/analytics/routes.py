import os
from datetime import date

from flask import current_app, render_template, request

from app.extensions import db
from app.models.company import Company
from . import bp
from .charts import build_monthly_chart, build_category_chart
from .services import (
    get_emissions_summary,
    get_emissions_by_category,
    get_monthly_emissions,
    compare_latest_months,
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

    # Temporary local development access.
    # S3 will replace this with authenticated company access.
    if current_app.debug:
        company_id = os.getenv("ANALYTICS_DEV_COMPANY_ID")

        if company_id:
            company = db.session.get(Company, company_id)

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
    )