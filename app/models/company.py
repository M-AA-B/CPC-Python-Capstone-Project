import uuid

from app.extensions import db


class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    industry = db.Column(db.String(100))
    
    # Cascades deletion: removing a company removes its departments
    departments = db.relationship('Department', backref='company', lazy=True, cascade='all, delete-orphan')

    def get_departments(self) -> list:
        """Returns the list of departments belonging to this company."""
        return list(self.departments)

    def get_total_employees(self) -> int:
        """Calculates or returns total employees across all departments (placeholder for S3)."""
        return 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "industry": self.industry,
            "department_count": len(self.departments)
        }
