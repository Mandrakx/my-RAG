"""
Tests for JSON schema validations
"""

import pytest
from jsonschema import ValidationError
from src.ingestion.schemas import SchemaValidator


def test_validate_transcript_metadata():
    """Test transcript metadata validation"""

    valid_metadata = {
        "job_id": "test-123",
        "timestamp": "2025-10-10T10:00:00Z",
        "audio_filename": "test.m4a",
        "duration_seconds": 120.5,
        "language": "fr"
    }

    assert SchemaValidator.validate_metadata(valid_metadata) is True


def test_validate_transcript_metadata_invalid():
    """Test invalid transcript metadata"""

    invalid_metadata = {
        # Missing required job_id
        "timestamp": "2025-10-10T10:00:00Z"
    }

    with pytest.raises(ValidationError):
        SchemaValidator.validate_metadata(invalid_metadata)


def test_validate_transcript_document():
    """Test complete transcript document validation"""

    valid_transcript = {
        "metadata": {
            "job_id": "test-123",
            "timestamp": "2025-10-10T10:00:00Z"
        },
        "segments": [
            {
                "speaker": "John",
                "text": "Hello world",
                "start_time": 0.0,
                "confidence": 0.95
            }
        ]
    }

    assert SchemaValidator.validate_transcript(valid_transcript) is True


def test_validate_transcript_document_with_turns():
    """Test transcript with turns instead of segments"""

    valid_transcript = {
        "metadata": {
            "job_id": "test-456",
            "timestamp": "2025-10-10T10:00:00Z"
        },
        "turns": [
            {
                "speaker": "Alice",
                "text": "Bonjour"
            }
        ]
    }

    assert SchemaValidator.validate_transcript(valid_transcript) is True


def test_validate_normalized_conversation():
    """Test normalized conversation validation"""

    valid_conversation = {
        "metadata": {
            "job_id": "test-123",
            "date": "2025-10-10T10:00:00Z",
            "duration_seconds": 120,
            "language": "fr",
            "source": "transcript-service"
        },
        "turns": [
            {
                "turn": 0,
                "speaker": "John",
                "text": "Hello",
                "timestamp_ms": None,
                "confidence": None
            }
        ],
        "participants": [
            {
                "speaker": "John",
                "role": "participant",
                "turn_count": 1
            }
        ],
        "statistics": {
            "total_turns": 1,
            "total_speakers": 1,
            "avg_confidence": None
        }
    }

    assert SchemaValidator.validate_normalized_conversation(valid_conversation) is True


def test_validate_normalized_conversation_invalid():
    """Test invalid normalized conversation"""

    invalid_conversation = {
        "metadata": {
            "job_id": "test-123",
            "date": "2025-10-10T10:00:00Z"
        },
        # Missing required turns
        "participants": []
    }

    with pytest.raises(ValidationError):
        SchemaValidator.validate_normalized_conversation(invalid_conversation)


def test_validate_redis_event():
    """Test Redis event message validation"""

    valid_event = {
        "job_id": "test-123",
        "bucket": "ingestion",
        "object_key": "test/file.json",
        "event_type": "put",
        "timestamp": "2025-10-10T10:00:00Z"
    }

    assert SchemaValidator.validate_redis_event(valid_event) is True


def test_validate_redis_event_invalid_type():
    """Test Redis event with invalid event type"""

    invalid_event = {
        "job_id": "test-123",
        "bucket": "ingestion",
        "object_key": "test/file.json",
        "event_type": "invalid_type"  # Not in enum
    }

    with pytest.raises(ValidationError):
        SchemaValidator.validate_redis_event(invalid_event)


def test_validate_turn_confidence_range():
    """Test turn confidence must be between 0 and 1"""

    # Valid confidence
    valid_turn = {
        "turn": 0,
        "speaker": "John",
        "text": "Hello",
        "timestamp_ms": None,
        "confidence": 0.85
    }

    from jsonschema import validate
    from src.ingestion.schemas import CONVERSATION_TURN_SCHEMA

    validate(instance=valid_turn, schema=CONVERSATION_TURN_SCHEMA)

    # Invalid confidence > 1
    invalid_turn = {
        "turn": 0,
        "speaker": "John",
        "text": "Hello",
        "timestamp_ms": None,
        "confidence": 1.5
    }

    with pytest.raises(ValidationError):
        validate(instance=invalid_turn, schema=CONVERSATION_TURN_SCHEMA)
