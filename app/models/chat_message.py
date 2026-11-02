"""S3 Domain Model: ChatMessage (Owner: Junaid Ahmad · 7222074)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone


class ChatMessage:
    """Represents a single user or AI coach message in conversation history (UML S3)."""

    VALID_SENDERS = ("user", "assistant")

    def __init__(
        self,
        user_id: str,
        sender: str,
        content: str,
        created_at: datetime | None = None,
        message_id: str | None = None,
    ):
        """Constructor: Proper state initialization."""
        self._id: str = message_id or str(uuid.uuid4())
        self._user_id: str = user_id
        self._sender: str = "user"
        self._content: str = ""
        self._created_at: datetime = created_at or datetime.now(timezone.utc)
        self.initialize_message(sender=sender, content=content)

    # --- Initialization / Setup Method ---
    def initialize_message(self, sender: str, content: str) -> None:
        """Validates sender role and non-empty message body."""
        self.set_sender(sender)
        self.set_content(content)

    # --- Encapsulation: Getters & Setters ---
    def get_id(self) -> str:
        return self._id

    def get_user_id(self) -> str:
        return self._user_id

    def get_sender(self) -> str:
        return self._sender

    def set_sender(self, sender: str) -> None:
        cleaned = (sender or "").strip().lower()
        if cleaned not in self.VALID_SENDERS:
            raise ValueError(f"Sender must be one of {self.VALID_SENDERS}.")
        self._sender = cleaned

    def get_content(self) -> str:
        return self._content

    def set_content(self, content: str) -> None:
        cleaned = (content or "").strip()
        if not cleaned:
            raise ValueError("Message content cannot be empty.")
        self._content = cleaned

    def get_created_at(self) -> datetime:
        return self._created_at

    # --- UML Domain Method ---
    def to_dict(self) -> dict:
        """UML method: serializes chat message attributes."""
        return {
            "id": self._id,
            "user_id": self._user_id,
            "sender": self._sender,
            "content": self._content,
            "created_at": self._created_at.isoformat(),
        }
