import os

from flask import current_app, render_template

from app.extensions import db
from app.models.company import Company
from . import bp
from .services import (
    get_emissions_summary,
    get_emissions_by_category,
)


@bp.get("/")
def index():
    company = None
    summary = None
    category_totals = []

    # Temporary company selection for local development.
    # Later, S3's login will identify the user's company.
    if current_app.debug:
        company_id = os.getenv("ANALYTICS_DEV_COMPANY_ID")

        if company_id:
            company = db.session.get(Company, company_id)

            if company is not None:
                summary = get_emissions_summary(company.id)
                category_totals = get_emissions_by_category(company.id)

    return render_template(
        "analytics/index.html",
        company=company,
        summary=summary,
        category_totals=category_totals,
    )

    