# Enterprise Carbon Footprint Tracker & AI Assistant — Hometask 1 (OOP Concepts)

**Group 13 — Compact Programming, FH Dortmund**

This branch (`Homeassignment1`) contains the pure Object-Oriented Programming (OOP) translation of our Group 13 Capstone Project UML class diagrams across all three subsystems. Every class implements explicit state initialization (`__init__`), configuration/setup methods, and encapsulated getters & setters with domain validation.

---

## Team Overview

| Team Member | Program | Matriculation ID | Assigned Subsystem | Implemented OOP Classes (≥ 3 per Member) |
|---|---|---|---|---|
| **Mohammed Al-Amine Bennani** | MDT | `7222047` | **S1 — Data Collection & Calculation** (`app/data_collection/`, `app/models/`) | `Company`, `Department`, `EmissionFactor`, `ActivityRecord`, `EmissionCalculator`, `CsvImporter` |
| **Vanessa Mukamanzi** | MDT | `7223964` | **S2 — Analytics & Dashboard** (`app/analytics/`, `app/models/target.py`) | `ReductionTarget`, `AnalyticsService`, `DashboardReport` |
| **Junaid Ahmad** | MDT | `7222074` | **S3 — AI Assistant & User Access** (`app/user_access/`, `app/ai_assistant/`, `app/models/`) | `User`, `ChatMessage`, `Recommendation`, `AuthService`, `PromptBuilder`, `AIAssistant` |

---

## Directory Structure

```text
.
├── README.md
├── demo.py                      # Runnable OOP demonstration across S1, S2, and S3
└── app/
    ├── models/                  # Domain models (Company, Department, EmissionFactor, ActivityRecord, Target, User, ChatMessage, Recommendation)
    ├── data_collection/         # S1 — Mohammed Al-Amine Bennani (7222047): EmissionCalculator, CsvImporter
    ├── analytics/               # S2 — Vanessa Mukamanzi (7223964): AnalyticsService, DashboardReport, CarbonScorer
    ├── user_access/             # S3 — Junaid Ahmad (7222074): AuthService
    └── ai_assistant/            # S3 — Junaid Ahmad (7222074): PromptBuilder, AIAssistant
```

---

## System Design (UML Class Diagrams)

### Subsystem 1 — Data Collection & Calculation (Mohammed Al-Amine Bennani · `7222047`)

```mermaid
classDiagram
    class Company {
        -str _id
        -str _name
        -str _industry
        -list _departments
        -int _employee_count
        +configure_profile(name, industry, employee_count) None
        +get_name() str
        +set_name(name) None
        +get_departments() list
        +get_total_employees() int
        +set_total_employees(count) None
    }

    class Department {
        -str _id
        -str _company_id
        -str _name
        -float _floor_area_m2
        -list _activity_records
        +configure_department(company_id, name, floor_area_m2) None
        +get_name() str
        +set_name(name) None
        +get_floor_area_m2() float
        +set_floor_area_m2(area) None
        +get_activity_records() list
    }

    class ActivityRecord {
        -str _id
        -str _department_id
        -EmissionFactor _factor
        -float _quantity
        -str _unit
        -float _calculated_co2e_kg
        -date _record_date
        +initialize_record(quantity, unit, record_date) None
        +get_quantity() float
        +set_quantity(value) None
        +get_unit() str
        +set_unit(unit) None
        +get_calculated_co2e_kg() float
        +is_valid() bool
        +update_quantity(new_val) None
    }

    class EmissionFactor {
        -int _id
        -str _category
        -float _kg_co2e_per_unit
        -str _unit
        -int _scope
        -int _valid_year
        +configure_factor(category, kg_co2e_per_unit, unit, scope, valid_year) None
        +get_kg_co2e_per_unit() float
        +set_kg_co2e_per_unit(value) None
        +is_active(year) bool
    }

    class EmissionCalculator {
        <<Service>>
        -int _precision
        -dict _scope_mapping
        -list _factors
        +reset_configuration() None
        +register_scope_category(category, scope) None
        +calculate(rec) float
        +assign_scope(category) int
        +fetch_factor(category, year) EmissionFactor
    }

    class CsvImporter {
        <<Service>>
        -str _encoding
        -list _error_log
        +initialize_session() None
        +read_file(csv_source) list
        +validate_row(row) bool
        +save_valid_rows() list
    }

    Company "1" o-- "*" Department
    Department "1" o-- "*" ActivityRecord
    ActivityRecord "*" --> "1" EmissionFactor
    EmissionCalculator ..> ActivityRecord : calculates
    EmissionCalculator ..> EmissionFactor : fetches
    CsvImporter ..> ActivityRecord : creates
```

### Subsystem 2 — Analytics & Dashboard (Vanessa Mukamanzi · `7223964`)

```mermaid
classDiagram
    class ReductionTarget {
        -int _target_id
        -float _baseline
        -float _target_percent
        +configure_target(baseline, target_percent) None
        +get_baseline() float
        +set_baseline(baseline) None
        +get_target() float
        +set_target(target_percent) None
    }

    class AnalyticsService {
        <<Service>>
        -list _records
        -ReductionTarget _target
        -date _start_date
        -date _end_date
        -str _category_filter
        +reset_filters() None
        +configure_filters(start_date, end_date, category) None
        +get_records() list
        +set_records(records) None
        +filter_records(start_date, end_date, category) list
        +calculate_total() float
        +group_by_category() dict
        +calculate_score() float
    }

    class DashboardReport {
        <<Service>>
        -AnalyticsService _service
        -str _report_title
        -str _export_filename
        +configure_report(report_title, export_filename) None
        +get_report_title() str
        +set_report_title(title) None
        +generate_charts() dict
        +display_summary() dict
        +export_CSV() str
    }

    AnalyticsService ..> ReductionTarget : uses target
    DashboardReport --> AnalyticsService : formats result
```

### Subsystem 3 — AI Assistant & User Access (Junaid Ahmad · `7222074`)

```mermaid
classDiagram
    class User {
        -str _id
        -str _company_id
        -str _department_id
        -str _email
        -str _password_hash
        -str _role
        +initialize_account(email, password, role) None
        +get_email() str
        +set_email(email) None
        +get_role() str
        +set_role(role) None
        +set_password(password) None
        +check_password(password) bool
        +has_role(role) bool
    }

    class ChatMessage {
        -str _id
        -str _user_id
        -str _sender
        -str _content
        -datetime _created_at
        +initialize_message(sender, content) None
        +get_content() str
        +set_content(content) None
        +to_dict() dict
    }

    class Recommendation {
        -str _id
        -str _department_id
        -str _title
        -float _est_saving_kg
        -str _effort
        -str _status
        +initialize_recommendation(title, est_saving_kg, effort) None
        +get_status() str
        +set_status(status) None
        +accept() None
        +mark_done() None
        +reject() None
    }

    class AuthService {
        <<Service>>
        -str _default_company_id
        -dict _users_by_email
        -User _active_user
        +reset_session() None
        +register(email, password, role, company_id, department_id) User
        +login(email, password) User
        +require_role(role, user) bool
    }

    class PromptBuilder {
        <<Service>>
        -str _system_prompt
        -int _max_hotspots
        +configure_templates(system_prompt, max_hotspots) None
        +get_system_prompt() str
        +set_system_prompt(prompt) None
        +build_context(company_id, category_totals) dict
        +advice_prompt(hotspots, department_name) str
    }

    class AIAssistant {
        <<Service>>
        -str _model
        -PromptBuilder _prompt_builder
        -list _history
        +configure_assistant(model, clear_history) None
        +get_model() str
        +set_model(model) None
        +ask(user, question, context) ChatMessage
        +recommend(department_id, hotspots) list
        +summarise(month, category_totals) str
    }

    AuthService ..> User : manages
    AIAssistant --> PromptBuilder : uses
    AIAssistant ..> ChatMessage : stores
    AIAssistant ..> Recommendation : creates
```

---

## Running the OOP Verification Demo

No external libraries are required (Python 3.10+ standard library only):

```bash
python demo.py
```
