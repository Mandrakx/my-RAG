"""
JSON Schema validations for ingestion pipeline

Supports both legacy (v1.0) and enriched (v1.1+) transcript formats.
v1.1 adds optional NLP annotations (sentiment, entities) from upstream services.
"""

import json
from typing import Dict, Any, Optional, List
from jsonschema import validate, ValidationError
import logging

logger = logging.getLogger(__name__)

# Schema for NLP annotations (v1.1+) - Defined first since used by TRANSCRIPT_SEGMENT_SCHEMA
NLP_SENTIMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "description": "Sentiment analysis annotation (optional, from transcript service)",
    "required": ["label", "score"],
    "properties": {
        "label": {
            "type": "string",
            "enum": ["very_positive", "positive", "neutral", "negative", "very_negative", "mixed"]
        },
        "score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "stars": {
            "type": "integer",
            "minimum": 1,
            "maximum": 5
        },
        "metadata": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "version": {"type": "string"}
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}

NLP_ENTITY_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "description": "Named entity extracted via NER (optional, from transcript service)",
    "required": ["type", "text"],
    "properties": {
        "type": {
            "type": "string",
            "enum": ["PERSON", "ORG", "LOC", "DATE", "TIME", "MONEY", "MISC"]
        },
        "text": {
            "type": "string",
            "minLength": 1
        },
        "start_char": {
            "type": "integer",
            "minimum": 0
        },
        "end_char": {
            "type": "integer",
            "minimum": 0
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "metadata": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "normalized_form": {"type": "string"}
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}

NLP_ANNOTATIONS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "description": "Optional NLP annotations from transcript service (v1.1+)",
    "properties": {
        "sentiment": NLP_SENTIMENT_SCHEMA,
        "entities": {
            "type": "array",
            "items": NLP_ENTITY_SCHEMA
        }
    },
    "additionalProperties": True
}

# Schema for transcript metadata
TRANSCRIPT_METADATA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["job_id", "timestamp"],
    "properties": {
        "job_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9-_]+$",
            "minLength": 1,
            "maxLength": 128
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "audio_filename": {
            "type": "string",
            "minLength": 1
        },
        "duration_seconds": {
            "type": "number",
            "minimum": 0
        },
        "language": {
            "type": "string",
            "enum": ["fr", "en", "es", "de", "it", "pt"]
        },
        "model_version": {
            "type": "string"
        },
        "source": {
            "type": "string",
            "default": "transcript-service"
        }
    },
    "additionalProperties": True
}

# Schema for transcript segment/turn
TRANSCRIPT_SEGMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["speaker", "text"],
    "properties": {
        "speaker": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "text": {
            "type": "string",
            "minLength": 1
        },
        "start_time": {
            "type": "number",
            "minimum": 0
        },
        "end_time": {
            "type": "number",
            "minimum": 0
        },
        "timestamp_ms": {
            "type": "integer",
            "minimum": 0
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "annotations": NLP_ANNOTATIONS_SCHEMA
    },
    "additionalProperties": True
}

# Schema for complete transcript document
TRANSCRIPT_DOCUMENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["metadata"],
    "properties": {
        "metadata": TRANSCRIPT_METADATA_SCHEMA,
        "segments": {
            "type": "array",
            "items": TRANSCRIPT_SEGMENT_SCHEMA,
            "minItems": 1
        },
        "turns": {
            "type": "array",
            "items": TRANSCRIPT_SEGMENT_SCHEMA,
            "minItems": 1
        },
        "transcript": {
            "type": "string",
            "minLength": 1
        }
    },
    "oneOf": [
        {"required": ["segments"]},
        {"required": ["turns"]},
        {"required": ["transcript"]}
    ],
    "additionalProperties": True
}

# Schema for normalized conversation turn
CONVERSATION_TURN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["turn", "speaker", "text"],
    "properties": {
        "turn": {
            "type": "integer",
            "minimum": 0
        },
        "speaker": {
            "type": "string",
            "minLength": 1
        },
        "text": {
            "type": "string",
            "minLength": 1
        },
        "timestamp_ms": {
            "type": ["integer", "null"],
            "minimum": 0
        },
        "confidence": {
            "type": ["number", "null"],
            "minimum": 0.0,
            "maximum": 1.0
        }
    },
    "additionalProperties": False
}

# Schema for normalized conversation
NORMALIZED_CONVERSATION_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["metadata", "turns", "participants"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["job_id", "date"],
            "properties": {
                "job_id": {"type": "string"},
                "date": {"type": "string", "format": "date-time"},
                "duration_seconds": {"type": ["number", "null"]},
                "language": {"type": "string"},
                "source": {"type": "string"},
                "model_version": {"type": ["string", "null"]},
                "audio_filename": {"type": ["string", "null"]}
            }
        },
        "turns": {
            "type": "array",
            "items": CONVERSATION_TURN_SCHEMA,
            "minItems": 1
        },
        "participants": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["speaker"],
                "properties": {
                    "speaker": {"type": "string"},
                    "role": {"type": "string"},
                    "turn_count": {"type": "integer", "minimum": 0}
                }
            }
        },
        "statistics": {
            "type": "object",
            "properties": {
                "total_turns": {"type": "integer", "minimum": 0},
                "total_speakers": {"type": "integer", "minimum": 0},
                "avg_confidence": {"type": ["number", "null"]}
            }
        }
    },
    "additionalProperties": False
}

# Schema for Redis event message
REDIS_EVENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["job_id", "bucket", "object_key"],
    "properties": {
        "job_id": {
            "type": "string",
            "minLength": 1
        },
        "bucket": {
            "type": "string",
            "minLength": 1
        },
        "object_key": {
            "type": "string",
            "minLength": 1
        },
        "event_type": {
            "type": "string",
            "enum": ["put", "delete", "copy"]
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "file_size": {
            "type": "integer",
            "minimum": 0
        },
        "content_type": {
            "type": "string"
        }
    },
    "additionalProperties": True
}


class SchemaValidator:
    """Validator for ingestion data schemas"""

    @staticmethod
    def has_nlp_annotations(data: Dict[str, Any]) -> bool:
        """
        Check if transcript data contains NLP annotations (v1.1+)

        Args:
            data: Transcript or segment data

        Returns:
            True if NLP annotations are present
        """
        # Check at segment level
        segments = data.get('segments', []) or data.get('turns', [])
        if segments:
            first_segment = segments[0]
            annotations = first_segment.get('annotations', {})
            return bool(annotations.get('sentiment') or annotations.get('entities'))

        return False

    @staticmethod
    def extract_sentiment_from_segment(segment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract sentiment annotation from a segment

        Returns:
            Sentiment dict or None if not present
        """
        return segment.get('annotations', {}).get('sentiment')

    @staticmethod
    def extract_entities_from_segment(segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract entity annotations from a segment

        Returns:
            List of entity dicts (empty if not present)
        """
        return segment.get('annotations', {}).get('entities', [])

    @staticmethod
    def validate_nlp_sentiment(data: Dict[str, Any]) -> bool:
        """
        Validate NLP sentiment annotation

        Args:
            data: Sentiment annotation data

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=NLP_SENTIMENT_SCHEMA)
            logger.debug("NLP sentiment validation passed")
            return True
        except ValidationError as e:
            logger.error(f"NLP sentiment validation failed: {e.message}")
            raise

    @staticmethod
    def validate_nlp_entity(data: Dict[str, Any]) -> bool:
        """
        Validate NLP entity annotation

        Args:
            data: Entity annotation data

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=NLP_ENTITY_SCHEMA)
            logger.debug("NLP entity validation passed")
            return True
        except ValidationError as e:
            logger.error(f"NLP entity validation failed: {e.message}")
            raise

    @staticmethod
    def validate_transcript(data: Dict[str, Any]) -> bool:
        """
        Validate transcript document

        Args:
            data: Transcript data to validate

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=TRANSCRIPT_DOCUMENT_SCHEMA)
            logger.debug("Transcript validation passed")
            return True
        except ValidationError as e:
            logger.error(f"Transcript validation failed: {e.message}")
            raise

    @staticmethod
    def validate_normalized_conversation(data: Dict[str, Any]) -> bool:
        """
        Validate normalized conversation

        Args:
            data: Normalized conversation data

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=NORMALIZED_CONVERSATION_SCHEMA)
            logger.debug("Normalized conversation validation passed")
            return True
        except ValidationError as e:
            logger.error(f"Normalized conversation validation failed: {e.message}")
            raise

    @staticmethod
    def validate_redis_event(data: Dict[str, Any]) -> bool:
        """
        Validate Redis event message

        Args:
            data: Redis event data

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=REDIS_EVENT_SCHEMA)
            logger.debug("Redis event validation passed")
            return True
        except ValidationError as e:
            logger.error(f"Redis event validation failed: {e.message}")
            raise

    @staticmethod
    def validate_metadata(data: Dict[str, Any]) -> bool:
        """
        Validate transcript metadata

        Args:
            data: Metadata to validate

        Returns:
            True if valid

        Raises:
            ValidationError if invalid
        """
        try:
            validate(instance=data, schema=TRANSCRIPT_METADATA_SCHEMA)
            logger.debug("Metadata validation passed")
            return True
        except ValidationError as e:
            logger.error(f"Metadata validation failed: {e.message}")
            raise


def save_schemas_to_files():
    """Save all schemas to individual JSON files"""
    import os
    from pathlib import Path

    schema_dir = Path(__file__).parent / "schemas"
    schema_dir.mkdir(exist_ok=True)

    schemas = {
        "transcript_metadata.schema.json": TRANSCRIPT_METADATA_SCHEMA,
        "transcript_segment.schema.json": TRANSCRIPT_SEGMENT_SCHEMA,
        "transcript_document.schema.json": TRANSCRIPT_DOCUMENT_SCHEMA,
        "conversation_turn.schema.json": CONVERSATION_TURN_SCHEMA,
        "normalized_conversation.schema.json": NORMALIZED_CONVERSATION_SCHEMA,
        "redis_event.schema.json": REDIS_EVENT_SCHEMA,
        "nlp_sentiment.schema.json": NLP_SENTIMENT_SCHEMA,
        "nlp_entity.schema.json": NLP_ENTITY_SCHEMA,
        "nlp_annotations.schema.json": NLP_ANNOTATIONS_SCHEMA
    }

    for filename, schema in schemas.items():
        filepath = schema_dir / filename
        with open(filepath, 'w') as f:
            json.dump(schema, f, indent=2)
        print(f"Saved schema: {filepath}")


if __name__ == "__main__":
    # Save schemas when run directly
    save_schemas_to_files()
