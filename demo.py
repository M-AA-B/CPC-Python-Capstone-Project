"""End-to-end demonstration of all Hometask 1 OOP classes across Subsystems S1, S2, and S3."""
from datetime import date

from app.ai_assistant import AIAssistant, PromptBuilder
from app.user_access import AuthService
from app.analytics import AnalyticsService, DashboardReport
from app.models import ReductionTarget
from app.data_collection import CsvImporter, EmissionCalculator
from app.models import ActivityRecord, Company, Department, EmissionFactor


def main() -> None:
    # --- Subsystem 1: Data Collection & Calculation (Mohammed · 7222047) ---
    company = Company(name="EcoTech GmbH", industry="Manufacturing")
    company.set_total_employees(45)

    logistics = Department(company_id=company.get_id(), name="Logistics", floor_area_m2=800.0)
    office = Department(company_id=company.get_id(), name="Office", floor_area_m2=450.0)
    company.add_department(logistics)
    company.add_department(office)

    elec_factor = EmissionFactor(1, "electricity", 0.42, "kWh", scope=2, valid_year=2026)
    fuel_factor = EmissionFactor(2, "company_vehicles", 2.68, "l", scope=1, valid_year=2026)

    calculator = EmissionCalculator(precision=2, factors=[elec_factor, fuel_factor])
    rec1 = ActivityRecord(logistics.get_id(), fuel_factor, quantity=250.0, unit="l", record_date=date(2026, 3, 10))
    logistics.add_activity_record(rec1)

    importer = CsvImporter(calculator=calculator)
    importer.read_file(
        "department_id,category,quantity,unit,record_date\n"
        f"{office.get_id()},electricity,1000,kWh,2026-03-15\n"
    )
    imported_records = importer.save_valid_rows()
    for r in imported_records:
        office.add_activity_record(r)

    all_records = logistics.get_activity_records() + office.get_activity_records()
    print(f"[S1] Company: {company.get_name()} | Departments: {len(company.get_departments())} | Records: {len(all_records)}")

    # --- Subsystem 2: Analytics & Dashboard (Vanessa · 7223964) ---
    target = ReductionTarget(target_id=1, baseline=1500.0, target_percent=20.0)
    analytics = AnalyticsService(records=all_records, target=target)
    report = DashboardReport(analytics_service=analytics, report_title="March 2026 Footprint")
    summary = report.display_summary()
    print(f"[S2] Total: {summary['total_co2e_kg']} kg CO2e | Score: {summary['carbon_score']}/100 | Hotspot: {summary['highest_category']}")

    # --- Subsystem 3: AI Assistant & User Access (Junaid · 7222074) ---
    auth = AuthService(default_company_id=company.get_id())
    manager = auth.register("manager@ecotech.de", "securePass123", role="manager", department_id=logistics.get_id())
    auth.login("manager@ecotech.de", "securePass123")
    auth.require_role("manager")

    builder = PromptBuilder()
    ai_context = builder.build_context(company.get_id(), analytics.group_by_category())
    coach = AIAssistant(model="gpt-4o-mini", prompt_builder=builder)
    reply = coach.ask(manager, "Where should we cut emissions first?", ai_context)
    tips = coach.recommend(logistics.get_id(), ai_context["top_hotspots"])
    tips[0].accept()
    print(f"[S3] Coach Reply: {reply.get_content()}")
    print(f"[S3] Generated {len(tips)} tips | First tip: '{tips[0].get_title()}' (status={tips[0].get_status()})")


if __name__ == "__main__":
    main()
