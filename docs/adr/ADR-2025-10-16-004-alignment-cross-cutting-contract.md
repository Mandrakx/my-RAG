# ADR-2025-10-16-004-alignment-cross-cutting-contract

## Status
Accepted — 2025-10-16

## Context

Following the establishment of the cross-cutting contract for Audio → Transcript → RAG integration (ADR-2025-10-03-003), a detailed code review of the `my-RAG` ingestion pipeline revealed significant gaps between the documented contract and the actual implementation.

### Key Contract Documents
- `docs/adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md` - Cross-cutting contract
- `docs/design/audio-redis-message-schema.json` - Redis message format
- `docs/design/conversation-payload.schema.json` - Conversation payload schema
- `docs/design/cross-cutting-concern.md` - Integration requirements
- `docs/api/transcript-api.openapi.yaml` - API specification

### Identified Gaps

**Critical (Blocking Integration)**:
1. **Redis Message Format Mismatch**: Consumer expects `{job_id, bucket, object_key}` but contract specifies `{external_event_id, package_uri, checksum, schema_version, ...}`
2. **Stream/Group Names**: Using `ingestion:events` / `rag-processors` instead of documented `audio.ingestion` / `rag-ingestion`
3. **Missing trace_id**: No distributed tracing support (trace_id not extracted or propagated)
4. **Missing Checksum Validation**: No verification of `sha256:...` checksums from Redis messages or tar.gz internal checksums

**Medium (Quality/Observability)**:
5. **external_event_id Pattern**: Validation too permissive (`^[A-Za-z0-9._:-]+$` vs strict `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`)
6. **No Dead Letter Queue**: Failed messages not routed to DLQ with remediation hints
7. **Missing Prometheus Metrics**: No instrumentation for SLAs (`audio_ingest_ack_latency_seconds`, `audio_ingest_failures_total`, etc.)

**Low (Future Enhancement)**:
8. **MinIO Path Pattern**: Not enforcing `drop/<YYYY>/<MM>/<DD>/<external_event_id>.tar.gz` structure
9. **SLA Monitoring**: No tracking of 5s ack / 60s processing kickoff targets
10. **Archive Validation**: Partial validation of tar.gz structure (checksums.sha256 not verified)

### Business Impact
- **Transcript service cannot integrate** until Redis message format aligns
- **No end-to-end tracing** across iOS → Transcript → RAG pipeline
- **Data integrity risk** without checksum validation
- **Difficult troubleshooting** without standardized error codes and DLQ

## Decision

Align the `my-RAG` ingestion pipeline with ADR-2025-10-03-003 contract by implementing the following changes in priority order:

### Phase 1: Critical Fixes (Blocking - Week 1)
1. **Update Redis Message Parser** (`consumer.py`)
   - Parse new message format: `{external_event_id, package_uri, checksum, schema_version, retry_count, produced_at, producer, priority, metadata}`
   - Extract `package_uri` (format: `minio://bucket/path`) and parse into bucket + object key
   - Extract and propagate `metadata.trace_id` for distributed tracing

2. **Update Redis Configuration** (`config.py`)
   - Change stream name: `ingestion:events` → `audio.ingestion`
   - Change consumer group: `rag-processors` → `rag-ingestion`
   - Add DLQ stream: `audio.ingestion.deadletter`

3. **Implement Checksum Validation** (`storage.py`, new `checksum_validator.py`)
   - Validate Redis message checksum format: `^sha256:[a-f0-9]{64}$`
   - Verify tar.gz file checksum after download
   - Verify internal `checksums.sha256` file against extracted files

4. **Strengthen external_event_id Validation** (`transcript_validator.py`)
   - Update pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
   - Add format validation: ISO8601 timestamp + 8-char hex UUID

### Phase 2: Observability & Quality (Week 2)
5. **Add Distributed Tracing** (`consumer.py`, `storage.py`, logging config)
   - Extract `trace_id` from Redis metadata
   - Propagate in all logs (JSON structured logging)
   - Add to Qdrant metadata
   - Include in database job records

6. **Implement Dead Letter Queue** (`consumer.py`, new `error_handler.py`)
   - Route failed messages to `audio.ingestion.deadletter`
   - Include standardized error codes: `validation_error`, `checksum_mismatch`, `processing_failure`, etc.
   - Add remediation hints in DLQ payload

7. **Add Prometheus Instrumentation** (new `metrics.py`)
   - `audio_ingest_ack_latency_seconds` (histogram, buckets: 0.5, 1, 2, 3, 5, 10)
   - `audio_ingest_failures_total{reason="..."}` (counter)
   - `audio_ingest_messages_inflight` (gauge)
   - `audio_ingest_validation_duration_seconds` (summary)
   - `audio_ingest_retries_total` (counter)

### Phase 3: Enhanced Validation (Week 3)
8. **MinIO Path Enforcement** (`storage.py`)
   - Parse and validate path pattern: `drop/<YYYY>/<MM>/<DD>/<external_event_id>.tar.gz`
   - Extract date from path and cross-validate with conversation metadata

9. **Archive Structure Validation** (new `archive_validator.py`)
   - Verify tar.gz structure: root folder = `external_event_id`
   - Ensure mandatory files: `conversation.json`, `checksums.sha256`
   - Validate optional directories: `media/`, `artifacts/`, `logs/`
   - Verify no files exceed 2GB, total < 5GB

10. **SLA Monitoring & Alerts** (Prometheus alerts config)
    - Alert: Ack latency p95 > 3s (warning), > 5s (critical)
    - Alert: Validation failure rate > 5% over 15 min
    - Alert: Redis pending entries > 500 for > 10 min

## Rationale

### Why Now?
- Transcript service is ready to deliver packages in the documented format
- Current implementation blocks integration testing
- Early alignment prevents rework and data loss in production

### Why This Approach?
- **Phased rollout** minimizes risk and allows incremental testing
- **Critical fixes first** unblocks Transcript integration immediately
- **Observability second** ensures we can monitor and troubleshoot production
- **Enhanced validation last** provides defense-in-depth but not blocking

### Why Not Alternative Approaches?
- **Big Bang Rewrite**: Too risky, would delay integration by weeks
- **Gradual Schema Evolution**: Would require maintaining two parallel formats
- **Relaxing Contract Requirements**: Would compromise data integrity and observability

## Alternatives Considered

### Option 1: Maintain Backward Compatibility
**Description**: Support both old format (`job_id, bucket, object_key`) and new format (`external_event_id, package_uri, checksum`)

**Pros**:
- No breaking changes for existing producers
- Gradual migration path
- Reduced coordination overhead

**Cons**:
- Increased code complexity (dual parsers)
- No existing producers using old format (greenfield integration)
- Delays achieving full contract compliance
- Technical debt accumulation

**Verdict**: ❌ Rejected - No existing producers to maintain compatibility with

### Option 2: Wait for Transcript to Adapt to Current Format
**Description**: Ask Transcript service to emit messages in current my-RAG format

**Pros**:
- No code changes in my-RAG
- Immediate integration possible

**Cons**:
- Violates documented cross-cutting contract (ADR-2025-10-03-003)
- Pushes complexity upstream to Transcript
- Misses opportunity to add observability (trace_id, checksums)
- No alignment with industry best practices (checksums, DLQ, metrics)

**Verdict**: ❌ Rejected - Violates architectural contract and governance

### Option 3: Hybrid Approach (Selected)
**Description**: Three-phase implementation prioritizing critical blocking issues

**Pros**:
- Unblocks integration immediately (Phase 1)
- Incremental risk reduction
- Allows testing between phases
- Achieves full compliance within 3 weeks

**Cons**:
- Requires careful coordination of deployments
- Some technical debt remains until Phase 3 complete

**Verdict**: ✅ **Selected** - Best balance of speed, risk, and quality

## Consequences

### Positive
- **Enables Transcript Integration**: Phase 1 unblocks end-to-end pipeline testing
- **Improved Observability**: Distributed tracing (trace_id) across iOS → Transcript → RAG
- **Data Integrity**: Checksum validation prevents silent corruption
- **Better Error Handling**: DLQ with standardized error codes and remediation hints
- **SLA Compliance**: Prometheus metrics enable monitoring of 5s ack / 60s kickoff targets
- **Future-Proof**: Full alignment with documented contract reduces future rework

### Negative
- **Short-Term Development Overhead**: ~3 weeks of focused engineering effort
- **Deployment Coordination**: Requires synchronized deployment with Transcript service
- **Testing Burden**: Each phase requires integration testing with Transcript
- **Monitoring Setup**: Requires Prometheus/Grafana infrastructure (already planned)

### Neutral
- **No Breaking Changes for Users**: Changes are internal to ingestion pipeline
- **Schema Compatibility**: conversation-payload.schema.json remains unchanged
- **Database Schema**: No migrations required (trace_id fits in existing metadata fields)

## Implementation

### Action Plan

#### Phase 1: Critical Fixes (Week 1) - Priority: P0
1. **Day 1-2**: Update `config.py` Redis stream/group names
   - File: `src/ingestion/config.py:28-29`
   - Change: `redis_stream_name = "audio.ingestion"`, `redis_consumer_group = "rag-ingestion"`
   - Add: `redis_dlq_stream = "audio.ingestion.deadletter"`

2. **Day 2-3**: Create `redis_message_parser.py` for new message format
   - File: `src/ingestion/redis_message_parser.py` (new)
   - Parse: `external_event_id`, `package_uri`, `checksum`, `schema_version`, `metadata.trace_id`
   - Validate: Message schema against `audio-redis-message-schema.json`

3. **Day 3-4**: Update `consumer.py` message processing
   - File: `src/ingestion/consumer.py:79-104`
   - Replace: Parse new message format using `RedisMessageParser`
   - Extract: `trace_id` and add to logging context
   - Update: Database job records to include `trace_id`, `checksum`, `schema_version`

4. **Day 4-5**: Implement checksum validation
   - File: `src/ingestion/checksum_validator.py` (new)
   - Method: `validate_redis_checksum(message)` - validate format `sha256:...`
   - Method: `validate_tarball_checksum(file_path, expected_checksum)` - verify downloaded file
   - Method: `validate_internal_checksums(extracted_dir)` - verify `checksums.sha256`
   - Integrate: Call from `consumer.py` after download (line 138)

5. **Day 5**: Strengthen `external_event_id` validation
   - File: `src/ingestion/transcript_validator.py:127`
   - Update pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
   - Add validator: Parse and validate ISO8601 timestamp component

#### Phase 2: Observability (Week 2) - Priority: P1
6. **Day 6-7**: Implement distributed tracing
   - File: `src/ingestion/consumer.py` (throughout)
   - Add: `trace_id` to all log statements (structured JSON logging)
   - Update: `storage.py` to include `trace_id` in Qdrant metadata
   - Update: Database models to persist `trace_id` in job metadata

7. **Day 7-8**: Implement Dead Letter Queue
   - File: `src/ingestion/error_handler.py` (new)
   - Method: `publish_to_dlq(message, error_code, error_message, remediation_hint)`
   - Error codes: `validation_error`, `checksum_mismatch`, `processing_failure`, `duplicate_event`, etc.
   - Integrate: Catch exceptions in `consumer.py` and route to DLQ

8. **Day 8-10**: Add Prometheus instrumentation
   - File: `src/ingestion/metrics.py` (new)
   - Metrics: Define all counters, histograms, gauges per specification
   - File: `src/ingestion/consumer.py` (instrument)
   - Instrument: Measure ack latency, validation duration, failure counts
   - File: `docker-compose.yml` (update)
   - Add: Prometheus + Grafana services with pre-configured dashboards

#### Phase 3: Enhanced Validation (Week 3) - Priority: P2
9. **Day 11-12**: Enforce MinIO path pattern
   - File: `src/ingestion/storage.py`
   - Add: Parse `package_uri` and validate path format `drop/<YYYY>/<MM>/<DD>/<external_event_id>.tar.gz`
   - Add: Cross-validate extracted date with `conversation.json` metadata

10. **Day 12-13**: Archive structure validation
    - File: `src/ingestion/archive_validator.py` (new)
    - Validate: Root folder name matches `external_event_id`
    - Validate: Mandatory files present (`conversation.json`, `checksums.sha256`)
    - Validate: File size constraints (individual < 2GB, total < 5GB)

11. **Day 13-14**: SLA monitoring & alerts
    - File: `prometheus/alerts.yml` (new)
    - Define: Alert rules for ack latency, failure rate, queue depth
    - File: `grafana/dashboards/ingestion-sla.json` (new)
    - Create: Dashboard showing SLA compliance metrics

12. **Day 14-15**: Integration testing & documentation
    - Test: End-to-end with Transcript service (all phases)
    - Document: Update `docs/ingestion/README.md` with new message format
    - Document: Create runbook `docs/operations/ingestion-troubleshooting.md`

### Teams Impacted
- **RAG Platform Team** (my-RAG): Primary implementer
- **Transcript Team**: Coordination for integration testing
- **iOS Team**: Visibility into end-to-end tracing
- **Platform SRE**: Prometheus/Grafana setup, alert configuration

### Timeline
- **Week 1 (Oct 16-20)**: Phase 1 - Critical fixes (P0) ✅ Unblocks integration
- **Week 2 (Oct 21-27)**: Phase 2 - Observability (P1) ✅ Production-ready monitoring
- **Week 3 (Oct 28-Nov 3)**: Phase 3 - Enhanced validation (P2) ✅ Full compliance
- **Completion Target**: November 3, 2025

### Testing Strategy
- **Unit Tests**: Each new module (`redis_message_parser`, `checksum_validator`, `error_handler`, etc.)
- **Integration Tests**:
  - Phase 1: Mock Transcript messages → Verify parsing & checksum validation
  - Phase 2: Verify trace_id propagation, DLQ routing, metrics emission
  - Phase 3: Full tar.gz structure validation, SLA alert firing
- **End-to-End Tests**: With actual Transcript service (coordination required)

### Rollback Plan
- **Phase 1**: Feature flag `USE_NEW_REDIS_FORMAT` (env var) allows reverting to old parser
- **Phase 2**: DLQ and metrics are additive (no breaking changes)
- **Phase 3**: Enhanced validation can be disabled via config flags

## References
- **Primary**: `docs/adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md` - Cross-cutting contract
- **Schemas**:
  - `docs/design/audio-redis-message-schema.json` - Redis message format
  - `docs/design/conversation-payload.schema.json` - Conversation payload
- **API**: `docs/api/transcript-api.openapi.yaml` - Transcript service API
- **Related ADRs**:
  - `ADR-2025-09-30-002-minio-tar-gz-package.md` - MinIO package structure
  - `ADR-2025-10-10-001-nlp-hybrid-consumer.md` - NLP processing modes
- **External Resources**:
  - [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
  - [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
  - [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html)

## Notes

### Code Locations Summary
| Component | Files to Modify | New Files to Create |
|-----------|----------------|---------------------|
| Redis Config | `src/ingestion/config.py:28-29` | - |
| Message Parsing | `src/ingestion/consumer.py:79-104` | `src/ingestion/redis_message_parser.py` |
| Checksum Validation | `src/ingestion/consumer.py:138` | `src/ingestion/checksum_validator.py` |
| Validation Rules | `src/ingestion/transcript_validator.py:127` | - |
| Tracing | `src/ingestion/consumer.py`, `src/ingestion/storage.py` | - |
| Error Handling | `src/ingestion/consumer.py:222-238` | `src/ingestion/error_handler.py` |
| Metrics | `src/ingestion/consumer.py` (instrument) | `src/ingestion/metrics.py` |
| Archive Validation | `src/ingestion/storage.py` | `src/ingestion/archive_validator.py` |
| Infrastructure | `docker-compose.yml` | `prometheus/alerts.yml`, `grafana/dashboards/*.json` |

### Backward Compatibility Note
Since this is a greenfield integration (no existing Transcript → my-RAG data flow in production), there are **no backward compatibility concerns**. The old message format (`job_id, bucket, object_key`) was used only for local testing and can be safely removed.

### Migration Checklist
- [ ] Phase 1: Update config, parser, checksum validation, external_event_id pattern
- [ ] Phase 1 Testing: Integration test with Transcript mock
- [ ] Phase 2: Add tracing, DLQ, Prometheus metrics
- [ ] Phase 2 Testing: Verify observability pipeline end-to-end
- [ ] Phase 3: MinIO path enforcement, archive validation, SLA alerts
- [ ] Phase 3 Testing: Full contract compliance validation
- [ ] Documentation: Update README, create runbook, update API docs
- [ ] Deployment: Coordinate with Transcript team for synchronized rollout
- [ ] Monitoring: Verify Prometheus metrics, Grafana dashboards, alert firing

---
**Date**: 2025-10-16
**Author**: Claude Code Assistant
**Reviewers**: RAG Platform Team, Transcript Team Lead
