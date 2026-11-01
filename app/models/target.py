import uuid
from datetime import date, datetime, timezone
from math import isfinite

from app.extensions import db


class Target(db.Model):
    """Carbon reduction target model for Subsystem 2 (UML ReductionTarget & Hometask 1)."""

    __tablename__ = "targets"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    company_id = db.Column(
        db.String(36),
        db.ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    baseline_start = db.Column(db.Date, nullable=False)
    baseline_end = db.Column(db.Date, nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    reduction_percent = db.Column(db.Float, nullable=False)

    # Confirmation applies to both reporting periods.
    data_complete = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            "reduction_percent > 0 AND reduction_percent <= 100",
            name="ck_target_reduction_percent",
        ),
        db.CheckConstraint(
            "baseline_start <= baseline_end",
            name="ck_target_baseline_dates",
        ),
        db.CheckConstraint(
            "period_start <= period_end",
            name="ck_target_period_dates",
        ),
        db.CheckConstraint(
            "baseline_end < period_start",
            name="ck_target_period_order",
        ),
    )

    def __init__(self, **kwargs):
        """Constructor: Proper state initialization (Hometask 1)."""
        kwargs.setdefault("data_complete", False)
        super().__init__(**kwargs)

    # --- Initialization / Setup Methods (Hometask 1) ---
    def configure_periods(
        self,
        baseline_start: date,
        baseline_end: date,
        period_start: date,
        period_end: date,
    ) -> None:
        """Configures and validates baseline and target reporting date windows."""
        from app.analytics.exceptions import TargetValidationError

        if baseline_start > baseline_end or period_start > period_end:
            raise TargetValidationError("Each start date must be on or before its end date.")
        if baseline_end >= period_start:
            raise TargetValidationError("The baseline must finish before the target period.")
        self.baseline_start = baseline_start
        self.baseline_end = baseline_end
        self.period_start = period_start
        self.period_end = period_end

    # --- Encapsulation: Getters & Setters (UML S2 & Hometask 1) ---
    def get_target(self) -> float:
        """Accessor (getter) for target reduction percentage (UML S2)."""
        return float(self.reduction_percent)

    def set_target(self, reduction_percent: float) -> None:
        """Mutator (setter) for target reduction percentage with validation (UML S2)."""
        from app.analytics.exceptions import TargetValidationError

        try:
            value = float(reduction_percent)
        except (TypeError, ValueError):
            raise TargetValidationError("Enter a valid reduction percentage.") from None
        if not isfinite(value) or not 0 < value <= 100:
            raise TargetValidationError("Reduction must be greater than 0% and at most 100%.")
        self.reduction_percent = value

    def is_data_complete(self) -> bool:
        """Accessor (getter) for reporting completeness status."""
        return bool(self.data_complete)

    def set_data_complete(self, complete: bool) -> None:
        """Mutator (setter) for reporting completeness status."""
        self.data_complete = bool(complete)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "baseline_start": self.baseline_start.isoformat() if self.baseline_start else None,
            "baseline_end": self.baseline_end.isoformat() if self.baseline_end else None,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "reduction_percent": self.reduction_percent,
            "data_complete": self.data_complete,
        }


# Alias matching the S2 Capstone UML diagram class name
ReductionTarget = Target