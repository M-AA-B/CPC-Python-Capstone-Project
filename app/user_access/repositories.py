"""S3 Database Access Layer (Hometask 3) — Owner: Junaid Ahmad · 7222074.

Every S3 query goes through a repository that is bound to ONE company, so a
user can never read or change another company's rows by guessing an id.
Works the same on SQLite, PostgreSQL and MySQL (SQLAlchemy ORM, no raw SQL).
"""
from __future__ import annotations

from app.extensions import db
from app.models.user import Role, User
from app.user_access.exceptions import AccessDeniedError, InvalidInputError


class CompanyScopedRepository:
    """Base class: all reads and writes are limited to `company_id`.

    Subclasses set `model` to a table that has a `company_id` column, or
    override `_scoped_query()` when the company is reached through a join.
    """

    model = None

    def __init__(self, company_id: str):
        if not company_id:
            raise AccessDeniedError("A repository needs the company of the logged-in user.")
        self._company_id = company_id

    def get_company_id(self) -> str:
        return self._company_id

    def _scoped_query(self):
        return db.select(self.model).filter_by(company_id=self._company_id)

    def get(self, item_id: str):
        """The row with this id, or None if it does not exist or belongs to another company."""
        return db.session.scalar(self._scoped_query().filter(self.model.id == item_id))

    def list(self) -> list:
        return list(db.session.scalars(self._scoped_query()))

    def count(self) -> int:
        return db.session.scalar(db.select(db.func.count()).select_from(self._scoped_query().subquery()))

    def save(self, item) -> None:
        if getattr(item, "company_id", self._company_id) != self._company_id:
            raise AccessDeniedError("Cannot save a row that belongs to another company.")
        db.session.add(item)
        db.session.commit()


class UserRepository(CompanyScopedRepository):
    model = User

    def list(self, role: str | None = None) -> list[User]:
        query = self._scoped_query()
        if role:
            if role not in Role.ALL:
                raise InvalidInputError(f"Unknown role: {role!r}")
            query = query.filter_by(role=role)
        return list(db.session.scalars(query.order_by(User.email)))
