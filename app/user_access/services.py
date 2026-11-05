"""S3 Service Class: AuthService (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

from app.models import User


class AuthService:
    """Manages user registration, authentication, and role authorization (UML S3)."""

    def __init__(self, default_company_id: str = "default-company"):
        """Constructor: Proper state initialization."""
        self._default_company_id: str = default_company_id
        self._users_by_email: dict[str, User] = {}
        self._active_user: User | None = None
        self.reset_session()

    # --- Initialization / Setup Method ---
    def reset_session(self) -> None:
        """Clears currently logged-in session state."""
        self._active_user = None

    # --- Encapsulation: Getters & Setters ---
    def get_default_company_id(self) -> str:
        return self._default_company_id

    def set_default_company_id(self, company_id: str) -> None:
        cleaned = (company_id or "").strip()
        if not cleaned:
            raise ValueError("default_company_id cannot be empty.")
        self._default_company_id = cleaned

    def get_active_user(self) -> User | None:
        return self._active_user

    def get_registered_users(self) -> list[User]:
        return list(self._users_by_email.values())

    # --- UML Domain Methods ---
    def register(
        self,
        email: str,
        password: str,
        role: str = "employee",
        company_id: str | None = None,
        department_id: str | None = None,
    ) -> User:
        """UML method: registers a new User account with hashed password."""
        normalised = (email or "").strip().lower()
        if normalised in self._users_by_email:
            raise ValueError(f"Email {normalised!r} is already registered.")
        user = User(
            company_id=company_id or self._default_company_id,
            email=normalised,
            password=password,
            role=role,
            department_id=department_id,
        )
        self._users_by_email[normalised] = user
        return user

    def login(self, email: str, password: str) -> User | None:
        """UML method: authenticates credentials and updates active session user."""
        user = self._users_by_email.get((email or "").strip().lower())
        if user and user.check_password(password):
            self._active_user = user
            return user
        return None

    def require_role(self, role: str, user: User | None = None) -> bool:
        """UML method: checks whether the given (or active) user holds `role`."""
        target = user or self._active_user
        if target is None or not target.has_role(role):
            raise PermissionError(f"Role {role!r} is required.")
        return True
