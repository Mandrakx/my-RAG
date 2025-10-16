"""
Error Handler with Dead Letter Queue for Audio Ingestion

Handles error routing, standardized error codes, and DLQ publishing
Aligned with ADR-2025-10-03-003 cross-cutting contract
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """
    Standardized error codes for cross-team error handling

    Aligned with docs/design/cross-cutting-concern.md error catalogue
    """
    # Validation errors (4xx)
    VALIDATION_ERROR = "validation_error"
    INVALID_AUDIO_FORMAT = "invalid_audio_format"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_SCHEMA_VERSION = "invalid_schema_version"

    # Checksum errors (4xx)
    CHECKSUM_MISMATCH = "checksum_mismatch"
    CHECKSUM_FORMAT_INVALID = "checksum_format_invalid"

    # Duplicate/Conflict errors (4xx)
    DUPLICATE_EVENT = "duplicate_event"

    # Downstream errors (5xx)
    PROCESSING_FAILURE = "processing_failure"
    INGESTION_TIMEOUT = "ingestion_timeout"
    STORAGE_ERROR = "storage_error"
    DATABASE_ERROR = "database_error"

    # Infrastructure errors (5xx)
    MINIO_DOWNLOAD_FAILED = "minio_download_failed"
    REDIS_PUBLISH_FAILED = "redis_publish_failed"
    QDRANT_ERROR = "qdrant_error"

    # Expiration (4xx)
    PAYLOAD_EXPIRED = "payload_expired"

    # Unknown
    INTERNAL_SERVER_ERROR = "internal_server_error"


class RemediationHint(str, Enum):
    """Remediation hints for common error scenarios"""
    FIX_PAYLOAD_REPUBLISH = "Fix payload schema/format and republish within 24h"
    REBUILD_ARCHIVE = "Rebuild archive with correct checksums and republish"
    CHECK_DUPLICATE = "Investigate duplication; resend only if new transcript"
    RETRY_AUTOMATIC = "Automatic retry will occur; no action needed"
    CHECK_INFRASTRUCTURE = "Platform team investigating infrastructure issue"
    PRODUCE_FRESH_DROP = "Archive older than 72h; produce fresh drop if still required"
    ROTATE_CREDENTIALS = "Rotate MinIO/Redis credentials; confirm least-privilege policy"
    CONTACT_SUPPORT = "Contact platform team with trace_id for investigation"


class ErrorContext:
    """Context information for error handling"""

    def __init__(
        self,
        external_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        job_id: Optional[str] = None,
        package_uri: Optional[str] = None,
        retry_count: int = 0
    ):
        self.external_event_id = external_event_id
        self.trace_id = trace_id
        self.job_id = job_id
        self.package_uri = package_uri
        self.retry_count = retry_count
        self.timestamp = datetime.utcnow()


class ErrorHandler:
    """Handler for errors with DLQ routing"""

    def __init__(self, redis_client, dlq_stream: str):
        """
        Initialize error handler

        Args:
            redis_client: Redis client for DLQ publishing
            dlq_stream: DLQ stream name (e.g., "audio.ingestion.deadletter")
        """
        self.redis = redis_client
        self.dlq_stream = dlq_stream

    def get_remediation_hint(self, error_code: ErrorCode) -> str:
        """
        Get remediation hint for error code

        Args:
            error_code: Standardized error code

        Returns:
            Human-readable remediation hint
        """
        remediation_map = {
            ErrorCode.VALIDATION_ERROR: RemediationHint.FIX_PAYLOAD_REPUBLISH,
            ErrorCode.INVALID_AUDIO_FORMAT: RemediationHint.FIX_PAYLOAD_REPUBLISH,
            ErrorCode.MISSING_REQUIRED_FIELD: RemediationHint.FIX_PAYLOAD_REPUBLISH,
            ErrorCode.INVALID_SCHEMA_VERSION: RemediationHint.FIX_PAYLOAD_REPUBLISH,
            ErrorCode.CHECKSUM_MISMATCH: RemediationHint.REBUILD_ARCHIVE,
            ErrorCode.CHECKSUM_FORMAT_INVALID: RemediationHint.REBUILD_ARCHIVE,
            ErrorCode.DUPLICATE_EVENT: RemediationHint.CHECK_DUPLICATE,
            ErrorCode.PROCESSING_FAILURE: RemediationHint.RETRY_AUTOMATIC,
            ErrorCode.INGESTION_TIMEOUT: RemediationHint.RETRY_AUTOMATIC,
            ErrorCode.STORAGE_ERROR: RemediationHint.CHECK_INFRASTRUCTURE,
            ErrorCode.DATABASE_ERROR: RemediationHint.CHECK_INFRASTRUCTURE,
            ErrorCode.MINIO_DOWNLOAD_FAILED: RemediationHint.CHECK_INFRASTRUCTURE,
            ErrorCode.REDIS_PUBLISH_FAILED: RemediationHint.CHECK_INFRASTRUCTURE,
            ErrorCode.QDRANT_ERROR: RemediationHint.CHECK_INFRASTRUCTURE,
            ErrorCode.PAYLOAD_EXPIRED: RemediationHint.PRODUCE_FRESH_DROP,
            ErrorCode.INTERNAL_SERVER_ERROR: RemediationHint.CONTACT_SUPPORT,
        }

        return remediation_map.get(error_code, RemediationHint.CONTACT_SUPPORT).value

    def is_retryable(self, error_code: ErrorCode) -> bool:
        """
        Determine if error is retryable

        Args:
            error_code: Standardized error code

        Returns:
            True if error should trigger retry
        """
        retryable_errors = {
            ErrorCode.PROCESSING_FAILURE,
            ErrorCode.INGESTION_TIMEOUT,
            ErrorCode.STORAGE_ERROR,
            ErrorCode.DATABASE_ERROR,
            ErrorCode.MINIO_DOWNLOAD_FAILED,
            ErrorCode.REDIS_PUBLISH_FAILED,
            ErrorCode.QDRANT_ERROR,
            ErrorCode.CHECKSUM_MISMATCH,  # Retry once in case of transient corruption
        }

        return error_code in retryable_errors

    def classify_exception(self, exception: Exception) -> ErrorCode:
        """
        Classify exception to standardized error code

        Args:
            exception: Python exception

        Returns:
            Standardized ErrorCode
        """
        exception_str = str(exception).lower()
        exception_type = type(exception).__name__

        # Validation errors
        if 'validation' in exception_str or exception_type == 'ValidationError':
            return ErrorCode.VALIDATION_ERROR

        # Checksum errors
        if 'checksum' in exception_str:
            if 'mismatch' in exception_str:
                return ErrorCode.CHECKSUM_MISMATCH
            return ErrorCode.CHECKSUM_FORMAT_INVALID

        # Duplicate errors
        if 'duplicate' in exception_str or 'already exists' in exception_str:
            return ErrorCode.DUPLICATE_EVENT

        # Storage errors
        if 'minio' in exception_str or 's3' in exception_str:
            return ErrorCode.MINIO_DOWNLOAD_FAILED

        # Database errors
        if 'database' in exception_str or exception_type in ['IntegrityError', 'OperationalError']:
            return ErrorCode.DATABASE_ERROR

        # Qdrant errors
        if 'qdrant' in exception_str:
            return ErrorCode.QDRANT_ERROR

        # Timeout errors
        if 'timeout' in exception_str or exception_type == 'TimeoutError':
            return ErrorCode.INGESTION_TIMEOUT

        # Default
        return ErrorCode.PROCESSING_FAILURE

    def publish_to_dlq(
        self,
        original_message: Dict[str, Any],
        error_code: ErrorCode,
        error_message: str,
        error_stack: Optional[str] = None,
        context: Optional[ErrorContext] = None
    ) -> bool:
        """
        Publish failed message to Dead Letter Queue

        Args:
            original_message: Original Redis message that failed
            error_code: Standardized error code
            error_message: Human-readable error message
            error_stack: Full stack trace (optional)
            context: Error context (external_event_id, trace_id, etc.)

        Returns:
            True if successfully published to DLQ
        """
        try:
            remediation_hint = self.get_remediation_hint(error_code)

            dlq_payload = {
                # Original message (for replay)
                "original_message": original_message,

                # Error details
                "error": {
                    "code": error_code.value,
                    "message": error_message,
                    "stack_trace": error_stack,
                    "timestamp": datetime.utcnow().isoformat(),
                },

                # Remediation
                "remediation": {
                    "hint": remediation_hint,
                    "retryable": self.is_retryable(error_code),
                },

                # Context for debugging
                "context": {
                    "external_event_id": context.external_event_id if context else None,
                    "trace_id": context.trace_id if context else None,
                    "job_id": context.job_id if context else None,
                    "package_uri": context.package_uri if context else None,
                    "retry_count": context.retry_count if context else 0,
                },

                # Metadata
                "dlq_metadata": {
                    "stream": self.dlq_stream,
                    "published_at": datetime.utcnow().isoformat(),
                    "source": "my-rag-ingestion",
                },
            }

            # Publish to DLQ stream
            self.redis.xadd(
                self.dlq_stream,
                {
                    "payload": json.dumps(dlq_payload),
                    "error_code": error_code.value,
                    "external_event_id": context.external_event_id if context else "unknown",
                    "trace_id": context.trace_id if context else "unknown",
                }
            )

            logger.warning(
                f"Published to DLQ: {error_code.value} - "
                f"event_id={context.external_event_id if context else 'unknown'}, "
                f"trace_id={context.trace_id if context else 'unknown'}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to publish to DLQ: {e}")
            logger.error(traceback.format_exc())
            return False

    def handle_error(
        self,
        exception: Exception,
        original_message: Dict[str, Any],
        context: Optional[ErrorContext] = None
    ) -> ErrorCode:
        """
        Handle error: classify, log, and publish to DLQ

        Args:
            exception: Exception that occurred
            original_message: Original Redis message
            context: Error context

        Returns:
            Classified ErrorCode
        """
        # Classify exception
        error_code = self.classify_exception(exception)
        error_message = str(exception)
        error_stack = traceback.format_exc()

        # Log error with context
        log_msg = f"Error processing message: {error_code.value} - {error_message}"
        if context and context.trace_id:
            log_msg = f"[trace_id={context.trace_id}] {log_msg}"

        logger.error(log_msg)
        logger.debug(f"Stack trace:\n{error_stack}")

        # Publish to DLQ
        self.publish_to_dlq(
            original_message=original_message,
            error_code=error_code,
            error_message=error_message,
            error_stack=error_stack,
            context=context
        )

        return error_code
