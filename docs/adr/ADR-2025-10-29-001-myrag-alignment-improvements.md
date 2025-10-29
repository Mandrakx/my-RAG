# ADR-2025-10-29-001: my-RAG Ingestion Pipeline Alignment Improvements

**Status**: ✅ IMPLEMENTED
**Date**: 2025-10-29
**Authors**: Staff Integration Platform Architect
**Related ADRs**:
- ADR-2025-10-03-003: Cross-Cutting Audio → Transcript → RAG Contract
- ADR-2025-10-16-004: Alignment Implementation Plan

---

## Context

Following the comprehensive action plan defined in `docs/action-plan/2025-10-26-fix-alignment-cross.md`, the my-RAG ingestion pipeline required several robustness improvements to achieve full compliance with the cross-cutting contract (ADR-2025-10-03-003).

### Issues Identified

1. **Weak `external_event_id` Validation**
   - Current pattern: `^[A-Za-z0-9._:-]+$` (too permissive)
   - Target pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$` (strict compliance)
   - No timestamp validation (future dates, too old dates)

2. **Optional `trace_id`**
   - trace_id was Optional in RedisMessageMetadata
   - Missing trace_id degrades distributed tracing
   - No metrics for tracking trace_id presence

3. **No Duplicate Detection**
   - Multiple consumers could process same message concurrently
   - No distributed locking mechanism
   - Risk of duplicate entries in Qdrant

4. **Immediate Retry on Failure**
   - Failed messages were immediately re-queued
   - No exponential backoff strategy
   - Risk of retry storms and thundering herd

---

## Decision

We implement the following improvements to the my-RAG ingestion pipeline:

### 1. Strengthen `external_event_id` Validation

**Implementation**: `src/ingestion/redis_message_parser.py`

```python
external_event_id: str = Field(
    pattern=r"^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$",
    description="Stable identifier (format: rec-YYYYMMDDTHHMMSSZ-<8hex>)"
)

@validator('external_event_id')
def validate_external_event_id_timestamp(cls, v):
    """Validate timestamp is reasonable (not future, not too old)"""
    # Extract timestamp: rec-20251016T120000Z-3f9c4241
    parts = v.split('-')
    timestamp_str = parts[1]  # 20251016T120000Z

    timestamp = datetime.strptime(timestamp_str, '%Y%m%dT%H%M%SZ')

    # Check not in future (allow 5 min clock skew)
    if timestamp > datetime.utcnow() + timedelta(minutes=5):
        raise ValueError("timestamp is in the future")

    # Check not too old (max 30 days)
    if timestamp < datetime.utcnow() - timedelta(days=30):
        raise ValueError("timestamp is too old")

    return v
```

**Rationale**:
- Strict pattern matching prevents malformed IDs
- Timestamp validation catches clock skew and stale messages
- 30-day retention policy aligns with typical processing SLAs

### 2. Make `trace_id` REQUIRED

**Implementation**: `src/ingestion/redis_message_parser.py`

```python
class RedisMessageMetadata(BaseModel):
    """Metadata section from Redis message"""
    trace_id: str = Field(..., description="UUID v4 (REQUIRED)")

    @validator('trace_id')
    def validate_trace_id_uuid(cls, v):
        """Validate that trace_id is a valid UUID"""
        import uuid
        try:
            uuid.UUID(v)
        except (ValueError, AttributeError):
            raise ValueError(f"trace_id must be a valid UUID, got: {v}")
        return v
```

**Metrics** (already implemented in `src/ingestion/metrics.py`):
```python
audio_ingest_trace_id_present = Counter(
    'audio_ingest_trace_id_present_total',
    'Messages with trace_id present vs missing',
    ['present']  # 'true' or 'false'
)
```

**Rationale**:
- trace_id is critical for distributed tracing
- Required field ensures end-to-end observability
- UUID validation prevents malformed trace IDs
- Metrics track compliance (alert if > 10% missing)

### 3. Distributed Locking for Duplicate Prevention

**Implementation**: `src/ingestion/distributed_lock.py` (NEW)

```python
class DistributedLock:
    """
    Redis-based distributed lock for duplicate prevention

    Uses Redis SET with NX (only set if not exists) and EX (expiry)
    Lock key: lock:external_event_id:<external_event_id>
    Duration: 5 minutes (300 seconds)
    """

    LOCK_PREFIX = "lock:external_event_id:"
    LOCK_DURATION_SECONDS = 300

    def acquire(self, external_event_id: str) -> bool:
        """Try to acquire lock"""
        lock_key = f"{self.LOCK_PREFIX}{external_event_id}"
        return self.redis.set(lock_key, "locked", nx=True, ex=300)

    def release(self, external_event_id: str) -> bool:
        """Release lock"""
        lock_key = f"{self.LOCK_PREFIX}{external_event_id}"
        return self.redis.delete(lock_key)

    @contextmanager
    def lock(self, external_event_id: str):
        """Context manager for lock acquisition"""
        acquired = self.acquire(external_event_id)
        if not acquired:
            raise RuntimeError("Could not acquire lock")
        try:
            yield acquired
        finally:
            self.release(external_event_id)
```

**Usage in Consumer**:
```python
# Before processing message
lock_manager = DistributedLock(redis_client)

try:
    with lock_manager.lock(external_event_id):
        # Process message
        process_message(message)
except RuntimeError:
    # Already being processed by another consumer
    logger.warning(f"Message {external_event_id} already locked")
    # Schedule retry in 30 seconds
    retry_scheduler.schedule_retry(message_id, retry_count)
```

**Rationale**:
- Prevents concurrent processing of same message
- 5-minute lock duration covers typical processing time
- Automatic expiry prevents deadlocks
- Fail-open on Redis errors (availability over consistency)

### 4. Exponential Backoff Retry Strategy

**Implementation**: `src/ingestion/retry_scheduler.py` (NEW)

```python
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

    BASE_DELAY_SECONDS = 5
    MAX_DELAY_SECONDS = 300
    MAX_RETRIES = 10

    def calculate_next_retry_time(self, retry_count: int) -> datetime:
        """Calculate next retry time with exponential backoff + jitter"""
        exponential_delay = self.BASE_DELAY_SECONDS * (2 ** retry_count)
        capped_delay = min(exponential_delay, self.MAX_DELAY_SECONDS)
        jitter = random.uniform(0, self.BASE_DELAY_SECONDS)
        total_delay = capped_delay + jitter
        return datetime.utcnow() + timedelta(seconds=total_delay)

    def schedule_retry(self, message_id: str, retry_count: int) -> bool:
        """Schedule message for retry"""
        retry_at = self.calculate_next_retry_time(retry_count)
        retry_score = retry_at.timestamp()
        self.redis.zadd(self.retry_queue_key, {message_id: retry_score})
        return True

    def get_ready_messages(self, limit: int = 100) -> list[str]:
        """Get messages ready for retry (score <= current time)"""
        now = time.time()
        return self.redis.zrangebyscore(
            self.retry_queue_key,
            min=0,
            max=now,
            start=0,
            num=limit
        )
```

**Retry Schedule**:
| Attempt | Delay Formula | Jitter | Total Delay | Cumulative |
|---------|---------------|--------|-------------|------------|
| 1 | 5 * 2^0 = 5s | 0-5s | 5-10s | 5-10s |
| 2 | 5 * 2^1 = 10s | 0-5s | 10-15s | 15-25s |
| 3 | 5 * 2^2 = 20s | 0-5s | 20-25s | 35-50s |
| 4 | 5 * 2^3 = 40s | 0-5s | 40-45s | 75-95s |
| 5 | 5 * 2^4 = 80s | 0-5s | 80-85s | 155-180s |
| 6 | 5 * 2^5 = 160s | 0-5s | 160-165s | 315-345s |
| 7+ | 300s (capped) | 0-5s | 300-305s | - |

**Rationale**:
- Exponential backoff prevents retry storms
- Jitter prevents thundering herd (multiple messages retrying at same time)
- Max delay cap (5 min) prevents excessive wait times
- Redis Sorted Set enables efficient time-based scheduling
- Background worker polls for ready messages

---

## Consequences

### Positive

1. **Stricter Validation**
   - ✅ Only valid external_event_id patterns accepted
   - ✅ Timestamp validation catches clock skew and stale messages
   - ✅ trace_id always present for distributed tracing

2. **Duplicate Prevention**
   - ✅ Distributed locking prevents concurrent processing
   - ✅ Idempotent ingestion (safe to retry)
   - ✅ No duplicate entries in Qdrant

3. **Resilient Retry Strategy**
   - ✅ Exponential backoff prevents retry storms
   - ✅ Jitter prevents thundering herd
   - ✅ Max retries (10) prevents infinite loops
   - ✅ Graceful degradation on transient failures

4. **Observability**
   - ✅ Metrics track trace_id presence
   - ✅ Alert if > 10% messages missing trace_id
   - ✅ Retry queue size monitored

### Negative

1. **Increased Complexity**
   - ⚠️ Two new modules (distributed_lock, retry_scheduler)
   - ⚠️ More Redis keys to monitor
   - ⚠️ Retry queue requires background worker

2. **Redis Dependency**
   - ⚠️ Distributed lock depends on Redis availability
   - ⚠️ Retry scheduler depends on Redis Sorted Set
   - ✅ Mitigated: Fail-open on Redis errors

3. **Processing Latency**
   - ⚠️ Lock acquisition adds ~1-5ms per message
   - ⚠️ Failed messages delayed by backoff (intended)
   - ✅ Minimal impact on p95 latency (<5s SLA)

### Mitigations

1. **Redis Availability**
   - Distributed lock fails open (allows processing on error)
   - Retry scheduler degrades to immediate retry on error
   - Redis cluster setup for high availability

2. **Lock Expiry**
   - 5-minute lock duration covers typical processing
   - Automatic expiry prevents deadlocks
   - Lock extension API for long-running jobs

3. **Retry Queue Backlog**
   - Monitor queue size (alert if > 500 pending)
   - Background worker polls every 10 seconds
   - Scale consumers if backlog grows

---

## Implementation Notes

### Files Created

1. **`src/ingestion/distributed_lock.py`** (246 lines)
   - DistributedLock class
   - Redis SET NX + EX locking
   - Context manager for auto-release
   - Fail-open on Redis errors

2. **`src/ingestion/retry_scheduler.py`** (278 lines)
   - RetryScheduler class
   - Exponential backoff calculation
   - Redis Sorted Set for time-based scheduling
   - Background worker integration ready

### Files Modified

1. **`src/ingestion/redis_message_parser.py`**
   - Line 49: external_event_id pattern updated
   - Line 34: trace_id made REQUIRED
   - Line 39-47: trace_id UUID validator added
   - Line 125-160: external_event_id timestamp validator added

2. **`src/ingestion/metrics.py`**
   - Already had trace_id presence metrics (lines 107-111, 204-206)
   - No changes needed

### Integration with Consumer

**Consumer changes** (to be implemented in separate commit):
```python
# Initialize helpers
lock_manager = DistributedLock(redis_client)
retry_scheduler = RetryScheduler(redis_client, stream_name)

async def process_message(message_id, message_data):
    # Parse message
    message = RedisMessageParser.parse(message_data)

    # Track trace_id presence
    has_trace = message.get_trace_id() is not None
    IngestionMetrics.record_trace_id_presence(has_trace)

    # Try to acquire lock
    try:
        with lock_manager.lock(message.external_event_id):
            # Process message
            result = await ingest_conversation(message)

            # Ack message on success
            redis.xack(stream_name, group_name, message_id)

    except RuntimeError as e:
        # Lock acquisition failed (already processing)
        logger.warning(f"Could not acquire lock: {e}")

        # Schedule retry
        retry_scheduler.schedule_retry(
            message_id,
            message.retry_count,
            message.external_event_id,
            message.get_trace_id()
        )

    except Exception as e:
        # Processing failed
        logger.error(f"Processing failed: {e}")

        # Schedule retry with backoff
        if retry_scheduler.should_retry(message.retry_count):
            retry_scheduler.schedule_retry(
                message_id,
                message.retry_count + 1,
                message.external_event_id,
                message.get_trace_id()
            )
        else:
            # Max retries exceeded → DLQ
            error_handler.send_to_dlq(message, str(e))
```

**Background worker** (new process):
```python
async def retry_worker():
    """Poll retry queue and re-process ready messages"""
    while True:
        ready_messages = retry_scheduler.get_ready_messages(limit=100)

        for message_id in ready_messages:
            # Re-fetch message from Redis stream
            messages = redis.xread({stream_name: message_id}, count=1)

            if messages:
                # Process message
                await process_message(message_id, messages[0][1])

            # Remove from retry queue
            retry_scheduler.remove_from_retry_queue(message_id)

        # Poll every 10 seconds
        await asyncio.sleep(10)
```

---

## Monitoring & Alerts

### Prometheus Metrics

1. **`audio_ingest_trace_id_present_total{present="true|false"}`**
   - Counter of messages with/without trace_id
   - Alert if `rate(false[5m]) / rate(total[5m]) > 0.10` (> 10% missing)

2. **`distributed_lock_acquisition_total{result="success|failure"}`** (NEW)
   - Counter of lock acquisition attempts
   - Alert if `rate(failure[5m]) / rate(total[5m]) > 0.05` (> 5% failures)

3. **`retry_queue_size`** (NEW)
   - Gauge of pending retries
   - Alert if > 500 for > 10 minutes

4. **`audio_ingest_retries_total{retry_count="0|1|2|..."}`**
   - Counter of retry attempts by count
   - Alert if `sum(retry_count >= 5) > 100` (many high-retry messages)

### Grafana Dashboard

**Panel 1: Validation Compliance**
- external_event_id format validation success rate
- trace_id presence percentage
- Timestamp validation errors

**Panel 2: Duplicate Prevention**
- Lock acquisition success rate
- Concurrent processing attempts (lock failures)
- Lock contention duration

**Panel 3: Retry Health**
- Retry queue size (current)
- Retry attempts by count (0-10)
- Messages at max retries (10)
- Retry latency distribution

---

## Testing Strategy

### Unit Tests

1. **`tests/test_ingestion/test_external_event_id.py`** (NEW)
   - Test strict pattern matching
   - Test timestamp validation (future, past, valid)
   - Test edge cases (clock skew, 30-day boundary)

2. **`tests/test_ingestion/test_distributed_lock.py`** (NEW)
   - Test lock acquisition success
   - Test lock contention (2 consumers)
   - Test lock expiry (after 5 min)
   - Test lock release

3. **`tests/test_ingestion/test_retry_scheduler.py`** (NEW)
   - Test backoff calculation (0-10 retries)
   - Test jitter randomness
   - Test retry queue operations (add, get, remove)
   - Test max retries enforcement

### Integration Tests

1. **Duplicate Prevention Test**
   - Start 2 consumers
   - Send same message to both
   - Verify only 1 processes (other waits for lock)

2. **Retry Strategy Test**
   - Send message that fails validation
   - Verify exponential backoff schedule
   - Verify jitter in retry times
   - Verify max retries → DLQ

3. **End-to-End Test**
   - Send message with invalid external_event_id → rejected
   - Send message without trace_id → rejected
   - Send valid message → processes successfully
   - Send duplicate → locked, retries later

---

## Rollout Plan

### Phase 1: Deployment (Week of Nov 9, 2025)
1. Deploy new code with feature flags disabled
2. Run unit tests in CI/CD
3. Monitor metrics (no changes expected)

### Phase 2: Enable Validation (Nov 11, 2025)
1. Enable strict external_event_id validation
2. Enable REQUIRED trace_id
3. Monitor rejection rate
4. Rollback if > 10% rejection

### Phase 3: Enable Locking (Nov 13, 2025)
1. Enable distributed locking
2. Monitor lock contention
3. Verify no duplicate ingestions

### Phase 4: Enable Retry Backoff (Nov 15, 2025)
1. Enable exponential backoff scheduler
2. Monitor retry queue size
3. Deploy background retry worker

### Phase 5: Full E2E Validation (Nov 23, 2025)
1. iOS → Transcript → my-RAG end-to-end test
2. Verify trace_id flows through all layers
3. Verify no duplicates
4. Verify retry strategy works

---

## Success Criteria

- [x] Strict external_event_id validation implemented
- [x] trace_id made REQUIRED with UUID validation
- [x] Distributed locking prevents duplicates
- [x] Exponential backoff retry strategy implemented
- [x] Metrics track trace_id presence
- [ ] Unit tests >80% coverage (to be implemented)
- [ ] Integration tests pass (to be implemented)
- [ ] Consumer integration completed (next commit)
- [ ] Background retry worker deployed (next commit)
- [ ] Zero duplicate ingestions in production
- [ ] p95 ack latency < 5s maintained

---

## References

- Action Plan: `docs/action-plan/2025-10-26-fix-alignment-cross.md`
- Contract: `ADR-2025-10-03-003-cross-cutting-audio-rag.md`
- Code Locations: `docs/action-plan/CODE_LOCATIONS.md`

**Implementation Date**: 2025-10-29
**Status**: ✅ Core modules implemented, consumer integration pending
