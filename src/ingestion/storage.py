"""
Storage module for ingestion pipeline
Handles MinIO and PostgreSQL persistence
"""

import json
import logging
import tempfile
import tarfile
from pathlib import Path
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
        Download and extract transcript archive from MinIO

        Handles tar.gz archives per ADR-2025-10-03-003 contract.

        Args:
            bucket: MinIO bucket name
            object_key: Object key

        Returns:
            Dict with:
                - conversation.json: Parsed conversation data
                - metadata: Archive metadata
                - tarball_path: Path to downloaded tar.gz (for checksum validation)
                - extracted_dir: Path to extracted directory (for internal checksum validation)
                - file_size: Size of downloaded file in bytes
        """
        try:
            logger.info(f"Downloading from MinIO: {bucket}/{object_key}")

            # Download object to temporary file
            response = self.minio.get_object(bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()

            file_size = len(data)
            logger.info(f"Downloaded {file_size} bytes")

            # Handle tar.gz archives (primary format per contract)
            if object_key.endswith('.tar.gz'):
                # Save to temporary file for checksum validation
                temp_dir = Path(tempfile.mkdtemp(prefix='my-rag-ingestion-'))
                tarball_path = temp_dir / Path(object_key).name

                with open(tarball_path, 'wb') as f:
                    f.write(data)

                logger.info(f"Saved tarball to {tarball_path}")

                # Extract archive
                extracted_dir = temp_dir / 'extracted'
                extracted_dir.mkdir()

                with tarfile.open(tarball_path, 'r:gz') as tar:
                    # Extract all files
                    tar.extractall(path=extracted_dir)

                    # List extracted files for debugging
                    members = tar.getmembers()
                    logger.info(f"Extracted {len(members)} files from archive")

                # Find conversation.json (should be in root of external_event_id folder)
                conversation_json_path = None
                for item in extracted_dir.rglob('conversation.json'):
                    conversation_json_path = item
                    break

                if not conversation_json_path:
                    raise FileNotFoundError("conversation.json not found in archive")

                # Parse conversation.json
                with open(conversation_json_path, 'r', encoding='utf-8') as f:
                    conversation_data = json.load(f)

                logger.info(f"Loaded conversation.json from {conversation_json_path}")

                # Build metadata
                metadata = {
                    'source_bucket': bucket,
                    'source_key': object_key,
                    'downloaded_at': datetime.utcnow().isoformat(),
                    'archive_size_bytes': file_size
                }

                return {
                    'conversation.json': conversation_data,
                    'metadata': metadata,
                    'tarball_path': tarball_path,  # For checksum validation
                    'extracted_dir': extracted_dir.parent,  # Parent contains both tarball and extracted/
                    'file_size': file_size
                }

            # Fallback for legacy formats (JSON, JSON.gz)
            elif object_key.endswith('.json') or object_key.endswith('.json.gz'):
                if object_key.endswith('.gz'):
                    data = gzip.decompress(data)

                transcript = json.loads(data.decode('utf-8'))

                return {
                    'conversation.json': transcript,
                    'metadata': {
                        'source_bucket': bucket,
                        'source_key': object_key,
                        'downloaded_at': datetime.utcnow().isoformat()
                    },
                    'tarball_path': None,
                    'extracted_dir': None,
                    'file_size': file_size
                }

            else:
                raise ValueError(f"Unsupported file format: {object_key}")

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

    async def store_conversation_from_transcript(
        self,
        payload: Any,
        source_metadata: Dict[str, Any]
    ) -> Conversation:
        """
        Store conversation from validated transcript payload

        Args:
            payload: Validated ConversationPayload from transcript
            source_metadata: Source metadata (trace_id, checksum, etc.)

        Returns:
            Created Conversation object
        """
        try:
            db = clients.get_db_session()

            # Extract meeting metadata
            meeting_meta = payload.meeting_metadata

            # Build full transcript text
            transcript_lines = []
            for seg in payload.segments:
                # Find participant display_name from speaker_id
                participant = next(
                    (p for p in payload.participants if p.speaker_id == seg.speaker_id),
                    None
                )
                speaker_name = participant.display_name if participant else seg.speaker_id
                transcript_lines.append(f"{speaker_name}: {seg.text}")

            full_transcript = '\n'.join(transcript_lines)

            # Calculate duration
            duration_sec = meeting_meta.duration_sec
            if not duration_sec and meeting_meta.end_at:
                delta = meeting_meta.end_at - meeting_meta.scheduled_start
                duration_sec = int(delta.total_seconds())

            duration_minutes = int(duration_sec / 60) if duration_sec else None

            # Extract location if present
            location_gps = None
            location_name = None
            if meeting_meta.location:
                location_gps = {
                    'lat': meeting_meta.location.lat,
                    'lon': meeting_meta.location.lon
                }
                location_name = meeting_meta.location.display_name

            # Build participants list
            participants_list = [
                {
                    'speaker_id': p.speaker_id,
                    'display_name': p.display_name,
                    'email': p.email,
                    'role': p.role,
                    'company': p.company
                }
                for p in payload.participants
            ]

            # Create conversation
            conversation = Conversation(
                title=meeting_meta.title or self._generate_title_from_segments(payload.segments, participants_list),
                date=meeting_meta.scheduled_start,
                duration_minutes=duration_minutes,
                language=payload.primary_language or 'fr',
                conversation_type=self._infer_conversation_type(participants_list, {}),
                interaction_type='professional',
                transcript=full_transcript,
                participants=participants_list,
                tags=payload.tags or [],
                main_topics=[],  # Will be populated by NLP processing
                confidence_score=self._calculate_avg_confidence(payload.segments),
                location_name=location_name,
                location_gps=location_gps,
                qdrant_collection=self.config.qdrant_collection,
                user_id=source_metadata.get('user_id')
            )

            db.add(conversation)
            db.flush()  # Get conversation.id

            # Create turns from segments
            for idx, seg in enumerate(payload.segments):
                participant = next(
                    (p for p in payload.participants if p.speaker_id == seg.speaker_id),
                    None
                )
                speaker_name = participant.display_name if participant else seg.speaker_id

                turn = ConversationTurn(
                    conversation_id=conversation.id,
                    turn_index=idx,
                    speaker=speaker_name,
                    text=seg.text,
                    timestamp_ms=seg.start_ms
                )
                db.add(turn)

            db.commit()
            db.refresh(conversation)

            logger.info(
                f"Stored conversation {conversation.id} from transcript: "
                f"{len(payload.segments)} segments, {len(payload.participants)} participants"
            )
            return conversation

        except Exception as e:
            logger.error(f"Error storing conversation from transcript: {e}")
            db.rollback()
            raise

    def _generate_title_from_segments(self, segments: list, participants: list) -> str:
        """Generate conversation title from first segment"""
        if not segments:
            return "Untitled Conversation"

        # Use first few words
        first_text = segments[0].text
        words = first_text.split()[:7]
        title = ' '.join(words)

        if len(first_text.split()) > 7:
            title += '...'

        # Add participants info
        if len(participants) == 2:
            names = [p['display_name'] for p in participants[:2]]
            title = f"{names[0]} & {names[1]}: {title}"
        elif len(participants) > 2:
            title = f"Group ({len(participants)}): {title}"

        return title[:200]

    def _calculate_avg_confidence(self, segments: list) -> float:
        """Calculate average confidence from segments"""
        if not segments:
            return 1.0

        confidences = [seg.confidence for seg in segments if seg.confidence is not None]
        if not confidences:
            return 1.0

        return sum(confidences) / len(confidences)
