"""S1 Domain Model: Department (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .activity_record import ActivityRecord


class Department:
    """Represents an organizational unit within a company (UML S1)."""

    def __init__(
        self,
        company_id: str,
        name: str,
        floor_area_m2: float = 0.0,
        department_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = department_id or str(uuid.uuid4())
        self._company_id: str = ""
        self._name: str = ""
        self._floor_area_m2: float = 0.0
        self._activity_records: list[ActivityRecord] = []
        self.configure_department(company_id=company_id, name=name, floor_area_m2=floor_area_m2)

    def configure_department(self, company_id: str, name: str, floor_area_m2: float = 0.0) -> None:
        """Initialization method: configures department ownership, name, and floor space."""
        if not (company_id or "").strip():
            raise ValueError("company_id cannot be empty.")
        self._company_id = company_id.strip()
        self.set_name(name)
        self.set_floor_area_m2(floor_area_m2)

    def get_id(self) -> str:
        return self._id

    def get_company_id(self) -> str:
        return self._company_id

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Department name cannot be empty.")
        self._name = cleaned

    def get_floor_area_m2(self) -> float:
        return self._floor_area_m2

    def set_floor_area_m2(self, area: float) -> None:
        val = float(area)
        if val < 0:
            raise ValueError("Floor area cannot be negative.")
        self._floor_area_m2 = val

    def get_activity_records(self) -> list[ActivityRecord]:
        """UML method: returns all activity records logged under this department."""
        return list(self._activity_records)

    def add_activity_record(self, record: ActivityRecord) -> None:
        self._activity_records.append(record)
