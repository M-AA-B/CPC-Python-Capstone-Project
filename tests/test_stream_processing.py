"""
Tests for Hometask 2: Real-Time Stream Processing Pipeline
- ABC/abstractmethod interface contracts
- Inheritance & Polymorphism (ScopeFilter, MetricTonCO2eTransformer)
- Operator Overloading (__or__ / __add__ pipeline composition)
- Iterators & Generators (__iter__ / __next__ on TelemetryStream)
- Domain: Enterprise Carbon Footprint Tracker (flight bookings, server logs, freight)
"""
import pytest
from app.data_collection.stream_processing import (
    TelemetryRecord,
    TelemetryStream,
    StreamProcessor,
    ScopeFilter,
    MetricTonCO2eTransformer,
    CompositeStreamProcessor,
)


# --- Fixtures ---

@pytest.fixture
def flight_event():
    return TelemetryRecord(event_id="ev-001", source="flight_booking", scope=3, activity_metric=5000.0, unit="passenger-km")

@pytest.fixture
def server_event():
    return TelemetryRecord(event_id="ev-002", source="server_utility_log", scope=2, activity_metric=10000.0, unit="kWh")

@pytest.fixture
def freight_event():
    return TelemetryRecord(event_id="ev-003", source="freight_logistics", scope=3, activity_metric=2000.0, unit="ton-km")

@pytest.fixture
def scope1_event():
    return TelemetryRecord(event_id="ev-004", source="company_vehicles", scope=1, activity_metric=500.0, unit="liters")

@pytest.fixture
def sample_stream(flight_event, server_event, freight_event, scope1_event):
    stream = TelemetryStream([flight_event, server_event, freight_event, scope1_event])
    return stream


# --- Hometask 1: OOP - Encapsulation via @property getters/setters ---

def test_telemetry_record_getters_setters(flight_event):
    """Tests TelemetryRecord @property accessor/mutator methods (Hometask 1 encapsulation)."""
    assert flight_event.source == "flight_booking"
    assert flight_event.scope == 3
    assert flight_event.activity_metric == 5000.0

    flight_event.source = "updated_source"
    assert flight_event.source == "updated_source"

    flight_event.scope = 1
    assert flight_event.scope == 1

    flight_event.activity_metric = 999.5
    assert flight_event.activity_metric == 999.5

    with pytest.raises(ValueError):
        flight_event.scope = 5  # invalid scope

    with pytest.raises(ValueError):
        flight_event.activity_metric = -1.0  # negative metric


# --- Hometask 2: Abstract Base Classes (ABCs) ---

def test_stream_processor_is_abstract():
    """StreamProcessor must be abstract and cannot be instantiated directly (Hometask 2 ABC)."""
    with pytest.raises(TypeError):
        StreamProcessor()


# --- Hometask 2: Inheritance & Polymorphism ---

def test_scope_filter_allows_matching_scope(server_event):
    """ScopeFilter (Polymorphic StreamProcessor) passes records matching target scope."""
    filt = ScopeFilter(target_scopes=2)
    result = filt.process(server_event)
    assert result is server_event


def test_scope_filter_blocks_non_matching_scope(flight_event):
    """ScopeFilter returns None to drop records not matching target scope."""
    filt = ScopeFilter(target_scopes=1)
    result = filt.process(flight_event)
    assert result is None


def test_transformer_calculates_co2e_metric_tons(server_event):
    """MetricTonCO2eTransformer assigns calculated_co2e_metric_tons in metric tons (Hometask 2)."""
    transformer = MetricTonCO2eTransformer()
    result = transformer.process(server_event)
    assert result.calculated_co2e_metric_tons is not None
    # 10000 kWh * 0.00042 metric_tons/kWh = 4.2
    assert result.calculated_co2e_metric_tons == pytest.approx(4.2, rel=1e-3)


def test_transformer_flight_booking(flight_event):
    """MetricTonCO2eTransformer correctly calculates flight booking emissions."""
    transformer = MetricTonCO2eTransformer()
    result = transformer.process(flight_event)
    # 5000 passenger-km * 0.00015 = 0.75 metric tons CO2e
    assert result.calculated_co2e_metric_tons == pytest.approx(0.75, rel=1e-3)


# --- Hometask 2: Operator Overloading (__or__ / __add__) ---

def test_pipeline_composition_with_pipe_operator(server_event, freight_event, flight_event):
    """Operator overloading: '|' composes processors into a CompositeStreamProcessor (Hometask 2)."""
    scope2_filter = ScopeFilter(target_scopes=2)
    transformer = MetricTonCO2eTransformer()

    pipeline = scope2_filter | transformer
    assert isinstance(pipeline, CompositeStreamProcessor)

    # server_event is Scope 2 - should pass filter and get transformed
    result = pipeline.process(server_event)
    assert result is not None
    assert result.calculated_co2e_metric_tons is not None

    # flight_event is Scope 3 - should be filtered out
    result = pipeline.process(flight_event)
    assert result is None


def test_pipeline_composition_with_add_operator(server_event):
    """Operator overloading: '+' also composes processors (Hometask 2 __add__)."""
    pipeline = ScopeFilter(target_scopes=2) + MetricTonCO2eTransformer()
    assert isinstance(pipeline, CompositeStreamProcessor)
    result = pipeline.process(server_event)
    assert result is not None


def test_chained_multi_stage_pipeline(flight_event, server_event, freight_event, scope1_event):
    """Tests chaining 3 processors with '|' into a multi-stage composite pipeline."""
    scope3_filter = ScopeFilter(target_scopes=3)
    transformer = MetricTonCO2eTransformer()
    scope2_filter = ScopeFilter(target_scopes={1, 3})  # second passthrough filter

    pipeline = scope3_filter | transformer | scope2_filter
    assert isinstance(pipeline, CompositeStreamProcessor)
    assert len(pipeline.processors) == 3


# --- Hometask 2: Iterators & Generators (__iter__ & __next__) ---

def test_telemetry_stream_iterator_protocol(sample_stream):
    """TelemetryStream implements __iter__ and __next__ for event consumption (Hometask 2)."""
    count = 0
    for record in sample_stream:
        assert isinstance(record, TelemetryRecord)
        count += 1
    assert count == 4


def test_telemetry_stream_raises_stop_iteration(sample_stream):
    """TelemetryStream correctly raises StopIteration after consuming all events."""
    it = iter(sample_stream)
    events_consumed = []
    with pytest.raises(StopIteration):
        while True:
            events_consumed.append(next(it))
    assert len(events_consumed) == 4


def test_telemetry_stream_is_reusable(sample_stream):
    """TelemetryStream can be iterated multiple times (re-entrant)."""
    first_pass = list(sample_stream)
    second_pass = list(sample_stream)
    assert len(first_pass) == len(second_pass) == 4


def test_stream_process_stream_generator(sample_stream):
    """process_stream() is a generator yielding only non-filtered records."""
    scope3_filter = ScopeFilter(target_scopes=3)
    transformer = MetricTonCO2eTransformer()
    pipeline = scope3_filter | transformer

    results = list(pipeline.process_stream(sample_stream))
    # Only flight_event (Scope 3) and freight_event (Scope 3) should pass
    assert len(results) == 2
    for r in results:
        assert r.scope == 3
        assert r.calculated_co2e_metric_tons is not None


# --- Full Pipeline End-to-End (Enterprise Carbon Footprint Tracker context) ---

def test_full_carbon_footprint_pipeline():
    """
    End-to-end Hometask 2 demonstration:
    Ingests operational telemetry (flight bookings, server logs, freight),
    filters by Scope 3, transforms to metric tons CO2e.
    """
    events = [
        TelemetryRecord(source="flight_booking",      scope=3, activity_metric=8000.0,  unit="passenger-km"),
        TelemetryRecord(source="server_utility_log",  scope=2, activity_metric=50000.0, unit="kWh"),  # filtered out
        TelemetryRecord(source="freight_logistics",   scope=3, activity_metric=3000.0,  unit="ton-km"),
        TelemetryRecord(source="server_utility_log",  scope=2, activity_metric=30000.0, unit="kWh"),  # filtered out
    ]

    stream = TelemetryStream(events)
    pipeline = ScopeFilter(target_scopes=3) | MetricTonCO2eTransformer()

    scope3_results = list(pipeline.process_stream(stream))

    assert len(scope3_results) == 2
    assert all(r.scope == 3 for r in scope3_results)
    assert all(r.calculated_co2e_metric_tons is not None for r in scope3_results)

    # flight: 8000 * 0.00015 = 1.2 metric tons
    assert scope3_results[0].calculated_co2e_metric_tons == pytest.approx(1.2, rel=1e-3)
    # freight: 3000 * 0.00008 = 0.24 metric tons
    assert scope3_results[1].calculated_co2e_metric_tons == pytest.approx(0.24, rel=1e-3)

