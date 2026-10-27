"""TODO: Define the user SQLAlchemy model after team agreement.
See docs/data-contract.md. No database table is defined in this placeholder.
"""
from app.extensions import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)