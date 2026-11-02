"""S1 Service Class: EmissionCalculator (Owner: Mohammed Al-Amine Bennani · 7222047)."""
from __future__ import annotations

from app.models import ActivityRecord, EmissionFactor


class EmissionCalculator:
    """Service class for GHG CO2e calculations, scope assignments, and factor lookup (UML S1)."""

    DEFAULT_SCOPE_MAPPING = {
        "company_vehicles": 1,
        "natural_gas": 1,
        "diesel_generator": 1,
        "electricity": 2,
        "district_heating": 2,
        "business_travel": 3,
        "waste": 3,
        "freight_logistics": 3,
    }

    def __init__(
        self,
        precision: int = 2,
        factors: list[EmissionFactor] | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._precision: int = 2
        self._scope_mapping: dict[str, int] = {}
        self._factors: list[EmissionFactor] = []
        self.reset_configuration()
        self.precision = precision
        if factors:
            for factor in factors:
                self.register_factor(factor)

    # --- Initialization / Setup Method ---
    def reset_configuration(self) -> None:
        """Resets calculator rounding precision and default GHG scope mapping."""
        self._precision = 2
        self._scope_mapping = dict(self.DEFAULT_SCOPE_MAPPING)

    # --- Encapsulation: Getters & Setters ---
    @property
    def precision(self) -> int:
        return self._precision

    @precision.setter
    def precision(self, value: int) -> None:
        val = int(value)
        if not 0 <= val <= 6:
            raise ValueError("Precision must be between 0 and 6 decimal places.")
        self._precision = val

    @property
    def scope_mapping(self) -> dict[str, int]:
        return dict(self._scope_mapping)

    def register_scope_category(self, category: str, scope: int) -> None:
        """Mutator adding or updating a category-to-scope rule."""
        if scope not in (1, 2, 3):
            raise ValueError("Scope must be 1, 2, or 3.")
        self._scope_mapping[category.strip().lower()] = scope

    def get_factors(self) -> list[EmissionFactor]:
        return list(self._factors)

    def register_factor(self, factor: EmissionFactor) -> None:
        self._factors.append(factor)

    # --- UML Domain Methods ---
    def calculate(self, rec: ActivityRecord) -> float:
        """UML method: calculates CO2e (kg) for an ActivityRecord."""
        if not rec.is_valid():
            raise ValueError("Cannot calculate emissions for an invalid ActivityRecord.")
        return round(
            rec.get_quantity() * rec.get_factor().get_kg_co2e_per_unit(),
            self._precision,
        )

    def assign_scope(self, category: str) -> int:
        """UML method: assigns GHG Protocol Scope (1, 2, or 3) from category."""
        return self._scope_mapping.get((category or "").strip().lower(), 3)

    def fetch_factor(self, category: str, year: int) -> EmissionFactor | None:
        """UML method: retrieves an active EmissionFactor for category and year."""
        target = (category or "").strip().lower()
        for factor in self._factors:
            if factor.get_category() == target and factor.is_active(year):
                return factor
        return None
