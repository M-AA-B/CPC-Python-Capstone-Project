"""S3 - User Access. Owner: Junaid.

Registration, login and user management. Page protection (require_role, CSRF)
is in permissions.py.
"""
import re

from flask import render_template
from flask_login import login_user, logout_user

from app.extensions import db, login_manager
from app.models.company import Company
from app.models.department import Department
from app.models.user import Role, User
from app.user_access.permissions import csrf_token

MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(ValueError):
    """A problem the user can fix; the message is shown on the form."""


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, user_id)


def register_user_access(app) -> None:
    """Called once from create_app()."""
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("user_access/403.html"), 403


class AuthService:

    @staticmethod
    def normalise_email(email: str) -> str:
        return (email or "").strip().lower()

    @classmethod
    def _check_new_account(cls, email: str, password: str) -> str:
        email = cls.normalise_email(email)
        if not EMAIL_PATTERN.match(email) or len(email) > 120:
            raise AuthError("Please enter a valid email address.")
        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if db.session.scalar(db.select(User).filter_by(email=email)):
            raise AuthError("An account with this email already exists.")
        return email

    @classmethod
    def register(cls, company_name: str, email: str, password: str,
                 departments: list[str] | None = None, name: str | None = None) -> User:
        """Create a new company with its departments; its first user becomes the admin."""
        company_name = (company_name or "").strip()
        if not company_name:
            raise AuthError("Please enter a company name.")
        email = cls._check_new_account(email, password)
        if db.session.scalar(db.select(Company).filter_by(name=company_name)):
            raise AuthError("This company is already registered. Ask its admin to add you.")

        company = Company(name=company_name)
        db.session.add(company)
        db.session.flush()

        # dict.fromkeys removes duplicates but keeps the order
        for dept_name in dict.fromkeys(d.strip() for d in departments or [] if d.strip()):
            db.session.add(Department(company_id=company.id, name=dept_name))

        user = User(company_id=company.id, email=email, name=(name or "").strip() or None,
                    role=Role.ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def create_user(cls, admin: User, email: str, password: str, role: str,
                    department_id: str | None = None, name: str | None = None) -> User:
        """An admin adds a manager or employee (or another admin) to their own company."""
        if not admin.has_role(Role.ADMIN):
            raise AuthError("Only admins can add users.")
        email = cls._check_new_account(email, password)
        if role not in Role.ALL:
            raise AuthError("Unknown role.")

        if department_id:
            department = db.session.get(Department, department_id)
            if department is None or department.company_id != admin.company_id:
                raise AuthError("Unknown department.")
        elif role != Role.ADMIN:
            raise AuthError("Managers and employees need a department.")

        user = User(company_id=admin.company_id, department_id=department_id or None,
                    email=email, name=(name or "").strip() or None, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate(cls, email: str, password: str) -> User | None:
        user = db.session.scalar(db.select(User).filter_by(email=cls.normalise_email(email)))
        if user is None or not user.check_password(password or ""):
            return None
        return user

    @classmethod
    def login(cls, email: str, password: str, remember: bool = False) -> User | None:
        user = cls.authenticate(email, password)
        if user is not None:
            login_user(user, remember=remember)
        return user

    @staticmethod
    def logout() -> None:
        logout_user()

    @staticmethod
    def company_users(company_id: str) -> list[User]:
        return db.session.scalars(
            db.select(User).filter_by(company_id=company_id).order_by(User.email)
        ).all()

    @staticmethod
    def company_departments(company_id: str) -> list[Department]:
        return db.session.scalars(
            db.select(Department).filter_by(company_id=company_id).order_by(Department.name)
        ).all()
