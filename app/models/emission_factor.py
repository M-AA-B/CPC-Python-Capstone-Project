"""S1 Domain Model: EmissionFactor (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations


class EmissionFactor:
    """Represents a versioned greenhouse gas conversion factor in kg CO2e per unit (UML S1)."""

    def __init__(
        self,
        factor_id: int,
        category: str,
        kg_co2e_per_unit: float,
        unit: str,
        scope: int,
        valid_year: int,
    ):
        """Constructor: Proper state initialization."""
        self._id: int = int(factor_id)
        self._category: str = ""
        self._kg_co2e_per_unit: float = 0.0
        self._unit: str = ""
        self._scope: int = 1
        self._valid_year: int = 2026
        self.configure_factor(category, kg_co2e_per_unit, unit, scope, valid_year)

    def configure_factor(
        self,
        category: str,
        kg_co2e_per_unit: float,
        unit: str,
        scope: int,
        valid_year: int,
    ) -> None:
        """Initialization method: configures factor attributes with domain validation."""
        self.set_category(category)
        self.set_kg_co2e_per_unit(kg_co2e_per_unit)
        self.set_unit(unit)
        self.set_scope(scope)
        self.set_valid_year(valid_year)

    def get_id(self) -> int:
        return self._id

    def get_category(self) -> str:
        return self._category

    def set_category(self, category: str) -> None:
        cleaned = (category or "").strip().lower()
        if not cleaned:
            raise ValueError("Category cannot be empty.")
        self._category = cleaned

    def get_kg_co2e_per_unit(self) -> float:
        return self._kg_co2e_per_unit

    def set_kg_co2e_per_unit(self, value: float) -> None:
        val = float(value)
        if val < 0:
            raise ValueError("Emission factor cannot be negative.")
        self._kg_co2e_per_unit = val

    def get_unit(self) -> str:
        return self._unit

    def set_unit(self, unit: str) -> None:
        cleaned = (unit or "").strip()
        if not cleaned:
            raise ValueError("Unit cannot be empty.")
        self._unit = cleaned

    def get_scope(self) -> int:
        return self._scope

    def set_scope(self, scope: int) -> None:
        val = int(scope)
        if val not in (1, 2, 3):
            raise ValueError("Scope must be 1, 2, or 3.")
        self._scope = val

    def get_valid_year(self) -> int:
        return self._valid_year

    def set_valid_year(self, year: int) -> None:
        val = int(year)
        if val < 1990 or val > 2100:
            raise ValueError("valid_year must be between 1990 and 2100.")
        self._valid_year = val

    def is_active(self, year: int) -> bool:
        """UML method: checks whether this factor applies to the given reporting year."""
        return self._valid_year == int(year)
