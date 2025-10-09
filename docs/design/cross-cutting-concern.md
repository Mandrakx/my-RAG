# Cross-Cutting Concerns - Audio Integration

## Archive Contract

### Naming Rules
- Archive file name: `<external_event_id>.tar.gz` (lowercase, dash-separated). Example: `20250930T080000Z-audio-v1-3f9c4241.tar.gz`.
- Each archive contains a single top-level folder mirroring the identifier: `<external_event_id>/`.
- All inner files use ASCII characters, kebab-case, and `.json`, `.txt`, `.wav`, `.flac`, `.mp3`, `.log`, or `.pdf` extensions.

### Directory Layout (single-level under the root folder)
```
<external_event_id>/
|-- conversation.json          # transcript payload (mandatory)
|-- media/                     # audio/video assets (optional)
|-- artifacts/                 # slides, calendars... (optional)
|-- logs/                      # producer logs for troubleshooting (optional)
`-- checksums.sha256           # SHA-256 for every file listed above (mandatory)
```
- Empty directories must be omitted.
- `media/`, `artifacts/`, and `logs/` may contain subfolders; depth limited to 2 levels to simplify validation.

### File Semantics
| File | Requirements |
|------|--------------|
| `conversation.json` | UTF-8 without BOM, Unix line endings, 2-space indentation, conforms to `schema_version` stated inside. |
| `checksums.sha256` | One entry per file (relative path from root, no leading `./`), format `<hash>  <relative_path>`, newline at end of file. |
| media files | PCM WAV 16-bit, FLAC, or MP3 320 kbps max. Filenames follow `<external_event_id>_<channel>.ext`. |
| logs | Plain-text UTF-8. File names map to producing service (`transcription.log`, `diarization.log`). |
| artifacts | Any binary/text asset agreed beforehand; each entry documented in transcript `attachments` section. |

### Validation Rules
1. Archive must unpack without warnings using `tar -tzf` and `tar -xzf`.
2. Root folder name equals `external_event_id` contained in `conversation.json`.
3. `checksums.sha256` lists every file (including itself) except the parent directory.
4. `sha256sum -c checksums.sha256` passes on a clean workspace.
5. `conversation.json` schema validation succeeds using `docs/design/conversation-payload.schema.json` (JSON Schema draft 2020-12).
6. No individual file exceeds 2 GiB; total archive size <= 5 GiB.

## conversation.json Schema Requirements
- Latest canonical schema: `docs/design/conversation-payload.schema.json`.
- Encoding: UTF-8, canonical ordering: metadata -> participants -> segments -> analytics -> attachments.
- Mandatory top-level keys: `schema_version`, `external_event_id`, `source_system`, `created_at`, `meeting_metadata`, `participants`, `segments`.
- `meeting_metadata` must include `scheduled_start` and either `duration_sec` or `end_at`.
- Each `segment` includes `segment_id`, `speaker_id`, `start_ms`, `end_ms`, `text`, `language`, `confidence`.
- Optional sections:
  - `quality_flags` (booleans for `low_confidence`, `missing_audio`, `overlapping_speech`).
  - `attachments` with URIs (HTTP(S) or object storage).
  - `analytics` for diarization, topics, or sentiment; keys documented per `schema_version`.
- Numeric timestamps referenced in milliseconds relative to `scheduled_start`.
- Any unrecognised key triggers a validation warning; producers must keep a changelog when introducing new attributes.

## Drop Workflow Lifecycle
1. **Package build (audio team)**: Assemble archive, populate `conversation.json`, compute checksums, drop metadata into build log.
2. **Upload**: Push to `minio://ingestion/drop/<YYYY>/<MM>/<DD>/<external_event_id>.tar.gz`.
3. **Notification**: Publish Redis Streams message (see contract below) immediately after upload (max skew 2s).
4. **Reception (RAG team)**: Ingestion service listens via consumer group `rag-ingestion`. Ack expected within 5 seconds.
5. **Validation**: Service downloads archive, verifies checksum, validates schema, and stages artefacts to processing area.
6. **Processing kickoff**: Orchestration job created < 60 seconds after message receipt; status visible via monitoring dashboard.
7. **Retention**: Archive retained in MinIO for 72 hours; Redis message kept for 48 hours or until acked + 24h.
8. **Purge**: Automated lifecycle policy removes old artefacts; long-term storage handled by analytics project if required.

## Responsibilities & SLA Matrix
| Step | Responsable principal | Co-responsable | SLA | Notes |
|------|----------------------|----------------|-----|-------|
| Package build | Audio team | RAG team (review tooling) | Delivery window negotiated per batch | Audio ensures schema compliance before drop. |
| Upload & notify | Audio team | Platform SRE (credentials) | Notification <= 2s after upload | Retries occur only after explicit failure signal. |
| Ack message | RAG ingestion | Platform SRE (infra health) | Ack < 5s | Automatic alarm at 3s warning threshold. |
| Validation | RAG ingestion | Audio team (support) | Completion < 1 min | Failures reported in deadletter with reason + remediation. |
| Retry handling | Audio team | RAG ingestion | <= 5 attempts within 30 min | Use exponential backoff (5/10/20/40/55s). |
| Deadletter triage | Joint | Incident commander | Response < 15 min | ESC escalated via shared channel. |
| Archive cleanup | Platform SRE | Audio team (audit) | Daily | Bucket lifecycle rules audited quarterly. |

## Redis Streams Contract
- Stream: `audio.ingestion` (namespace `audio:` reserved; environment-specific suffix allowed, e.g., `audio.ingestion.prod`).
- Consumer group: `rag-ingestion` (instances register as `<service>-<hostname>`).
- Message payload is JSON serialised as UTF-8 and stored in field `payload`; alternate field `headers` reserved for future use.
- Size limits: payload <= 256 KB, message count <= 100k pending entries to keep latency bounded.
- Producers append entry id `*`; ingestion reads via `XREADGROUP` with `COUNT 16 BLOCK 2000`. Idle entries > 15 min move to retry queue.

### Message Schema (JSON)
| Field | Type | Description |
|-------|------|-------------|
| `external_event_id` | string | Matches archive folder and filename. |
| `package_uri` | string (URI) | MinIO URI using `minio://bucket/path`. |
| `checksum` | string | `sha256:<64 hex>`. |
| `schema_version` | string | Major.minor semantic; ingestion rejects unknown major. |
| `retry_count` | integer | Start at 0; increment on each producer retry. |
| `produced_at` | string (ISO 8601) | UTC timestamp when message published. |
| `producer` | object | `{ "service": "audio-pipeline", "instance": "ip-10-0-1-12" }`. |
| `priority` | string | `normal` (default) or `high` for expedited processing. |
| `metadata` | object | Free-form (must remain under 1 KB). |

Formal JSON Schema: `docs/design/audio-redis-message-schema.json` (kept authoritative).

### Shared Error Codes
| Code | Owned by | Trigger | Expected action |
|------|----------|---------|-----------------|
| `validation_error` | Audio | Schema failure, missing mandatory file | Fix payload, republish within 24h. |
| `checksum_mismatch` | Audio | SHA mismatch vs `checksums.sha256` | Rebuild archive, republish. |
| `duplicate_event` | Joint | Event already processed | Investigate duplication; resend only if new transcript. |
| `ingestion_timeout` | RAG | Ack > 5s or processing not started < 1 min | Platform investigates, replays backlog. |
| `processing_failure` | RAG | Downstream pipeline crash post-ack | Replay from staged package; update status feed. |
| `unauthorized` | Audio | Invalid credentials for MinIO/Redis | Rotate credentials, confirm least-privilege policy. |
| `payload_expired` | RAG | Archive older than 72h | Audio produces fresh drop if information still required. |

Error code catalogue tracked in shared runbook; changes require both teams to sign off.

## Monitoring & Observability Plan
- **Logs**: Structured JSON logs with keys `external_event_id`, `stream`, `package_uri`, `correlation_id`, `status`. Retention 30 days. Log levels: `INFO` for lifecycle, `WARN` for retries, `ERROR` for validation failures.
- **Metrics (Prometheus)**:
  - `audio_ingest_ack_latency_seconds` (histogram, buckets: 0.5,1,2,3,5,10).
  - `audio_ingest_validation_duration_seconds` (summary).
  - `audio_ingest_failures_total{reason="checksum"|...}`.
  - `audio_ingest_messages_inflight` (gauge from Redis pending entries).
  - `audio_ingest_retries_total` (counter).
- **Alerts**:
  - Ack latency p95 > 3s for 5 minutes -> warning, >5s -> critical.
  - Validation failure rate > 5% over 15 minutes.
  - Redis pending entries > 500 for > 10 minutes.
  - MinIO write errors (S3 PutObject 5xx) detected via bucket metrics.
- **Dashboards**:
  - Ingestion overview: latency, throughput, failure reasons, backlog.
  - Package drilldown: link event ID -> logs, MinIO object, orchestration run.
  - Retry heatmap: `external_event_id` vs retry_count.
- **Tracing**: Use OpenTelemetry trace id propagated in Redis message (`metadata.trace_id`) and ingestion service logs to correlate to downstream jobs.
- **Runbooks**: Link to `docs/guides/operations/minio-drop-playbook.md` for operational steps; include quick links to Grafana dashboard and Kibana saved searches.

## Open Topics to Align
- Final JSON schema governance (version bump process, owner).
- Credential rotation cadence for MinIO/Redis (target quarterly).
- Automatic archive quarantine for data privacy requests (process TBD).


