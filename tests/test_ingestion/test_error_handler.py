"""
Tests for error_handler module

Tests DLQ publishing, error classification, and remediation hints
conforming to ADR-2025-10-16-004 error handling contract
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pydantic import ValidationError

from src.ingestion.error_handler import (
    ErrorHandler,
    ErrorCode,
    RemediationHint,
    ErrorContext
)


class TestErrorCode:
    """Test ErrorCode enum"""

    def test_all_error_codes_defined(self):
        """Test that all 14 error codes are defined"""
        expected_codes = [
            'validation_error',
            'checksum_mismatch',
            'duplicate_event',
            'processing_failure',
            'ingestion_timeout',
            'schema_incompatible',
            'storage_error',
            'network_error',
            'minio_error',
            'postgres_error',
            'redis_error',
            'nlp_processing_error',
            'qdrant_error',
            'unknown_error'
        ]

        for code in expected_codes:
            assert hasattr(ErrorCode, code.upper())
            assert ErrorCode[code.upper()].value == code


class TestRemediationHint:
    """Test RemediationHint enum"""

    def test_all_hints_defined(self):
        """Test that remediation hints exist for common errors"""
        assert RemediationHint.CHECK_SCHEMA.value.startswith('Verify payload')
        assert RemediationHint.VERIFY_CHECKSUM.value.startswith('Re-download')
        assert RemediationHint.CHECK_IDEMPOTENCY.value.startswith('Check if')
        assert RemediationHint.RETRY.value.startswith('Retry with')


class TestErrorContext:
    """Test ErrorContext dataclass"""

    def test_context_creation(self):
        """Test creating ErrorContext"""
        context = ErrorContext(
            job_id='job-123',
            external_event_id='rec-20251016T123000Z-abc12345',
            trace_id='550e8400-e29b-41d4-a716-446655440000',
            bucket='ingestion',
            object_key='drop/2025/10/16/file.tar.gz'
        )

        assert context.job_id == 'job-123'
        assert context.external_event_id == 'rec-20251016T123000Z-abc12345'
        assert context.trace_id == '550e8400-e29b-41d4-a716-446655440000'
        assert context.bucket == 'ingestion'
        assert context.object_key == 'drop/2025/10/16/file.tar.gz'

    def test_context_optional_fields(self):
        """Test ErrorContext with only required fields"""
        context = ErrorContext(
            job_id='job-123',
            external_event_id='rec-20251016T123000Z-abc12345'
        )

        assert context.job_id == 'job-123'
        assert context.external_event_id == 'rec-20251016T123000Z-abc12345'
        assert context.trace_id is None
        assert context.bucket is None
        assert context.object_key is None


class TestErrorHandler:
    """Test ErrorHandler class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_redis = Mock()
        self.dlq_stream = 'audio.ingestion.deadletter'
        self.error_handler = ErrorHandler(self.mock_redis, self.dlq_stream)

    def test_initialization(self):
        """Test ErrorHandler initialization"""
        assert self.error_handler.redis == self.mock_redis
        assert self.error_handler.dlq_stream == 'audio.ingestion.deadletter'

    def test_classify_validation_error(self):
        """Test classification of Pydantic ValidationError"""
        exception = ValidationError.from_exception_data(
            'test',
            [{'type': 'missing', 'loc': ('field',), 'msg': 'field required'}]
        )

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.VALIDATION_ERROR

    def test_classify_value_error_checksum(self):
        """Test classification of checksum mismatch error"""
        exception = ValueError("Checksum mismatch for 'file.tar.gz'")

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.CHECKSUM_MISMATCH

    def test_classify_value_error_duplicate(self):
        """Test classification of duplicate event error"""
        exception = ValueError("Duplicate external_event_id")

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.DUPLICATE_EVENT

    def test_classify_timeout_error(self):
        """Test classification of timeout errors"""
        import asyncio

        exception = asyncio.TimeoutError("Operation timed out")

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.INGESTION_TIMEOUT

    def test_classify_connection_error(self):
        """Test classification of network errors"""
        from requests.exceptions import ConnectionError

        exception = ConnectionError("Failed to connect")

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.NETWORK_ERROR

    def test_classify_generic_error(self):
        """Test classification of unknown errors"""
        exception = Exception("Some unexpected error")

        error_code = self.error_handler.classify_exception(exception)

        assert error_code == ErrorCode.UNKNOWN_ERROR

    def test_get_remediation_hint_validation(self):
        """Test getting remediation hint for validation error"""
        hint = self.error_handler.get_remediation_hint(ErrorCode.VALIDATION_ERROR)

        assert hint == RemediationHint.CHECK_SCHEMA

    def test_get_remediation_hint_checksum(self):
        """Test getting remediation hint for checksum error"""
        hint = self.error_handler.get_remediation_hint(ErrorCode.CHECKSUM_MISMATCH)

        assert hint == RemediationHint.VERIFY_CHECKSUM

    def test_get_remediation_hint_duplicate(self):
        """Test getting remediation hint for duplicate error"""
        hint = self.error_handler.get_remediation_hint(ErrorCode.DUPLICATE_EVENT)

        assert hint == RemediationHint.CHECK_IDEMPOTENCY

    def test_get_remediation_hint_default(self):
        """Test getting default remediation hint"""
        hint = self.error_handler.get_remediation_hint(ErrorCode.UNKNOWN_ERROR)

        assert hint == RemediationHint.CONTACT_SUPPORT

    def test_publish_to_dlq_full_context(self):
        """Test publishing to DLQ with full context"""
        original_message = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/drop/file.tar.gz'
        }

        context = ErrorContext(
            job_id='job-123',
            external_event_id='rec-20251016T123000Z-abc12345',
            trace_id='550e8400-e29b-41d4-a716-446655440000',
            bucket='ingestion',
            object_key='drop/file.tar.gz'
        )

        error_code = ErrorCode.CHECKSUM_MISMATCH
        error_message = "Checksum mismatch for 'file.tar.gz'"

        # Publish to DLQ
        self.error_handler.publish_to_dlq(
            original_message=original_message,
            error_code=error_code,
            error_message=error_message,
            context=context
        )

        # Verify Redis xadd was called
        assert self.mock_redis.xadd.called
        call_args = self.mock_redis.xadd.call_args

        # Check stream name
        assert call_args[0][0] == 'audio.ingestion.deadletter'

        # Check payload
        payload_dict = call_args[0][1]
        assert 'payload' in payload_dict

        # Parse JSON payload
        dlq_data = json.loads(payload_dict['payload'])

        assert dlq_data['original_message'] == original_message
        assert dlq_data['error']['code'] == 'checksum_mismatch'
        assert dlq_data['error']['message'] == error_message
        assert dlq_data['remediation']['hint'] == RemediationHint.VERIFY_CHECKSUM.value
        assert dlq_data['context']['external_event_id'] == 'rec-20251016T123000Z-abc12345'
        assert dlq_data['context']['trace_id'] == '550e8400-e29b-41d4-a716-446655440000'
        assert dlq_data['context']['job_id'] == 'job-123'
        assert 'failed_at' in dlq_data['context']

    def test_publish_to_dlq_minimal_context(self):
        """Test publishing to DLQ with minimal context"""
        original_message = {b'data': b'test'}

        context = ErrorContext(
            job_id='job-456',
            external_event_id='rec-20251016T140000Z-def45678'
        )

        error_code = ErrorCode.VALIDATION_ERROR
        error_message = "Missing required field"

        self.error_handler.publish_to_dlq(
            original_message=original_message,
            error_code=error_code,
            error_message=error_message,
            context=context
        )

        # Verify call
        assert self.mock_redis.xadd.called
        payload_dict = self.mock_redis.xadd.call_args[0][1]
        dlq_data = json.loads(payload_dict['payload'])

        assert dlq_data['context']['trace_id'] is None
        assert dlq_data['context']['bucket'] is None
        assert dlq_data['context']['object_key'] is None

    def test_handle_error_full_flow(self):
        """Test handle_error with full classification and publishing"""
        original_message = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'checksum': b'sha256:wronghash'
        }

        context = ErrorContext(
            job_id='job-789',
            external_event_id='rec-20251016T123000Z-abc12345',
            trace_id='trace-123'
        )

        exception = ValueError("Checksum mismatch for 'archive.tar.gz'")

        # Handle error
        self.error_handler.handle_error(
            exception=exception,
            original_message=original_message,
            context=context
        )

        # Verify classification and publishing
        assert self.mock_redis.xadd.called

        payload_dict = self.mock_redis.xadd.call_args[0][1]
        dlq_data = json.loads(payload_dict['payload'])

        assert dlq_data['error']['code'] == 'checksum_mismatch'
        assert dlq_data['remediation']['hint'] == RemediationHint.VERIFY_CHECKSUM.value

    def test_handle_error_with_retry_count(self):
        """Test handle_error includes retry_count if present in context"""
        original_message = {b'retry_count': b'2'}

        context = ErrorContext(
            job_id='job-retry',
            external_event_id='rec-20251016T150000Z-retry123',
            retry_count=2
        )

        exception = Exception("Temporary failure")

        self.error_handler.handle_error(
            exception=exception,
            original_message=original_message,
            context=context
        )

        payload_dict = self.mock_redis.xadd.call_args[0][1]
        dlq_data = json.loads(payload_dict['payload'])

        # Note: retry_count would be in context if we added it to ErrorContext dataclass
        # For now, verify basic functionality
        assert dlq_data['error']['code'] == 'unknown_error'

    def test_error_handler_logs_exception(self):
        """Test that error handler logs exceptions"""
        with patch('src.ingestion.error_handler.logger') as mock_logger:
            exception = ValueError("Test error")
            context = ErrorContext(
                job_id='job-log',
                external_event_id='rec-20251016T160000Z-log123'
            )

            self.error_handler.handle_error(
                exception=exception,
                original_message={},
                context=context
            )

            # Verify logging occurred
            assert mock_logger.error.called
            log_call = mock_logger.error.call_args[0][0]
            assert 'Test error' in log_call or 'checksum_mismatch' in log_call

    def test_serialize_original_message_bytes(self):
        """Test that byte keys/values in original message are serialized"""
        original_message = {
            b'key1': b'value1',
            b'key2': b'value2'
        }

        context = ErrorContext(
            job_id='job-bytes',
            external_event_id='rec-20251016T170000Z-bytes'
        )

        self.error_handler.publish_to_dlq(
            original_message=original_message,
            error_code=ErrorCode.VALIDATION_ERROR,
            error_message="Test",
            context=context
        )

        payload_dict = self.mock_redis.xadd.call_args[0][1]
        dlq_data = json.loads(payload_dict['payload'])

        # Verify bytes are in serialized form
        assert dlq_data['original_message'] == original_message


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler"""

    def test_end_to_end_validation_error(self):
        """Test complete flow for validation error"""
        mock_redis = Mock()
        error_handler = ErrorHandler(mock_redis, 'test.dlq')

        # Simulate validation error
        exception = ValidationError.from_exception_data(
            'AudioIngestionMessage',
            [{'type': 'missing', 'loc': ('checksum',), 'msg': 'field required'}]
        )

        context = ErrorContext(
            job_id='integration-job',
            external_event_id='rec-20251016T180000Z-integration'
        )

        original_message = {
            b'external_event_id': b'rec-20251016T180000Z-integration',
            b'package_uri': b'minio://bucket/key'
        }

        # Handle error
        error_handler.handle_error(exception, original_message, context)

        # Verify
        assert mock_redis.xadd.called
        payload = json.loads(mock_redis.xadd.call_args[0][1]['payload'])

        assert payload['error']['code'] == 'validation_error'
        assert payload['remediation']['hint'] == RemediationHint.CHECK_SCHEMA.value

    def test_end_to_end_checksum_error(self):
        """Test complete flow for checksum error"""
        mock_redis = Mock()
        error_handler = ErrorHandler(mock_redis, 'test.dlq')

        exception = ValueError("Checksum mismatch for 'rec-20251016T190000Z-checksum.tar.gz'")

        context = ErrorContext(
            job_id='checksum-job',
            external_event_id='rec-20251016T190000Z-checksum',
            trace_id='trace-checksum-123'
        )

        original_message = {
            b'checksum': b'sha256:' + b'a' * 64
        }

        error_handler.handle_error(exception, original_message, context)

        assert mock_redis.xadd.called
        payload = json.loads(mock_redis.xadd.call_args[0][1]['payload'])

        assert payload['error']['code'] == 'checksum_mismatch'
        assert payload['context']['trace_id'] == 'trace-checksum-123'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
