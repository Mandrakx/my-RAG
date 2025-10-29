"""
Distributed locking mechanism using Redis for duplicate message prevention

Implements Redis-based distributed locking to prevent concurrent processing
of the same external_event_id across multiple consumer instances.

Aligned with ADR-2025-10-29-001 (my-RAG alignment improvements)
"""

import logging
from typing import Optional
from contextlib import contextmanager
import redis

logger = logging.getLogger(__name__)


class DistributedLock:
    """
    Redis-based distributed lock for duplicate prevention

    Uses Redis SET with NX (only set if not exists) and EX (expiry) options
    to implement a distributed lock mechanism.

    Lock key format: lock:external_event_id:<external_event_id>
    Lock duration: 5 minutes (300 seconds)
    """

    # Lock configuration
    LOCK_PREFIX = "lock:external_event_id:"
    LOCK_DURATION_SECONDS = 300  # 5 minutes
    LOCK_VALUE = "locked"  # Simple value to indicate lock is held

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize distributed lock

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def _get_lock_key(self, external_event_id: str) -> str:
        """
        Get Redis key for lock

        Args:
            external_event_id: External event ID to lock

        Returns:
            Redis lock key
        """
        return f"{self.LOCK_PREFIX}{external_event_id}"

    def acquire(
        self,
        external_event_id: str,
        duration_seconds: Optional[int] = None
    ) -> bool:
        """
        Try to acquire lock for external_event_id

        Args:
            external_event_id: External event ID to lock
            duration_seconds: Lock duration (defaults to LOCK_DURATION_SECONDS)

        Returns:
            True if lock was acquired, False if already locked
        """
        lock_key = self._get_lock_key(external_event_id)
        duration = duration_seconds or self.LOCK_DURATION_SECONDS

        try:
            # SET key value NX EX duration
            # NX: Only set if key doesn't exist
            # EX: Set expiry time in seconds
            acquired = self.redis.set(
                lock_key,
                self.LOCK_VALUE,
                nx=True,
                ex=duration
            )

            if acquired:
                logger.info(
                    f"Acquired lock for {external_event_id} "
                    f"(duration={duration}s, key={lock_key})"
                )
            else:
                logger.warning(
                    f"Failed to acquire lock for {external_event_id} "
                    f"(already locked by another consumer, key={lock_key})"
                )

            return bool(acquired)

        except redis.RedisError as e:
            logger.error(f"Redis error acquiring lock for {external_event_id}: {e}")
            # On Redis errors, fail open (allow processing)
            # This prevents Redis outages from blocking all ingestion
            return True

    def release(self, external_event_id: str) -> bool:
        """
        Release lock for external_event_id

        Args:
            external_event_id: External event ID to unlock

        Returns:
            True if lock was released, False otherwise
        """
        lock_key = self._get_lock_key(external_event_id)

        try:
            deleted = self.redis.delete(lock_key)

            if deleted:
                logger.info(f"Released lock for {external_event_id} (key={lock_key})")
            else:
                logger.warning(
                    f"Lock not found for {external_event_id} "
                    f"(may have expired, key={lock_key})"
                )

            return bool(deleted)

        except redis.RedisError as e:
            logger.error(f"Redis error releasing lock for {external_event_id}: {e}")
            return False

    def extend(
        self,
        external_event_id: str,
        additional_seconds: int
    ) -> bool:
        """
        Extend lock duration (if still held)

        Args:
            external_event_id: External event ID
            additional_seconds: Additional seconds to extend lock

        Returns:
            True if lock was extended, False otherwise
        """
        lock_key = self._get_lock_key(external_event_id)

        try:
            # Get current TTL
            ttl = self.redis.ttl(lock_key)

            if ttl <= 0:
                logger.warning(f"Lock not found or expired for {external_event_id}")
                return False

            # Extend expiry
            new_ttl = ttl + additional_seconds
            extended = self.redis.expire(lock_key, new_ttl)

            if extended:
                logger.info(
                    f"Extended lock for {external_event_id} "
                    f"(+{additional_seconds}s, new_ttl={new_ttl}s)"
                )

            return bool(extended)

        except redis.RedisError as e:
            logger.error(f"Redis error extending lock for {external_event_id}: {e}")
            return False

    def is_locked(self, external_event_id: str) -> bool:
        """
        Check if external_event_id is currently locked

        Args:
            external_event_id: External event ID

        Returns:
            True if locked, False otherwise
        """
        lock_key = self._get_lock_key(external_event_id)

        try:
            exists = self.redis.exists(lock_key)
            return bool(exists)

        except redis.RedisError as e:
            logger.error(f"Redis error checking lock for {external_event_id}: {e}")
            # On error, assume not locked (fail open)
            return False

    @contextmanager
    def lock(
        self,
        external_event_id: str,
        duration_seconds: Optional[int] = None
    ):
        """
        Context manager for acquiring and releasing locks

        Usage:
            with lock_manager.lock("rec-20251029-12345678"):
                # Process message
                pass

        Args:
            external_event_id: External event ID to lock
            duration_seconds: Lock duration

        Yields:
            True if lock was acquired, False otherwise

        Raises:
            RuntimeError if lock cannot be acquired
        """
        acquired = self.acquire(external_event_id, duration_seconds)

        if not acquired:
            raise RuntimeError(
                f"Could not acquire lock for {external_event_id} "
                "(message already being processed)"
            )

        try:
            yield acquired
        finally:
            self.release(external_event_id)


def create_distributed_lock(redis_client: redis.Redis) -> DistributedLock:
    """
    Factory function to create DistributedLock instance

    Args:
        redis_client: Redis client

    Returns:
        DistributedLock instance
    """
    return DistributedLock(redis_client)
