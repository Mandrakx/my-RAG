"""
Storage module for ingestion pipeline
Handles MinIO and PostgreSQL persistence
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO
import gzip

from .config import IngestionConfig, clients
from .models import Conversation, ConversationTurn, IngestionJob
from .normalizer import TranscriptNormalizer

logger = logging.getLogger(__name__)


class IngestionStorage:
    """
    Handles storage operations for ingestion pipeline
    - MinIO: Raw and normalized transcripts
    - PostgreSQL: Conversation metadata and search index
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()
        self.minio = clients.minio
        self.normalizer = TranscriptNormalizer(config)

    async def download_transcript(self, bucket: str, object_key: str) -> Dict[str, Any]:
        """
        Download transcript from MinIO

        Args:
            bucket: MinIO bucket name
            object_key: Object key

        Returns:
            Transcript data as dict
        """
        try:
            logger.info(f"Downloading from MinIO: {bucket}/{object_key}")

            # Download object
            response = self.minio.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()

            # Handle different file types
            if object_key.endswith('.gz'):
                # Decompress gzip
                data = gzip.decompress(data)

            if object_key.endswith('.json') or object_key.endswith('.json.gz'):
                # Parse JSON
                transcript = json.loads(data.decode('utf-8'))
            elif object_key.endswith('.tar.gz'):
                # Extract from tar.gz (assume transcript.json inside)
                import tarfile
                tar_buffer = BytesIO(data)
                with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
                    # Look for transcript.json or similar
                    for member in tar.getmembers():
                        if member.name.endswith('.json') and 'transcript' in member.name.lower():
                            file_obj = tar.extractfile(member)
                            if file_obj:
                                transcript = json.loads(file_obj.read().decode('utf-8'))
                                break
                    else:
                        raise Exception("No transcript.json found in tar.gz")
            else:
                # Try parsing as JSON
                transcript = json.loads(data.decode('utf-8'))

            logger.info(f"Successfully downloaded transcript: {len(data)} bytes")
            return transcript

        except Exception as e:
            logger.error(f"Error downloading from MinIO: {e}")
            raise

    async def upload_normalized(self, bucket: str, key: str, data: Dict[str, Any]):
        """
        Upload normalized conversation to MinIO

        Args:
            bucket: MinIO bucket
            key: Object key
            data: Normalized conversation data
        """
        try:
            # Convert to JSONL format
            jsonl_content = self.normalizer.to_jsonl(data)

            # Upload to MinIO
            data_bytes = jsonl_content.encode('utf-8')
            data_stream = BytesIO(data_bytes)

            self.minio.put_object(
                bucket_name=bucket,
                object_name=key,
                data=data_stream,
                length=len(data_bytes),
                content_type='application/x-ndjson'
            )

            logger.info(f"Uploaded normalized data to MinIO: {bucket}/{key}")

        except Exception as e:
            logger.error(f"Error uploading to MinIO: {e}")
            raise

    async def store_conversation(
        self,
        job_id: str,
        normalized_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Conversation:
        """
        Store conversation in PostgreSQL

        Args:
            job_id: Job ID from ingestion
            normalized_data: Normalized conversation data
            metadata: Original metadata

        Returns:
            Created Conversation object
        """
        try:
            db = clients.get_db_session()

            # Extract data from normalized conversation
            conv_metadata = normalized_data.get('metadata', {})
            turns = normalized_data.get('turns', [])
            participants = normalized_data.get('participants', [])
            statistics = normalized_data.get('statistics', {})

            # Create conversation
            conversation = Conversation(
                title=self._generate_title(turns, participants),
                date=self._parse_datetime(conv_metadata.get('date')),
                duration_minutes=self._get_duration_minutes(conv_metadata.get('duration_seconds')),
                language=conv_metadata.get('language', 'fr'),
                conversation_type=self._infer_conversation_type(participants, statistics),
                interaction_type='professional',  # Default, can be inferred later
                transcript=self._build_full_transcript(turns),
                participants=participants,
                tags=[],
                main_topics=[],
                confidence_score=statistics.get('avg_confidence', 1.0) or 1.0,
                qdrant_collection=self.config.qdrant_collection,
                user_id=metadata.get('user_id')  # From original metadata
            )

            db.add(conversation)
            db.flush()  # Get conversation.id

            # Create turns
            for turn_data in turns:
                turn = ConversationTurn(
                    conversation_id=conversation.id,
                    turn_index=turn_data.get('turn', 0),
                    speaker=turn_data.get('speaker', 'Unknown'),
                    text=turn_data.get('text', ''),
                    timestamp_ms=turn_data.get('timestamp_ms')
                )
                db.add(turn)

            db.commit()
            db.refresh(conversation)

            logger.info(f"Stored conversation {conversation.id} with {len(turns)} turns")
            return conversation

        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            db.rollback()
            raise

    def _generate_title(self, turns: list, participants: list) -> str:
        """Generate conversation title"""
        if not turns:
            return "Untitled Conversation"

        # Use first few words of first turn
        first_text = turns[0].get('text', '')
        words = first_text.split()[:7]
        title = ' '.join(words)

        if len(first_text.split()) > 7:
            title += '...'

        # Add participants info
        if len(participants) == 2:
            speakers = [p.get('speaker') for p in participants[:2]]
            title = f"{speakers[0]} & {speakers[1]}: {title}"
        elif len(participants) > 2:
            title = f"Group ({len(participants)}): {title}"

        return title[:200]  # Limit length

    def _parse_datetime(self, date_value: Any) -> datetime:
        """Parse datetime from various formats"""
        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.fromtimestamp(float(date_value))
                except:
                    pass

        return datetime.utcnow()

    def _get_duration_minutes(self, duration_seconds: Optional[float]) -> Optional[int]:
        """Convert duration to minutes"""
        if duration_seconds is None:
            return None
        return int(duration_seconds / 60)

    def _infer_conversation_type(self, participants: list, statistics: dict) -> str:
        """Infer conversation type from participants"""
        num_speakers = len(participants)

        if num_speakers == 1:
            return 'monologue'
        elif num_speakers == 2:
            return 'one_to_one'
        elif num_speakers <= 5:
            return 'small_group'
        else:
            return 'meeting'

    def _build_full_transcript(self, turns: list) -> str:
        """Build full transcript text from turns"""
        lines = []
        for turn in turns:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            lines.append(f"{speaker}: {text}")

        return '\n'.join(lines)

    async def archive_raw_data(self, source_bucket: str, source_key: str, job_id: str):
        """
        Archive raw data to archive bucket

        Args:
            source_bucket: Source bucket
            source_key: Source object key
            job_id: Job ID for organizing archive
        """
        try:
            archive_bucket = self.config.minio_bucket_archive
            archive_key = f"{datetime.utcnow().strftime('%Y/%m/%d')}/{job_id}/{source_key}"

            # Copy to archive
            self.minio.copy_object(
                bucket_name=archive_bucket,
                object_name=archive_key,
                source=f"{source_bucket}/{source_key}"
            )

            logger.info(f"Archived to {archive_bucket}/{archive_key}")

        except Exception as e:
            logger.error(f"Error archiving data: {e}")
            # Don't raise - archiving is non-critical

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        db = clients.get_db_session()
        return db.query(Conversation).filter_by(id=conversation_id).first()

    async def get_conversation_turns(self, conversation_id: str) -> list:
        """Get all turns for a conversation"""
        db = clients.get_db_session()
        return db.query(ConversationTurn).filter_by(
            conversation_id=conversation_id
        ).order_by(ConversationTurn.turn_index).all()

    async def update_conversation_summary(self, conversation_id: str, summary: str):
        """Update conversation summary"""
        db = clients.get_db_session()
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.summary = summary
            db.commit()

    async def update_conversation_topics(self, conversation_id: str, topics: list):
        """Update conversation main topics"""
        db = clients.get_db_session()
        conversation = db.query(Conversation).filter_by(id=conversation_id).first()
        if conversation:
            conversation.main_topics = topics
            db.commit()
