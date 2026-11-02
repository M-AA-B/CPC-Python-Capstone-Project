import uuid
from datetime import datetime, timezone

from app.extensions import db


class ActivityRecord(db.Model):
    __tablename__ = 'activity_records'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True)
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'), nullable=False)
    factor_id = db.Column(db.Integer, db.ForeignKey('emission_factors.id'), nullable=False)
    
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=True)
    co2e_kg = db.Column(db.Float, nullable=False, default=0.0)
    scope = db.Column(db.Integer, nullable=True)
    
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Synonyms / Aliases to support both naming conventions
    emission_factor_id = db.synonym('factor_id')
    user_id = db.synonym('created_by')
    activity_value = db.synonym('quantity')
    calculated_co2e = db.synonym('co2e_kg')

    def __init__(self, **kwargs):
        """Constructor: Initializes state and handles attribute aliases (Hometask 1)."""
        if 'user_id' in kwargs and 'created_by' not in kwargs:
            kwargs['created_by'] = kwargs.pop('user_id')
        if 'emission_factor_id' in kwargs and 'factor_id' not in kwargs:
            kwargs['factor_id'] = kwargs.pop('emission_factor_id')
        if 'activity_value' in kwargs and 'quantity' not in kwargs:
            kwargs['quantity'] = kwargs.pop('activity_value')
        if 'calculated_co2e' in kwargs and 'co2e_kg' not in kwargs:
            kwargs['co2e_kg'] = kwargs.pop('calculated_co2e')
        super().__init__(**kwargs)

    # --- Explicit Accessor & Mutator Methods (Hometask 1 Encapsulation) ---
    def get_quantity(self) -> float:
        """Accessor (getter) for quantity."""
        return self.quantity

    def set_quantity(self, value: float) -> None:
        """Mutator (setter) for quantity with input validation."""
        val = float(value)
        if val < 0:
            raise ValueError("Activity quantity cannot be negative.")
        self.quantity = val
        if self.factor and hasattr(self.factor, 'kg_co2e_per_unit'):
            self.co2e_kg = round(self.quantity * self.factor.kg_co2e_per_unit, 2)

    def get_unit(self) -> str:
        """Accessor (getter) for unit."""
        return self.unit or ""

    def set_unit(self, value: str) -> None:
        """Mutator (setter) for unit."""
        if not value:
            raise ValueError("Unit cannot be empty.")
        self.unit = str(value)

    def get_co2e_kg(self) -> float:
        """Accessor (getter) for calculated co2e_kg."""
        return self.co2e_kg

    def is_valid(self) -> bool:
        """Validates that quantity is non-negative and dates are consistent (UML S1)."""
        if self.quantity is None or self.quantity < 0:
            return False
        if self.period_start and self.period_end and self.period_start > self.period_end:
            return False
        return True

    def update_quantity(self, new_val: float) -> None:
        """Updates quantity and recalculates CO2e emissions in real-time (UML S1)."""
        self.set_quantity(new_val)

    def to_dict(self) -> dict:
        """Serializes record to dictionary for JSON output."""
        return {
            "id": self.id,
            "company_id": self.company_id,
            "department_id": self.department_id,
            "factor_id": self.factor_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "date": self.period_start.isoformat() if self.period_start else None,
            "category": self.category,
            "quantity": self.quantity,
            "activity_value": self.quantity,
            "unit": self.unit,
            "co2e_kg": self.co2e_kg,
            "calculated_co2e": self.co2e_kg,
            "scope": self.scope,
            "created_by": self.created_by,
            "user_id": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
