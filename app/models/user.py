"""S3 Domain Models: User, ChatMessage, Recommendation.

Owner: Junaid Ahmad (7222074)
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone


class User:
    """Represents an authenticated platform user with company/department scope and role (UML S3)."""

    VALID_ROLES = ("admin", "manager", "employee")

    def __init__(
        self,
        company_id: str,
        email: str,
        password: str,
        role: str = "employee",
        department_id: str | None = None,
        user_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = user_id or str(uuid.uuid4())
        self._company_id: str = company_id
        self._department_id: str | None = department_id
        self._email: str = ""
        self._password_hash: str = ""
        self._role: str = "employee"
        self.initialize_account(email=email, password=password, role=role)

    # --- Initialization / Setup Method ---
    def initialize_account(self, email: str, password: str, role: str = "employee") -> None:
        """Normalizes email, validates role, and hashes initial password."""
        self.set_email(email)
        self.set_role(role)
        self.set_password(password)

    # --- Encapsulation: Getters & Setters ---
    def get_id(self) -> str:
        return self._id

    def get_company_id(self) -> str:
        return self._company_id

    def get_department_id(self) -> str | None:
        return self._department_id

    def set_department_id(self, department_id: str | None) -> None:
        self._department_id = department_id

    def get_email(self) -> str:
        return self._email

    def set_email(self, email: str) -> None:
        cleaned = (email or "").strip().lower()
        if "@" not in cleaned:
            raise ValueError("Invalid email address.")
        self._email = cleaned

    def get_role(self) -> str:
        return self._role

    def set_role(self, role: str) -> None:
        cleaned = (role or "").strip().lower()
        if cleaned not in self.VALID_ROLES:
            raise ValueError(f"Role must be one of {self.VALID_ROLES}.")
        self._role = cleaned

    def set_password(self, password: str) -> None:
        """Stores only a salted scrypt hash, never plaintext.

        scrypt is deliberately slow, so leaked hashes are hard to brute-force
        (a plain SHA-256 can be guessed billions of times per second).
        """
        if len(password or "") < 8:
            raise ValueError("Password must be at least 8 characters.")
        salt = secrets.token_hex(16)
        self._password_hash = f"scrypt${salt}${self._hash(password, salt)}"

    # --- UML Domain Methods ---
    @staticmethod
    def _hash(password: str, salt: str) -> str:
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt.encode("utf-8"), n=2**14, r=8, p=1
        ).hex()

    def check_password(self, password: str) -> bool:
        """UML method: verifies candidate password against stored salted hash."""
        parts = self._password_hash.split("$")
        if len(parts) != 3 or parts[0] != "scrypt":
            return False
        _method, salt, expected_digest = parts
        candidate = self._hash(password or "", salt)
        return secrets.compare_digest(candidate, expected_digest)

    def has_role(self, role: str) -> bool:
        """UML method: returns True if the user holds the specified role."""
        return self._role == (role or "").strip().lower()
