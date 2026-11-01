"""S2 — DashboardReport OOP class for chart generation, summaries, and CSV export (UML S2 & Hometask 1)."""

from .charts import build_category_chart, build_monthly_chart
from .exceptions import AnalyticsError
from .exports import build_analytics_csv
from .services import compare_latest_months


class DashboardReport:
    """Encapsulates analytics dashboard presentation, charts, and CSV export (UML S2 & Hometask 1)."""

    def __init__(
        self,
        summary: dict | None = None,
        category_totals: list[dict] | None = None,
        monthly_totals: list[dict] | None = None,
        filename: str = "emissions-analytics.csv",
    ):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._summary: dict = {"record_count": 0, "total_emissions": 0.0}
        self._category_totals: list[dict] = []
        self._monthly_totals: list[dict] = []
        self._filename: str = "emissions-analytics.csv"
        self.load_data(summary, category_totals, monthly_totals)
        self.filename = filename

    # --- Initialization / Setup Methods (Hometask 1) ---
    def load_data(
        self,
        summary: dict | None = None,
        category_totals: list[dict] | None = None,
        monthly_totals: list[dict] | None = None,
    ) -> None:
        """Loads or refreshes aggregated analytics datasets for reporting."""
        self.summary = summary or {"record_count": 0, "total_emissions": 0.0}
        self.category_totals = category_totals or []
        self.monthly_totals = monthly_totals or []

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def summary(self) -> dict:
        return dict(self._summary)

    @summary.setter
    def summary(self, value: dict) -> None:
        if not isinstance(value, dict):
            raise AnalyticsError("Summary must be a dictionary.")
        self._summary = {
            "record_count": int(value.get("record_count", 0)),
            "total_emissions": float(value.get("total_emissions", 0.0)),
        }

    @property
    def category_totals(self) -> list[dict]:
        return list(self._category_totals)

    @category_totals.setter
    def category_totals(self, value: list[dict]) -> None:
        if not isinstance(value, list):
            raise AnalyticsError("Category totals must be a list.")
        self._category_totals = list(value)

    @property
    def monthly_totals(self) -> list[dict]:
        return list(self._monthly_totals)

    @monthly_totals.setter
    def monthly_totals(self, value: list[dict]) -> None:
        if not isinstance(value, list):
            raise AnalyticsError("Monthly totals must be a list.")
        self._monthly_totals = list(value)

    @property
    def filename(self) -> str:
        return self._filename

    @filename.setter
    def filename(self, value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned or not cleaned.endswith(".csv"):
            raise AnalyticsError("Export filename must be a non-empty .csv name.")
        self._filename = cleaned

    # --- UML Domain Methods (UML S2) ---
    def generate_charts(self) -> dict[str, str | None]:
        """Generates Plotly HTML charts for monthly trends and category breakdown (UML S2)."""
        return {
            "monthly_chart": build_monthly_chart(self._monthly_totals),
            "category_chart": build_category_chart(self._category_totals),
        }

    def display_summary(self) -> dict:
        """Builds a structured dashboard summary including top category and month-over-month comparison (UML S2)."""
        top_category = self._category_totals[0]["category"] if self._category_totals else None
        return {
            "record_count": self._summary["record_count"],
            "total_emissions": self._summary["total_emissions"],
            "highest_category": top_category,
            "comparison": compare_latest_months(self._monthly_totals),
        }

    def export_csv(self) -> str:
        """Exports the report's summary, category totals, and monthly totals as CSV text."""
        return build_analytics_csv(
            self._summary,
            self._category_totals,
            self._monthly_totals,
        )

    # Exact UML diagram method alias
    export_CSV = export_csv

