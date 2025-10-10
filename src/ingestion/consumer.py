"""
Redis Streams consumer for ingestion events
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from .config import IngestionConfig, clients
from .models import IngestionJob, IngestionStatus
from .transcript_validator import validate_conversation_from_transcript
from .storage import IngestionStorage
from .schemas import SchemaValidator

# Import NLP processor
try:
    from ..nlp.processor import NLPProcessorFactory
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("NLP modules not available, embeddings will be skipped")

logger = logging.getLogger(__name__)


class RedisStreamConsumer:
    """
    Consumer for Redis Streams ingestion events
    Listens for audio drop notifications from Transcript service
    """

    def __init__(self, config: Optional[IngestionConfig] = None, enable_nlp: bool = True):
        self.config = config or IngestionConfig()
        self.redis = clients.redis
        self.running = False
        # NO normalizer - transcript provides FINAL format!
        self.storage = IngestionStorage(self.config)

        # Initialize NLP processor if available
        self.nlp_processor = None
        if enable_nlp and NLP_AVAILABLE:
            try:
                self.nlp_processor = NLPProcessorFactory.create_local_gpu_processor(
                    qdrant_url=self.config.qdrant_url
                )
                logger.info("NLP processor initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize NLP processor: {e}")

        # Consumer configuration
        self.stream_name = self.config.redis_stream_name
        self.group_name = self.config.redis_consumer_group
        self.consumer_name = self.config.redis_consumer_name
        self.block_ms = self.config.redis_block_ms
        self.batch_size = self.config.redis_batch_size

    async def ensure_consumer_group(self):
        """Create consumer group if it doesn't exist"""
        try:
            # Try to create the group
            self.redis.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group '{self.group_name}' for stream '{self.stream_name}'")
        except Exception as e:
            if 'BUSYGROUP' in str(e):
                logger.info(f"Consumer group '{self.group_name}' already exists")
            else:
                logger.error(f"Error creating consumer group: {e}")
                raise

    async def process_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """
        Process a single ingestion event message

        Args:
            message_id: Redis stream message ID
            message_data: Message payload

        Returns:
            True if processing succeeded, False otherwise
        """
        job_id = None
        try:
            # Parse message data
            job_id = message_data.get(b'job_id', b'').decode('utf-8')
            bucket = message_data.get(b'bucket', b'').decode('utf-8')
            object_key = message_data.get(b'object_key', b'').decode('utf-8')
            event_type = message_data.get(b'event_type', b'put').decode('utf-8')
            timestamp_str = message_data.get(b'timestamp', b'').decode('utf-8')

            logger.info(f"Processing ingestion event: job_id={job_id}, bucket={bucket}, key={object_key}")

            if not job_id or not bucket or not object_key:
                logger.error(f"Invalid message data: {message_data}")
                return False

            # Create ingestion job in database
            db = clients.get_db_session()

            # Check if job already exists
            existing_job = db.query(IngestionJob).filter_by(job_id=job_id).first()
            if existing_job:
                if existing_job.status == IngestionStatus.COMPLETED.value:
                    logger.info(f"Job {job_id} already completed, skipping")
                    return True
                elif existing_job.status == IngestionStatus.FAILED.value and existing_job.retry_count >= self.config.max_retries:
                    logger.warning(f"Job {job_id} already failed max retries, skipping")
                    return False

                # Update existing job for retry
                job = existing_job
                job.status = IngestionStatus.DOWNLOADING.value
                job.retry_count += 1
                job.started_at = datetime.utcnow()
            else:
                # Create new job
                job = IngestionJob(
                    job_id=job_id,
                    source_bucket=bucket,
                    source_key=object_key,
                    status=IngestionStatus.DOWNLOADING.value,
                    started_at=datetime.utcnow()
                )
                db.add(job)

            db.commit()

            # Step 1: Download from MinIO
            logger.info(f"[{job_id}] Downloading from MinIO: {bucket}/{object_key}")
            transcript_data = await self.storage.download_transcript(bucket, object_key)

            if not transcript_data:
                raise Exception("Failed to download transcript from MinIO")

            # Update status
            job.status = IngestionStatus.NORMALIZING.value  # Actually "VALIDATING"
            db.commit()

            # Step 2: VALIDATE (not normalize!) - transcript provides FINAL format
            logger.info(f"[{job_id}] Validating conversation.json from transcript")

            # Extract conversation.json from tar.gz
            conversation_json = transcript_data.get('conversation.json')
            if not conversation_json:
                raise Exception("Missing conversation.json in transcript package")

            # Validate against schema (strict!)
            validated_payload = validate_conversation_from_transcript(conversation_json)

            logger.info(
                f"[{job_id}] Validation passed: {validated_payload.external_event_id}, "
                f"{len(validated_payload.segments)} segments, {len(validated_payload.participants)} participants"
            )

            # Step 3: Store in database (as-is, preserve all metadata!)
            logger.info(f"[{job_id}] Storing conversation")
            conversation = await self.storage.store_conversation_from_transcript(
                payload=validated_payload,
                source_metadata=transcript_data.get('metadata', {})
            )

            # Update job status
            job.status = IngestionStatus.EMBEDDING.value
            job.conversation_id = conversation.id
            db.commit()

            logger.info(f"[{job_id}] Conversation created: {conversation.id}")

            # Step 4: NLP Processing (HYBRID: consume upstream or fallback to local)
            nlp_mode = self._detect_nlp_mode(conversation_json)
            logger.info(f"[{job_id}] NLP mode: {nlp_mode}")

            if nlp_mode == 'enriched':
                # v1.1: Consume upstream NLP annotations
                logger.info(f"[{job_id}] Consuming upstream NLP annotations (v1.1)")
                try:
                    await self._consume_upstream_nlp(
                        job_id=job_id,
                        job=job,
                        conversation=conversation,
                        payload=validated_payload,
                        conversation_json=conversation_json
                    )
                except Exception as nlp_error:
                    logger.error(f"[{job_id}] Upstream NLP consumption failed: {nlp_error}")
                    logger.error(traceback.format_exc())
                    # Fallback to local NLP
                    if self.nlp_processor:
                        logger.info(f"[{job_id}] Falling back to local NLP processing...")
                        await self._run_local_nlp(job_id, job, conversation, validated_payload)

            elif nlp_mode == 'legacy' and self.nlp_processor:
                # v1.0: Run local NLP processing
                logger.info(f"[{job_id}] Running local NLP processing (v1.0 fallback)")
                await self._run_local_nlp(job_id, job, conversation, validated_payload)

            else:
                logger.info(f"[{job_id}] NLP processing skipped (not available)")

            # Mark as completed
            job.status = IngestionStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()

            # Calculate processing duration
            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds() * 1000
                job.processing_duration_ms = int(duration)

            db.commit()

            logger.info(f"[{job_id}] Ingestion completed successfully")
            return True

        except Exception as e:
            logger.error(f"[{job_id}] Error processing message: {e}")
            logger.error(traceback.format_exc())

            # Update job with error
            try:
                db = clients.get_db_session()
                if job_id:
                    job = db.query(IngestionJob).filter_by(job_id=job_id).first()
                    if job:
                        job.status = IngestionStatus.FAILED.value
                        job.error_message = str(e)
                        job.error_stack = traceback.format_exc()
                        job.last_error_at = datetime.utcnow()
                        db.commit()
            except Exception as db_error:
                logger.error(f"Error updating job status: {db_error}")

            return False

    async def run(self):
        """Run the consumer loop"""
        self.running = True
        await self.ensure_consumer_group()

        logger.info(f"Starting Redis Stream consumer: {self.consumer_name}")
        logger.info(f"Stream: {self.stream_name}, Group: {self.group_name}")

        while self.running:
            try:
                # Read messages from stream
                messages = self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_name: '>'},
                    count=self.batch_size,
                    block=self.block_ms
                )

                if not messages:
                    # No messages, continue loop
                    await asyncio.sleep(0.1)
                    continue

                # Process each message
                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            message_id_str = message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id

                            success = await self.process_message(message_id_str, message_data)

                            if success:
                                # Acknowledge message
                                self.redis.xack(self.stream_name, self.group_name, message_id)
                                logger.debug(f"Acknowledged message: {message_id_str}")
                            else:
                                logger.warning(f"Failed to process message: {message_id_str}")
                                # Message will be retried by another consumer or deadletter queue

                        except Exception as e:
                            logger.error(f"Error handling message {message_id}: {e}")
                            continue

            except KeyboardInterrupt:
                logger.info("Received interrupt, stopping consumer...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying

        logger.info("Consumer stopped")

    def stop(self):
        """Stop the consumer"""
        self.running = False

    def _detect_nlp_mode(self, conversation_json: Dict[str, Any]) -> str:
        """
        Detect if payload contains upstream NLP annotations (v1.1) or is legacy (v1.0)

        Returns:
            'enriched' if v1.1 with NLP annotations, 'legacy' otherwise
        """
        has_annotations = SchemaValidator.has_nlp_annotations(conversation_json)
        return 'enriched' if has_annotations else 'legacy'

    async def _consume_upstream_nlp(
        self,
        job_id: str,
        job: IngestionJob,
        conversation: Any,
        payload: Any,
        conversation_json: Dict[str, Any]
    ):
        """
        Consume upstream NLP annotations from transcript service (v1.1)

        Extracts sentiment and entities from segments, aggregates stats,
        and updates conversation metadata.
        """
        segments = conversation_json.get('segments', [])
        analytics = conversation_json.get('analytics', {})

        # Extract segment-level annotations
        sentiments = []
        all_entities = []
        persons = set()

        for seg in segments:
            # Extract sentiment
            sentiment = SchemaValidator.extract_sentiment_from_segment(seg)
            if sentiment:
                sentiments.append({
                    'label': sentiment.get('label'),
                    'score': sentiment.get('score'),
                    'stars': sentiment.get('stars')
                })

            # Extract entities
            entities = SchemaValidator.extract_entities_from_segment(seg)
            for entity in entities:
                all_entities.append(entity)
                if entity.get('type') == 'PERSON':
                    persons.add(entity.get('text'))

        # Get conversation-level analytics
        sentiment_summary = analytics.get('sentiment_summary', {})
        entities_summary = analytics.get('entities_summary', {})

        # Update conversation with extracted topics (top persons)
        if persons:
            await self.storage.update_conversation_topics(
                conversation.id,
                topics=list(persons)[:5]
            )

        # Update job metadata with upstream NLP stats
        job.processing_metadata = {
            'nlp_source': 'upstream_transcript',
            'schema_version': conversation_json.get('schema_version', '1.1'),
            'num_segments_with_sentiment': len(sentiments),
            'num_entities_extracted': len(all_entities),
            'num_persons': len(persons),
            'avg_sentiment_stars': sentiment_summary.get('avg_stars'),
            'overall_sentiment': sentiment_summary.get('overall'),
            'sentiment_distribution': sentiment_summary.get('distribution'),
            'entities_by_type': {
                k: len(v) for k, v in entities_summary.items()
            }
        }

        logger.info(
            f"[{job_id}] Upstream NLP consumed: "
            f"{len(sentiments)} segments with sentiment, "
            f"{len(all_entities)} entities ({len(persons)} persons), "
            f"overall: {sentiment_summary.get('overall', 'N/A')}"
        )

    async def _run_local_nlp(
        self,
        job_id: str,
        job: IngestionJob,
        conversation: Any,
        validated_payload: Any
    ):
        """
        Run local NLP processing (fallback for v1.0 or if upstream fails)

        Executes full NLP pipeline: chunking, embeddings, NER, sentiment.
        """
        try:
            # Convert segments to turns format for NLP
            turns = [
                {
                    'turn': idx,
                    'speaker': seg.display_name if hasattr(seg, 'display_name') else seg.speaker_id,
                    'text': seg.text,
                    'timestamp_ms': seg.start_ms,
                    'confidence': seg.confidence
                }
                for idx, seg in enumerate(validated_payload.segments)
            ]

            # Run NLP pipeline
            nlp_result = await self.nlp_processor.process_conversation(
                conversation_id=conversation.id,
                turns=turns,
                metadata={
                    'job_id': job_id,
                    'external_event_id': validated_payload.external_event_id,
                    'date': validated_payload.meeting_metadata.scheduled_start.isoformat(),
                    'language': validated_payload.primary_language or 'fr'
                }
            )

            # Update conversation with NLP results
            await self.storage.update_conversation_topics(
                conversation.id,
                topics=list(nlp_result.entities.get('PER', []))[:5]  # Top persons as topics
            )

            # Update job metadata with NLP stats
            job.processing_metadata = {
                'nlp_source': 'local_my_rag',
                'num_chunks': nlp_result.num_chunks,
                'num_embeddings': nlp_result.num_embeddings,
                'num_persons': len(nlp_result.persons),
                'avg_sentiment': nlp_result.sentiment_analysis['stats'].get('avg_stars'),
                'nlp_processing_ms': nlp_result.processing_time_ms
            }

            logger.info(
                f"[{job_id}] Local NLP complete: "
                f"{nlp_result.num_chunks} chunks, "
                f"{len(nlp_result.persons)} persons, "
                f"sentiment: {nlp_result.sentiment_analysis['stats'].get('avg_stars'):.1f}"
            )

        except Exception as nlp_error:
            logger.error(f"[{job_id}] Local NLP processing failed: {nlp_error}")
            logger.error(traceback.format_exc())
            # Set flag for partial NLP
            job.processing_metadata = job.processing_metadata or {}
            job.processing_metadata['nlp_partial'] = True
            raise


async def main():
    """Main entry point for consumer"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    consumer = RedisStreamConsumer()
    try:
        await consumer.run()
    finally:
        clients.close_all()


if __name__ == "__main__":
    asyncio.run(main())
