"""S3 Real-Time Insights (Hometask 2) — Owner: Junaid Ahmad · 7222074.

Subsystem 3 processors that plug into the S1 stream framework
(app/data_collection/stream_processing.py) and react to telemetry as it arrives:

    ScopeFilter | MetricTonCO2eTransformer          (S1, Mohammed)
        | HotspotDetector | RecommendationTrigger | AISummaryAggregator   (S3)

HotspotDetector        flags events / departments that emit too much and raises alerts
RecommendationTrigger  turns a hotspot into an S3 Recommendation (once per department + source)
AISummaryAggregator    keeps running totals: the only data the AI coach is allowed to see
LiveCoachMonitor       runs the pipeline and yields alerts the moment they happen (generator)

Departments come from TelemetryRecord.metadata["department"].
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Iterable, Iterator

from app.data_collection.stream_processing import (
    CompositeStreamProcessor,
    StreamProcessor,
    TelemetryRecord,
)
from app.models import Recommendation

UNASSIGNED = "unassigned"


def _department(record: TelemetryRecord) -> str:
    return str(record.metadata.get("department") or UNASSIGNED)


def _tons(record: TelemetryRecord) -> float:
    tons = record.calculated_co2e_metric_tons
    if tons is None:
        raise ValueError(
            f"Event {record.event_id} has no CO2e value yet: put MetricTonCO2eTransformer before S3 processors."
        )
    return tons


# --- Alerts ------------------------------------------------------------------

class HotspotAlert:
    """One real-time warning about a department. Sortable by severity (operator overloading)."""

    def __init__(self, department: str, source: str, co2e_t: float, reason: str):
        self._department = department
        self._source = source
        self._co2e_t = round(float(co2e_t), 4)
        self._reason = reason

    def get_department(self) -> str:
        return self._department

    def get_source(self) -> str:
        return self._source

    def get_co2e_t(self) -> float:
        return self._co2e_t

    def get_reason(self) -> str:
        return self._reason

    def __lt__(self, other: HotspotAlert) -> bool:
        """`alert_a < alert_b` compares emissions, so sorted(alerts) orders by severity."""
        if not isinstance(other, HotspotAlert):
            return NotImplemented
        return self._co2e_t < other._co2e_t

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HotspotAlert):
            return NotImplemented
        return (self._department, self._source, self._co2e_t, self._reason) == (
            other._department, other._source, other._co2e_t, other._reason)

    def __str__(self) -> str:
        return f"[{self._department}] {self._source}: {self._co2e_t:.4f} t CO2e - {self._reason}"

    def __repr__(self) -> str:
        return f"HotspotAlert({self._department!r}, {self._source!r}, {self._co2e_t!r}, {self._reason!r})"


class AlertFeed:
    """Queue of pending alerts. Iterator protocol: each alert is delivered exactly once."""

    def __init__(self):
        self._pending: list[HotspotAlert] = []
        self._delivered: int = 0

    def push(self, alert: HotspotAlert) -> None:
        self._pending.append(alert)

    def get_delivered_count(self) -> int:
        return self._delivered

    def __iter__(self) -> AlertFeed:
        return self

    def __next__(self) -> HotspotAlert:
        if not self._pending:
            raise StopIteration
        self._delivered += 1
        return self._pending.pop(0)

    def __len__(self) -> int:
        return len(self._pending)


# --- S3 stream processors ------------------------------------------------------

class StatefulProcessor(StreamProcessor):
    """Abstract base for S3 processors that remember what they have seen in the stream.

    Adds two more contract methods to StreamProcessor.process():
    snapshot() reports the current state, reset() starts over (e.g. at the start of a month).
    """

    @abstractmethod
    def snapshot(self) -> dict:
        """Current state as a plain dict."""

    @abstractmethod
    def reset(self) -> None:
        """Forget everything seen so far."""


class HotspotDetector(StatefulProcessor):
    """Flags a record when one event is large, or when it pushes its department over budget."""

    def __init__(self, event_threshold_t: float = 1.0, department_budget_t: float = 5.0):
        self._event_threshold_t: float = 1.0
        self._department_budget_t: float = 5.0
        self._totals_t: dict[str, float] = {}
        self._feed: AlertFeed = AlertFeed()
        self.set_event_threshold_t(event_threshold_t)
        self.set_department_budget_t(department_budget_t)

    def get_event_threshold_t(self) -> float:
        return self._event_threshold_t

    def set_event_threshold_t(self, tons: float) -> None:
        value = float(tons)
        if value <= 0:
            raise ValueError("Event threshold must be greater than 0 t.")
        self._event_threshold_t = value

    def get_department_budget_t(self) -> float:
        return self._department_budget_t

    def set_department_budget_t(self, tons: float) -> None:
        value = float(tons)
        if value <= 0:
            raise ValueError("Department budget must be greater than 0 t.")
        self._department_budget_t = value

    def alerts(self) -> AlertFeed:
        return self._feed

    def process(self, record: TelemetryRecord) -> TelemetryRecord:
        tons = _tons(record)
        department = _department(record)
        before = self._totals_t.get(department, 0.0)
        after = before + tons
        self._totals_t[department] = after

        reasons = []
        if tons >= self._event_threshold_t:
            reasons.append(f"single event above {self._event_threshold_t} t")
        if before < self._department_budget_t <= after:
            reasons.append(f"department passed its {self._department_budget_t} t budget")
        if reasons:
            reason = "; ".join(reasons)
            record.metadata["hotspot"] = reason
            self._feed.push(HotspotAlert(department, record.source, tons, reason))
        return record

    def snapshot(self) -> dict:
        return {
            "department_totals_t": {d: round(t, 4) for d, t in self._totals_t.items()},
            "over_budget": sorted(d for d, t in self._totals_t.items() if t >= self._department_budget_t),
        }

    def reset(self) -> None:
        self._totals_t.clear()
        self._feed = AlertFeed()


class RecommendationTrigger(StatefulProcessor):
    """Creates one S3 Recommendation per (department, source) the first time it becomes a hotspot."""

    def __init__(self, saving_share: float = 0.15):
        self._saving_share: float = 0.15
        self._recommendations: dict[tuple[str, str], Recommendation] = {}
        self.set_saving_share(saving_share)

    def get_saving_share(self) -> float:
        return self._saving_share

    def set_saving_share(self, share: float) -> None:
        value = float(share)
        if not 0 < value <= 1:
            raise ValueError("Saving share must be between 0 and 1.")
        self._saving_share = value

    def get_recommendations(self) -> list[Recommendation]:
        return list(self._recommendations.values())

    @staticmethod
    def _effort(saving_kg: float) -> str:
        if saving_kg >= 1000:
            return "high"
        return "medium" if saving_kg >= 100 else "low"

    def process(self, record: TelemetryRecord) -> TelemetryRecord:
        if record.metadata.get("hotspot"):
            key = (_department(record), record.source)
            if key not in self._recommendations:
                saving_kg = _tons(record) * 1000 * self._saving_share
                self._recommendations[key] = Recommendation(
                    department_id=key[0],
                    title=f"Cut {record.source.replace('_', ' ')} emissions by {self._saving_share:.0%}",
                    est_saving_kg=saving_kg,
                    effort=self._effort(saving_kg),
                )
        return record

    def snapshot(self) -> dict:
        return {"recommendations": [tip.to_dict() for tip in self._recommendations.values()]}

    def reset(self) -> None:
        self._recommendations.clear()


class AISummaryAggregator(StatefulProcessor):
    """Running totals per category, scope and department. Raw events never leave this class."""

    def __init__(self):
        self._by_category_kg: dict[str, float] = {}
        self._by_scope_kg: dict[int, float] = {}
        self._by_department_kg: dict[str, float] = {}
        self._events: int = 0

    def process(self, record: TelemetryRecord) -> TelemetryRecord:
        kg = _tons(record) * 1000
        for totals, key in ((self._by_category_kg, record.source),
                            (self._by_scope_kg, record.scope),
                            (self._by_department_kg, _department(record))):
            totals[key] = totals.get(key, 0.0) + kg
        self._events += 1
        return record

    def category_totals(self) -> dict[str, float]:
        """kg CO2e per category, ready for PromptBuilder.build_context()."""
        return {name: round(kg, 2) for name, kg in self._by_category_kg.items()}

    def snapshot(self) -> dict:
        return {
            "events": self._events,
            "total_co2e_kg": round(sum(self._by_category_kg.values()), 2),
            "by_category_kg": self.category_totals(),
            "by_scope_kg": {f"scope_{s}": round(kg, 2) for s, kg in sorted(self._by_scope_kg.items())},
            "by_department_kg": {d: round(kg, 2) for d, kg in self._by_department_kg.items()},
        }

    def reset(self) -> None:
        self._by_category_kg.clear()
        self._by_scope_kg.clear()
        self._by_department_kg.clear()
        self._events = 0

    def __len__(self) -> int:
        return self._events


# --- Orchestration -------------------------------------------------------------

class LiveCoachMonitor:
    """Runs the S1 + S3 pipeline over a stream and yields alerts in real time."""

    def __init__(self, s1_pipeline: StreamProcessor,
                 detector: HotspotDetector | None = None,
                 trigger: RecommendationTrigger | None = None,
                 aggregator: AISummaryAggregator | None = None):
        self._detector = detector or HotspotDetector()
        self._trigger = trigger or RecommendationTrigger()
        self._aggregator = aggregator or AISummaryAggregator()
        # Operator overloading from the S1 framework: S1 steps | S3 steps
        self._pipeline: CompositeStreamProcessor = (
            s1_pipeline | self._detector | self._trigger | self._aggregator
        )

    def get_pipeline(self) -> CompositeStreamProcessor:
        return self._pipeline

    def get_detector(self) -> HotspotDetector:
        return self._detector

    def get_trigger(self) -> RecommendationTrigger:
        return self._trigger

    def get_aggregator(self) -> AISummaryAggregator:
        return self._aggregator

    def watch(self, stream: Iterable[TelemetryRecord]) -> Iterator[HotspotAlert]:
        """Generator: processes one event at a time and yields its alerts immediately."""
        for _record in self._pipeline.process_stream(stream):
            yield from self._detector.alerts()

    def reset(self) -> None:
        """Polymorphism: every S3 processor resets itself in its own way."""
        for processor in (self._detector, self._trigger, self._aggregator):
            processor.reset()
