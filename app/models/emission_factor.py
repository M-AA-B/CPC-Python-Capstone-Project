from datetime import datetime, timezone
from app.extensions import db


class EmissionFactor(db.Model):
    __tablename__ = 'emission_factors'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    kg_co2e_per_unit = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    scope = db.Column(db.Integer, nullable=False)
    valid_year = db.Column(db.Integer, nullable=False)

    records = db.relationship('ActivityRecord', backref='factor', lazy=True)

    def is_active(self, year: int | None = None) -> bool:
        """Determines if this factor is valid for a given calendar year (defaults to current year)."""
        if year is None:
            year = datetime.now(timezone.utc).year
        return self.valid_year == year

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "kg_co2e_per_unit": self.kg_co2e_per_unit,
            "unit": self.unit,
            "scope": self.scope,
            "valid_year": self.valid_year
        }
