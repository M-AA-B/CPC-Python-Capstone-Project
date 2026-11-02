from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.company import Company
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.user import User

app = create_app()
with app.app_context():
    user = User(id="user-123", email="test@example.com", name="Test User")
    company = Company(id="123e4567-e89b-12d3-a456-426614174000", name="Test Corp", industry="Tech")
    dept = Department(id="123e4567-e89b-12d3-a456-426614174001", company_id=company.id, name="IT", floor_area_m2=500.0)
    factor = EmissionFactor(id=1, category="electricity", kg_co2e_per_unit=0.42, unit="kWh", scope=2, valid_year=2026)
    
    db.session.merge(user)
    db.session.merge(company)
    db.session.merge(dept)
    db.session.merge(factor)
    db.session.commit()
    print("Database seeded successfully.")