import traceback
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from app.data_collection.calculations import EmissionCalculator, calculate_emissions, assign_scope
from app.data_collection.csv_import import CsvImporter
from app.data_collection.exceptions import (
    DataCollectionError,
    RecordOwnershipError,
    ResourceNotFoundError,
    ValidationError,
)
from app.data_collection.services import (
    create_activity_record,
    delete_activity_record,
    get_activity_records,
    update_activity_record,
)
from app.extensions import db
from app.models.emission_factor import EmissionFactor

s1_bp = Blueprint('data', __name__, url_prefix='/activities')


@s1_bp.errorhandler(DataCollectionError)
def handle_s1_error(error):
    """Centralized error-handling for all Subsystem 1 custom domain exceptions (Hometask 4)."""
    return jsonify(error.to_dict()), error.status_code


@s1_bp.route('/', methods=['GET'])
@s1_bp.route('/form', methods=['GET'])
def index():
    """Renders the HTML data entry form interface with existing records and active factors."""
    try:
        records = get_activity_records()
        factors = EmissionFactor.query.all()
    except Exception:
        records = []
        factors = []
    return render_template('data_collection/record_form.html', records=records, factors=factors)


@s1_bp.route('/api/records', methods=['GET'])
def list_records():
    """Outputs searchable and sortable activity records as JSON (Hometask 3 & S1 FR8)."""
    filters = {
        'company_id': request.args.get('company_id'),
        'department_id': request.args.get('department_id'),
        'category': request.args.get('category'),
        'scope': request.args.get('scope'),
        'created_by': request.args.get('user_id'),
        'sort': request.args.get('sort', 'created_at'),
        'order': request.args.get('order', 'desc')
    }
    # Remove empty query params
    filters = {k: v for k, v in filters.items() if v}
    records = get_activity_records(filters)
    return jsonify([r.to_dict() for r in records]), 200


@s1_bp.route('/api/records/<record_id>', methods=['GET'])
def get_record(record_id):
    """Fetches a single activity record by ID (Hometask 3)."""
    records = get_activity_records()
    record = next((r for r in records if str(r.id) == str(record_id)), None)
    if not record:
        raise ResourceNotFoundError("ActivityRecord", record_id)
    return jsonify(record.to_dict()), 200


@s1_bp.route('/api/records', methods=['POST'])
@s1_bp.route('/api/records/create', methods=['POST'])
def create_record():
    """JSON API endpoint to create a single activity record."""
    data = request.json or {}
    user_id = data.get('user_id') or data.get('current_user_id')
    
    try:
        record = create_activity_record(data, user_id)
        return jsonify({"message": "Record created successfully", "id": str(record.id)}), 201
    except DataCollectionError as e:
        return jsonify(e.to_dict()), e.status_code
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@s1_bp.route('/api/records/<record_id>', methods=['PUT', 'PATCH'])
def edit_record(record_id):
    """JSON API endpoint to edit an existing activity record with ownership check (S1 FR9)."""
    data = request.json or {}
    user_id = data.get('user_id') or data.get('current_user_id')
    if not user_id:
        return jsonify({"error": "User ID is required for authorization"}), 400

    try:
        updated = update_activity_record(record_id, data, user_id)
        return jsonify({"message": "Record updated successfully", "record": updated.to_dict()}), 200
    except DataCollectionError as e:
        return jsonify(e.to_dict()), e.status_code
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@s1_bp.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    """JSON API endpoint to delete an activity record with ownership check."""
    data = request.json or {}
    user_id = data.get('user_id') or data.get('current_user_id')
    
    try:
        delete_activity_record(record_id, user_id)
        return jsonify({"message": "Record deleted successfully"}), 200
    except DataCollectionError as e:
        return jsonify(e.to_dict()), e.status_code
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@s1_bp.route('/api/calculate', methods=['POST'])
def live_calculate():
    """Real-time calculation preview endpoint without DB persistence (Hometask 2)."""
    data = request.json or {}
    quantity = data.get('quantity')
    factor_id = data.get('factor_id')
    category = data.get('category')

    if quantity is None:
        return jsonify({"error": "Quantity is required"}), 400

    factor_value = data.get('factor_kg_co2e')
    scope = None
    if factor_id:
        factor = db.session.get(EmissionFactor, int(factor_id))
        if factor:
            factor_value = factor.kg_co2e_per_unit
            scope = factor.scope
            category = category or factor.category

    if factor_value is None:
        return jsonify({"error": "Valid factor_id or factor_kg_co2e is required"}), 400

    try:
        co2e = calculate_emissions(float(quantity), float(factor_value))
        if scope is None and category:
            scope = assign_scope(category)
        return jsonify({
            "quantity": float(quantity),
            "factor_kg_co2e": float(factor_value),
            "calculated_co2e_kg": co2e,
            "scope": scope
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@s1_bp.route('/api/factors', methods=['GET'])
def list_factors():
    """Returns active emission factors for dropdowns and external subsystems."""
    factors = EmissionFactor.query.all()
    return jsonify([f.to_dict() for f in factors]), 200


@s1_bp.route('/submit', methods=['POST'])
def handle_form_submission():
    """Handles standard HTML form POST submissions."""
    data = {
        "company_id": request.form.get('company_id'),
        "department_id": request.form.get('department_id'),
        "factor_id": request.form.get('factor_id', 1),
        "period_start": request.form.get('period_start'),
        "period_end": request.form.get('period_end'),
        "category": request.form.get('category'),
        "quantity": request.form.get('quantity', 0),
        "unit": request.form.get('unit'),
        "factor_unit": request.form.get('factor_unit', request.form.get('unit')),
        "factor_kg_co2e": request.form.get('factor_kg_co2e', 0.42)
    }
    user_id = request.form.get('current_user_id') or request.form.get('user_id', 'user-123')
    
    try:
        record = create_activity_record(data, user_id)
        flash(f"Activity record created! Calculated: {record.co2e_kg} kg CO2e", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        
    return redirect(url_for('data.index'))


@s1_bp.route('/api/upload', methods=['POST'])
@s1_bp.route('/api/records/upload-csv', methods=['POST'])
def upload_csv():
    """Processes bulk activity records uploaded via CSV file using CsvImporter service (Hometask 1)."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    user_id = request.form.get('user_id') or request.form.get('current_user_id', 'user-123')
    
    try:
        importer = CsvImporter()
        result = importer.process(file, user_id)
        status_code = 201 if result["inserted"] > 0 else 400
        return jsonify({
            "message": f"Processed {result['inserted']} records successfully.",
            "errors": result["errors"]
        }), status_code
    except Exception as e:
        return jsonify({"error": f"Failed to parse CSV file: {str(e)}"}), 400
