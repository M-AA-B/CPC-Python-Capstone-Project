"""S2 Service Class: AnalyticsService (Owner: Vanessa Mukamanzi · 7223964)."""
from __future__ import annotations

from datetime import date

from app.models import ActivityRecord, ReductionTarget
from .scoring import CarbonScorer


class AnalyticsService:
    """Aggregates, filters, and scores company ActivityRecords against a ReductionTarget (UML S2)."""

    def __init__(
        self,
        records: list[ActivityRecord] | None = None,
        target: ReductionTarget | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._records: list[ActivityRecord] = list(records) if records else []
        self._target: ReductionTarget | None = target
        self._start_date: date | None = None
        self._end_date: date | None = None
        self._category_filter: str | None = None
        self.reset_filters()

    # --- Initialization / Setup Method ---
    def reset_filters(self) -> None:
        """Clears active date and category filters."""
        self._start_date = None
        self._end_date = None
        self._category_filter = None

    def configure_filters(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> None:
        """Configures date range and category filters with chronological validation."""
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must be on or before end_date.")
        self._start_date = start_date
        self._end_date = end_date
        self._category_filter = category.strip().lower() if category else None

    # --- Encapsulation: Getters & Setters ---
    def get_records(self) -> list[ActivityRecord]:
        return list(self._records)

    def set_records(self, records: list[ActivityRecord]) -> None:
        self._records = list(records)

    def get_target(self) -> ReductionTarget | None:
        return self._target

    def set_target(self, target: ReductionTarget | None) -> None:
        self._target = target

    # --- UML Domain Methods ---
    def filter_records(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        category: str | None = None,
    ) -> list[ActivityRecord]:
        """UML method: filters records without mutating stored ActivityRecord instances."""
        s_date = start_date if start_date is not None else self._start_date
        e_date = end_date if end_date is not None else self._end_date
        cat = category.strip().lower() if category else self._category_filter

        filtered: list[ActivityRecord] = []
        for rec in self._records:
            if s_date and rec.get_record_date() < s_date:
                continue
            if e_date and rec.get_record_date() > e_date:
                continue
            if cat and rec.get_category() != cat:
                continue
            filtered.append(rec)
        return filtered

    def calculate_total(self) -> float:
        """UML method: returns total emissions (kg CO2e) across active filtered records."""
        return round(sum(r.get_calculated_co2e_kg() for r in self.filter_records()), 2)

    def group_by_category(self) -> dict[str, float]:
        """UML method: groups filtered emissions (kg CO2e) by category."""
        totals: dict[str, float] = {}
        for rec in self.filter_records():
            cat = rec.get_category()
            totals[cat] = round(totals.get(cat, 0.0) + rec.get_calculated_co2e_kg(), 2)
        return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))

    def calculate_score(self) -> float | None:
        """UML method: calculates bounded 0..100 Carbon Score progress towards ReductionTarget."""
        if self._target is None:
            return None
        baseline = self._target.get_baseline()
        required_reduction = baseline * (self._target.get_target() / 100.0)
        achieved_reduction = baseline - self.calculate_total()
        raw_score = (achieved_reduction / required_reduction) * 100.0
        return round(max(0.0, min(100.0, raw_score)), 1)
