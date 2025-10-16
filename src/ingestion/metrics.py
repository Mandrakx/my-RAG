"""
Prometheus Metrics for Audio Ingestion

Instrumentation aligned with ADR-2025-10-03-003 SLA monitoring requirements
"""

import logging
from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Optional
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)

# ==============================================================================
# Metrics Definitions (per ADR-2025-10-03-003)
# ==============================================================================

# Ack Latency (SLA: p95 < 3s warning, < 5s critical)
audio_ingest_ack_latency_seconds = Histogram(
    'audio_ingest_ack_latency_seconds',
    'Time from message receipt to ack (seconds)',
    buckets=[0.5, 1, 2, 3, 5, 10, 30, 60]
)

# Validation Duration
audio_ingest_validation_duration_seconds = Summary(
    'audio_ingest_validation_duration_seconds',
    'Time spent validating conversation.json schema'
)

# Processing Duration (end-to-end)
audio_ingest_processing_duration_seconds = Histogram(
    'audio_ingest_processing_duration_seconds',
    'Total processing time from download to completion',
    buckets=[5, 10, 30, 60, 120, 300, 600]
)

# Checksum Validation Duration
audio_ingest_checksum_duration_seconds = Summary(
    'audio_ingest_checksum_duration_seconds',
    'Time spent validating checksums (tar.gz + internal)'
)

# Failures by reason
audio_ingest_failures_total = Counter(
    'audio_ingest_failures_total',
    'Total number of ingestion failures',
    ['reason']  # validation_error, checksum_mismatch, processing_failure, etc.
)

# Success counter
audio_ingest_success_total = Counter(
    'audio_ingest_success_total',
    'Total number of successful ingestions'
)

# Messages inflight (pending in Redis)
audio_ingest_messages_inflight = Gauge(
    'audio_ingest_messages_inflight',
    'Number of messages pending in Redis stream'
)

# Retries
audio_ingest_retries_total = Counter(
    'audio_ingest_retries_total',
    'Total number of retry attempts',
    ['retry_count']
)

# DLQ publishes
audio_ingest_dlq_published_total = Counter(
    'audio_ingest_dlq_published_total',
    'Total messages published to dead letter queue',
    ['error_code']
)

# Download size (for capacity planning)
audio_ingest_download_bytes = Histogram(
    'audio_ingest_download_bytes',
    'Size of downloaded tar.gz files in bytes',
    buckets=[1e6, 10e6, 50e6, 100e6, 200e6, 500e6]  # 1MB to 500MB
)

# Segment count (for analytics)
audio_ingest_segments_total = Histogram(
    'audio_ingest_segments_total',
    'Number of segments per conversation',
    buckets=[10, 50, 100, 200, 500, 1000, 2000]
)

# Participants count
audio_ingest_participants_total = Histogram(
    'audio_ingest_participants_total',
    'Number of participants per conversation',
    buckets=[1, 2, 3, 5, 10, 20]
)

# NLP processing mode (v1.0 vs v1.1)
audio_ingest_nlp_mode = Counter(
    'audio_ingest_nlp_mode_total',
    'Count of NLP processing modes used',
    ['mode']  # enriched (v1.1), legacy (v1.0), skipped
)

# Trace ID propagation
audio_ingest_trace_id_present = Counter(
    'audio_ingest_trace_id_present_total',
    'Messages with trace_id present vs missing',
    ['present']  # 'true' or 'false'
)


# ==============================================================================
# Metrics Helper Class
# ==============================================================================

class IngestionMetrics:
    """Helper class for recording ingestion metrics"""

    @staticmethod
    def record_ack_latency(seconds: float):
        """Record message ack latency"""
        audio_ingest_ack_latency_seconds.observe(seconds)

    @staticmethod
    def record_validation_duration(seconds: float):
        """Record schema validation duration"""
        audio_ingest_validation_duration_seconds.observe(seconds)

    @staticmethod
    def record_processing_duration(seconds: float):
        """Record total processing duration"""
        audio_ingest_processing_duration_seconds.observe(seconds)

    @staticmethod
    def record_checksum_duration(seconds: float):
        """Record checksum validation duration"""
        audio_ingest_checksum_duration_seconds.observe(seconds)

    @staticmethod
    def record_failure(reason: str):
        """
        Record ingestion failure

        Args:
            reason: Error code (e.g., 'validation_error', 'checksum_mismatch')
        """
        audio_ingest_failures_total.labels(reason=reason).inc()

    @staticmethod
    def record_success():
        """Record successful ingestion"""
        audio_ingest_success_total.inc()

    @staticmethod
    def update_messages_inflight(count: int):
        """Update inflight messages gauge"""
        audio_ingest_messages_inflight.set(count)

    @staticmethod
    def record_retry(retry_count: int):
        """
        Record retry attempt

        Args:
            retry_count: Current retry count (0, 1, 2, 3, ...)
        """
        audio_ingest_retries_total.labels(retry_count=str(retry_count)).inc()

    @staticmethod
    def record_dlq_publish(error_code: str):
        """Record DLQ publish"""
        audio_ingest_dlq_published_total.labels(error_code=error_code).inc()

    @staticmethod
    def record_download_size(size_bytes: int):
        """Record tar.gz download size"""
        audio_ingest_download_bytes.observe(size_bytes)

    @staticmethod
    def record_conversation_metrics(num_segments: int, num_participants: int):
        """
        Record conversation-level metrics

        Args:
            num_segments: Number of segments in conversation
            num_participants: Number of participants
        """
        audio_ingest_segments_total.observe(num_segments)
        audio_ingest_participants_total.observe(num_participants)

    @staticmethod
    def record_nlp_mode(mode: str):
        """
        Record NLP processing mode used

        Args:
            mode: 'enriched' (v1.1), 'legacy' (v1.0), or 'skipped'
        """
        audio_ingest_nlp_mode.labels(mode=mode).inc()

    @staticmethod
    def record_trace_id_presence(present: bool):
        """Record whether trace_id was present in message"""
        audio_ingest_trace_id_present.labels(present=str(present).lower()).inc()

    @staticmethod
    @contextmanager
    def time_validation():
        """Context manager for timing validation"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            IngestionMetrics.record_validation_duration(duration)

    @staticmethod
    @contextmanager
    def time_checksum_validation():
        """Context manager for timing checksum validation"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            IngestionMetrics.record_checksum_duration(duration)

    @staticmethod
    @contextmanager
    def time_processing():
        """Context manager for timing entire processing"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            IngestionMetrics.record_processing_duration(duration)


# ==============================================================================
# Prometheus Exporter Setup
# ==============================================================================

def start_metrics_server(port: int = 9090):
    """
    Start Prometheus metrics HTTP server

    Args:
        port: HTTP port to expose metrics (default: 9090)

    Note:
        Metrics will be available at http://localhost:9090/metrics
    """
    from prometheus_client import start_http_server

    try:
        start_http_server(port)
        logger.info(f"Prometheus metrics server started on port {port}")
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
    except Exception as e:
        logger.error(f"Failed to start Prometheus metrics server: {e}")
        raise


# ==============================================================================
# Alert Thresholds (for reference - actual alerts in prometheus/alerts.yml)
# ==============================================================================

SLA_THRESHOLDS = {
    "ack_latency_warning_p95": 3.0,  # seconds
    "ack_latency_critical_p95": 5.0,  # seconds
    "validation_failure_rate_threshold": 0.05,  # 5%
    "messages_inflight_warning": 500,
    "messages_inflight_critical": 1000,
}


def log_sla_warning(metric_name: str, current_value: float, threshold: float):
    """
    Log SLA threshold warning

    Args:
        metric_name: Name of metric
        current_value: Current value
        threshold: Threshold value
    """
    logger.warning(
        f"SLA threshold exceeded: {metric_name}={current_value:.2f} "
        f"(threshold={threshold:.2f})"
    )
