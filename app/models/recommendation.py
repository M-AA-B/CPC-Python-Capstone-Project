"""S3 - AI Assistant. Owner: Junaid. An AI-generated reduction tip for one department."""
import uuid
from datetime import datetime, timezone

from app.extensions import db


class Effort:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    ALL = (LOW, MEDIUM, HIGH)


class Status:
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DONE = "done"

    ALL = (PROPOSED, ACCEPTED, REJECTED, DONE)


def _now():
    return datetime.now(timezone.utc)


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    est_saving_kg = db.Column(db.Float, nullable=False)   # estimated CO2e saving per year
    est_cost_eur = db.Column(db.Float, nullable=True)     # None = unknown
    effort = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False, default=Status.PROPOSED)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    department = db.relationship('Department')

    __table_args__ = (
        db.CheckConstraint("est_saving_kg >= 0", name="ck_recommendation_saving"),
        db.CheckConstraint("effort IN ('low', 'medium', 'high')", name="ck_recommendation_effort"),
        db.CheckConstraint("status IN ('proposed', 'accepted', 'rejected', 'done')",
                           name="ck_recommendation_status"),
    )

    def accept(self) -> None:
        self.status = Status.ACCEPTED

    def reject(self) -> None:
        self.status = Status.REJECTED

    def mark_done(self) -> None:
        self.status = Status.DONE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "department_id": self.department_id,
            "title": self.title,
            "description": self.description,
            "est_saving_kg": self.est_saving_kg,
            "est_cost_eur": self.est_cost_eur,
            "effort": self.effort,
            "status": self.status,
        }
