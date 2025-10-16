"""
Validation stricte des payloads conversation.json depuis transcript
PAS de normalisation - transcript livre le format FINAL
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field, validator
from datetime import datetime
from jsonschema import validate, ValidationError as JSONSchemaError

logger = logging.getLogger(__name__)

# Load conversation-payload.schema.json
SCHEMA_PATH = Path(__file__).parent.parent.parent / "docs" / "design" / "conversation-payload.schema.json"

with open(SCHEMA_PATH) as f:
    CONVERSATION_PAYLOAD_SCHEMA = json.load(f)


class Location(BaseModel):
    """Location from transcript"""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    display_name: Optional[str] = Field(None, max_length=256)
    address: Optional[str] = Field(None, max_length=512)
    floor: Optional[str] = Field(None, max_length=32)
    room: Optional[str] = Field(None, max_length=64)


class MeetingMetadata(BaseModel):
    """Meeting metadata from transcript"""
    scheduled_start: datetime
    title: Optional[str] = Field(None, min_length=1, max_length=256)
    duration_sec: Optional[int] = Field(None, ge=1, le=86400)
    end_at: Optional[datetime] = None
    location: Optional[Location] = None
    timezone: Optional[str] = None
    organizer: Optional[str] = Field(None, min_length=1, max_length=128)
    agenda: Optional[str] = Field(None, max_length=4096)

    @validator('duration_sec', 'end_at', always=True)
    def check_duration_or_end(cls, v, values):
        """At least one of duration_sec or end_at must be present"""
        if 'duration_sec' not in values and 'end_at' not in values:
            if v is None:
                raise ValueError('Either duration_sec or end_at must be provided')
        return v


class Participant(BaseModel):
    """Participant from transcript (avec speaker_id déjà identifié)"""
    speaker_id: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    email: Optional[str] = None
    role: Optional[str] = Field(None, max_length=64)
    company: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    metadata: Optional[Dict[str, Any]] = None  # Contient voice_matches!

    class Config:
        extra = "forbid"


class Entity(BaseModel):
    """Entity from segment annotations"""
    type: str = Field(max_length=64)
    text: str = Field(min_length=1)
    start_char: Optional[int] = Field(None, ge=0)
    end_char: Optional[int] = Field(None, ge=0)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    metadata: Optional[Dict[str, Any]] = None


class Sentiment(BaseModel):
    """Sentiment from segment annotations (v1.1+)"""
    label: str = Field(pattern="^(very_positive|positive|neutral|negative|very_negative|mixed)$")
    score: float = Field(ge=0, le=1)
    stars: Optional[int] = Field(None, ge=1, le=5)
    metadata: Optional[Dict[str, Any]] = None


class SegmentAnnotations(BaseModel):
    """Annotations optionnelles du segment"""
    topics: Optional[list[str]] = None
    entities: Optional[list[Entity]] = None
    sentiment: Optional[Sentiment] = None


class Segment(BaseModel):
    """Segment from transcript - DÉJÀ diarisé, transcrit, identifié"""
    segment_id: str = Field(min_length=1, max_length=64)
    speaker_id: str = Field(min_length=1, max_length=64)  # Référence participant
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str = Field(min_length=1)
    language: str  # BCP-47
    confidence: float = Field(ge=0, le=1)

    # Optionnels
    channel: Optional[int] = Field(None, ge=0, le=32)
    duration_ms: Optional[int] = Field(None, ge=1)
    offset_ms: Optional[int] = Field(None, ge=0)
    speaker_label: Optional[str] = Field(None, max_length=64)
    annotations: Optional[SegmentAnnotations] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"


class QualityFlags(BaseModel):
    """Flags de qualité calculés par transcript"""
    low_confidence: bool = False
    missing_audio: bool = False
    overlapping_speech: bool = False


class ConversationPayload(BaseModel):
    """
    Payload FINAL produit par transcript
    my-RAG ne fait QUE valider - PAS normaliser!
    """
    schema_version: str = Field(pattern=r"^\d+\.\d+$")
    external_event_id: str = Field(
        min_length=4,
        max_length=128,
        pattern=r"^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$",
        description="Format: rec-<ISO8601>-<UUID> (e.g., rec-20251003T091500Z-3f9c4241)"
    )
    source_system: str = Field(min_length=1, max_length=64)
    created_at: datetime

    meeting_metadata: MeetingMetadata
    participants: list[Participant] = Field(min_items=1)
    segments: list[Segment] = Field(min_items=1)

    # Optionnels
    quality_flags: Optional[QualityFlags] = None
    attachments: Optional[Dict[str, Any]] = None
    analytics: Optional[Dict[str, Any]] = None
    tags: Optional[list[str]] = None
    primary_language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"  # Strict - reject unknown fields

    @validator('participants')
    def check_speaker_refs(cls, participants, values):
        """Ensure all speaker_ids in segments reference valid participants"""
        speaker_ids = {p.speaker_id for p in participants}

        if 'segments' in values:
            for seg in values['segments']:
                if seg.speaker_id not in speaker_ids:
                    raise ValueError(
                        f"Segment {seg.segment_id} references unknown speaker_id: {seg.speaker_id}"
                    )
        return participants


class TranscriptValidator:
    """
    Validateur STRICT pour payloads transcript

    Responsabilités:
    - ✅ Valider JSON Schema
    - ✅ Valider références (speaker_id, etc.)
    - ✅ Vérifier cohérence données
    - ❌ PAS de normalisation (déjà fait par transcript!)
    - ❌ PAS de parsing multi-formats (un seul format accepté)
    """

    @staticmethod
    def validate_json_schema(data: Dict[str, Any]) -> None:
        """
        Valide contre conversation-payload.schema.json

        Raises:
            JSONSchemaError si invalide
        """
        try:
            validate(instance=data, schema=CONVERSATION_PAYLOAD_SCHEMA)
            logger.debug("JSON Schema validation passed")
        except JSONSchemaError as e:
            logger.error(f"JSON Schema validation failed: {e.message}")
            raise

    @staticmethod
    def validate_pydantic(data: Dict[str, Any]) -> ConversationPayload:
        """
        Valide et parse avec Pydantic

        Returns:
            ConversationPayload validé

        Raises:
            ValidationError si invalide
        """
        try:
            payload = ConversationPayload(**data)
            logger.info(
                f"Validated conversation: {payload.external_event_id}, "
                f"{len(payload.segments)} segments, {len(payload.participants)} participants"
            )
            return payload
        except Exception as e:
            logger.error(f"Pydantic validation failed: {e}")
            raise

    @staticmethod
    def validate_conversation(data: Dict[str, Any]) -> ConversationPayload:
        """
        Validation complète (JSON Schema + Pydantic)

        Args:
            data: conversation.json from transcript

        Returns:
            ConversationPayload validé

        Raises:
            ValidationError si invalide
        """
        # Step 1: JSON Schema validation
        TranscriptValidator.validate_json_schema(data)

        # Step 2: Pydantic validation (stricter)
        payload = TranscriptValidator.validate_pydantic(data)

        # Step 3: Business logic validation
        TranscriptValidator._validate_business_rules(payload)

        return payload

    @staticmethod
    def _validate_business_rules(payload: ConversationPayload):
        """Validate business logic rules"""

        # Check: segments are chronologically ordered
        prev_end = 0
        for seg in payload.segments:
            if seg.start_ms < prev_end:
                logger.warning(
                    f"Segment {seg.segment_id} overlaps previous segment "
                    f"(start={seg.start_ms}, prev_end={prev_end})"
                )
            prev_end = seg.end_ms

        # Check: quality flags consistency
        if payload.quality_flags:
            if payload.quality_flags.low_confidence:
                low_conf_count = sum(1 for s in payload.segments if s.confidence < 0.7)
                if low_conf_count == 0:
                    logger.warning("quality_flags.low_confidence=true but no low confidence segments")

        # Check: primary_language vs segment languages
        if payload.primary_language:
            segment_languages = {s.language for s in payload.segments}
            if payload.primary_language not in segment_languages:
                logger.warning(
                    f"primary_language '{payload.primary_language}' not found in segments"
                )

        logger.debug("Business rules validation passed")

    @staticmethod
    def validate_and_extract(
        data: Dict[str, Any]
    ) -> tuple[ConversationPayload, Dict[str, Any]]:
        """
        Validate et extrait métadonnées critiques

        Returns:
            (payload validé, metadata pour storage)
        """
        payload = TranscriptValidator.validate_conversation(data)

        # Extract critical metadata (preserve voice_matches!)
        metadata = {
            'external_event_id': payload.external_event_id,
            'source_system': payload.source_system,
            'schema_version': payload.schema_version,
            'created_at': payload.created_at.isoformat(),
            'num_segments': len(payload.segments),
            'num_participants': len(payload.participants),
            'duration_sec': payload.meeting_metadata.duration_sec,
            'primary_language': payload.primary_language,
            'quality_flags': payload.quality_flags.dict() if payload.quality_flags else None,

            # IMPORTANT: Preserve voice identification results
            'voice_matches': [
                {
                    'speaker_id': p.speaker_id,
                    'display_name': p.display_name,
                    'voice_metadata': p.metadata
                }
                for p in payload.participants
                if p.metadata and 'voice_matches' in p.metadata
            ] if any(p.metadata for p in payload.participants) else None
        }

        return payload, metadata


def validate_conversation_from_transcript(
    conversation_json: Dict[str, Any]
) -> ConversationPayload:
    """
    Entry point pour validation de conversation.json

    Usage:
        conversation = validate_conversation_from_transcript(data)
        # conversation est déjà normalisé par transcript!
        # Pas besoin de re-parser ou re-normaliser
    """
    return TranscriptValidator.validate_conversation(conversation_json)
