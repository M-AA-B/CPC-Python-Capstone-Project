import uuid
from datetime import datetime, timezone

from app.extensions import db


class Target(db.Model):
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