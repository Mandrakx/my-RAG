# Ingestion Monitoring Plan

## Scope
Monitoring strategy for the MinIO drop and Redis-triggered ingestion pipeline that powers the conversation RAG stack. Covers logging, metrics, tracing, and alerting so audio and RAG teams share the same operational picture.

## Logging Strategy
- Structured JSON logs with mandatory keys: `timestamp`, `level`, `service`, `external_event_id`, `package_uri`, `correlation_id`, `message`.
- Emit `correlation_id` sourced from Redis message `metadata.trace_id`; propagate to downstream orchestration jobs.
- Log categories:
  - `INGESTION_RECEIVED` at message arrival (includes Redis message id).
  - `VALIDATION_PASSED` / `VALIDATION_FAILED` with duration and failing rule.
  - `PROCESSING_STARTED` / `PROCESSING_COMPLETED` with orchestration run id.
- Log retention: 30 days in centralized store (Loki/ELK). Cold storage for 90 days when flagged by incident review.
- Enrich logs with `retry_count` and `schema_version` to simplify filtering.

## Metrics (Prometheus)
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `audio_ingest_messages_total` | counter | `status` (`received`, `validated`, `failed`) | Throughput of ingestion service.
| `audio_ingest_ack_latency_seconds` | histogram | `status` | Time between Redis publish and consumer ack. Buckets: 0.25,0.5,1,2,3,5,10.
| `audio_ingest_validation_duration_seconds` | summary | `outcome` | Time to download and validate archive.
| `audio_ingest_pending_entries` | gauge | `stream` | Redis pending entries (raw from `XPENDING`).
| `audio_ingest_retries_total` | counter | `reason` | Retry counts coming from producer notifications.
| `audio_ingest_deadletter_total` | counter | `code` | Deadletter events grouped by shared error code.

Collectors: ingestion service exports `/metrics`; Redis exporter provides stream depth; MinIO exporter surfaces S3 PutObject/GET errors.

## Alerts
| Alert | Expr | Severity | Action |
|-------|------|----------|--------|
| `AudioIngestAckLatencyHigh` | `histogram_quantile(0.95, rate(audio_ingest_ack_latency_seconds_bucket[5m])) > 3` | warning | Investigate ingestion health, check Redis backlog.
| `AudioIngestAckLatencyCritical` | `... > 5` | critical | Page platform on-call, evaluate scaling/restarts.
| `AudioIngestValidationFailureSpike` | `increase(audio_ingest_failures_total[15m]) / increase(audio_ingest_messages_total[15m]) > 0.05` | warning | Coordinate with audio team for payload issues.
| `AudioIngestPendingQueue` | `audio_ingest_pending_entries > 500` for 10 minutes | warning | Drain backlog; consider scaling consumers.
| `AudioIngestDeadletterCritical` | `increase(audio_ingest_deadletter_total[10m]) > 5` | critical | Incident response; follow deadletter playbook.
| `MinioDropWriteErrors` | `rate(minio_s3_requests_error_total{operation="PutObject"}[5m]) > 0` | warning | Validate MinIO availability/credentials.

Alert destinations: shared Slack channel `#rag-audio-alerts` (warning), PagerDuty service `RAG-Ingestion` (critical).

## Dashboards
- **Ingestion Overview**: throughput, ack latency, validation duration, backlog trend (Grafana playlist `RAG-Ingestion`).
- **Deadletter Drilldown**: table of recent deadletters, linked logs, reason distribution.
- **Package Timeline**: single external_event_id view showing timestamps for notification, ack, validation, processing, completion.

## Tracing
- Use OpenTelemetry to emit span `audio.ingest.receive` with attributes `external_event_id`, `redis_message_id`, `retry_count`.
- Downstream tasks attach child spans `audio.ingest.validate` and `audio.ingest.stage`.
- Trace id injected into Redis message `metadata.trace_id` and persisted in logs/DB for later joins.

## Ownership & Review
- Dashboard + alert templates owned by Platform SRE.
- Audio and RAG leads review metrics and thresholds quarterly.
- Any change to shared metrics or alert thresholds tracked via ADR or runbook update.

## References
- `docs/design/cross-cutting-concern.md`
- `docs/guides/operations/minio-drop-playbook.md`
- `monitoring/metrics/README.md` (to be populated)
