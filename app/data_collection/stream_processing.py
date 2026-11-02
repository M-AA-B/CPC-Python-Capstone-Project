from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator, Iterable, Any
import uuid


class TelemetryRecord:
    """Represents an operational telemetry event for real-time stream ingestion (Hometask 2)."""

    def __init__(
        self,
        event_id: str | None = None,
        source: str = "operational_telemetry",
        scope: int = 1,
        activity_metric: float = 0.0,
        unit: str = "kWh",
        metadata: dict | None = None
    ):
        self._event_id = event_id or str(uuid.uuid4())
        self._source = source
        self._scope = int(scope)
        self._activity_metric = float(activity_metric)
        self._unit = unit
        self._metadata = metadata or {}
        self._calculated_co2e_metric_tons: float | None = None

    # --- Encapsulation: Getters & Setters (Hometask 1) ---
    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, value: str) -> None:
        if not value:
            raise ValueError("Source cannot be empty.")
        self._source = str(value)

    @property
    def scope(self) -> int:
        return self._scope

    @scope.setter
    def scope(self, value: int) -> None:
        if value not in (1, 2, 3):
            raise ValueError("Scope must be 1, 2, or 3.")
        self._scope = int(value)

    @property
    def activity_metric(self) -> float:
        return self._activity_metric

    @activity_metric.setter
    def activity_metric(self, value: float) -> None:
        val = float(value)
        if val < 0:
            raise ValueError("Activity metric value cannot be negative.")
        self._activity_metric = val

    @property
    def unit(self) -> str:
        return self._unit

    @unit.setter
    def unit(self, value: str) -> None:
        self._unit = str(value)

    @property
    def calculated_co2e_metric_tons(self) -> float | None:
        return self._calculated_co2e_metric_tons

    @calculated_co2e_metric_tons.setter
    def calculated_co2e_metric_tons(self, value: float | None) -> None:
        if value is not None and value < 0:
            raise ValueError("Calculated CO2e metric tons cannot be negative.")
        self._calculated_co2e_metric_tons = round(float(value), 4) if value is not None else None

    @property
    def metadata(self) -> dict:
        return self._metadata

    def to_dict(self) -> dict:
        return {
            "event_id": self._event_id,
            "source": self._source,
            "scope": self._scope,
            "activity_metric": self._activity_metric,
            "unit": self._unit,
            "metadata": self._metadata,
            "calculated_co2e_metric_tons": self._calculated_co2e_metric_tons
        }


class StreamProcessor(ABC):
    """Abstract Base Class (ABC) defining interface contract for stream processors (Hometask 2)."""

    @abstractmethod
    def process(self, record: TelemetryRecord) -> TelemetryRecord | None:
        """Processes a single record. Returns the modified record, or None to filter it out."""
        pass

    def __or__(self, other: StreamProcessor) -> CompositeStreamProcessor:
        """Operator overloading: compose processing pipelines using the pipe '|' operator."""
        if not isinstance(other, StreamProcessor):
            return NotImplemented
        return CompositeStreamProcessor([self, other])

    def __add__(self, other: StreamProcessor) -> CompositeStreamProcessor:
        """Operator overloading: compose processing pipelines using the '+' operator."""
        return self.__or__(other)

    def process_stream(self, stream: Iterable[TelemetryRecord]) -> Iterator[TelemetryRecord]:
        """Generator that yields successfully processed, non-filtered records."""
        for record in stream:
            result = self.process(record)
            if result is not None:
                yield result


class CompositeStreamProcessor(StreamProcessor):
    """Polymorphic composite pipeline that chains multiple StreamProcessors together."""

    def __init__(self, processors: list[StreamProcessor] | None = None):
        self.processors: list[StreamProcessor] = []
        if processors:
            for p in processors:
                if isinstance(p, CompositeStreamProcessor):
                    self.processors.extend(p.processors)
                else:
                    self.processors.append(p)

    def process(self, record: TelemetryRecord) -> TelemetryRecord | None:
        current: TelemetryRecord | None = record
        for processor in self.processors:
            if current is None:
                return None
            current = processor.process(current)
        return current

    def __or__(self, other: StreamProcessor) -> CompositeStreamProcessor:
        if isinstance(other, CompositeStreamProcessor):
            return CompositeStreamProcessor(self.processors + other.processors)
        elif isinstance(other, StreamProcessor):
            return CompositeStreamProcessor(self.processors + [other])
        return NotImplemented


class ScopeFilter(StreamProcessor):
    """Specialized stream processor filtering operational activity records by Scope tag (1, 2, or 3)."""

    def __init__(self, target_scopes: int | Iterable[int]):
        if isinstance(target_scopes, int):
            self._target_scopes = {target_scopes}
        else:
            self._target_scopes = set(target_scopes)

    @property
    def target_scopes(self) -> set[int]:
        return self._target_scopes

    def process(self, record: TelemetryRecord) -> TelemetryRecord | None:
        """Filters out records not matching target scopes."""
        if record.scope in self._target_scopes:
            return record
        return None


class MetricTonCO2eTransformer(StreamProcessor):
    """Transforms operational activity metrics into metric tons of CO2e using domain emission factors."""

    DEFAULT_FACTORS_PER_UNIT_TO_METRIC_TONS = {
        # kg CO2e / unit * 0.001 = metric tons CO2e / unit
        "flight_booking": 0.00015,       # ~0.15 kg CO2e / passenger-km = 0.00015 metric tons
        "server_utility_log": 0.00042,   # ~0.42 kg CO2e / kWh = 0.00042 metric tons
        "freight_logistics": 0.00008,    # ~0.08 kg CO2e / ton-km = 0.00008 metric tons
        "electricity": 0.00042,
        "natural_gas": 0.00203,
        "company_vehicles": 0.00268,
        "business_travel": 0.00018,
        "waste": 0.00052
    }

    def __init__(self, custom_factors: dict[str, float] | None = None):
        self._factors = dict(self.DEFAULT_FACTORS_PER_UNIT_TO_METRIC_TONS)
        if custom_factors:
            self._factors.update(custom_factors)

    def process(self, record: TelemetryRecord) -> TelemetryRecord:
        """Transforms activity metrics to metric tons CO2e."""
        factor = self._factors.get(record.source.lower()) or self._factors.get(record.unit.lower(), 0.00042)
        record.calculated_co2e_metric_tons = record.activity_metric * factor
        return record


class TelemetryStream:
    """Consumes real-time events, implementing Python's Iterator protocol (__iter__ & __next__)."""

    def __init__(self, events: Iterable[TelemetryRecord] | None = None):
        self._events: list[TelemetryRecord] = list(events) if events else []
        self._index: int = 0

    def add_event(self, event: TelemetryRecord) -> None:
        self._events.append(event)

    def __iter__(self) -> TelemetryStream:
        self._index = 0
        return self

    def __next__(self) -> TelemetryRecord:
        if self._index < len(self._events):
            record = self._events[self._index]
            self._index += 1
            return record
        raise StopIteration

    def __len__(self) -> int:
        return len(self._events)

