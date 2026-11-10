from datetime import date, datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import db
from app.models.activity_record import ActivityRecord
from app.models.company import Company
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.target import Target
from app.models.user import Role, User

app = create_app()
with app.app_context():
    db.create_all()

    # 1. Companies
    demo_company = Company(id="123e4567-e89b-12d3-a456-426614174000", name="Test Corp", industry="Tech")
    legacy_company = Company(id="comp_001", name="Legacy Eco Corp", industry="Manufacturing")
    db.session.merge(demo_company)
    db.session.merge(legacy_company)

    # 2. Departments
    dept_it = Department(id="123e4567-e89b-12d3-a456-426614174001", company_id=demo_company.id, name="IT", floor_area_m2=500.0)
    dept_hq = Department(id="1", company_id=legacy_company.id, name="HQ", floor_area_m2=1000.0)
    dept_ops = Department(id="2", company_id=legacy_company.id, name="Operations", floor_area_m2=1500.0)
    for d in (dept_it, dept_hq, dept_ops):
        db.session.merge(d)

    # 3. Seed Users for Test Corp
    # Admin: admin@testcorp.com | Admin1 | Admin | IT | password123
    admin_user = User.query.filter_by(id="user-123").first()
    if not admin_user:
        admin_user = User.query.filter_by(email="admin@testcorp.com").first()
    if not admin_user:
        admin_user = User.query.filter_by(email="test@example.com").first()
    
    if not admin_user:
        admin_user = User(
            id="user-123",
            email="admin@testcorp.com",
            name="Admin1",
            company_id=demo_company.id,
            department_id=dept_it.id,
            role=Role.ADMIN
        )
    else:
        admin_user.email = "admin@testcorp.com"
        admin_user.company_id = demo_company.id
        admin_user.department_id = dept_it.id
        admin_user.role = Role.ADMIN
        admin_user.name = "Admin1"
    admin_user.set_password("password123")
    db.session.add(admin_user)
    db.session.flush()

    # Employee: employee@testcorp.com | Employee1 | Employee | IT | password123
    emp_user = User.query.filter_by(id="user-124").first()
    if not emp_user:
        emp_user = User.query.filter_by(email="employee@testcorp.com").first()
    if not emp_user:
        emp_user = User.query.filter_by(email="test1@example.com").first()

    if not emp_user:
        emp_user = User(
            id="user-124",
            email="employee@testcorp.com",
            name="Employee1",
            company_id=demo_company.id,
            department_id=dept_it.id,
            role=Role.EMPLOYEE
        )
    else:
        emp_user.email = "employee@testcorp.com"
        emp_user.company_id = demo_company.id
        emp_user.department_id = dept_it.id
        emp_user.role = Role.EMPLOYEE
        emp_user.name = "Employee1"
    emp_user.set_password("password123")
    db.session.add(emp_user)
    db.session.flush()

    # Clean up any leftover test accounts with old emails that aren't admin_user or emp_user
    leftover_test_users = User.query.filter(
        User.email.in_(["test@example.com", "test1@example.com"]),
        User.id.notin_([admin_user.id, emp_user.id])
    ).all()
    for lu in leftover_test_users:
        db.session.delete(lu)
    db.session.flush()

    # 4. Standard Emission Factors
    factors = [
        EmissionFactor(id=1, category="electricity", kg_co2e_per_unit=0.42, unit="kWh", scope=2, valid_year=2026),
        EmissionFactor(id=2, category="natural_gas", kg_co2e_per_unit=2.03, unit="m3", scope=1, valid_year=2026),
        EmissionFactor(id=3, category="diesel", kg_co2e_per_unit=2.68, unit="liters", scope=1, valid_year=2026),
        EmissionFactor(id=4, category="flight", kg_co2e_per_unit=0.15, unit="km", scope=3, valid_year=2026),
        EmissionFactor(id=5, category="waste", kg_co2e_per_unit=0.50, unit="kg", scope=3, valid_year=2026),
    ]
    for f in factors:
        db.session.merge(f)

    # 5. Clean & Calibrated Target for Test Corp (Baseline: August 2026, Evaluation: October 2026)
    Target.query.filter_by(company_id=demo_company.id).delete()
    Target.query.filter_by(company_id=legacy_company.id).delete()
    db.session.flush()

    target_demo = Target(
        id="target-demo-001",
        company_id=demo_company.id,
        baseline_start=date(2026, 8, 1),
        baseline_end=date(2026, 8, 31),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        reduction_percent=20.0,
        data_complete=True,
        created_at=datetime.now(timezone.utc)
    )
    db.session.merge(target_demo)

    # Target for legacy company
    target_legacy = Target(
        id="target-legacy-001",
        company_id=legacy_company.id,
        baseline_start=date(2026, 8, 1),
        baseline_end=date(2026, 8, 31),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        reduction_percent=20.0,
        data_complete=True,
        created_at=datetime.now(timezone.utc)
    )
    db.session.merge(target_legacy)

    # 6. Activity records
    # Delete old activity records first before inserting new ones
    ActivityRecord.query.filter_by(company_id=demo_company.id).delete()
    ActivityRecord.query.filter_by(company_id=legacy_company.id).delete()
    db.session.flush()

    # Calibrated baseline: August 2026: 10,000 kWh electricity = 4,200 kg CO2e
    baseline_demo = ActivityRecord(
        id="baseline-rec-demo-001",
        company_id=demo_company.id,
        department_id=dept_it.id,
        factor_id=1,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        category="electricity",
        quantity=10000.0,
        unit="kWh",
        co2e_kg=4200.0,
        scope=2,
        created_by=admin_user.id
    )
    # Calibrated evaluation: October 2026: 8,600 kWh electricity = 3,612 kg CO2e
    # Target: 20% reduction from 4,200 kg = 840 kg -> Score = 70.0 / 100
    eval_demo = ActivityRecord(
        id="eval-rec-demo-001",
        company_id=demo_company.id,
        department_id=dept_it.id,
        factor_id=1,
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        category="electricity",
        quantity=8600.0,
        unit="kWh",
        co2e_kg=3612.0,
        scope=2,
        created_by=admin_user.id
    )
    db.session.merge(baseline_demo)
    db.session.merge(eval_demo)

    # Activity records for legacy company
    baseline_legacy = ActivityRecord(
        id="baseline-rec-legacy-001",
        company_id=legacy_company.id,
        department_id=dept_hq.id,
        factor_id=1,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        category="electricity",
        quantity=10000.0,
        unit="kWh",
        co2e_kg=4200.0,
        scope=2,
        created_by=admin_user.id
    )
    db.session.merge(baseline_legacy)

    # 7. For other user-created companies, clear records so they start clean
    for company in Company.query.all():
        if company.id not in (demo_company.id, legacy_company.id):
            ActivityRecord.query.filter_by(company_id=company.id).delete()
            if not Target.query.filter_by(company_id=company.id).first():
                t = Target(
                    company_id=company.id,
                    baseline_start=date(2026, 8, 1),
                    baseline_end=date(2026, 8, 31),
                    period_start=date(2026, 10, 1),
                    period_end=date(2026, 10, 31),
                    reduction_percent=20.0,
                    data_complete=True,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(t)

    db.session.commit()
    print("Database seeded successfully with demo users, company, targets, calibrated records, and factors.")
