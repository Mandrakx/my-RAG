"""
Ingestion pipeline for audio transcripts from transcript service
Handles MinIO drops, Redis events, and validation

IMPORTANT: my-RAG ne normalise PAS - transcript livre le format FINAL
Role: Validation + Storage + RAG Processing uniquement
"""

from .consumer import RedisStreamConsumer
from .transcript_validator import TranscriptValidator, validate_conversation_from_transcript
from .storage import IngestionStorage

__all__ = [
    "RedisStreamConsumer",
    "TranscriptValidator",
    "validate_conversation_from_transcript",
    "IngestionStorage"
]
