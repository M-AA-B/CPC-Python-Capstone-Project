"""S3 Database Access Layer for the AI assistant (Hometask 3) — Owner: Junaid Ahmad · 7222074."""
from __future__ import annotations

from datetime import datetime, time, timezone

from app.extensions import db
from app.models.ai_request import AIRequest
from app.models.chat_message import ChatMessage
from app.models.recommendation import Recommendation, Status
from app.models.user import Role, User
from app.user_access.repositories import CompanyScopedRepository


class RecommendationRepository(CompanyScopedRepository):
    model = Recommendation

    # Which status may follow which: a rejected or finished tip cannot be reopened.
    ALLOWED_TRANSITIONS = {
        Status.PROPOSED: (Status.ACCEPTED, Status.REJECTED),
        Status.ACCEPTED: (Status.DONE, Status.REJECTED),
        Status.REJECTED: (),
        Status.DONE: (),
    }

    def visible_to(self, user: User):
        """Admins and managers see the whole company; employees only their own department."""
        query = self._scoped_query()
        if user.has_role(Role.EMPLOYEE):
            query = query.filter_by(department_id=user.department_id)
        return query

    def list_for(self, user: User, status: str | None = None,
                 department_id: str | None = None) -> list[Recommendation]:
        query = self.visible_to(user)
        if status:
            if status not in Status.ALL:
                raise ValueError(f"Unknown status: {status!r}")
            query = query.filter_by(status=status)
        if department_id:
            query = query.filter_by(department_id=department_id)
        return list(db.session.scalars(query.order_by(Recommendation.created_at.desc())))

    def get_for(self, user: User, recommendation_id: str) -> Recommendation | None:
        return db.session.scalar(self.visible_to(user).filter(Recommendation.id == recommendation_id))

    def change_status(self, recommendation: Recommendation, new_status: str) -> Recommendation:
        """Moves a tip along its workflow. ValueError if the step is not allowed."""
        if new_status not in Status.ALL:
            raise ValueError(f"Unknown status: {new_status!r}")
        if new_status not in self.ALLOWED_TRANSITIONS[recommendation.status]:
            raise ValueError(f"A {recommendation.status} recommendation cannot become {new_status}.")
        recommendation.status = new_status
        self.save(recommendation)
        return recommendation


class ChatMessageRepository(CompanyScopedRepository):
    """Chat messages have no company column: the company is reached through the user."""

    model = ChatMessage

    def _scoped_query(self):
        return (db.select(ChatMessage).join(User, ChatMessage.user_id == User.id)
                .filter(User.company_id == self._company_id))

    def history(self, user_id: str, limit: int = 50) -> list[ChatMessage]:
        """The user's last `limit` messages, oldest first."""
        newest_first = db.session.scalars(
            self._scoped_query().filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc()).limit(limit)
        ).all()
        return list(reversed(newest_first))

    def save(self, item) -> None:
        owner = db.session.get(User, item.user_id)
        if owner is None or owner.company_id != self._company_id:
            raise PermissionError("Cannot save a message for a user of another company.")
        db.session.add(item)
        db.session.commit()


class AIRequestRepository(CompanyScopedRepository):
    model = AIRequest

    def count_today(self) -> int:
        midnight = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return db.session.scalar(
            db.select(db.func.count()).select_from(
                self._scoped_query().filter(AIRequest.created_at >= midnight).subquery()
            )
        )

    def tokens_today(self) -> int:
        midnight = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        total = db.session.scalar(
            db.select(db.func.coalesce(db.func.sum(AIRequest.total_tokens), 0))
            .where(AIRequest.company_id == self._company_id, AIRequest.created_at >= midnight)
        )
        return int(total or 0)
