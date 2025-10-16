"""
Redis Message Parser for audio.ingestion stream

Parses messages conforming to audio-redis-message-schema.json
Aligned with ADR-2025-10-03-003 cross-cutting contract
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
from pydantic import BaseModel, Field, validator
from jsonschema import validate, ValidationError as JSONSchemaError
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Load audio-redis-message-schema.json
SCHEMA_PATH = Path(__file__).parent.parent.parent / "docs" / "design" / "audio-redis-message-schema.json"

with open(SCHEMA_PATH) as f:
    REDIS_MESSAGE_SCHEMA = json.load(f)


class ProducerInfo(BaseModel):
    """Producer information from Redis message"""
    service: str = Field(min_length=1, max_length=64)
    instance: Optional[str] = Field(None, min_length=1, max_length=64)


class RedisMessageMetadata(BaseModel):
    """Metadata section from Redis message"""
    trace_id: Optional[str] = Field(None, description="UUID v4 for distributed tracing")

    class Config:
        extra = "allow"  # Allow additional metadata fields


class AudioIngestionMessage(BaseModel):
    """
    Message format for audio.ingestion stream

    Conforms to docs/design/audio-redis-message-schema.json
    """
    external_event_id: str = Field(
        min_length=4,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
        description="Stable identifier matching archive name"
    )
    package_uri: str = Field(
        description="MinIO URI pointing to tar.gz archive (format: minio://bucket/path)"
    )
    checksum: str = Field(
        pattern=r"^sha256:[a-f0-9]{64}$",
        description="SHA-256 checksum prefixed with 'sha256:'"
    )
    schema_version: str = Field(
        pattern=r"^\d+\.\d+$",
        description="Semantic version (major.minor)"
    )
    retry_count: int = Field(
        ge=0,
        le=10,
        description="Number of delivery attempts by producer"
    )
    produced_at: datetime = Field(description="UTC timestamp when message was emitted")

    # Optional fields
    producer: Optional[ProducerInfo] = None
    priority: Optional[str] = Field("normal", pattern="^(normal|high)$")
    metadata: Optional[RedisMessageMetadata] = None

    @validator('package_uri')
    def validate_minio_uri(cls, v):
        """Validate MinIO URI format"""
        if not v.startswith('minio://'):
            raise ValueError("package_uri must start with 'minio://'")

        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("package_uri must include bucket name")
        if not parsed.path or parsed.path == '/':
            raise ValueError("package_uri must include object path")

        return v

    def parse_package_uri(self) -> Tuple[str, str]:
        """
        Parse package_uri into bucket and object key

        Returns:
            (bucket, object_key) tuple

        Example:
            minio://ingestion/drop/2025/10/16/rec-20251003T091500Z-3f9c4241.tar.gz
            → ("ingestion", "drop/2025/10/16/rec-20251003T091500Z-3f9c4241.tar.gz")
        """
        parsed = urlparse(self.package_uri)
        bucket = parsed.netloc
        object_key = parsed.path.lstrip('/')
        return bucket, object_key

    def get_trace_id(self) -> Optional[str]:
        """Extract trace_id from metadata for distributed tracing"""
        if self.metadata:
            return self.metadata.trace_id
        return None

    def get_checksum_hash(self) -> str:
        """Extract hash from checksum (remove 'sha256:' prefix)"""
        return self.checksum.replace('sha256:', '')


class RedisMessageParser:
    """Parser for audio.ingestion Redis Stream messages"""

    @staticmethod
    def parse_bytes_dict(message_data: Dict[bytes, bytes]) -> Dict[str, Any]:
        """
        Convert Redis bytes dictionary to Python dict

        Args:
            message_data: Raw message data from Redis (bytes keys/values)

        Returns:
            Parsed dictionary with string keys and appropriate values
        """
        parsed = {}

        for key, value in message_data.items():
            # Decode key
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key

            # Decode value
            value_str = value.decode('utf-8') if isinstance(value, bytes) else value

            # Try to parse JSON values (for nested objects like producer, metadata)
            if key_str in ['producer', 'metadata'] and value_str:
                try:
                    parsed[key_str] = json.loads(value_str)
                except json.JSONDecodeError:
                    parsed[key_str] = value_str
            elif key_str == 'retry_count':
                parsed[key_str] = int(value_str)
            else:
                parsed[key_str] = value_str

        return parsed

    @staticmethod
    def validate_schema(data: Dict[str, Any]) -> bool:
        """
        Validate message against audio-redis-message-schema.json

        Args:
            data: Message data to validate

        Returns:
            True if valid

        Raises:
            JSONSchemaError if invalid
        """
        try:
            validate(instance=data, schema=REDIS_MESSAGE_SCHEMA)
            logger.debug("Redis message schema validation passed")
            return True
        except JSONSchemaError as e:
            logger.error(f"Redis message schema validation failed: {e.message}")
            raise

    @staticmethod
    def parse(message_data: Dict[bytes, bytes]) -> AudioIngestionMessage:
        """
        Parse and validate Redis message

        Args:
            message_data: Raw message data from Redis xreadgroup

        Returns:
            Validated AudioIngestionMessage

        Raises:
            ValidationError if message is invalid
        """
        # Step 1: Convert bytes to dict
        data = RedisMessageParser.parse_bytes_dict(message_data)

        logger.debug(f"Parsed Redis message: {data.get('external_event_id')}")

        # Step 2: Validate against JSON Schema
        RedisMessageParser.validate_schema(data)

        # Step 3: Parse with Pydantic (stricter validation)
        try:
            message = AudioIngestionMessage(**data)

            # Log trace_id if available
            trace_id = message.get_trace_id()
            if trace_id:
                logger.info(
                    f"Parsed message: {message.external_event_id} "
                    f"(trace_id={trace_id}, retry_count={message.retry_count})"
                )
            else:
                logger.info(
                    f"Parsed message: {message.external_event_id} "
                    f"(retry_count={message.retry_count})"
                )

            return message

        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            raise

    @staticmethod
    def is_high_priority(message: AudioIngestionMessage) -> bool:
        """Check if message has high priority"""
        return message.priority == "high"

    @staticmethod
    def should_retry(message: AudioIngestionMessage, max_retries: int = 3) -> bool:
        """Check if message should be retried based on retry_count"""
        return message.retry_count < max_retries
