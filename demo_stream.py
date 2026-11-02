"""Hometask 2 Demo: Real-Time Carbon Telemetry Stream Pipeline integrated with Hometask 1 OOP."""
from datetime import date

from app.analytics import AnalyticsService, DashboardReport
from app.data_collection import (
    MetricTonCO2eTransformer,
    ScopeFilter,
    TelemetryRecord,
    TelemetryStream,
)
from app.models import ActivityRecord, EmissionFactor, ReductionTarget


def main() -> None:
    events = [
        TelemetryRecord(event_id="ev-01", source="company_vehicles", scope=1, activity_metric=400.0, unit="l"),
        TelemetryRecord(event_id="ev-02", source="server_utility_log", scope=2, activity_metric=25000.0, unit="kWh"),
        TelemetryRecord(event_id="ev-03", source="flight_booking", scope=3, activity_metric=8000.0, unit="passenger-km"),
        TelemetryRecord(event_id="ev-04", source="freight_logistics", scope=3, activity_metric=12000.0, unit="ton-km"),
    ]
    stream = TelemetryStream(events)

    # Operator overloading: `|` (__or__) and `+` (__add__)
    scope3_pipeline = ScopeFilter(target_scopes=3) | MetricTonCO2eTransformer()
    scope2_pipeline = ScopeFilter(target_scopes=2) + MetricTonCO2eTransformer()

    print("=== Scope 3 Value-Chain Telemetry (`|` pipeline) ===")
    for rec in scope3_pipeline.process_stream(stream):
        print(f"  [{rec.event_id}] {rec.source} -> {rec.calculated_co2e_metric_tons:.4f} metric tons CO2e")

    print("\n=== Scope 2 Data-Center Telemetry (`+` pipeline) ===")
    streamed_records: list[ActivityRecord] = []
    grid_factor = EmissionFactor(10, "server_utility_log", 0.42, "kWh", scope=2, valid_year=2026)
    for rec in scope2_pipeline.process_stream(stream):
        print(f"  [{rec.event_id}] {rec.source} -> {rec.calculated_co2e_metric_tons:.4f} metric tons CO2e")
        streamed_records.append(
            ActivityRecord(
                department_id="data-center-01",
                factor=grid_factor,
                quantity=rec.activity_metric,
                unit=rec.unit,
                record_date=date(2026, 4, 1),
            )
        )

    # Connect streamed records into Hometask 1 S2 AnalyticsService & DashboardReport
    analytics = AnalyticsService(
        records=streamed_records,
        target=ReductionTarget(target_id=1, baseline=15000.0, target_percent=30.0),
    )
    summary = DashboardReport(analytics, report_title="Live Telemetry Analytics").display_summary()
    print(f"\n[Hometask 1 + 2 Integration] Dashboard Total: {summary['total_co2e_kg']} kg CO2e | Score: {summary['carbon_score']}/100")


if __name__ == "__main__":
    main()
