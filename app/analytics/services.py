"""S2 — Analytics & Dashboard. Owner: Vanessa."""

from datetime import date

from sqlalchemy import func, select

from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.department import Department

from .scoring import calculate_target_progress


def apply_filters(
    statement, start_date=None, end_date=None, category=None
):
    """Filter records without changing stored data."""
    if start_date is not None:
        statement = statement.where(
            ActivityRecord.period_start >= start_date
        )

    if end_date is not None:
        statement = statement.where(
            ActivityRecord.period_start <= end_date
        )

    if category:
        normalised_category = func.coalesce(
            func.nullif(func.trim(ActivityRecord.category), ""),
            "Uncategorised",
        )
        statement = statement.where(
            normalised_category == category
        )

    return statement


class AnalyticsService:
    """Service class for aggregating, filtering, and scoring company emissions (UML S2 & Hometask 1)."""

    def __init__(
        self,
        company_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._company_id = company_id
        self._start_date = start_date
        self._end_date = end_date
        self._category = category.strip() if isinstance(category, str) else category

    # --- Initialization / Setup Methods (Hometask 1) ---
    def configure_filters(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> None:
        """Configures and validates date range and category filters."""
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("Start date must be on or before end date.")
        self._start_date = start_date
        self._end_date = end_date
        self._category = category.strip() if isinstance(category, str) else category

    def reset_filters(self) -> None:
        """Resets all active date and category filters."""
        self._start_date = None
        self._end_date = None
        self._category = None

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def company_id(self) -> str | None:
        return self._company_id

    @company_id.setter
    def company_id(self, value: str | None) -> None:
        if value is not None and not str(value).strip():
            raise ValueError("Company ID cannot be empty.")
        self._company_id = str(value).strip() if value is not None else None

    @property
    def start_date(self) -> date | None:
        return self._start_date

    @start_date.setter
    def start_date(self, value: date | None) -> None:
        if value is not None and self._end_date is not None and value > self._end_date:
            raise ValueError("Start date must be on or before end date.")
        self._start_date = value

    @property
    def end_date(self) -> date | None:
        return self._end_date

    @end_date.setter
    def end_date(self, value: date | None) -> None:
        if value is not None and self._start_date is not None and self._start_date > value:
            raise ValueError("Start date must be on or before end date.")
        self._end_date = value

    @property
    def category(self) -> str | None:
        return self._category

    @category.setter
    def category(self, value: str | None) -> None:
        self._category = value.strip() if isinstance(value, str) else value

    # --- UML Domain Methods (UML S2) ---
    def filter_records(self, statement):
        """Applies configured filters to a SQLAlchemy statement without mutating stored data."""
        return apply_filters(
            statement,
            self._start_date,
            self._end_date,
            self._category,
        )

    def get_summary(self) -> dict:
        """Calculates record count and total emissions (kg CO2e) for the configured company."""
        statement = (
            select(
                func.count(ActivityRecord.id),
                func.coalesce(func.sum(ActivityRecord.co2e_kg), 0.0),
            )
            .select_from(ActivityRecord)
            .join(
                Department,
                ActivityRecord.department_id == Department.id,
            )
            .where(Department.company_id == self._company_id)
        )

        statement = self.filter_records(statement)

        record_count, total_emissions = db.session.execute(
            statement
        ).one()

        return {
            "record_count": record_count,
            "total_emissions": float(total_emissions),
        }

    def calculate_total(self) -> float:
        """Returns total filtered emissions in kg CO2e (UML S2)."""
        return self.get_summary()["total_emissions"]

    def group_by_category(self) -> list[dict]:
        """Groups one company's filtered emissions by category (UML S2)."""
        category = func.coalesce(
            func.nullif(func.trim(ActivityRecord.category), ""),
            "Uncategorised",
        )
        total = func.sum(ActivityRecord.co2e_kg)

        statement = (
            select(
                category.label("category"),
                total.label("total_emissions"),
            )
            .select_from(ActivityRecord)
            .join(
                Department,
                ActivityRecord.department_id == Department.id,
            )
            .where(Department.company_id == self._company_id)
            .group_by(category)
            .order_by(total.desc(), category)
        )

        statement = self.filter_records(statement)
        results = db.session.execute(statement).all()

        return [
            {
                "category": row.category,
                "total_emissions": float(row.total_emissions),
            }
            for row in results
        ]

    def get_monthly_totals(self) -> list[dict]:
        """Groups dated activity records by year and month."""
        year = func.extract("year", ActivityRecord.period_start)
        month = func.extract("month", ActivityRecord.period_start)

        statement = (
            select(
                year.label("year"),
                month.label("month"),
                func.sum(ActivityRecord.co2e_kg).label("total_emissions"),
            )
            .select_from(ActivityRecord)
            .join(
                Department,
                ActivityRecord.department_id == Department.id,
            )
            .where(
                Department.company_id == self._company_id,
                ActivityRecord.period_start.is_not(None),
            )
            .group_by(year, month)
            .order_by(year, month)
        )

        statement = self.filter_records(statement)
        results = db.session.execute(statement).all()

        return [
            {
                "month": f"{int(row.year):04d}-{int(row.month):02d}",
                "total_emissions": float(row.total_emissions),
            }
            for row in results
        ]

    @staticmethod
    def calculate_score(
        baseline_kg: float,
        current_kg: float,
        reduction_percent: float,
        data_complete: bool = False,
    ) -> dict:
        """Calculates target-progress score (UML S2)."""
        return calculate_target_progress(
            baseline_kg,
            current_kg,
            reduction_percent,
            data_complete=data_complete,
        )


def get_emissions_summary(
    company_id, start_date=None, end_date=None, category=None
):
    """Calculate filtered emissions for one company's departments."""
    return AnalyticsService(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
    ).get_summary()


def get_emissions_by_category(
    company_id, start_date=None, end_date=None, category_filter=None
):
    """Group one company's filtered emissions by category."""
    return AnalyticsService(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        category=category_filter,
    ).group_by_category()


def get_monthly_emissions(
    company_id, start_date=None, end_date=None, category=None
):
    """Group dated activity records by year and month."""
    return AnalyticsService(
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        category=category,
    ).get_monthly_totals()


def compare_latest_months(monthly_totals):
    """Compare the latest two months only when they are consecutive."""
    if len(monthly_totals) < 2:
        return {
            "available": False,
            "reason": "At least two consecutive months with records are needed.",
        }

    previous = monthly_totals[-2]
    latest = monthly_totals[-1]

    previous_year, previous_month = map(
        int, previous["month"].split("-")
    )
    latest_year, latest_month = map(
        int, latest["month"].split("-")
    )

    previous_index = previous_year * 12 + previous_month
    latest_index = latest_year * 12 + latest_month

    if latest_index - previous_index != 1:
        return {
            "available": False,
            "reason": "The latest recorded months are not consecutive.",
        }

    previous_total = previous["total_emissions"]
    latest_total = latest["total_emissions"]
    difference = latest_total - previous_total

    percentage = (
        difference / previous_total * 100
        if previous_total != 0
        else None
    )

    return {
        "available": True,
        "previous_month": previous["month"],
        "latest_month": latest["month"],
        "previous_total": previous_total,
        "latest_total": latest_total,
        "difference": difference,
        "percentage": percentage,
    }
