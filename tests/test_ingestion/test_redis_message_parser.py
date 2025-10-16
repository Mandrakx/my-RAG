"""
Tests for redis_message_parser module

Tests Redis message parsing, validation, and URI parsing
conforming to ADR-2025-10-03-003 contract
"""

import pytest
from datetime import datetime
from src.ingestion.redis_message_parser import (
    RedisMessageParser,
    AudioIngestionMessage,
    ProducerInfo,
    RedisMessageMetadata
)
from pydantic import ValidationError
from jsonschema import ValidationError as JSONSchemaError


class TestRedisMessageParser:
    """Test suite for RedisMessageParser"""

    def test_parse_valid_message(self):
        """Test parsing a valid Redis message with all fields"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/drop/2025/10/16/rec-20251016T123000Z-abc12345.tar.gz',
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.1',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z',
            b'priority': b'normal',
            b'producer': b'{"service": "audio-pipeline", "instance": "worker-1"}',
            b'metadata': b'{"trace_id": "550e8400-e29b-41d4-a716-446655440000"}'
        }

        message = RedisMessageParser.parse(message_data)

        assert message.external_event_id == 'rec-20251016T123000Z-abc12345'
        assert message.checksum == 'sha256:' + 'a' * 64
        assert message.schema_version == '1.1'
        assert message.retry_count == 0
        assert message.priority == 'normal'
        assert message.producer.service == 'audio-pipeline'
        assert message.producer.instance == 'worker-1'
        assert message.get_trace_id() == '550e8400-e29b-41d4-a716-446655440000'

    def test_parse_minimal_message(self):
        """Test parsing a message with only required fields"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/drop/2025/10/16/file.tar.gz',
            b'checksum': b'sha256:' + b'f' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        message = RedisMessageParser.parse(message_data)

        assert message.external_event_id == 'rec-20251016T123000Z-abc12345'
        assert message.get_trace_id() is None
        assert message.priority == 'normal'  # Default

    def test_parse_package_uri(self):
        """Test parsing package_uri into bucket and object_key"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/drop/2025/10/16/rec-20251016T123000Z-abc12345.tar.gz',
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.1',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        message = RedisMessageParser.parse(message_data)
        bucket, object_key = message.parse_package_uri()

        assert bucket == 'ingestion'
        assert object_key == 'drop/2025/10/16/rec-20251016T123000Z-abc12345.tar.gz'

    def test_get_checksum_hash(self):
        """Test extracting hash from checksum (remove sha256: prefix)"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/file.tar.gz',
            b'checksum': b'sha256:abc123def456',
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        message = RedisMessageParser.parse(message_data)
        hash_value = message.get_checksum_hash()

        assert hash_value == 'abc123def456'

    def test_invalid_checksum_format(self):
        """Test that invalid checksum format raises error"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/file.tar.gz',
            b'checksum': b'invalid-checksum',  # Missing sha256: prefix
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        with pytest.raises((ValidationError, JSONSchemaError)):
            RedisMessageParser.parse(message_data)

    def test_invalid_package_uri_no_bucket(self):
        """Test that package_uri without bucket raises error"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio:///file.tar.gz',  # No bucket
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        with pytest.raises(ValidationError):
            RedisMessageParser.parse(message_data)

    def test_invalid_package_uri_no_path(self):
        """Test that package_uri without path raises error"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion',  # No path
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        with pytest.raises(ValidationError):
            RedisMessageParser.parse(message_data)

    def test_missing_required_field(self):
        """Test that missing required field raises error"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            # Missing package_uri
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        with pytest.raises((ValidationError, JSONSchemaError)):
            RedisMessageParser.parse(message_data)

    def test_retry_count_validation(self):
        """Test retry_count validation"""
        # Valid retry_count
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/file.tar.gz',
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'3',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        message = RedisMessageParser.parse(message_data)
        assert message.retry_count == 3

        # Invalid retry_count (too high)
        message_data[b'retry_count'] = b'99'
        with pytest.raises(ValidationError):
            RedisMessageParser.parse(message_data)

    def test_is_high_priority(self):
        """Test priority checking"""
        # Normal priority
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/file.tar.gz',
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'0',
            b'produced_at': b'2025-10-16T12:30:00Z',
            b'priority': b'normal'
        }

        message = RedisMessageParser.parse(message_data)
        assert not RedisMessageParser.is_high_priority(message)

        # High priority
        message_data[b'priority'] = b'high'
        message = RedisMessageParser.parse(message_data)
        assert RedisMessageParser.is_high_priority(message)

    def test_should_retry(self):
        """Test retry logic"""
        message_data = {
            b'external_event_id': b'rec-20251016T123000Z-abc12345',
            b'package_uri': b'minio://ingestion/file.tar.gz',
            b'checksum': b'sha256:' + b'a' * 64,
            b'schema_version': b'1.0',
            b'retry_count': b'2',
            b'produced_at': b'2025-10-16T12:30:00Z'
        }

        message = RedisMessageParser.parse(message_data)
        assert RedisMessageParser.should_retry(message, max_retries=3)

        # At max retries
        message_data[b'retry_count'] = b'3'
        message = RedisMessageParser.parse(message_data)
        assert not RedisMessageParser.should_retry(message, max_retries=3)


class TestAudioIngestionMessage:
    """Test AudioIngestionMessage model"""

    def test_model_creation(self):
        """Test creating AudioIngestionMessage directly"""
        message = AudioIngestionMessage(
            external_event_id='rec-20251016T123000Z-abc12345',
            package_uri='minio://ingestion/drop/file.tar.gz',
            checksum='sha256:' + 'a' * 64,
            schema_version='1.1',
            retry_count=0,
            produced_at=datetime.utcnow()
        )

        assert message.external_event_id == 'rec-20251016T123000Z-abc12345'
        assert message.retry_count == 0

    def test_invalid_schema_version(self):
        """Test that invalid schema_version format raises error"""
        with pytest.raises(ValidationError):
            AudioIngestionMessage(
                external_event_id='rec-20251016T123000Z-abc12345',
                package_uri='minio://ingestion/file.tar.gz',
                checksum='sha256:' + 'a' * 64,
                schema_version='1',  # Invalid format (missing .minor)
                retry_count=0,
                produced_at=datetime.utcnow()
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
