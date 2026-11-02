"""S1 Domain Model: ActivityRecord (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations

import uuid
from datetime import date

from .emission_factor import EmissionFactor


class ActivityRecord:
    """Represents a recorded operational emission activity linked to a factor and department (UML S1)."""

    def __init__(
        self,
        department_id: str,
        factor: EmissionFactor,
        quantity: float,
        unit: str,
        record_date: date | None = None,
        record_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = record_id or str(uuid.uuid4())
        self._department_id: str = department_id
        self._factor: EmissionFactor = factor
        self._quantity: float = 0.0
        self._unit: str = ""
        self._co2e_kg: float = 0.0
        self._record_date: date = record_date or date.today()
        self.initialize_record(quantity=quantity, unit=unit, record_date=self._record_date)

    def initialize_record(self, quantity: float, unit: str, record_date: date) -> None:
        """Initialization method: assigns unit, date, and quantity and computes initial CO2e."""
        self.set_unit(unit)
        self.set_record_date(record_date)
        self.set_quantity(quantity)

    def get_id(self) -> str:
        return self._id

    def get_department_id(self) -> str:
        return self._department_id

    def get_factor(self) -> EmissionFactor:
        return self._factor

    def get_category(self) -> str:
        return self._factor.get_category()

    def get_scope(self) -> int:
        return self._factor.get_scope()

    def get_quantity(self) -> float:
        return self._quantity

    def set_quantity(self, value: float) -> None:
        val = float(value)
        if val < 0:
            raise ValueError("Quantity cannot be negative.")
        self._quantity = val
        self._co2e_kg = round(self._quantity * self._factor.get_kg_co2e_per_unit(), 2)

    def get_unit(self) -> str:
        return self._unit

    def set_unit(self, unit: str) -> None:
        cleaned = (unit or "").strip()
        if not cleaned:
            raise ValueError("Unit cannot be empty.")
        self._unit = cleaned

    def get_co2e_kg(self) -> float:
        return self._co2e_kg

    def get_calculated_co2e_kg(self) -> float:
        return self._co2e_kg

    def get_record_date(self) -> date:
        return self._record_date

    def set_record_date(self, record_date: date) -> None:
        if not isinstance(record_date, date):
            raise TypeError("record_date must be a datetime.date instance.")
        self._record_date = record_date

    def is_valid(self) -> bool:
        """UML method: verifies non-negative quantity and matching factor unit."""
        return self._quantity >= 0 and self._unit.lower() == self._factor.get_unit().lower()

    def update_quantity(self, new_val: float) -> None:
        """UML method: updates quantity and recalculates CO2e emissions."""
        self.set_quantity(new_val)
