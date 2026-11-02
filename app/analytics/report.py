"""S2 Service Class: DashboardReport (Owner: Vanessa Mukamanzi · 7223964)."""
from __future__ import annotations

import csv
import io

from .services import AnalyticsService


class DashboardReport:
    """Formats AnalyticsService results into chart specifications, summaries, and CSV exports (UML S2)."""

    def __init__(
        self,
        analytics_service: AnalyticsService,
        report_title: str = "Emissions Dashboard",
    ):
        """Constructor: Proper state initialization."""
        self._service: AnalyticsService = analytics_service
        self._report_title: str = ""
        self._export_filename: str = "emissions-analytics.csv"
        self.configure_report(report_title=report_title, export_filename="emissions-analytics.csv")

    # --- Initialization / Setup Method ---
    def configure_report(self, report_title: str, export_filename: str = "emissions-analytics.csv") -> None:
        """Initializes report header title and CSV export filename."""
        self.set_report_title(report_title)
        self.set_export_filename(export_filename)

    # --- Encapsulation: Getters & Setters ---
    def get_service(self) -> AnalyticsService:
        return self._service

    def set_service(self, service: AnalyticsService) -> None:
        if not isinstance(service, AnalyticsService):
            raise TypeError("service must be an AnalyticsService instance.")
        self._service = service

    def get_report_title(self) -> str:
        return self._report_title

    def set_report_title(self, title: str) -> None:
        cleaned = (title or "").strip()
        if not cleaned:
            raise ValueError("Report title cannot be empty.")
        self._report_title = cleaned

    def get_export_filename(self) -> str:
        return self._export_filename

    def set_export_filename(self, filename: str) -> None:
        cleaned = (filename or "").strip()
        if not cleaned.endswith(".csv"):
            raise ValueError("Export filename must end with .csv")
        self._export_filename = cleaned

    # --- UML Domain Methods ---
    def generate_charts(self) -> dict[str, dict]:
        """UML method: builds structured chart configurations for category breakdown."""
        by_cat = self._service.group_by_category()
        return {
            "category_bar_chart": {
                "title": f"{self._report_title} — By Category (kg CO2e)",
                "x": list(by_cat.keys()),
                "y": list(by_cat.values()),
            }
        }

    def display_summary(self) -> dict:
        """UML method: returns summary KPIs including total CO2e, top category, and Carbon Score."""
        by_cat = self._service.group_by_category()
        highest_category = next(iter(by_cat.keys()), None)
        return {
            "title": self._report_title,
            "total_co2e_kg": self._service.calculate_total(),
            "highest_category": highest_category,
            "carbon_score": self._service.calculate_score(),
            "by_category": by_cat,
        }

    def export_CSV(self) -> str:
        """UML method: exports displayed analytics totals to CSV text."""
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Section", "Label", "Emissions (kg CO2e)"])
        writer.writerow(["Summary", "Total emissions", f"{self._service.calculate_total():.2f}"])
        for cat, val in self._service.group_by_category().items():
            writer.writerow(["Category", cat, f"{val:.2f}"])
        return output.getvalue()
