"""S1 Service Class: CsvImporter (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations

import csv
import io
from datetime import date

from app.models import ActivityRecord
from .calculations import EmissionCalculator


class CsvImporter:
    """Service class for reading, validating, and importing CSV activity rows (UML S1)."""

    def __init__(self, calculator: EmissionCalculator, encoding: str = "utf-8"):
        """Constructor: Proper state initialization."""
        self._calculator: EmissionCalculator = calculator
        self._encoding: str = "utf-8"
        self._error_log: list[str] = []
        self._pending_rows: list[dict] = []
        self._saved_records: list[ActivityRecord] = []
        self.encoding = encoding
        self.initialize_session()

    # --- Initialization / Setup Method ---
    def initialize_session(self) -> None:
        """Clears error logs and staged CSV rows before starting a new import batch."""
        self._error_log.clear()
        self._pending_rows.clear()

    # --- Encapsulation: Getters & Setters ---
    @property
    def encoding(self) -> str:
        return self._encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("Encoding cannot be empty.")
        self._encoding = cleaned

    @property
    def error_log(self) -> list[str]:
        return list(self._error_log)

    @property
    def saved_records(self) -> list[ActivityRecord]:
        return list(self._saved_records)

    # --- UML Domain Methods ---
    def read_file(self, csv_source: str) -> list[dict]:
        """UML method: reads CSV rows from a file path or raw CSV text."""
        self.initialize_session()
        if "\n" in csv_source:
            stream = io.StringIO(csv_source)
            rows = list(csv.DictReader(stream))
        else:
            with open(csv_source, mode="r", encoding=self._encoding, newline="") as handle:
                rows = list(csv.DictReader(handle))
        self._pending_rows = rows
        return list(rows)

    def validate_row(self, row: dict) -> bool:
        """UML method: checks required CSV columns, positive quantity, and matching factor."""
        try:
            category = (row.get("category") or "").strip()
            quantity = float(row.get("quantity", -1))
            unit = (row.get("unit") or "").strip()
            rec_date = date.fromisoformat((row.get("record_date") or "").strip())
            factor = self._calculator.fetch_factor(category, rec_date.year)
            if not category or quantity < 0 or factor is None:
                return False
            return factor.get_unit().lower() == unit.lower()
        except (TypeError, ValueError):
            return False

    def save_valid_rows(self) -> list[ActivityRecord]:
        """UML method: converts valid staged CSV rows into ActivityRecord instances."""
        created: list[ActivityRecord] = []
        for idx, row in enumerate(self._pending_rows, start=1):
            if not self.validate_row(row):
                self._error_log.append(f"Row {idx}: validation failed for {row!r}")
                continue
            rec_date = date.fromisoformat(row["record_date"].strip())
            factor = self._calculator.fetch_factor(row["category"], rec_date.year)
            assert factor is not None
            record = ActivityRecord(
                department_id=row.get("department_id", "default-dept"),
                factor=factor,
                quantity=float(row["quantity"]),
                unit=row["unit"].strip(),
                record_date=rec_date,
            )
            created.append(record)
            self._saved_records.append(record)
        return created
