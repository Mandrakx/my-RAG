"""
Retry scheduler with exponential backoff for failed message processing

Implements exponential backoff strategy with jitter to prevent retry storms
and thundering herd scenarios.

Aligned with ADR-2025-10-29-001 (my-RAG alignment improvements)
"""

import logging
import random
import time
from typing import Optional
from datetime import datetime, timedelta
import redis

logger = logging.getLogger(__name__)


class RetryScheduler:
    """
    Exponential backoff retry scheduler using Redis Sorted Set

    Strategy:
        - Formula: min(max_delay, base_delay * 2^retry_count) + jitter
        - Base delay: 5 seconds
        - Max delay: 300 seconds (5 minutes)
        - Jitter: random(0, base_delay)
        - Max retries: 10

    Redis Sorted Set:
        - Key: retry_queue:<stream_name>
        - Score: Unix timestamp when message should be retried
        - Member: message_id
    """

    # Retry configuration
    BASE_DELAY_SECONDS = 5
    MAX_DELAY_SECONDS = 300  # 5 minutes
    MAX_RETRIES = 10

    def __init__(
        self,
        redis_client: redis.Redis,
        stream_name: str,
        base_delay: Optional[int] = None,
        max_delay: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize retry scheduler

        Args:
            redis_client: Redis client instance
            stream_name: Stream name (for retry queue key)
            base_delay: Base delay in seconds (defaults to BASE_DELAY_SECONDS)
            max_delay: Max delay in seconds (defaults to MAX_DELAY_SECONDS)
            max_retries: Max retry attempts (defaults to MAX_RETRIES)
        """
        self.redis = redis_client
        self.stream_name = stream_name
        self.retry_queue_key = f"retry_queue:{stream_name}"

        self.base_delay = base_delay or self.BASE_DELAY_SECONDS
        self.max_delay = max_delay or self.MAX_DELAY_SECONDS
        self.max_retries = max_retries or self.MAX_RETRIES

    def calculate_next_retry_time(
        self,
        retry_count: int,
        base_delay: Optional[int] = None
    ) -> datetime:
        """
        Calculate next retry time with exponential backoff + jitter

        Formula: min(max_delay, base_delay * 2^retry_count) + jitter
        Jitter: random(0, base_delay)

        Args:
            retry_count: Current retry count (0-based)
            base_delay: Override base delay (defaults to self.base_delay)

        Returns:
            UTC datetime when message should be retried
        """
        base = base_delay or self.base_delay

        # Calculate exponential backoff
        exponential_delay = base * (2 ** retry_count)

        # Cap at max_delay
        capped_delay = min(exponential_delay, self.max_delay)

        # Add jitter: random(0, base_delay)
        jitter = random.uniform(0, base)
        total_delay = capped_delay + jitter

        # Calculate retry timestamp
        retry_at = datetime.utcnow() + timedelta(seconds=total_delay)

        logger.debug(
            f"Calculated retry delay: retry_count={retry_count}, "
            f"exponential={exponential_delay}s, capped={capped_delay}s, "
            f"jitter={jitter:.2f}s, total={total_delay:.2f}s, retry_at={retry_at}"
        )

        return retry_at

    def schedule_retry(
        self,
        message_id: str,
        retry_count: int,
        external_event_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> bool:
        """
        Schedule message for retry at calculated time

        Args:
            message_id: Redis Stream message ID
            retry_count: Current retry count
            external_event_id: Optional external event ID (for logging)
            trace_id: Optional trace ID (for logging)

        Returns:
            True if scheduled successfully, False otherwise
        """
        if retry_count >= self.max_retries:
            logger.error(
                f"Max retries ({self.max_retries}) exceeded for message {message_id} "
                f"(external_event_id={external_event_id}, trace_id={trace_id})"
            )
            return False

        retry_at = self.calculate_next_retry_time(retry_count)
        retry_score = retry_at.timestamp()

        try:
            # Add to sorted set: ZADD retry_queue score member
            self.redis.zadd(self.retry_queue_key, {message_id: retry_score})

            logger.info(
                f"Scheduled retry for message {message_id} at {retry_at} "
                f"(retry_count={retry_count}, external_event_id={external_event_id}, "
                f"trace_id={trace_id})"
            )

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error scheduling retry for {message_id}: {e}")
            return False

    def get_ready_messages(self, limit: int = 100) -> list[str]:
        """
        Get message IDs ready for retry (score <= current time)

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of message IDs ready for retry
        """
        now = time.time()

        try:
            # ZRANGEBYSCORE retry_queue -inf now LIMIT 0 limit
            ready_messages = self.redis.zrangebyscore(
                self.retry_queue_key,
                min=0,
                max=now,
                start=0,
                num=limit
            )

            if ready_messages:
                logger.info(
                    f"Found {len(ready_messages)} messages ready for retry "
                    f"(limit={limit})"
                )

            return [msg.decode('utf-8') if isinstance(msg, bytes) else msg
                    for msg in ready_messages]

        except redis.RedisError as e:
            logger.error(f"Redis error getting ready messages: {e}")
            return []

    def remove_from_retry_queue(self, message_id: str) -> bool:
        """
        Remove message from retry queue (after successful retry or max retries)

        Args:
            message_id: Message ID to remove

        Returns:
            True if removed, False otherwise
        """
        try:
            removed = self.redis.zrem(self.retry_queue_key, message_id)

            if removed:
                logger.debug(f"Removed {message_id} from retry queue")
            else:
                logger.warning(f"Message {message_id} not found in retry queue")

            return bool(removed)

        except redis.RedisError as e:
            logger.error(f"Redis error removing {message_id} from retry queue: {e}")
            return False

    def get_retry_queue_size(self) -> int:
        """
        Get number of messages in retry queue

        Returns:
            Number of pending retries
        """
        try:
            size = self.redis.zcard(self.retry_queue_key)
            return int(size)

        except redis.RedisError as e:
            logger.error(f"Redis error getting retry queue size: {e}")
            return 0

    def get_message_retry_time(self, message_id: str) -> Optional[datetime]:
        """
        Get scheduled retry time for message

        Args:
            message_id: Message ID

        Returns:
            Scheduled retry datetime, or None if not in queue
        """
        try:
            score = self.redis.zscore(self.retry_queue_key, message_id)

            if score is None:
                return None

            return datetime.utcfromtimestamp(float(score))

        except redis.RedisError as e:
            logger.error(f"Redis error getting retry time for {message_id}: {e}")
            return None

    def should_retry(self, retry_count: int) -> bool:
        """
        Check if message should be retried based on retry count

        Args:
            retry_count: Current retry count

        Returns:
            True if should retry, False if max retries exceeded
        """
        return retry_count < self.max_retries

    def clear_retry_queue(self) -> bool:
        """
        Clear all messages from retry queue (for testing/maintenance)

        Returns:
            True if cleared, False otherwise
        """
        try:
            self.redis.delete(self.retry_queue_key)
            logger.info(f"Cleared retry queue: {self.retry_queue_key}")
            return True

        except redis.RedisError as e:
            logger.error(f"Redis error clearing retry queue: {e}")
            return False


def create_retry_scheduler(
    redis_client: redis.Redis,
    stream_name: str
) -> RetryScheduler:
    """
    Factory function to create RetryScheduler instance

    Args:
        redis_client: Redis client
        stream_name: Stream name

    Returns:
        RetryScheduler instance
    """
    return RetryScheduler(redis_client, stream_name)
