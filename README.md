# Enterprise Carbon Footprint Tracker & AI Assistant

**Group 13 — Compact Programming (Capstone Project), FH Dortmund**

Our platform helps small and mid-sized enterprises record operational activities across Scopes 1–3, stream real-time telemetry into metric tons of CO₂e, visualize emissions and Carbon Score progress on an interactive dashboard, and receive department-tailored reduction recommendations from an AI Sustainability Coach.

# Video Link: https://drive.google.com/file/d/1rdvxHfZwUQ5P8bO8CM_qvj3MuijpoXvl

---

## Team Overview & Student Identification

| Team Member | Program | Matriculation ID | Assigned Subsystem | Main Packages |
|---|---|---|---|---|
| **Mohammed Al-Amine Bennani** | MDT | `7222047` | **S1 — Data Collection, Calculation & Stream Processing** | `app/data_collection`, `app/models` |
| **Vanessa Mukamanzi** | MDT | `7223964` | **S2 — Analytics & Dashboard** | `app/analytics`, `app/models/target.py` |
| **Junaid Ahmad** | MDT | `7222074` | **S3 — AI Assistant & User Access** | `app/ai_assistant`, `app/user_access`, `app/models` |

---

## Current Features

- **S1 — Data Collection & Stream Processing:**
  - Manual activity entry forms, REST JSON CRUD endpoints (`/activities/api/records`), and bulk CSV import (`CsvImporter`).
  - Automated CO₂e calculation and GHG Protocol Scope 1–3 assignment (`EmissionCalculator`).
  - Event-driven real-time telemetry stream pipeline (`StreamProcessor`, `ScopeFilter`, `MetricTonCO2eTransformer`, `TelemetryStream`) converting flight bookings, server utility logs, and freight payloads into metric tons of CO₂e.
- **S2 — Analytics & Dashboard:**
  - Company-isolated emission totals, category breakdowns, and consecutive monthly comparisons (`AnalyticsService`).
  - Interactive Plotly bar charts, date/category filtering, and UTF-8 CSV report exports (`DashboardReport`).
  - Carbon reduction target management (`Target` / `ReductionTarget`) and bounded target-progress scoring (`CarbonScorer`).
- **S3 — AI Assistant & User Access:**
  - Company registration, salted password hashing, session authentication, CSRF protection, and role-based access control (`Admin`, `Manager`, `Employee`) via `AuthService` and `@require_role`.
  - Privacy-preserving AI Sustainability Coach (`AIAssistant`, `AIClient`, `PromptBuilder`) sending only aggregated company totals to OpenAI, with validated JSON department recommendations (`Recommendation`) and plain-language monthly summaries.

---

## System Design & UML Class Diagrams

### Subsystem 1 — Data Collection & Calculation (S1)

```mermaid
classDiagram
    class Company {
        +String id
        +String name
        +String industry
        +get_departments() list
        +get_total_employees() int
        +to_dict() dict
    }

    class Department {
        +String id
        +String company_id
        +String name
        +Float floor_area_m2
        +get_activity_records() list
        +to_dict() dict
    }

    class ActivityRecord {
        +String id
        +String company_id
        +String department_id
        +int factor_id
        +Float quantity
        +String unit
        +Float co2e_kg
        +int scope
        +Date period_start
        +Date period_end
        +get_quantity() float
        +set_quantity(value) None
        +get_unit() str
        +set_unit(value) None
        +get_co2e_kg() float
        +is_valid() bool
        +update_quantity(new_val) None
    }

    class EmissionFactor {
        +int id
        +String category
        +Float kg_co2e_per_unit
        +String unit
        +int scope
        +int valid_year
        +is_active(year) bool
    }

    class EmissionCalculator {
        <<Service>>
        -int _precision
        -dict _scope_mapping
        +reset_configuration() None
        +register_scope_category(category, scope) None
        +calculate(quantity, factor_kg_co2e) float
        +assign_scope(category) int
        +fetch_factor(category, year) EmissionFactor
    }

    class CsvImporter {
        <<Service>>
        -str _encoding
        -list _error_log
        -int _valid_count
        +initialize_session() None
        +process(file_storage, user_id) dict
        +validate_and_save_row(row, user_id) ActivityRecord
    }

    Company "1" o-- "*" Department
    Department "1" o-- "*" ActivityRecord
    ActivityRecord "*" --> "1" EmissionFactor
    EmissionCalculator ..> ActivityRecord : calculates
    EmissionCalculator ..> EmissionFactor : fetches
    CsvImporter ..> ActivityRecord : creates
```

### Subsystem 2 — Analytics & Dashboard (S2)

```mermaid
classDiagram
    class Target {
        +String id
        +String company_id
        +Date baseline_start
        +Date baseline_end
        +Date period_start
        +Date period_end
        +Float reduction_percent
        +bool data_complete
        +configure_periods(b_start, b_end, p_start, p_end) None
        +get_target() float
        +set_target(reduction_percent) None
        +is_data_complete() bool
        +set_data_complete(complete) None
    }

    class AnalyticsService {
        <<Service>>
        -str _company_id
        -date _start_date
        -date _end_date
        -str _category
        +configure_filters(start_date, end_date, category) None
        +reset_filters() None
        +filter_records(statement) Select
        +calculate_total() float
        +group_by_category() list
        +get_monthly_totals() list
        +calculate_score(baseline_kg, current_kg, reduction_percent, data_complete) dict
    }

    class DashboardReport {
        <<Service>>
        -dict _summary
        -list _category_totals
        -list _monthly_totals
        -str _filename
        +load_data(summary, category_totals, monthly_totals) None
        +generate_charts() dict
        +display_summary() dict
        +export_CSV() str
    }

    class CarbonScorer {
        <<Service>>
        -float _min_score
        -float _max_score
        +configure_bounds(min_score, max_score) None
        +reset_defaults() None
        +calculate(baseline_kg, current_kg, reduction_percent, data_complete) dict
    }

    AnalyticsService ..> Target : evaluates
    AnalyticsService ..> CarbonScorer : delegates scoring
    DashboardReport ..> AnalyticsService : formats results
```

### Subsystem 3 — AI Assistant & User Access (S3)

```mermaid
classDiagram
    class User {
        +String id
        +String company_id
        +String department_id
        +String email
        +String password_hash
        +String role
        +get_role() str
        +set_role(role) None
        +set_password(password) None
        +check_password(password) bool
        +has_role(roles) bool
    }

    class ChatMessage {
        +String id
        +String user_id
        +String sender
        +String content
        +DateTime created_at
        +to_dict() dict
    }

    class Recommendation {
        +String id
        +String company_id
        +String department_id
        +String title
        +Float est_saving_kg
        +Float est_cost_eur
        +String effort
        +String status
        +accept() None
        +reject() None
        +mark_done() None
    }

    class AuthService {
        <<Service>>
        +register(company_name, email, password, departments, name) User
        +create_user(admin, email, password, role, department_id, name) User
        +authenticate(email, password) User
        +login(email, password, remember) User
        +logout() None
    }

    class AIClient {
        <<Service>>
        -str _model
        -float _timeout
        -int _max_tokens
        -int _daily_limit
        +configure(model, timeout, max_tokens, daily_limit) None
        +from_config() AIClient
        +requests_today(company_id) int
        +complete(messages, company_id, kind, user_id, json_output) str
    }

    class PromptBuilder {
        <<Service>>
        -str _system_prompt
        -int _max_hotspots
        +reset_templates() None
        +build_context(company_id, start, end) dict
        +chat_messages(summary, question, history) list
        +advice_prompt(summary, department, annual_kg) list
        +summary_prompt(summary, month_label) list
    }

    class AIAssistant {
        <<Service>>
        -AIClient _client
        -PromptBuilder _prompts
        -int _history_limit
        +reset_defaults() None
        +from_app() AIAssistant
        +ask(user, question) ChatMessage
        +recommend(company_id, department_id, user_id) list
        +summarise(company_id, month, user_id) str
    }

    User "1" --> "*" ChatMessage : owns
    AuthService ..> User : manages
    AIAssistant --> AIClient : uses
    AIAssistant --> PromptBuilder : uses
    AIAssistant ..> ChatMessage : stores
    AIAssistant ..> Recommendation : creates
```

---

## Real-Time Stream Processing Pipeline (Hometask 2)

Our event-driven telemetry pipeline (`app/data_collection/stream_processing.py`) ingests live operational events (`flight_booking`, `server_utility_log`, `freight_logistics`), filters events by GHG Scope (1, 2, or 3), and transforms activity metrics into metric tons of CO₂e:

- **Abstract Base Class:** `StreamProcessor(ABC)` with `@abstractmethod process(record)`.
- **Inheritance & Polymorphism:** `ScopeFilter`, `MetricTonCO2eTransformer`, and `CompositeStreamProcessor`.
- **Operator Overloading:** Compose multi-stage pipelines intuitively via `|` (`__or__`) or `+` (`__add__`), e.g. `pipeline = ScopeFilter(target_scopes=3) | MetricTonCO2eTransformer()`.
- **Iterators & Generators:** `TelemetryStream` implements `__iter__` and `__next__`; `StreamProcessor.process_stream()` yields transformed records lazily.

### Stream Processing Class Diagram

```mermaid
classDiagram
    class TelemetryRecord {
        -str _event_id
        -str _source
        -int _scope
        -float _activity_metric
        -str _unit
        -float _calculated_co2e_metric_tons
        +to_dict() dict
    }

    class TelemetryStream {
        -list _events
        -int _index
        +add_event(event) None
        +__iter__() TelemetryStream
        +__next__() TelemetryRecord
        +__len__() int
    }

    class StreamProcessor {
        <<abstract>>
        +process(record)* TelemetryRecord
        +__or__(other) CompositeStreamProcessor
        +__add__(other) CompositeStreamProcessor
        +process_stream(stream) Iterator
    }

    class CompositeStreamProcessor {
        +list processors
        +process(record) TelemetryRecord
    }

    class ScopeFilter {
        -set _target_scopes
        +process(record) TelemetryRecord
    }

    class MetricTonCO2eTransformer {
        -dict _factors
        +process(record) TelemetryRecord
    }

    StreamProcessor <|-- CompositeStreamProcessor
    StreamProcessor <|-- ScopeFilter
    StreamProcessor <|-- MetricTonCO2eTransformer
    TelemetryStream "1" o-- "*" TelemetryRecord : yields
    StreamProcessor ..> TelemetryRecord : transforms
```

---

## Technologies & Database Layer (Hometask 3)

- **Backend & Web APIs:** Python 3.12+, Flask 3, Flask-Login, Jinja2, REST JSON endpoints & CSV export
- **Database Access Layer (SQLAlchemy ORM):**
  - **Local development:** SQLite (`sqlite:///carbon_dev.db`)
  - **Docker Compose:** PostgreSQL 16 (`postgresql+psycopg://...`)
  - **MySQL compatible:** `PyMySQL` included (`mysql+pymysql://carbon_user:password@localhost:3306/carbon_tracker`)
- **Analytics & AI:** pandas, Plotly, OpenAI Python SDK (`gpt-4o-mini` default)
- **Testing & Error Handling:** `pytest` + subsystem-specific exception hierarchies:
  - **S1:** `DataCollectionError` (`ValidationError`, `UnitMismatchError`, `PeriodValidationError`, `RecordOwnershipError`, `ResourceNotFoundError`, `CompanyIsolationError`) in `app/data_collection/exceptions.py`
  - **S2:** `AnalyticsError` (`InvalidFilterError`, `TargetValidationError`, `AnalyticsAccessError`) in `app/analytics/exceptions.py`
  - **S3:** `S3Error` (`AuthError`, `InvalidCredentialsError`, `AccessDeniedError`, `ResourceNotFoundError`, `InvalidInputError`, `WorkflowError`, `AIUnavailable`, `AIRateLimitError`, `InvalidAIOutput`, ...) and the `S3ErrorHandler` class in `app/user_access/exceptions.py`

### Subsystem 3 Web API & Database Access Layer (Junaid Ahmad · `7222074`)

**JSON API** (`app/ai_assistant/api.py`, all under `/api/s3`). Every answer is JSON, including errors (`{"ok": false, "error": "..."}`).
Login uses the session cookie; `POST`/`PATCH` requests need the `X-CSRFToken` header returned by `/login` and `/me`.

| Method | Endpoint | Who | Purpose |
|---|---|---|---|
| POST | `/api/s3/login` | anyone | Log in with `{"email", "password"}` |
| POST | `/api/s3/logout` | logged in | Log out |
| GET | `/api/s3/me` | logged in | Current user and CSRF token |
| GET | `/api/s3/users?role=` | admin | Users of the admin's company |
| GET | `/api/s3/recommendations?status=&department_id=` | logged in | Reduction tips (employees: own department only) |
| GET | `/api/s3/recommendations/<id>` | logged in | One tip |
| PATCH | `/api/s3/recommendations/<id>` | admin, manager | `{"status": "accepted" \| "rejected" \| "done"}` |
| GET | `/api/s3/chat/history?limit=` | logged in | Own chat messages, oldest first |
| POST | `/api/s3/chat` | logged in | Ask the AI coach `{"question"}` |
| GET | `/api/s3/ai-usage` | admin | OpenAI requests and tokens used today |

Status codes: `401` not logged in, `403` wrong role, `404` not found or another company's data, `409` workflow step not allowed (a rejected or done tip cannot be reopened), `503` AI not available.

**Database access layer** (`app/user_access/repositories.py`, `app/ai_assistant/repositories.py`):
`CompanyScopedRepository` binds every query to the logged-in user's company, so another company's rows are never returned, even for a guessed id.
`UserRepository`, `RecommendationRepository`, `ChatMessageRepository` (company reached through a join on `users`) and `AIRequestRepository` inherit from it.

```mermaid
classDiagram
    class CompanyScopedRepository {
        +model
        -str _company_id
        +get_company_id() str
        +get(item_id)
        +list() list
        +count() int
        +save(item) None
    }
    class UserRepository {
        +list(role) list
    }
    class RecommendationRepository {
        +dict ALLOWED_TRANSITIONS
        +list_for(user, status, department_id) list
        +get_for(user, recommendation_id) Recommendation
        +change_status(recommendation, new_status) Recommendation
    }
    class ChatMessageRepository {
        +history(user_id, limit) list
    }
    class AIRequestRepository {
        +count_today() int
        +tokens_today() int
    }
    CompanyScopedRepository <|-- UserRepository
    CompanyScopedRepository <|-- RecommendationRepository
    CompanyScopedRepository <|-- ChatMessageRepository
    CompanyScopedRepository <|-- AIRequestRepository
```

**Running on MySQL.** Set `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` in `.env`, then:

```bash
docker compose -f compose.yaml -f compose.mysql.yaml up --build
```

`compose.mysql.yaml` adds a MySQL 8.4 container and points `DATABASE_URL` at it (`mysql+pymysql://...?charset=utf8mb4`); `run.py` creates the tables. Without Docker, point `DATABASE_URL` at any MySQL 8 server. `cryptography` is in `requirements.txt` because PyMySQL needs it for MySQL 8 logins.

**Example session** (PowerShell, app running on port 5000):

```powershell
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$login = Invoke-RestMethod -Method Post http://127.0.0.1:5000/api/s3/login -WebSession $s `
  -ContentType "application/json" -Body '{"email": "you@company.de", "password": "yourPassword"}'
Invoke-RestMethod http://127.0.0.1:5000/api/s3/recommendations -WebSession $s
```

**Tests:** `python -m unittest discover tests` (19 tests: API, permissions, company isolation, repositories, MySQL table definitions).

---

## Local Setup

Create and activate a virtual environment:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
cp -n .env.example .env
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Configure `.env` (supports SQLite locally, PostgreSQL in Docker, or MySQL):

```env
SECRET_KEY=replace-with-a-random-local-secret
DATABASE_URL=sqlite:///carbon_dev.db
ANALYTICS_DEV_COMPANY_ID=123e4567-e89b-12d3-a456-426614174000
OPENAI_API_KEY=your-openai-api-key
```

Seed the local sample company and emission factors, then start the server:

```bash
python seed.py
python run.py
```

*(Alternatively, run with Flask CLI: `python -m flask --app run:app run --debug`.)*

Open http://127.0.0.1:5000.

---

## Carbon Score

The score shows progress towards a company's reduction target. For example, a company with a baseline of 100 kg CO₂e and a 20% reduction target receives 50/100 when its emissions fall to 90 kg CO₂e. Scoring requires completed reporting periods, a positive baseline, and confirmation of complete, comparable data; otherwise, the score displays an unavailable state.

---

## Automated Tests (Hometask 4)

Run the full test suite (230 tests across all subsystems, OpenAI mocked):

```bash
python -m pytest -q
```

### Subsystem 3 Error Handling (Junaid Ahmad · `7222074`)

All S3 errors share one base class, `S3Error`, in `app/user_access/exceptions.py`. Each error carries an HTTP `status_code`, a message that is safe to show, optional `details`, and `to_dict()` for JSON.
Each error also inherits from the matching built-in exception (`ValueError`, `PermissionError`, `LookupError`, `RuntimeError`), so existing `except ValueError:` code keeps working.

```mermaid
classDiagram
    class S3Error {
        +int status_code
        +str message
        +dict details
        +to_dict() dict
    }
    class AuthError
    class InvalidCredentialsError
    class AccessDeniedError
    class ResourceNotFoundError
    class UnknownDepartmentError
    class InvalidInputError
    class InvalidQuestionError
    class WorkflowError
    class AIError
    class AIUnavailable
    class AINotConfiguredError
    class AIRateLimitError
    class NoEmissionDataError
    class InvalidAIOutput
    class S3ErrorHandler {
        -str _error_template
        -dict _handled
        +init_app(app) None
        +handle(error) Response
        +handled_counts() dict
        +wants_json() bool
    }
    S3Error <|-- AuthError
    AuthError <|-- InvalidCredentialsError
    S3Error <|-- AccessDeniedError
    S3Error <|-- ResourceNotFoundError
    ResourceNotFoundError <|-- UnknownDepartmentError
    S3Error <|-- InvalidInputError
    InvalidInputError <|-- InvalidQuestionError
    S3Error <|-- WorkflowError
    S3Error <|-- AIError
    AIError <|-- AIUnavailable
    AIUnavailable <|-- AINotConfiguredError
    AIUnavailable <|-- AIRateLimitError
    AIUnavailable <|-- NoEmissionDataError
    AIError <|-- InvalidAIOutput
    S3ErrorHandler ..> S3Error : handles
```

| Status | S3 error |
|---|---|
| 400 | `AuthError`, `InvalidInputError`, `InvalidQuestionError` |
| 401 | `InvalidCredentialsError` |
| 403 | `AccessDeniedError` |
| 404 | `ResourceNotFoundError`, `UnknownDepartmentError` |
| 409 | `WorkflowError` |
| 422 | `NoEmissionDataError` |
| 429 | `AIRateLimitError` |
| 502 | `InvalidAIOutput` |
| 503 | `AIError`, `AIUnavailable`, `AINotConfiguredError` |

`S3ErrorHandler` is installed once in `register_user_access()`. It logs every S3 error (5xx at ERROR level), counts errors by type, and answers with JSON for `/api/` requests or with the S3 error page otherwise.
The S3 JSON API raises these errors and leaves the response to the handler: for example `WorkflowError` → `409`, `AIRateLimitError` → `429`, `AINotConfiguredError` → `503`.

S3 tests: `tests/test_s3_exceptions.py` (error hierarchy, status codes, handler), `tests/test_s3_api.py` (API and repositories), `tests/test_ai_assistant.py`, `tests/test_ai_prompts.py`, `tests/test_user_access.py`, `tests/test_s3_oop.py`.

---

## Team Workflow

We work on feature branches and review changes before merging. Shared model changes are discussed with the affected subsystem owners. Do not commit `.env`, API keys, local databases, virtual environments, or real company data. Further documentation is in `docs/architecture.md` and `docs/data-contract.md`.
