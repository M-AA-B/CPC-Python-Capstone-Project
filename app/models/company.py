"""S1 Domain Model: Company (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .department import Department


class Company:
    """Represents an enterprise tracking its carbon footprint across departments (UML S1)."""

    def __init__(self, name: str, industry: str = "General", company_id: str | None = None):
        """Constructor: Proper state initialization."""
        self._id: str = company_id or str(uuid.uuid4())
        self._name: str = ""
        self._industry: str = ""
        self._departments: list[Department] = []
        self._employee_count: int = 0
        self.configure_profile(name=name, industry=industry)

    def configure_profile(self, name: str, industry: str = "General", employee_count: int = 0) -> None:
        """Initialization method: configures company profile metadata and employee count."""
        self.set_name(name)
        self.set_industry(industry)
        self.set_total_employees(employee_count)

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        cleaned = (name or "").strip()
        if not cleaned:
            raise ValueError("Company name cannot be empty.")
        self._name = cleaned

    def get_industry(self) -> str:
        return self._industry

    def set_industry(self, industry: str) -> None:
        self._industry = (industry or "General").strip()

    def get_departments(self) -> list[Department]:
        """UML method: returns a shallow copy of the company's departments."""
        return list(self._departments)

    def add_department(self, department: Department) -> None:
        if department not in self._departments:
            self._departments.append(department)

    def get_total_employees(self) -> int:
        """UML method: returns total employees registered in the company."""
        return self._employee_count

    def set_total_employees(self, count: int) -> None:
        val = int(count)
        if val < 0:
            raise ValueError("Employee count cannot be negative.")
        self._employee_count = val
