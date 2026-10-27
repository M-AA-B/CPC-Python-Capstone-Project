from datetime import datetime, timezone
from app.extensions import db
from app.models.emission_factor import EmissionFactor


class EmissionCalculator:
    """Service class for greenhouse gas emissions calculations and scope assignments (UML S1)."""

    SCOPE_MAPPING = {
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

    @classmethod
    def calculate(cls, quantity: float, factor_kg_co2e: float) -> float:
        """Calculates CO2e emissions (kg) = quantity * factor_kg_co2e rounded to 2 decimal places."""
        if quantity is None or factor_kg_co2e is None:
            raise ValueError("Quantity and factor value must not be None.")
        if quantity < 0:
            raise ValueError("Activity quantity cannot be negative.")
        return round(float(quantity) * float(factor_kg_co2e), 2)

    @classmethod
    def assign_scope(cls, category: str) -> int:
        """Auto-assigns GHG Protocol Scope (1, 2, or 3) based on category classification."""
        if not category:
            return 3
        return cls.SCOPE_MAPPING.get(category.strip().lower(), 3)

    @classmethod
    def fetch_factor(cls, category: str, year: int | None = None) -> EmissionFactor | None:
        """Fetches the active emission factor for a specific category and valid year."""
        if year is None:
            year = datetime.now(timezone.utc).year
        return EmissionFactor.query.filter_by(category=category.strip().lower(), valid_year=year).first()


# Functional wrapper aliases for backward compatibility
def calculate_emissions(quantity: float, factor_kg_co2e: float) -> float:
    return EmissionCalculator.calculate(quantity, factor_kg_co2e)


def assign_scope(category: str) -> int:
    return EmissionCalculator.assign_scope(category)
