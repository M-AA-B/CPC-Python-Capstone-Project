"""S3 - AI Assistant. Owner: Junaid. One message in a user's chat with the AI coach."""
import uuid
from datetime import datetime, timezone

from app.extensions import db


class Sender:
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    sender = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        db.CheckConstraint("sender IN ('user', 'assistant')", name="ck_chat_sender"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
