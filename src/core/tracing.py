"""
OpenTelemetry tracing utilities for Context Engineering Sandbox.

This module provides a centralized tracing setup using OpenTelemetry
with OTLP export to Prometheus/Grafana. It includes utilities for:
- Distributed tracing with spans
- Metrics recording
- Function and span decorators
"""

import logging
import psutil
import os
import threading
import time
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps
from collections import deque

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter

from src.core.config import get_config

logger = logging.getLogger(__name__)

# Global tracer provider instance
_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[Any] = None
_initialized: bool = False

# Global metrics provider instance
_meter_provider: Optional[MeterProvider] = None
_meter: Optional[Any] = None
_metrics_initialized: bool = False

# Metrics instruments cache
_metrics_instruments: Optional[Dict[str, Any]] = None

# Latency history for percentile calculations
_latency_history: deque = deque(maxlen=1000)


def initialize_tracing() -> None:
    """
    Initialize OpenTelemetry tracing from configuration.
    
    Sets up the tracer provider with OTLP exporter or console exporter
    based on configuration. Must be called before using tracing utilities.
    
    Raises:
        Exception: If tracing initialization fails
    """
    global _tracer_provider, _tracer, _initialized
    
    if _initialized:
        logger.warning("Tracing already initialized, skipping re-initialization")
        return
    
    try:
        config = get_config()
        
        # Get raw section and handle nested structure
        # tracing.yaml has root "tracing:" key, so config section contains {"tracing": {...}}
        tracing_config_raw = config.get_section("tracing")
        
        # Extract the actual config dict (handle nested "tracing" key)
        if isinstance(tracing_config_raw, dict) and "tracing" in tracing_config_raw:
            # Nested structure: {"tracing": {"service_name": ..., ...}}
            tracing_config = tracing_config_raw["tracing"]
        elif isinstance(tracing_config_raw, dict) and tracing_config_raw:
            # Flat structure: {"service_name": ..., ...}
            tracing_config = tracing_config_raw
        else:
            # Empty or invalid, use defaults
            tracing_config = {}
            logger.warning("No tracing configuration found, using defaults")
        
        logger.debug(f"Raw tracing config section: {tracing_config_raw}")
        logger.debug(f"Extracted tracing config: {tracing_config}")
        
        # Extract config values
        service_name = tracing_config.get("service_name", "context-engineering-sandbox")
        service_version = tracing_config.get("service_version", "1.5.0")
        exporter_type = tracing_config.get("exporter_type", "otlp")
        endpoint = tracing_config.get("otlp_endpoint", "localhost:4317")
        insecure = tracing_config.get("otlp_insecure", True)
        sampling_rate = tracing_config.get("sampling_rate", 1.0)
        metrics_export_interval_ms = tracing_config.get("metrics_export_interval_ms", 5000)
        
        logger.debug(f"Resolved endpoint: {endpoint}, insecure: {insecure}")
        logger.debug(f"Metrics export interval: {metrics_export_interval_ms}ms")
        
        # Configure resource with service information
        resource = Resource(
            attributes={
                "service.name": service_name,
                "service.version": service_version,
            }
        )
        
        if exporter_type == "otlp":
            
            logger.info(f"Initializing OTLP exporter to {endpoint} (insecure={insecure})")
            
            if endpoint == "localhost:4317":
                logger.warning(
                    "Using default endpoint 'localhost:4317'. "
                    "Expected endpoint from config: '51.210.255.198:4333'. "
                    "Check if tracing.yaml is loaded correctly."
                )
            
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                insecure=insecure,
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            
        elif exporter_type == "console":
            # Console exporter for development/debugging
            logger.info("Initializing console exporter")
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            
        else:
            raise ValueError(f"Unknown exporter type: {exporter_type}")
        
        # Configure sampling
        sampler = TraceIdRatioBased(sampling_rate)
        
        # Create and configure tracer provider
        _tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler
        )
        _tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)
        
        # Get tracer instance
        _tracer = trace.get_tracer(__name__)
        
        _initialized = True
        logger.info(f"OpenTelemetry tracing initialized (service={service_name}, endpoint={endpoint})")
        
        # Initialize metrics
        _initialize_metrics(resource, endpoint, insecure, metrics_export_interval_ms)
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}", exc_info=True)
        # Don't raise to allow application to continue without tracing
        raise


def _initialize_metrics(
    resource: Resource,
    endpoint: str,
    insecure: bool,
    export_interval_ms: int
) -> None:
    """
    Initialize OpenTelemetry Metrics API.
    
    Args:
        resource: Resource with service information
        endpoint: OTLP endpoint for metrics export
        insecure: Whether to use insecure connection
        export_interval_ms: Interval for periodic metric export in milliseconds
    """
    global _meter_provider, _meter, _metrics_instruments, _metrics_initialized
    
    if _metrics_initialized:
        logger.warning("Metrics already initialized, skipping re-initialization")
        return
    
    try:
        config = get_config()
        tracing_config_raw = config.get_section("tracing")
        
        # Extract config (handle nested structure)
        if isinstance(tracing_config_raw, dict) and "tracing" in tracing_config_raw:
            tracing_config = tracing_config_raw["tracing"]
        elif isinstance(tracing_config_raw, dict):
            tracing_config = tracing_config_raw
        else:
            tracing_config = {}
        
        # Check for separate metrics endpoint or metrics export type
        # Default: Use same endpoint as traces if not specified (for OTLP Collector setup)
        metrics_exporter_type = tracing_config.get("metrics_exporter_type", "console")
        if metrics_exporter_type == "otlp":
            # If OTLP is specified, default to same endpoint as traces (OTLP Collector pattern)
            metrics_endpoint = tracing_config.get("metrics_endpoint", endpoint)
            metrics_insecure = tracing_config.get("metrics_otlp_insecure", insecure)
        else:
            # For console or other types, endpoint doesn't matter
            metrics_endpoint = tracing_config.get("metrics_endpoint", endpoint)
            metrics_insecure = tracing_config.get("metrics_otlp_insecure", insecure)
        
        metric_exporter = None
        use_console_fallback = False
        
        # Try to create OTLP exporter if configured
        if metrics_exporter_type == "otlp":
            try:
                metric_exporter = OTLPMetricExporter(
                    endpoint=metrics_endpoint,
                    insecure=metrics_insecure,
                )
                # Inform user if using same endpoint (OTLP Collector pattern)
                if metrics_endpoint == endpoint:
                    logger.info(
                        f"Using OTLP Collector pattern: metrics export to {metrics_endpoint} "
                    )
                else:
                    logger.info(f"OTLP metrics export to {metrics_endpoint} (separate from traces)")
            except Exception as e:
                logger.warning(f"Failed to create OTLP metrics exporter: {e}")
                use_console_fallback = True
        elif metrics_exporter_type == "console":
            use_console_fallback = True
        
        # Fallback to console exporter if OTLP fails or is disabled
        if use_console_fallback or metric_exporter is None:
            logger.info(
                "Using console exporter for metrics. "
                "For production, set metrics_exporter_type: 'otlp' and metrics_endpoint to:\n"
                "  - OpenTelemetry Collector"
                "  - Prometheus via OTLP exporter\n"
                "Architecture: Application → OTLP Collector + Prometheus/Grafana (metrics)"
            )
            metric_exporter = ConsoleMetricExporter()
        
        # Create periodic export reader
        metric_reader = PeriodicExportingMetricReader(
            exporter=metric_exporter,
            export_interval_millis=export_interval_ms
        )
        
        # Create meter provider
        _meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(_meter_provider)
        
        # Get meter instance
        _meter = metrics.get_meter(__name__)
        
        # Initialize all metric instruments
        _initialize_metric_instruments()
        
        _metrics_initialized = True
        
        exporter_desc = "console" if use_console_fallback or metrics_exporter_type == "console" else f"OTLP ({metrics_endpoint})"
        logger.info(
            f"OpenTelemetry metrics initialized "
            f"(exporter: {exporter_desc}, interval: {export_interval_ms}ms, instruments: {len(_metrics_instruments)})"
        )
        
        # Start background polling for gauge metrics
        _start_metrics_polling()
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenElemetry metrics: {e}", exc_info=True)
        # Don't raise to allow application to continue without metrics
        # Metrics will still be collected and available via API, just not exported


def _initialize_metric_instruments() -> None:
    """
    Initialize all metric instruments.
    
    Creates Counter, Histogram, and Gauge instruments for all tracked metrics.
    """
    global _meter, _metrics_instruments
    
    if _meter is None:
        logger.error("Meter not initialized, cannot create instruments")
        return
    
    _metrics_instruments = {
        # Effectiveness metrics (histograms for scores 0-1)
        "accuracy": _meter.create_histogram(
            "revai.effectiveness.accuracy",
            description="Answer accuracy score (ROUGE-based)",
            unit="1"
        ),
        "relevance_score": _meter.create_histogram(
            "revai.effectiveness.relevance_score",
            description="Relevance score of response to query",
            unit="1"
        ),
        "hallucination_rate": _meter.create_histogram(
            "revai.effectiveness.hallucination_rate",
            description="Hallucination detection score (higher = more likely)",
            unit="1"
        ),
        "context_utilization": _meter.create_histogram(
            "revai.effectiveness.context_utilization",
            description="How much of provided context was utilized",
            unit="1"
        ),
        
        # Efficiency metrics
        "latency_p50": _meter.create_gauge(
            "revai.efficiency.latency_p50",
            description="50th percentile latency in milliseconds",
            unit="ms"
        ),
        "latency_p95": _meter.create_gauge(
            "revai.efficiency.latency_p95",
            description="95th percentile latency in milliseconds",
            unit="ms"
        ),
        "latency_p99": _meter.create_gauge(
            "revai.efficiency.latency_p99",
            description="99th percentile latency in milliseconds",
            unit="ms"
        ),
        "tokens_per_query": _meter.create_histogram(
            "revai.efficiency.tokens_per_query",
            description="Number of tokens used per query",
            unit="tokens"
        ),
        "cache_hit_rate": _meter.create_histogram(
            "revai.efficiency.cache_hit_rate",
            description="Cache hit rate (0-1)",
            unit="1"
        ),
        "cost_per_query": _meter.create_histogram(
            "revai.efficiency.cost_per_query",
            description="Cost per query in USD",
            unit="USD"
        ),
        
        # Scalability metrics
        "throughput": _meter.create_counter(
            "revai.scalability.throughput",
            description="Number of requests processed",
            unit="requests"
        ),
        "memory_usage": _meter.create_gauge(
            "revai.scalability.memory_usage",
            description="Memory usage in bytes",
            unit="bytes"
        ),
        "index_size": _meter.create_gauge(
            "revai.scalability.index_size",
            description="Size of vector index in bytes",
            unit="bytes"
        ),
        
        # Raw latency histogram for percentile calculations
        "latency": _meter.create_histogram(
            "revai.latency",
            description="Request latency in milliseconds",
            unit="ms"
        ),
    }
    
    logger.debug(f"Initialized {len(_metrics_instruments)} metric instruments")


def get_tracer() -> Any:
    """
    Get the global tracer instance.
    
    Returns:
        OpenTelemetry tracer instance
        
    Raises:
        RuntimeError: If tracing has not been initialized
    """
    global _tracer
    
    if not _initialized or _tracer is None:
        raise RuntimeError(
            "Tracing not initialized. Call initialize_tracing() first."
        )
    
    return _tracer


@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for creating a trace span.
    
    Args:
        name: Name of the span
        attributes: Optional dictionary of span attributes
        
    Yields:
        Span object that can be used to set additional attributes
        
    Example:
        >>> with trace_span("operation", {"key": "value"}) as span:
        ...     span.set_attribute("result", "success")
        ...     # do work
    """
    tracer = get_tracer()
    
    # start_as_current_span returns a context manager that handles span lifecycle
    with tracer.start_as_current_span(name) as span:
        try:
            # Set initial attributes if provided
            if attributes:
                for key, value in attributes.items():
                    # Convert value to string if not a supported type
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(key, value)
                    else:
                        span.set_attribute(key, str(value))
            
            # Log trace creation
            attrs_str = f" {{{', '.join(f'{k}={v}' for k, v in attributes.items())}}}" if attributes else ""
            logger.debug(f"Trace: {name}{attrs_str}")
            
            yield span
            
            # Log successful span completion
            logger.debug(f"Trace completed: {name}")
            
        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logger.debug(f"Trace failed: {name} - {str(e)}")
            raise


def trace_function(attributes: Optional[Dict[str, Any]] = None):
    """
    Decorator for automatically tracing function execution.
    
    Args:
        attributes: Optional dictionary of attributes to add to the span
        
    Returns:
        Decorator function
        
    Example:
        >>> @trace_function(attributes={"tool": "calculate"})
        ... def calculate(x, y):
        ...     return x + y
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate span name from function
            span_name = f"{func.__module__}.{func.__name__}"
            
            # Merge function attributes with provided attributes
            func_attrs = attributes.copy() if attributes else {}
            func_attrs.update({
                "function.name": func.__name__,
                "function.module": func.__module__,
            })
            
            with trace_span(span_name, func_attrs) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def record_metric(
    name: str,
    value: float,
    attributes: Optional[Dict[str, Any]] = None
) -> None:
    """
    Record a metric value using OpenTelemetry Metrics API.
    
    Records metrics to appropriate instruments (Counter, Histogram, Gauge)
    based on metric name. Also updates latency history for percentile calculations.
    
    Args:
        name: Name of the metric (maps to instrument names)
        value: Metric value
        attributes: Optional dictionary of metric attributes/labels
    """
    global _metrics_instruments, _latency_history
    
    try:
        if not _metrics_initialized:
            logger.debug(f"Metrics not initialized, skipping: {name}")
            return
        
        if _metrics_instruments is None:
            logger.debug(f"Metrics instruments not created, skipping: {name}")
            return
        
        # Convert attributes to label format (must be strings)
        labels = {}
        if attributes:
            for key, val in attributes.items():
                labels[key] = str(val) if not isinstance(val, (str, int, float, bool)) else str(val)
        
        # Format for logging
        labels_str = f" {{{', '.join(f'{k}={v}' for k, v in labels.items())}}}" if labels else ""
        
        # Record to appropriate instrument based on metric name
        instrument = _metrics_instruments.get(name)
        
        if instrument is not None:
            # Record based on instrument type
            if hasattr(instrument, 'record'):
                # Histogram
                instrument.record(value, attributes=labels)
                logger.debug(f"Metric: revai.{name}={value:.2f}{labels_str}")
            elif hasattr(instrument, 'set'):
                # Gauge
                instrument.set(value, attributes=labels)
                logger.debug(f"Metric: revai.{name}={value:.2f}{labels_str}")
            elif hasattr(instrument, 'add'):
                # Counter
                instrument.add(int(value), attributes=labels)
                logger.debug(f"Metric: revai.{name}+={int(value)}{labels_str}")
        else:
            # Try latency instrument for latency metrics
            if name == "latency":
                latency_instr = _metrics_instruments.get("latency")
                if latency_instr:
                    latency_instr.record(value, attributes=labels)
                    logger.debug(f"Metric: revai.latency={value:.2f}ms{labels_str}")
                    # Store in history for percentile calculation
                    _latency_history.append(value)
            
            # Also store as span attribute for trace correlation
            span = trace.get_current_span()
            if span.is_recording():
                span.set_attribute(f"metric.{name}", value)
        
    except Exception as e:
        logger.debug(f"Failed to record metric {name}: {e}")


def record_throughput(attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record a throughput event (typically request arrival).
    
    Increments the throughput counter metric.
    
    Args:
        attributes: Optional dictionary of attributes/labels
    """
    global _metrics_instruments
    
    try:
        if _metrics_initialized and _metrics_instruments:
            throughput_counter = _metrics_instruments.get("throughput")
            if throughput_counter:
                # Convert attributes to labels
                labels = {}
                if attributes:
                    for key, val in attributes.items():
                        labels[key] = str(val) if not isinstance(val, (str, int, float, bool)) else str(val)
                
                throughput_counter.add(1, attributes=labels)
        
        # Also record as span event for trace correlation
        span = trace.get_current_span()
        if span.is_recording():
            throughput_attrs = {"event.type": "throughput"}
            if attributes:
                throughput_attrs.update(attributes)
            span.add_event("throughput", attributes=throughput_attrs)
        
    except Exception as e:
        logger.debug(f"Failed to record throughput: {e}")


def update_memory_usage() -> None:
    """
    Update memory usage metrics.
    
    Records current process memory usage using the memory_usage gauge metric.
    """
    global _metrics_instruments
    
    try:
        if not _metrics_initialized or _metrics_instruments is None:
            return
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_bytes = float(memory_info.rss)
        
        # Record to memory_usage gauge
        memory_gauge = _metrics_instruments.get("memory_usage")
        if memory_gauge:
            memory_gauge.set(memory_bytes)
            logger.debug(f"Metric: revai.scalability.memory_usage={memory_bytes / 1024 / 1024:.1f}MB")
        
    except Exception as e:
        logger.debug(f"Failed to update memory usage: {e}")


def _update_latency_percentiles() -> None:
    """
    Calculate and update latency percentiles (P50, P95, P99).
    
    This should be called periodically to update gauge metrics with
    current percentile values from latency history.
    """
    global _latency_history, _metrics_instruments
    
    try:
        if not _metrics_initialized or _metrics_instruments is None:
            return
        
        if len(_latency_history) < 2:
            return
        
        # Calculate percentiles
        sorted_latencies = sorted(_latency_history)
        n = len(sorted_latencies)
        
        p50_idx = int(n * 0.50)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        p50 = sorted_latencies[p50_idx] if p50_idx < n else sorted_latencies[-1]
        p95 = sorted_latencies[p95_idx] if p95_idx < n else sorted_latencies[-1]
        p99 = sorted_latencies[p99_idx] if p99_idx < n else sorted_latencies[-1]
        
        # Update gauge metrics
        p50_gauge = _metrics_instruments.get("latency_p50")
        p95_gauge = _metrics_instruments.get("latency_p95")
        p99_gauge = _metrics_instruments.get("latency_p99")
        
        if p50_gauge:
            p50_gauge.set(p50)
        if p95_gauge:
            p95_gauge.set(p95)
        if p99_gauge:
            p99_gauge.set(p99)
            
    except Exception as e:
        logger.debug(f"Failed to update latency percentiles: {e}")


def _start_metrics_polling() -> None:
    """
    Start background thread for periodic metric updates.
    
    Polls metrics at configured intervals:
    - Memory usage updates
    - Latency percentile calculations
    """
    def _poll_metrics():
        try:
            config = get_config()
            tracing_config_raw = config.get_section("tracing")
            
            # Extract config (handle nested structure)
            if isinstance(tracing_config_raw, dict) and "tracing" in tracing_config_raw:
                tracing_config = tracing_config_raw["tracing"]
            elif isinstance(tracing_config_raw, dict):
                tracing_config = tracing_config_raw
            else:
                tracing_config = {}
            
            poll_interval_s = tracing_config.get("metrics_export_interval_ms", 5000) / 1000.0
            
            while _metrics_initialized:
                try:
                    update_memory_usage()
                    _update_latency_percentiles()
                except Exception as e:
                    logger.debug(f"Error in metrics polling: {e}")
                
                time.sleep(poll_interval_s)
                
        except Exception as e:
            logger.error(f"Metrics polling thread error: {e}")
    
    # Start polling thread
    polling_thread = threading.Thread(target=_poll_metrics, daemon=True)
    polling_thread.start()
    logger.debug("Started metrics polling thread")


def get_metrics_instruments() -> Dict[str, Any]:
    """
    Get metrics instruments for recording metrics.
    
    Returns a dictionary of OpenTelemetry metric instruments.
    
    Returns:
        Dictionary containing metric instruments
    """
    global _metrics_instruments
    
    if _metrics_instruments is None:
        logger.warning("Metrics instruments not initialized")
        return {}
    
    return _metrics_instruments


def record_latency(value: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record latency value and update percentiles.
    
    Convenience function for recording latency. Also stores value
    in history for percentile calculations.
    
    Args:
        value: Latency in milliseconds
        attributes: Optional dictionary of attributes
    """
    record_metric("latency", value, attributes)


def record_cache_hit_rate(value: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record cache hit rate (0-1).
    
    Args:
        value: Cache hit rate between 0 and 1
        attributes: Optional dictionary of attributes
    """
    record_metric("cache_hit_rate", value, attributes)


def record_cost_per_query(value: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record cost per query in USD.
    
    Args:
        value: Cost in USD
        attributes: Optional dictionary of attributes
    """
    record_metric("cost_per_query", value, attributes)


def record_index_size(value: float, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record vector index size in bytes.
    
    Args:
        value: Index size in bytes
        attributes: Optional dictionary of attributes
    """
    global _metrics_instruments
    
    try:
        if _metrics_initialized and _metrics_instruments:
            index_gauge = _metrics_instruments.get("index_size")
            if index_gauge:
                labels = {}
                if attributes:
                    for key, val in attributes.items():
                        labels[key] = str(val) if not isinstance(val, (str, int, float, bool)) else str(val)
                index_gauge.set(value, attributes=labels)
    except Exception as e:
        logger.debug(f"Failed to record index size: {e}")


def force_flush() -> None:
    """
    Force flush of all pending spans and metrics.
    
    Useful for ensuring spans and metrics are exported before application shutdown.
    """
    global _tracer_provider, _meter_provider
    
    if _tracer_provider:
        try:
            _tracer_provider.force_flush()
            logger.debug("Tracer provider flushed successfully")
        except Exception as e:
            logger.warning(f"Failed to flush tracer provider: {e}")
    
    if _meter_provider:
        try:
            # Force flush metrics readers
            for reader in _meter_provider._metric_readers:
                reader.force_flush()
            logger.debug("Metric provider flushed successfully")
        except Exception as e:
            logger.warning(f"Failed to flush metric provider: {e}")
