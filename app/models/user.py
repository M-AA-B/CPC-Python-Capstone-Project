"""S3 - User Access. Owner: Junaid.

A user belongs to one company and (for managers and employees) one department.
S1 and S2 use the logged-in user via flask_login.current_user, e.g. current_user.company_id.
"""
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role:
    """The three roles. Stored as plain text in users.role."""

    ADMIN = "admin"        # manages the company, departments and users
    MANAGER = "manager"    # enters activity data, sets targets, uses the AI assistant
    EMPLOYEE = "employee"  # views the dashboard and tips

    ALL = (ADMIN, MANAGER, EMPLOYEE)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)

    # Nullable so older seed/test users (id, email, name only) still work.
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=True, index=True)
    # None for admins, who are not part of a single department.
    department_id = db.Column(db.String(36), db.ForeignKey('departments.id'), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, default=Role.EMPLOYEE)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint("role IN ('admin', 'manager', 'employee')", name="ck_user_role"),
    )

    company = db.relationship('Company', backref='users')
    department = db.relationship('Department')

    def set_password(self, password: str) -> None:
        """Store only a salted hash (werkzeug scrypt), never the password itself."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles: str) -> bool:
        return self.role in roles

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "company_id": self.company_id,
            "department_id": self.department_id,
            "role": self.role,
        }
