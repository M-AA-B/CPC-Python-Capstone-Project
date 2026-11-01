"""S3 - AI Assistant. Owner: Junaid. One call to OpenAI, used for the daily limit per company."""
import uuid
from datetime import datetime, timezone

from app.extensions import db


class AIRequest(db.Model):
    __tablename__ = 'ai_requests'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    kind = db.Column(db.String(20), nullable=False)  # "chat", "recommend" or "summary"
    succeeded = db.Column(db.Boolean, nullable=False, default=False)
    total_tokens = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
