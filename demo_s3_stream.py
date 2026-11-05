"""Hometask 2 — S3 real-time insights demo (Junaid Ahmad · 7222074).

Live telemetry flows through the S1 pipeline (Mohammed) and straight on into
the S3 processors, which raise alerts, create recommendations and keep the
aggregated totals that the AI coach is allowed to see.

    python demo_s3_stream.py
"""
from app.ai_assistant import AIAssistant, PromptBuilder
from app.ai_assistant.stream_insights import HotspotDetector, LiveCoachMonitor
from app.data_collection import MetricTonCO2eTransformer, ScopeFilter, TelemetryRecord, TelemetryStream
from app.models import User


def main() -> None:
    events = [
        TelemetryRecord(source="company_vehicles", scope=1, activity_metric=400.0, unit="l",
                        metadata={"department": "logistics"}),
        TelemetryRecord(source="server_utility_log", scope=2, activity_metric=9000.0, unit="kWh",
                        metadata={"department": "it"}),
        TelemetryRecord(source="flight_booking", scope=3, activity_metric=8000.0, unit="passenger-km",
                        metadata={"department": "sales"}),
        TelemetryRecord(source="server_utility_log", scope=2, activity_metric=9000.0, unit="kWh",
                        metadata={"department": "it"}),
        TelemetryRecord(source="electricity", scope=2, activity_metric=1000.0, unit="kWh",
                        metadata={"department": "office"}),
    ]

    # S1 steps (Mohammed) | S3 steps (Junaid), joined with the overloaded `|` operator
    monitor = LiveCoachMonitor(
        ScopeFilter({1, 2, 3}) | MetricTonCO2eTransformer(),
        detector=HotspotDetector(event_threshold_t=1.0, department_budget_t=5.0),
    )
    steps = " | ".join(type(p).__name__ for p in monitor.get_pipeline().processors)
    print(f"Pipeline: {steps}\n")

    print("=== Live alerts (generator: printed while the stream is processed) ===")
    alerts = []
    for alert in monitor.watch(TelemetryStream(events)):
        print(f"  ALERT {alert}")
        alerts.append(alert)
    print(f"  Most severe (sorted with overloaded <): {max(alerts)}")

    print("\n=== Recommendations created from hotspots ===")
    for tip in monitor.get_trigger().get_recommendations():
        print(f"  {tip.get_department_id():<10} {tip.get_title()} | saves {tip.get_est_saving_kg()} kg | "
              f"effort {tip.get_effort()}")

    print("\n=== Aggregated summary (the only data the AI coach sees) ===")
    summary = monitor.get_aggregator().snapshot()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n=== AI coach answer from the live totals ===")
    context = PromptBuilder().build_context("ecotech-gmbh", monitor.get_aggregator().category_totals())
    manager = User("ecotech-gmbh", "manager@ecotech.de", "securePass123", role="manager")
    reply = AIAssistant().ask(manager, "Where should we act first?", context)
    print(f"  {reply.get_content()}")


if __name__ == "__main__":
    main()
