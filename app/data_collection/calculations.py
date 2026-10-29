from datetime import datetime, timezone
from app.models.emission_factor import EmissionFactor


class EmissionCalculator:
    """Service class for greenhouse gas emissions calculations and scope assignments (UML S1 & Hometask 1).
    
    Supports both instance and class-level usage to satisfy:
    - Hometask 1: OOP encapsulation via @property and setter methods.
    - Hometask 2: Used within the stream processing pipeline.
    """

    DEFAULT_SCOPE_MAPPING = {
        'company_vehicles': 1,
        'natural_gas': 1,
        'diesel_generator': 1,
        'heating_oil': 1,
        'refrigerants': 1,
        'electricity': 2,
        'district_heating': 2,
        'business_travel': 3,
        'waste': 3,
        'employee_commuting': 3,
        'purchased_goods': 3
    }

    def __init__(self, precision: int = 2, custom_scopes: dict[str, int] | None = None):
        """Constructor: Proper state initialization (Hometask 1)."""
        self._precision = precision
        self._scope_mapping = dict(self.DEFAULT_SCOPE_MAPPING)
        if custom_scopes:
            self._scope_mapping.update(custom_scopes)

    # --- Initialization Methods (Hometask 1) ---
    def reset_configuration(self) -> None:
        """Resets the calculator configuration to factory defaults."""
        self._precision = 2
        self._scope_mapping = dict(self.DEFAULT_SCOPE_MAPPING)

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def precision(self) -> int:
        """Getter for precision."""
        return self._precision

    @precision.setter
    def precision(self, value: int) -> None:
        """Setter for precision with validation."""
        val = int(value)
        if val < 0 or val > 6:
            raise ValueError("Precision must be between 0 and 6 decimal places.")
        self._precision = val

    @property
    def scope_mapping(self) -> dict[str, int]:
        """Getter for scope mapping dictionary (returns a copy)."""
        return dict(self._scope_mapping)

    def register_scope_category(self, category: str, scope: int) -> None:
        """Mutator method to configure custom scope mapping."""
        if scope not in (1, 2, 3):
            raise ValueError("Scope must be 1, 2, or 3.")
        self._scope_mapping[category.strip().lower()] = scope

    def calculate(self, quantity: float, factor_kg_co2e: float) -> float:
        """Calculates CO2e emissions (kg) = quantity * factor_kg_co2e (instance method)."""
        if quantity is None or factor_kg_co2e is None:
            raise ValueError("Quantity and factor value must not be None.")
        if float(quantity) < 0:
            raise ValueError("Activity quantity cannot be negative.")
        return round(float(quantity) * float(factor_kg_co2e), self._precision)

    def assign_scope(self, category: str) -> int:
        """Assigns GHG Protocol Scope (1, 2, or 3) based on category (instance method)."""
        if not category:
            return 3
        return self._scope_mapping.get(category.strip().lower(), 3)

    @classmethod
    def fetch_factor(cls, category: str, year: int | None = None) -> EmissionFactor | None:
        """Fetches the active emission factor for a category and valid year (UML S1)."""
        if year is None:
            year = datetime.now(timezone.utc).year
        return EmissionFactor.query.filter_by(category=category.strip().lower(), valid_year=year).first()


# ---------------------------------------------------------------------------
# Module-level default instance — used by functional wrappers and all callers
# that previously relied on classmethod or top-level function access.
# ---------------------------------------------------------------------------
_default_calculator = EmissionCalculator()


def calculate_emissions(quantity: float, factor_kg_co2e: float) -> float:
    """Module-level wrapper for backward-compatible and service-layer use."""
    return _default_calculator.calculate(quantity, factor_kg_co2e)


def assign_scope(category: str) -> int:
    """Module-level wrapper for backward-compatible scope assignment."""
    return _default_calculator.assign_scope(category)
