"""Hometask 2 — unit tests for the S3 real-time insight processors (Junaid Ahmad · 7222074).

Run with:  python -m unittest discover tests
"""
import inspect
import unittest

from app.ai_assistant import AIAssistant, AIClient, PromptBuilder
from app.ai_assistant.stream_insights import (
    AISummaryAggregator,
    AlertFeed,
    HotspotAlert,
    HotspotDetector,
    LiveCoachMonitor,
    RecommendationTrigger,
    StatefulProcessor,
)
from app.data_collection import (
    MetricTonCO2eTransformer,
    ScopeFilter,
    StreamProcessor,
    TelemetryRecord,
    TelemetryStream,
)
from app.models import User


def event(source, scope, metric, department, unit="kWh"):
    return TelemetryRecord(source=source, scope=scope, activity_metric=metric, unit=unit,
                           metadata={"department": department})


def sample_events():
    return [
        event("company_vehicles", 1, 400.0, "logistics", unit="l"),       # 1.072 t
        event("server_utility_log", 2, 25000.0, "it"),                     # 10.5 t
        event("flight_booking", 3, 8000.0, "sales", unit="passenger-km"),  # 1.2 t
        event("electricity", 2, 1000.0, "office"),                         # 0.42 t
    ]


def s1_pipeline(scopes=(1, 2, 3)):
    return ScopeFilter(set(scopes)) | MetricTonCO2eTransformer()


class AbstractContractTests(unittest.TestCase):
    def test_stateful_processor_is_abstract(self):
        self.assertTrue(inspect.isabstract(StatefulProcessor))
        with self.assertRaises(TypeError):
            StatefulProcessor()

    def test_s3_processors_are_polymorphic_stream_processors(self):
        for processor in (HotspotDetector(), RecommendationTrigger(), AISummaryAggregator()):
            self.assertIsInstance(processor, StreamProcessor)
            self.assertIsInstance(processor, StatefulProcessor)
            self.assertIsInstance(processor.snapshot(), dict)

    def test_s3_processor_needs_co2e_value_first(self):
        with self.assertRaises(ValueError):
            HotspotDetector().process(event("electricity", 2, 100.0, "office"))


class HotspotDetectorTests(unittest.TestCase):
    def test_large_events_raise_alerts(self):
        detector = HotspotDetector(event_threshold_t=1.0, department_budget_t=50.0)
        list((s1_pipeline() | detector).process_stream(TelemetryStream(sample_events())))
        alerts = list(detector.alerts())
        self.assertEqual([a.get_department() for a in alerts], ["logistics", "it", "sales"])
        self.assertEqual(len(detector.alerts()), 0)  # each alert is delivered once

    def test_department_budget_alert_fires_once(self):
        detector = HotspotDetector(event_threshold_t=100.0, department_budget_t=1.0)
        events = [event("electricity", 2, 2000.0, "office") for _ in range(3)]  # 0.84 t each
        list((s1_pipeline() | detector).process_stream(TelemetryStream(events)))
        alerts = list(detector.alerts())
        self.assertEqual(len(alerts), 1)
        self.assertIn("budget", alerts[0].get_reason())
        self.assertEqual(detector.snapshot()["over_budget"], ["office"])

    def test_setters_validate(self):
        with self.assertRaises(ValueError):
            HotspotDetector(event_threshold_t=0)
        with self.assertRaises(ValueError):
            HotspotDetector().set_department_budget_t(-1)


class AlertTests(unittest.TestCase):
    def test_alerts_sort_by_severity(self):
        small = HotspotAlert("office", "electricity", 0.5, "x")
        large = HotspotAlert("it", "server_utility_log", 10.5, "x")
        self.assertTrue(small < large)
        self.assertEqual(sorted([large, small]), [small, large])
        self.assertIn("10.5000 t CO2e", str(large))

    def test_feed_is_an_iterator(self):
        feed = AlertFeed()
        feed.push(HotspotAlert("a", "s", 1, "r"))
        feed.push(HotspotAlert("b", "s", 2, "r"))
        self.assertIs(iter(feed), feed)
        self.assertEqual(next(feed).get_department(), "a")
        self.assertEqual([a.get_department() for a in feed], ["b"])
        with self.assertRaises(StopIteration):
            next(feed)
        self.assertEqual(feed.get_delivered_count(), 2)


class RecommendationTriggerTests(unittest.TestCase):
    def test_one_recommendation_per_department_and_source(self):
        trigger = RecommendationTrigger(saving_share=0.10)
        pipeline = s1_pipeline() | HotspotDetector(event_threshold_t=1.0) | trigger
        events = sample_events() + [event("server_utility_log", 2, 25000.0, "it")]
        list(pipeline.process_stream(TelemetryStream(events)))
        tips = trigger.get_recommendations()
        self.assertEqual(sorted(t.get_department_id() for t in tips), ["it", "logistics", "sales"])
        it_tip = next(t for t in tips if t.get_department_id() == "it")
        self.assertEqual(it_tip.get_est_saving_kg(), 1050.0)  # 10.5 t * 10 %
        self.assertEqual(it_tip.get_effort(), "high")
        self.assertEqual(it_tip.get_status(), "proposed")

    def test_saving_share_validated(self):
        with self.assertRaises(ValueError):
            RecommendationTrigger(saving_share=1.5)


class AISummaryAggregatorTests(unittest.TestCase):
    def test_totals_by_category_scope_and_department(self):
        aggregator = AISummaryAggregator()
        list((s1_pipeline(scopes=(2,)) | aggregator).process_stream(TelemetryStream(sample_events())))
        snapshot = aggregator.snapshot()
        self.assertEqual(len(aggregator), 2)
        self.assertEqual(snapshot["total_co2e_kg"], 10920.0)
        self.assertEqual(snapshot["by_scope_kg"], {"scope_2": 10920.0})
        self.assertEqual(snapshot["by_department_kg"], {"it": 10500.0, "office": 420.0})

    def test_only_aggregates_reach_the_ai(self):
        aggregator = AISummaryAggregator()
        list((s1_pipeline() | aggregator).process_stream(TelemetryStream(sample_events())))
        context = PromptBuilder().build_context("ecotech", aggregator.category_totals())
        self.assertNotIn("event_id", str(context))
        self.assertEqual(list(context["top_hotspots"])[0], "server_utility_log")


class LiveCoachMonitorTests(unittest.TestCase):
    def test_watch_is_a_lazy_generator(self):
        monitor = LiveCoachMonitor(s1_pipeline())
        feed = monitor.watch(TelemetryStream(sample_events()))
        self.assertTrue(inspect.isgenerator(feed))
        first = next(feed)  # only processes events until the first alert
        self.assertEqual(first.get_department(), "logistics")
        self.assertEqual(len(monitor.get_aggregator()), 1)
        self.assertEqual(len(list(feed)), 2)
        self.assertEqual(len(monitor.get_aggregator()), 4)

    def test_pipeline_is_composed_with_operator(self):
        monitor = LiveCoachMonitor(s1_pipeline())
        names = [type(p).__name__ for p in monitor.get_pipeline().processors]
        self.assertEqual(names, ["ScopeFilter", "MetricTonCO2eTransformer", "HotspotDetector",
                                 "RecommendationTrigger", "AISummaryAggregator"])

    def test_reset_clears_every_processor(self):
        monitor = LiveCoachMonitor(s1_pipeline())
        list(monitor.watch(TelemetryStream(sample_events())))
        monitor.reset()
        self.assertEqual(len(monitor.get_aggregator()), 0)
        self.assertEqual(monitor.get_trigger().get_recommendations(), [])
        self.assertEqual(monitor.get_detector().snapshot()["department_totals_t"], {})

    def test_stream_feeds_the_ai_coach(self):
        monitor = LiveCoachMonitor(s1_pipeline())
        list(monitor.watch(TelemetryStream(sample_events())))
        context = PromptBuilder().build_context("ecotech", monitor.get_aggregator().category_totals())
        coach = AIAssistant(client=AIClient(api_key=""))
        user = User("ecotech", "m@x.de", "securePass123", role="manager")
        reply = coach.ask(user, "What is our biggest source?", context)
        self.assertIn("server_utility_log", reply.get_content())


if __name__ == "__main__":
    unittest.main()
