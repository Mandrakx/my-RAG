# Cross-Cutting Concerns - Audio Integration

**Status**: Active (aligned with ADR-2025-10-03-003)
**Last Updated**: 2025-10-16

## References
- `docs/adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md` - Authoritative source
- `docs/api/transcript-api.openapi.yaml` - Complete API specification
- `docs/adr/ADR-2025-10-16-006-authentication-authorization-architecture.md` - Authentication details

## Archive Contract

### Naming Rules
- **External Event ID Format**: `rec-<ISO8601>-<short UUID>` (e.g., `rec-20251003T091500Z-3f9c4241`)
  - Pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
  - `rec-` prefix (constant)
  - `20251003T091500Z` (ISO 8601 compact: YYYYMMDDTHHMMSSZ)
  - `-` separator
  - `3f9c4241` (8 lowercase hex chars from UUID)
- Archive file name: `<external_event_id>.tar.gz`. Example: `rec-20251003T091500Z-3f9c4241.tar.gz`.
- Each archive contains a single top-level folder mirroring the identifier: `<external_event_id>/`.
- All inner files use ASCII characters, kebab-case, and `.json`, `.txt`, `.wav`, `.flac`, `.m4a`, `.mp3`, `.srt`, `.vtt`, `.log`, or `.pdf` extensions.

### Directory Layout (single-level under the root folder)
```
<external_event_id>/
|-- conversation.json          # transcript payload (mandatory)
|-- media/                     # audio/video assets (optional)
|   `-- source.m4a            # original audio file
|-- artifacts/                 # transcription outputs (optional)
|   |-- result.srt            # SubRip subtitle format
|   `-- result.vtt            # WebVTT subtitle format
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

## Metadata Envelope (Device → Transcript)

When uploading audio, the iOS client must provide this metadata structure:

### Field Requirements Table

| Field | Required | Type | Validation | Notes |
|-------|----------|------|------------|-------|
| `external_event_id` | ✅ Yes | string | Pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$` | Stable event ID generated on device |
| `recorded_at_iso` | ✅ Yes | string | ISO 8601 format | Recording start timestamp |
| `timezone` | ✅ Yes | string | IANA timezone ID | e.g., "Europe/Paris", "America/New_York" |
| `trace_id` | ✅ Yes | string | Valid UUID v4 | For distributed tracing |
| `device.model` | ✅ Yes | string | - | iOS device model (e.g., "iPhone16,2") |
| `device.os_version` | ✅ Yes | string | - | iOS version (e.g., "18.0") |
| `device.app_version` | ✅ Yes | string | - | App version (e.g., "0.8.0") |
| `capture.language` | ✅ Yes | string | ISO 639-1 code | e.g., "fr", "en" |
| `capture.duration_ms` | ✅ Yes | integer | > 0 | Audio duration in milliseconds |
| `capture.file_size_bytes` | ✅ Yes | integer | > 0 | Audio file size in bytes |
| `capture.gps` | ❌ Optional | object | - | If location permission granted |
| `capture.gps.lat` | ✅ (if gps) | float | -90 to 90 | Latitude |
| `capture.gps.lon` | ✅ (if gps) | float | -180 to 180 | Longitude |
| `capture.gps.accuracy_m` | ✅ (if gps) | float | > 0 | Horizontal accuracy in meters |
| `capture.place_name` | ❌ Optional | string | - | Reverse geocoded place name |
| `capture.on_device_transcription` | ❌ Optional | boolean | - | Whether on-device transcription was used |
| `participants_hint` | ❌ Optional | array | - | User-provided participant hints |
| `participants_hint[].display_name` | ✅ (if provided) | string | - | Participant display name |
| `participants_hint[].role` | ❌ Optional | string | - | e.g., "client", "consultant" |
| `user_note` | ❌ Optional | string | - | Free-text note from user |
| `checksum_sha256` | ❌ Optional | string | - | SHA256 checksum (if available) |

### Example Metadata Envelope

```json
{
  "metadata": {
    "external_event_id": "rec-20251003T091500Z-3f9c4241",
    "recorded_at_iso": "2025-10-03T09:15:00Z",
    "timezone": "Europe/Paris",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "device": {
      "model": "iPhone16,2",
      "os_version": "18.0",
      "app_version": "0.8.0"
    },
    "capture": {
      "language": "fr",
      "duration_ms": 534000,
      "file_size_bytes": 12582912,
      "gps": {
        "lat": 48.8566,
        "lon": 2.3522,
        "accuracy_m": 12.0
      },
      "place_name": "Tour Eiffel, Paris",
      "on_device_transcription": true
    },
    "participants_hint": [
      {
        "display_name": "Camille",
        "role": "client"
      }
    ],
    "user_note": "Réunion stratégique Q4"
  }
}
```

**Implementation Reference**: `transcript/server/metadata_schema.py` (Pydantic models: `MetadataEnvelope`, `DeviceInfo`, `CaptureInfo`)

## conversation.json Schema Requirements
- Latest canonical schema: `docs/design/conversation-payload.schema.json`.
- Encoding: UTF-8, canonical ordering: metadata -> participants -> segments -> analytics -> attachments.
- Mandatory top-level keys: `schema_version`, `external_event_id`, `source_system`, `created_at`, `meeting_metadata`, `participants`, `segments`.
- `meeting_metadata` must include `scheduled_start` and either `duration_sec` or `end_at`.
- Each `segment` includes `segment_id`, `speaker_id`, `start_ms`, `end_ms`, `text`, `language`, `confidence`.
- Optional sections:
  - `quality_flags` (booleans for `low_confidence`, `missing_audio`, `overlapping_speech`, `nlp_partial`).
  - `attachments` with URIs (HTTP(S) or object storage).
  - `analytics` for sentiment_summary, entities_summary; structure versioned per `schema_version`.
  - `segments[].annotations` for per-segment `sentiment`, `entities`, `topics`.
- Numeric timestamps referenced in milliseconds relative to `scheduled_start`.
- Any unrecognised key triggers a validation warning; producers must keep a changelog when introducing new attributes.
- Voice identification results stored in `participants[*].metadata.voice_matches` with `{match_id, score, source}`.

## Authentication & Security

### API Authentication (iOS ↔ Transcript)

**Provider**: `fastapi_simple_security` for API key management

**Authentication Flow:**
1. **Initial Setup**:
   - iOS app calls `GET /auth/new?never_expires=true` to create API key
   - Backend returns: `{"api_key": "<secret_token>"}`
   - iOS stores key in Keychain with biometric protection

2. **Request Authentication**:
   - Add header: `Authorization: ApiKey <token>`
   - Backend validates against SQLite database (`data/api_keys.sqlite3`)

3. **Key Rotation** (recommended every 90 days):
   - Call `GET /auth/renew?never_expires=true`
   - Old key automatically revoked
   - Store new key in Keychain

4. **Key Revocation**:
   - `GET /auth/revoke?api_key=<key>` - Immediate invalidation
   - Use when key compromised or device lost

5. **Monitoring**:
   - `GET /auth/logs` - View API key usage history

**Rate Limits**: 5 authentication operations per minute per device

**Key Management Endpoints**:
- `GET /auth/new?never_expires=true` - Create new API key
- `GET /auth/revoke?api_key=<key>` - Revoke existing key
- `GET /auth/renew?never_expires=true` - Rotate key
- `GET /auth/logs` - View usage logs

**References**:
- `docs/adr/ADR-2025-10-16-006-authentication-authorization-architecture.md`
- `docs/API_KEY_SETUP.md`
- `docs/IOS_AUTHENTICATION_SPEC.md`

### Security Headers (All API Responses)

Applied via middleware to all responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS filtering |
| `Content-Security-Policy` | `default-src 'self'` | Restrict resource loading |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer info |

### Transport Security

- **TLS Version**: Minimum TLS 1.3
- **Certificate Pinning** (recommended): iOS clients should validate transcript API certificate to prevent MITM
- **Rate Limiting**: Enforced per device, returns `429` on abuse

### Webhooks (Optional - Future)

For event notifications with HMAC SHA-256 authentication:
- Headers: `X-Timestamp`, `X-Signature`, `X-Delivery-Id`
- Receivers validate freshness ±5 min to prevent replay attacks

## Drop Workflow Lifecycle
1. **Package build (transcript backend)**: Assemble archive, populate `conversation.json`, compute checksums, generate build log.
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

## API Protocol (iOS ↔ Transcript)

**Complete OpenAPI 3.0 Specification**: `docs/api/transcript-api.openapi.yaml`

**View Interactive Documentation**:
```bash
# Using Swagger UI (local)
npx swagger-ui-watcher docs/api/transcript-api.openapi.yaml

# Or paste content into https://editor.swagger.io
```

### Upload Flow Options

#### Option A: Two-Phase Upload (Recommended)

Better for large files, supports progress tracking, separates metadata validation from upload.

**Flow:**
1. `POST /v1/jobs/init` - Initialize with metadata, receive presigned S3/R2 URL
2. `PUT <upload_url>` - Upload audio directly to object storage
3. `POST /v1/jobs/{job_id}/commit` - Commit job with checksum for processing
4. `GET /v1/jobs/{job_id}` - Poll for status

**Example:**
```http
POST /v1/jobs/init
Authorization: ApiKey <token>
Content-Type: application/json

{
  "metadata": {
    "external_event_id": "rec-20251003T091500Z-3f9c4241",
    "recorded_at_iso": "2025-10-03T09:15:00Z",
    "timezone": "Europe/Paris",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    ...
  }
}

Response 201:
{
  "job_id": "job-550e8400-e29b-41d4-a716",
  "upload_url": "https://storage.example.com/presigned-url",
  "expires_at": "2025-10-09T11:00:00Z",
  "max_file_size_bytes": 524288000
}
```

#### Option B: Single Multipart Upload

Simpler for small files (<50MB), single HTTP request.

```http
POST /v1/jobs
Authorization: ApiKey <token>
Content-Type: multipart/form-data

[multipart body with metadata JSON + audio file]

Response 201:
{
  "job_id": "job-550e8400-e29b-41d4-a716",
  "status": "queued",
  "checksum_sha256": "a3f5b9c..."
}
```

### Health & Service Discovery

```http
GET /v1/health
Response 200:
{
  "status": "healthy",
  "version": "1.2.3",
  "services": {
    "api": "up",
    "storage": "up",
    "workers": "up",
    "worker_queue_depth": 12
  },
  "timestamp": "2025-10-09T10:30:00Z"
}

GET /v1/health/ready
Response 200: {"ready": true}
Response 503: {"ready": false, "reason": "maintenance", "retry_after": 300}
```

**iOS Implementation**: Call `/v1/health/ready` before job creation, cache result for 30s.

### Error Handling & Retry Policy

**Error Response Format:**
```json
{
  "error": {
    "code": "validation_error",
    "message": "Metadata validation failed",
    "details": {
      "field": "metadata.external_event_id",
      "reason": "Field is required and must match format rec-<ISO8601>-<UUID>"
    },
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "retry_after": null,
    "documentation_url": "https://docs.example.com/errors/validation_error"
  }
}
```

**HTTP Status Codes & Error Catalogue:**

| HTTP | Error Code | Description | iOS Action | Retry? |
|------|------------|-------------|------------|--------|
| 400 | `validation_error` | Metadata validation failed | Show error, log details | ❌ No |
| 400 | `invalid_audio_format` | Unsupported audio format | Show error | ❌ No |
| 401 | `unauthorized` | Invalid/expired API key | Prompt re-login | ❌ No |
| 403 | `forbidden` | User lacks permission | Show error | ❌ No |
| 408 | `request_timeout` | Upload timed out (300s) | Show retry option | ✅ Yes |
| 413 | `payload_too_large` | File exceeds 500MB | Show error with size | ❌ No |
| 422 | `checksum_mismatch` | SHA256 mismatch | Recalculate checksum | ✅ Yes (1x) |
| 429 | `rate_limit_exceeded` | Too many requests (10/min) | Wait `Retry-After` | ✅ Yes |
| 500 | `internal_server_error` | Unexpected server error | Show retry option | ✅ Yes |
| 502 | `bad_gateway` | Upstream unavailable | Show retry option | ✅ Yes |
| 503 | `service_unavailable` | Maintenance | Show maintenance msg | ✅ Yes |
| 504 | `gateway_timeout` | Gateway timeout | Show retry option | ✅ Yes |

**Retry Strategy (Exponential Backoff with Jitter):**
```
Max retries: 3
Backoff formula: min(max_delay, base_delay * 2^attempt) + random(0, jitter)

- Attempt 1: immediate
- Attempt 2: 2s + random(0-1s)
- Attempt 3: 4s + random(0-2s)
- Attempt 4: 8s + random(0-4s)

Special cases:
- 429 (Rate Limit): Respect `Retry-After` header, max 3 retries
- 503 (Maintenance): Respect `Retry-After`, max 1 retry then queue locally
- Network errors: Full retry cycle
```

### File Constraints

- **Max file size**: 500MB (HTTP 413 if exceeded)
- **Supported formats**: m4a (preferred), wav, mp3, flac, ogg
- **Min duration**: 1 second
- **Max duration**: 6 hours (may be split into chunks)
- **Timeout**: 300s upload, 5min-2h processing (depends on duration)
- **Checksum**: SHA256 required for commit phase (Option A) or validated server-side (Option B)

### Polling Recommendations

```
Status "queued" or "processing":
  - Poll every 5s for first minute
  - Then every 15s for next 5 minutes
  - Then every 30s until completion or timeout
  - Max polling duration: 3 hours

Status "completed":
  - Retrieve `package_uri` and download result
  - Delete local pending job

Status "failed":
  - Check `error.code` for remediation
  - Show user-friendly error message
  - Allow manual retry if transient error
```

## Open Topics to Align
- Final JSON schema governance (version bump process, owner).
- Credential rotation cadence for MinIO/Redis (target quarterly).
- Automatic archive quarantine for data privacy requests (process TBD).


