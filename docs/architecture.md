# Architecture and ownership

One Flask application, four Blueprints, one shared database.
S3 has separate access and assistant packages for clarity.

| Area | Owner | Main folders |
|---|---|---|
| S1 Data Collection & Calculation | Mohammed | app/data_collection |
| S2 Analytics & Dashboard | Vanessa | app/analytics |
| S3 AI Assistant & User Access | Junaid | app/ai_assistant, app/user_access |
| Shared setup, layout, models | Team | app/models, app/templates/base.html, app/extensions.py |

Jinja2 templates live in app/templates, styles/scripts in app/static.
Routes handle HTTP, services hold business logic, models define database tables.
S1 saves calculated emissions, S2 aggregates them, S3 uses aggregated summaries.
The starter does not implement authentication, roles, calculations or AI calls.
All pages are public placeholders. Add protection before introducing real data.
