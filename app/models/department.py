import uuid

from app.extensions import db


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.String(36), db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    floor_area_m2 = db.Column(db.Float)
    
    # Cascades deletion: removing a department removes its activity records
    records = db.relationship('ActivityRecord', backref='department', lazy=True, cascade='all, delete-orphan')

    def get_activity_records(self) -> list:
        """Returns all activity records registered under this department."""
        return list(self.records)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "floor_area_m2": self.floor_area_m2,
            "record_count": len(self.records)
        }
