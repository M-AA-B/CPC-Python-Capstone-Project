import io
import os
# FORCE SQLite in-memory before any Flask/SQLAlchemy code is imported
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TESTING"] = "True"

import pytest
from app import create_app
from app.data_collection.calculations import EmissionCalculator
from app.data_collection.exceptions import (
    DataCollectionError,
    PeriodValidationError,
    RecordOwnershipError,
    UnitMismatchError,
    ValidationError,
)
from app.extensions import db
from app.models.company import Company
from app.models.department import Department
from app.models.emission_factor import EmissionFactor
from app.models.activity_record import ActivityRecord
from app.models.user import User

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })

    with app.app_context():
        db.create_all()
        
        # Seed test prerequisites with unique IDs
        company = Company(id="comp_test", name="Test Eco Corp", industry="Technology")
        department = Department(id="dept_test", company_id="comp_test", name="Operations", floor_area_m2=350.0)
        factor = EmissionFactor(
            id=999, 
            category="electricity", 
            unit="kWh", 
            kg_co2e_per_unit=0.42, 
            scope=2, 
            valid_year=2026
        )
        user = User(id="user_test", email="test@example.com", name="Test User")

        db.session.add_all([company, department, factor, user])
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

# --- Core Functionality Tests ---

def test_create_record_json_success(client):
    payload = {
        "user_id": "user_test",
        "department_id": "dept_test",
        "emission_factor_id": 999,
        "activity_value": 150.0,
        "date": "2026-03-01",
        "scope": 2
    }
    response = client.post("/activities/api/records", json=payload)
    assert response.status_code == 201
    assert "id" in response.get_json()

def test_validation_unit_mismatch(client):
    payload = {
        "user_id": "user_test",
        "department_id": "dept_test",
        "emission_factor_id": 999,
        "activity_value": 50.0,
        "unit": "liters",
        "date": "2026-03-02",
        "scope": 2
    }
    response = client.post("/activities/api/records", json=payload)
    assert response.status_code == 400
    assert "Unit mismatch" in response.get_json()["error"]

def test_csv_batch_upload_success(app, client):
    csv_content = (
        "department_id,emission_factor_id,activity_value,unit,date,scope\n"
        "dept_test,999,200.0,kWh,2026-03-03,2\n"
    )
    data = {
        "user_id": "user_test",
        "file": (io.BytesIO(bytes(csv_content, "utf-8")), "batch.csv")
    }
    response = client.post("/activities/api/upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 201
    assert response.get_json()["message"] == "Processed 1 records successfully."

def test_delete_record_ownership(app, client):
    with app.app_context():
        record = ActivityRecord(
            id="rec_test_1",
            user_id="user_test",
            department_id="dept_test",
            emission_factor_id=999,
            activity_value=100.0,
            unit="kWh",
            calculated_co2e=42.0,
            scope=2
        )
        db.session.add(record)
        db.session.commit()

    # User who owns the record can delete it
    response = client.delete("/activities/api/records/rec_test_1", json={"user_id": "user_test"})
    assert response.status_code in [200, 204]

    # Verify unauthorized deletion returns 403
    with app.app_context():
        rec2 = ActivityRecord(
            id="rec_test_2",
            user_id="user_test",
            department_id="dept_test",
            emission_factor_id=999,
            activity_value=50.0,
            unit="kWh",
            calculated_co2e=21.0,
            scope=2
        )
        db.session.add(rec2)
        db.session.commit()

    unauthorized_res = client.delete("/activities/api/records/rec_test_2", json={"user_id": "other_user"})
    assert unauthorized_res.status_code == 403

# --- Hometask 3: Web APIs & Data Output Layer ---

def test_list_records_output_api(app, client):
    """Tests data output API endpoint with filtering and serialization (Hometask 3 & S1 FR8)."""
    with app.app_context():
        r = ActivityRecord(
            id="rec_output_1",
            user_id="user_test",
            department_id="dept_test",
            emission_factor_id=999,
            activity_value=300.0,
            unit="kWh",
            calculated_co2e=126.0,
            scope=2
        )
        db.session.add(r)
        db.session.commit()

    response = client.get("/activities/api/records?department_id=dept_test")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert any(item["id"] == "rec_output_1" for item in data)
    assert any(item["calculated_co2e"] == 126.0 for item in data)

def test_edit_record_api(app, client):
    """Tests updating an existing record with recalculation and ownership check (S1 FR9)."""
    with app.app_context():
        r = ActivityRecord(
            id="rec_edit_1",
            user_id="user_test",
            department_id="dept_test",
            emission_factor_id=999,
            activity_value=100.0,
            unit="kWh",
            calculated_co2e=42.0,
            scope=2
        )
        db.session.add(r)
        db.session.commit()

    # Successful edit with automatic CO2e recalculation
    update_res = client.put(
        "/activities/api/records/rec_edit_1",
        json={"user_id": "user_test", "quantity": 250.0}
    )
    assert update_res.status_code == 200
    updated_data = update_res.get_json()["record"]
    assert updated_data["quantity"] == 250.0
    assert updated_data["co2e_kg"] == 105.0  # 250.0 * 0.42

    # Forbidden edit by another user
    forbidden_res = client.put(
        "/activities/api/records/rec_edit_1",
        json={"user_id": "impostor_user", "quantity": 500.0}
    )
    assert forbidden_res.status_code == 403

# --- Hometask 2: Real-Time Processing ---

def test_realtime_calculate_api(client):
    """Tests synchronous calculation endpoint without database storage (Hometask 2)."""
    payload = {
        "quantity": 500.0,
        "factor_id": 999
    }
    response = client.post("/activities/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["calculated_co2e_kg"] == 210.0  # 500 * 0.42
    assert data["scope"] == 2

# --- Hometask 1: Object-Oriented Concepts (UML Classes & Methods) ---

def test_emission_calculator_service():
    """Tests EmissionCalculator service class methods (UML S1)."""
    calc = EmissionCalculator()
    assert calc.calculate(100.0, 0.42) == 42.0
    assert calc.assign_scope("electricity") == 2
    assert calc.assign_scope("company_vehicles") == 1
    assert calc.assign_scope("business_travel") == 3

    with pytest.raises(ValueError):
        calc.calculate(-10.0, 0.42)

def test_oop_domain_methods(app):
    """Tests OOP methods on domain models matching Group 13 UML class diagram."""
    with app.app_context():
        comp = db.session.get(Company, "comp_test")
        dept = db.session.get(Department, "dept_test")
        factor = db.session.get(EmissionFactor, 999)

        assert dept in comp.get_departments()
        assert factor.is_active(2026) is True
        assert factor.is_active(2020) is False

        rec = ActivityRecord(
            user_id="user_test",
            department_id="dept_test",
            emission_factor_id=999,
            activity_value=10.0,
            unit="kWh",
            calculated_co2e=4.2,
            scope=2
        )
        assert rec.is_valid() is True
        rec.factor = factor
        rec.update_quantity(20.0)
        assert rec.quantity == 20.0
        assert rec.co2e_kg == 8.4

# --- Hometask 4: Custom Exception Hierarchy ---

def test_custom_exception_hierarchy():
    """Tests Subsystem 1 custom exception hierarchy."""
    assert issubclass(UnitMismatchError, (ValidationError, DataCollectionError))
    assert issubclass(PeriodValidationError, (ValidationError, DataCollectionError))
    assert issubclass(RecordOwnershipError, DataCollectionError)

    err = UnitMismatchError("liters", "kWh")
    assert err.status_code == 400
    assert "Unit mismatch" in str(err)
