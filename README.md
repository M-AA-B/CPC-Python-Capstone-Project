# CPC-Python-Capstone-Project

Runnable development scaffold based on the team's Flask / Jinja2 / SQLAlchemy /
PostgreSQL architecture. Includes navigation, subsystem placeholders, Docker setup
and startup tests. Business features and database tables are intentionally pending.

## Requirements

Python 3.12 recommended. Docker Desktop or Docker Engine with Compose for containers.

## Local setup

Extract the ZIP and open this project folder in your editor.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

macOS / Linux:

```bash
source .venv/bin/activate
cp .env.example .env
```

Then, on either platform:

```bash
python -m pip install -r requirements.txt
python -m flask --app run:app run --debug
```

Open http://127.0.0.1:5000. Local setup defaults to SQLite to let everyone start
without PostgreSQL; the team's Docker setup uses PostgreSQL. Verify database
features against PostgreSQL when implementing models. Keep local development
bound to localhost. Debug mode and the included server are for development only.

## Docker setup (PostgreSQL)

Copy .env.example to .env if needed, then replace SECRET_KEY and
POSTGRES_PASSWORD with local random values. For this starter use an alphanumeric
POSTGRES_PASSWORD so the composed database URL needs no URL encoding.

```bash
docker compose up --build
```

Open http://127.0.0.1:5000. Stop containers with `docker compose down`.
Database data remains in the named volume. Container debug mode is disabled.
The health endpoint checks app startup only, not database connectivity.

## Working areas

- Mohammed: app/data_collection and templates/data_collection.
- Vanessa: app/analytics, templates/analytics, dashboard CSS/JS.
- Junaid: app/user_access, app/ai_assistant and matching templates.
- Everyone: discuss shared models, configuration and base layout changes first.

See docs/architecture.md and docs/data-contract.md.
Model files are placeholders, not working table definitions. Services, scoring,
imports, exports, permissions and prompts are also placeholders. No real data,
login, emission factors or OpenAI calls are included. Do not upload real company
data until authentication and company isolation have been implemented and tested.

## Database migrations — after agreeing and implementing models

Import the completed models in app/models/**init**.py. One team member initializes
migrations once, using the shared PostgreSQL setup:

```bash
docker compose exec web flask --app run:app db init
docker compose exec web flask --app run:app db migrate -m "Initial shared models"
docker compose exec web flask --app run:app db upgrade
```

Review and commit the generated migrations folder. Other members pull it and run
`db upgrade`; they should not each run `db init`. No migration directory is
included yet because no database tables have been agreed or implemented.

## Tests

```bash
python -m pytest
```

Included tests verify startup and placeholder page rendering only. Add calculation,
aggregation, authorization and mocked AI tests as features are implemented.
Dependency ranges are declared; agree on a tested lock file for reproducible builds.

## Put this starter on main

For an EXISTING team repository: clone it first, copy this folder's CONTENTS into
the repository root, preserving existing files, then review the diff. Do not copy
this folder as an extra nested project unless the team wants that layout.

```bash
git switch main
git pull --ff-only
git status
git add app tests docs data run.py requirements.txt pytest.ini Dockerfile compose.yaml README.md .gitignore .dockerignore .env.example
git diff --cached
git commit -m "Add shared Flask capstone starter structure"
git push origin main
```

If main is protected, push this commit on a setup branch and open a pull request.
Do not overwrite existing project files without reviewing and merging their content.
For an EMPTY repository, initialize Git and connect the actual repository URL first.
This ZIP does not include a Git repository or remote configuration.

## Team workflow after setup

Each member pulls main and creates a feature branch, for example:

```bash
git switch main
git pull --ff-only
git switch -c feature/s2-dashboard
```

Use feature/s1-data-collection or feature/s3-user-access for the other areas.
Commit focused changes, push the feature branch, and merge through a pull request.
Never commit .env, API keys, database files, virtual environments or client data.

## Starter verification

Six startup/page tests pass in the creation environment. Docker is not available
in that environment, so the Compose build and PostgreSQL startup need local verification.
