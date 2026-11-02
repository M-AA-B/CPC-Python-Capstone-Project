# Proposed shared data contract — requires team agreement

ActivityRecord: id (UUID), company_id (UUID), department_id (UUID),
period_start (date), period_end (date), category (controlled code), scope (1–3),
quantity (decimal), unit (controlled code), emission_factor_id (UUID),
co2e_kg (decimal), created_by (UUID), created_at (UTC timestamp).

- Records remain within one calendar month initially.
- S1 calculates co2e_kg = quantity × factor, after checking matching units.
- Use decimal database columns; round only for display/export as agreed.
- Each record retains its immutable factor version.
- Department must belong to the record's company.
- S2 aggregates stored co2e_kg; S3 consumes aggregated summaries only.
- Shared model changes require discussion with affected subsystem owners.

## Decisions still open
- Exact SQLAlchemy column types, decimal precision and relationships.
- Controlled categories/units and activity-to-scope mapping.
- Validation, duplicate import handling and audit log design.
- Permissions for Admin, Manager and Employee, including company isolation.
- Target periods, data completeness and score rules.

Proposed score: clamp((baseline-current)/(baseline-target)*100, 0, 100).
Only use when baseline > target and comparable, complete data exists.
This is a project target-progress indicator, not a certified rating.
No target or incomplete data should display an unavailable state, not zero.

## Suggested S2-to-S3 interface (not implemented)
get_summary(company_id, period_start, period_end, department_id=None)
returns total_co2e_kg, by_category, monthly_totals, target_progress and score.
Define the returned schema together. Authenticate and authorize the company
and department before querying. Never trust a supplied company_id by itself.
