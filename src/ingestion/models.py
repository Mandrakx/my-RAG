"""
Database models for ingestion pipeline
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
import uuid

Base = declarative_base()


class IngestionStatus(str, Enum):
    """Status of ingestion job"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    NORMALIZING = "normalizing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class IngestionJob(Base):
    """Ingestion job tracking table"""
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Source information (from Transcript service)
    job_id = Column(String, unique=True, nullable=False, index=True)
    external_event_id = Column(String, unique=True, nullable=False, index=True)  # NEW: Stable ID from contract
    source_bucket = Column(String, nullable=False)  # MinIO bucket
    source_key = Column(String, nullable=False)     # Object key in bucket

    # Cross-cutting contract fields (ADR-2025-10-03-003)
    trace_id = Column(String, nullable=True, index=True)  # NEW: For distributed tracing
    checksum = Column(String, nullable=True)  # NEW: SHA-256 checksum from Redis message
    schema_version = Column(String, nullable=True)  # NEW: Payload schema version

    # Status tracking
    status = Column(String, default=IngestionStatus.PENDING.value, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Processing details
    error_message = Column(Text, nullable=True)
    error_stack = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)  # NEW: Standardized error code (e.g., 'checksum_mismatch')
    processing_metadata = Column(JSON, default={})

    # Results
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=True)
    normalized_key = Column(String, nullable=True)  # Key in MinIO for normalized data

    # Metrics
    file_size_bytes = Column(Integer, nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="ingestion_job")


class Conversation(Base):
    """Conversation metadata table"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic metadata
    title = Column(String, nullable=True)
    date = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, nullable=True)
    language = Column(String, default="fr")

    # Classification
    conversation_type = Column(String, nullable=True)  # meeting, one_to_one, etc.
    interaction_type = Column(String, nullable=True)   # professional, personal, mixed

    # Location
    location_name = Column(String, nullable=True)
    location_address = Column(String, nullable=True)
    location_gps = Column(JSON, nullable=True)
    location_type = Column(String, nullable=True)

    # Content
    transcript = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)

    # Participants (stored as JSON array)
    participants = Column(JSON, default=[])

    # Tags and topics
    tags = Column(JSON, default=[])
    main_topics = Column(JSON, default=[])

    # Quality metrics
    confidence_score = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Vector storage reference
    qdrant_collection = Column(String, default="conversations")
    qdrant_point_id = Column(String, nullable=True)

    # User ownership (for multi-tenancy)
    user_id = Column(String, nullable=True, index=True)

    # Relationships
    ingestion_job = relationship("IngestionJob", back_populates="conversation", uselist=False)
    turns = relationship("ConversationTurn", back_populates="conversation", cascade="all, delete-orphan")


class ConversationTurn(Base):
    """Individual turns in a conversation"""
    __tablename__ = "conversation_turns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False, index=True)

    # Turn details
    turn_index = Column(Integer, nullable=False)
    speaker = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    timestamp_ms = Column(Integer, nullable=True)  # Position in audio

    # Sentiment
    sentiment = Column(String, nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)
    emotion = Column(String, nullable=True)

    # Vector reference
    qdrant_point_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="turns")


# Pydantic models for API validation

class IngestionJobCreate(BaseModel):
    """Create ingestion job request"""
    job_id: str
    source_bucket: str
    source_key: str
    metadata: Optional[Dict[str, Any]] = None


class IngestionJobResponse(BaseModel):
    """Ingestion job response"""
    id: str
    job_id: str
    status: IngestionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int
    error_message: Optional[str] = None
    conversation_id: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Create conversation request"""
    title: Optional[str] = None
    date: datetime
    duration_minutes: Optional[int] = None
    language: str = "fr"
    conversation_type: Optional[str] = None
    interaction_type: Optional[str] = None
    transcript: str
    participants: List[Dict[str, Any]] = []
    tags: List[str] = []
    user_id: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response"""
    id: str
    title: Optional[str]
    date: datetime
    duration_minutes: Optional[int]
    conversation_type: Optional[str]
    transcript: str
    summary: Optional[str]
    participants: List[Dict[str, Any]]
    tags: List[str]
    main_topics: List[str]
    confidence_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptMetadata(BaseModel):
    """Metadata from transcript file"""
    job_id: str
    audio_filename: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = "fr"
    timestamp: datetime
    model_version: Optional[str] = None
    source: str = "transcript-service"


class TranscriptSegment(BaseModel):
    """Individual segment from transcript"""
    speaker: str
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    confidence: Optional[float] = None


class TranscriptDocument(BaseModel):
    """Complete transcript document structure"""
    metadata: TranscriptMetadata
    segments: List[TranscriptSegment]

    def to_conversation_jsonl(self) -> List[Dict[str, Any]]:
        """Convert to conversation.jsonl format"""
        result = []
        for idx, segment in enumerate(self.segments):
            result.append({
                "turn": idx,
                "speaker": segment.speaker,
                "text": segment.text,
                "timestamp_ms": int(segment.start_time * 1000) if segment.start_time else None,
                "confidence": segment.confidence
            })
        return result
