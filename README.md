# Enterprise Carbon Footprint Tracker & AI Assistant

Group 13 — Compact Programming, FH Dortmund

Our project helps companies record their activities, understand their carbon
emissions and track progress towards reduction targets. The planned AI assistant
will explain emission changes and suggest improvements.

## Our team

Team member and Responsibility:

1. Mohammed Al-Amine Bennani --> S1 — Data Collection & Calculation
2. Vanessa Mukamanzi --> S2 — Analytics & Dashboard
3. Junaid Ahmad --> S3 — AI Assistant & User Access

## Current features

- Activity entry, CSV import and emission calculations
- Company emission totals and category breakdowns
- Monthly and category charts
- Date and category filters
- Monthly emissions comparisons
- Filtered CSV exports
- Reduction targets and target-progress scoring

Authentication, role permissions and AI integration are still being connected.

## Technologies

Python, Flask, Jinja2, SQLAlchemy, Plotly and pytest.
Local development uses SQLite; the Docker setup uses PostgreSQL.

## Local setup

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

On macOS / Linux:

```bash
source .venv/bin/activate
cp -n .env.example .env
```

Keep your existing `.env` if you have already configured it.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

For local development, configure these values in `.env`:

```env
DATABASE_URL=sqlite:///carbon_dev.db
ANALYTICS_DEV_COMPANY_ID=123e4567-e89b-12d3-a456-426614174000
```

Create the synthetic test company and supporting records:

```bash
python seed.py
```

Add activity records through S1, then start the application:

```bash
python -m flask --app run:app run --debug
```

Open http://127.0.0.1:5000.

Analytics currently uses the configured test company in debug mode.
Authenticated company access and target permissions require S3 integration.

## Carbon Score

The score shows progress towards a company's reduction target.

For example, a company with a baseline of 100 kg CO₂e and a 20% reduction
target receives 50/100 when its emissions fall to 90 kg CO₂e.

Scoring requires completed reporting periods, a positive baseline, and
confirmation of complete, comparable data. Otherwise, the score is unavailable.

The score is a project progress indicator, not a certified environmental rating.

## Tests

```bash
python -m pytest -q
```

The latest local run passed 67 tests, including analytics aggregation,
company isolation in service queries, filters, comparisons and scoring.

Tests currently use SQLite. PostgreSQL verification and route-level tests
remain pending.

## Remaining work

- Connect S3 login and role permissions to analytics and exports.
- Connect aggregated summaries to the AI assistant.
- Review reporting completeness rules together.
- Complete PostgreSQL, performance and responsive layout checks.

## Team workflow

We work on feature branches and review changes before merging.
Shared model changes are discussed with the affected subsystem owners.

Do not commit `.env`, API keys, local databases, virtual environments
or real company data. Keep the feature branches required for grading.

Further documentation is in `docs/architecture.md` and
`docs/data-contract.md`.
