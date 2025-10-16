# ADR: Cross-Cutting Contract for Audio → Transcript → RAG

## Status
Accepted — 2025-10-03

## Context
- The iOS client (`mneia-whisper`) records audio, collects contextual metadata (timestamp, GPS, device, optional participant hints) and must hand off to the transcription backend reliably over the public internet.
- The transcription service (`transcript`) exposes `/v1/jobs` for multipart uploads, runs WhisperX + diarisation + speaker identification, and currently returns ad-hoc JSON artefacts per job.
- The RAG platform (`my-RAG`) consumes canonical conversation packages (tar.gz + `conversation.json`) governed by `docs/design/conversation-payload.schema.json` and expects notifications on Redis Streams.
- Each team maintained its own implicit assumptions (naming, metadata fields, retry rules, observability), creating integration gaps, duplicate parsing logic, and limited traceability across systems.

## Decision
Adopt a shared cross-project contract covering identifiers, metadata, payload format, delivery, security, and observability. The following requirements are normative for all teams:

1. **Identifiers**
   - Generate a stable `external_event_id` on device before calling the backend. Reuse it as:
     - `CreateJobRequest.metadata.external_event_id` in Transcript.
     - Root folder and archive name `<external_event_id>.tar.gz`.
     - `conversation.json.external_event_id` and Redis notification payload.
   - Propagate `metadata.trace_id` (UUID) for distributed tracing; reuse it as Redis `metadata.trace_id` and include in logs/metrics.

2. **Metadata Envelope (device → Transcript)**
   - Mobile populates:
     ```json
     {
       "metadata": {
         "external_event_id": "rec-20251003T091500Z-3f9c4241",
         "recorded_at_iso": "2025-10-03T09:15:00Z",
         "timezone": "Europe/Paris",
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
         "user_note": "Réunion stratégique Q4",
         "trace_id": "550e8400-e29b-41d4-a716-446655440000"
       }
     }
     ```
   - Transcript persists the structure unchanged (`Job.metadata`) and passes it to workers. Optional checksum `checksum_sha256` should be provided when available.
   - **Validation**: Soft validation on receipt (warn on missing recommended fields); strict validation in worker before packaging.
   - **External Event ID format**: `rec-<ISO8601 timestamp>-<short UUID>` (e.g., `rec-20251003T091500Z-3f9c4241`).
     - Pattern: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
     - Example breakdown: `rec-20251003T091500Z-3f9c4241`
       - `rec-` prefix (constant)
       - `20251003T091500Z` (ISO 8601 compact format: YYYYMMDDTHHMMSSZ)
       - `-` separator
       - `3f9c4241` (8 lowercase hexadecimal characters from UUID)
   - **Optional fields**: `gps` (if permission denied), `place_name` (if reverse geocoding unavailable), `user_note` (if empty), `participants_hint` (if not provided during capture).

   **Field Requirements:**

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

   **Implementation Reference:**
   - Pydantic validation schema: `transcript/server/metadata_schema.py` (classes `MetadataEnvelope`, `DeviceInfo`, `CaptureInfo`)
   - The backend uses Pydantic for automatic validation with detailed error messages on schema violations

3. **Transcript Normalisation**
   - Whisper pipeline outputs segments conforming to `conversation-payload.schema.json`:
     - Keys: `segment_id`, `speaker_id`, `start_ms`, `end_ms`, `text`, `language`, `confidence`, optional `words`.
     - Speaker IDs derived from diarisation (e.g. `spk_tmp_01`).
   - Map voice identification results to participant suggestions and include under `participants[*].metadata.voice_matches` with `{match_id, score, source}`.
   - Assemble `conversation.json` with sections `metadata`, `meeting_metadata`, `participants`, `segments`, optional `quality_flags`, `attachments`, `analytics`.

4. **Archive Delivery & Notification**
   - Worker packages outputs into `<external_event_id>.tar.gz`:
     ```
     <external_event_id>/
       conversation.json
       media/
         source.m4a
       artifacts/
         result.srt
         result.vtt
       checksums.sha256
     ```
   - Publish Redis Streams message (`audio.ingestion`) matching `docs/design/audio-redis-message-schema.json` with checksum `sha256:<hash>`, `package_uri`, `schema_version`.
   - Retain packages 72h in object storage for retries; ingestion acknowledgements follow the SLA matrix (ack <5 s, processing kickoff <60 s).

5. **Security & Observability**
   - **API Protocol**: HTTPS/REST with multipart upload (FastAPI `/v1/jobs` endpoint). Presigned S3/R2 URLs for direct object storage upload.

   - **Authentication**:
     - **Provider**: fastapi_simple_security for API key management
     - **Storage Backend**: SQLite database (`data/api_keys.sqlite3`)
     - **Header Format**: `Authorization: ApiKey <token>`
     - **Client Storage**: Keys stored in iOS Keychain with biometric protection
     - **Expiration**: Non-expiring by default (configurable with `never_expires` parameter)
     - **Rotation**: Manual rotation via `GET /auth/renew` endpoint (old key automatically revoked)
     - **Revocation**: Immediate invalidation via `GET /auth/revoke` endpoint
     - **Key Management Endpoints** (all use GET method):
       - `GET /auth/new?never_expires=true` - Create new API key
       - `GET /auth/revoke?api_key=<key>` - Revoke existing key
       - `GET /auth/renew?never_expires=true` - Rotate key (old key revoked)
       - `GET /auth/logs` - View API key usage logs
     - **Rate Limits**: 5 authentication operations per minute per device
     - See ADR-2025-10-16-006 for complete authentication architecture

   - **Security Headers** (applied to all responses via middleware):
     - `Strict-Transport-Security: max-age=31536000; includeSubDomains` - Force HTTPS
     - `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
     - `X-Frame-Options: DENY` - Prevent clickjacking
     - `X-XSS-Protection: 1; mode=block` - XSS filtering
     - `Content-Security-Policy: default-src 'self'` - Restrict resource loading
     - `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer info

   - **Transport Security**:
     - Enforce TLS 1.3 minimum
     - **Certificate Pinning** (recommended): iOS clients should validate transcript API certificate to prevent MITM attacks
     - Request rate limits enforced (`429` response on abuse)

   - **Webhooks** (optional): HMAC SHA-256 with `X-Timestamp`, `X-Signature`, `X-Delivery-Id`; receivers validate freshness ±5 min.

   - **Logs/metrics**: structured JSON including `external_event_id`, `trace_id`, durations, payload sizes, retry counts. Prometheus counters align with RAG ingestion (`audio_ingest_ack_latency_seconds`, `audio_ingest_failures_total`, etc.).

   - **Errors**: use shared catalogue (`validation_error`, `checksum_mismatch`, `processing_failure`, `payload_expired`, ...). DLQ messages include `external_event_id` and remediation hints.

6. **API Protocol Specification (iOS ↔ Transcript)**

   **Complete OpenAPI 3.0 specification**: `docs/api/transcript-api.openapi.yaml`

   **View interactive documentation:**
   ```bash
   # Using Swagger UI (local)
   npx swagger-ui-watcher docs/api/transcript-api.openapi.yaml

   # Or paste content into https://editor.swagger.io
   ```

   ### 6.1 Upload Flow Options

   **Option A: Two-Phase Upload (Recommended)**

   Better for large files, supports progress tracking, and separates metadata validation from upload.

   ```
   1. POST /v1/jobs/init
      Headers:
        Authorization: ApiKey <token>
        Content-Type: application/json
      Body: { "metadata": {...} }
      Response 201:
        {
          "job_id": "job-550e8400-e29b-41d4-a716",
          "upload_url": "https://storage.example.com/presigned-url",
          "expires_at": "2025-10-09T11:00:00Z",
          "max_file_size_bytes": 524288000
        }

   2. PUT <upload_url>
      Headers:
        Content-Type: audio/m4a
        Content-MD5: <base64-encoded-md5>
      Body: <binary audio file>
      Response 200: (S3 confirmation)

   3. POST /v1/jobs/{job_id}/commit
      Headers:
        Authorization: ApiKey <token>
        Content-Type: application/json
      Body:
        {
          "checksum_sha256": "a3f5b9c...",
          "file_size_bytes": 12582912
        }
      Response 200:
        {
          "status": "queued",
          "estimated_completion_at": "2025-10-09T10:45:00Z"
        }

   4. GET /v1/jobs/{job_id} (Polling)
      Headers: Authorization: ApiKey <token>
      Response 200:
        {
          "job_id": "job-550e8400-e29b-41d4-a716",
          "external_event_id": "rec-20251003T091500Z-3f9c4241",
          "status": "queued|processing|completed|failed",
          "progress_percent": 45,
          "created_at": "2025-10-09T10:30:00Z",
          "updated_at": "2025-10-09T10:35:00Z",
          "completed_at": null,
          "package_uri": null,
          "error": null
        }
   ```

   **Option B: Single Multipart Upload**

   Simpler for small files (<50MB), single HTTP request.

   ```http
   POST /v1/jobs
   Headers:
     Authorization: ApiKey <token>
     Content-Type: multipart/form-data; boundary=----Boundary123

   Body:
   ------Boundary123
   Content-Disposition: form-data; name="metadata"
   Content-Type: application/json

   {
     "external_event_id": "rec-20251003T091500Z-3f9c4241",
     "recorded_at_iso": "2025-10-03T09:15:00Z",
     ...
   }

   ------Boundary123
   Content-Disposition: form-data; name="audio_file"; filename="recording.m4a"
   Content-Type: audio/m4a

   <binary audio data>
   ------Boundary123--

   Response 201:
   {
     "job_id": "job-550e8400-e29b-41d4-a716",
     "status": "queued",
     "checksum_sha256": "a3f5b9c..."
   }
   ```

   ### 6.2 Health & Service Discovery

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

   **iOS Implementation:**
   - Call `/v1/health/ready` before job creation
   - Cache result for 30s to avoid excessive calls
   - If 503, display user-friendly message with retry estimate

   ### 6.3 Error Handling & Retry Policy

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
   | 400 | `invalid_audio_format` | Unsupported audio format (expected: m4a, wav, mp3) | Show error | ❌ No |
   | 400 | `missing_required_field` | Required metadata field missing | Show error, fix metadata | ❌ No |
   | 401 | `unauthorized` | Invalid or expired API key | Prompt re-login | ❌ No |
   | 403 | `forbidden` | User lacks permission for this operation | Show error | ❌ No |
   | 408 | `request_timeout` | Upload timed out (timeout: 300s) | Show retry option | ✅ Yes |
   | 413 | `payload_too_large` | File exceeds 500MB limit | Show error with file size | ❌ No |
   | 422 | `checksum_mismatch` | SHA256 checksum does not match uploaded file | Recalculate checksum | ✅ Yes (1x) |
   | 422 | `invalid_presigned_url` | Presigned URL expired or malformed | Restart upload flow | ✅ Yes (1x) |
   | 429 | `rate_limit_exceeded` | Too many requests (limit: 10/min per device) | Wait `Retry-After` seconds | ✅ Yes |
   | 500 | `internal_server_error` | Unexpected server error | Show retry option | ✅ Yes |
   | 502 | `bad_gateway` | Upstream service unavailable | Show retry option | ✅ Yes |
   | 503 | `service_unavailable` | Service temporarily unavailable (maintenance) | Show maintenance message | ✅ Yes |
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
   - 503 (Maintenance): Respect `Retry-After` header, max 1 retry then queue locally
   - Network errors (DNS, connection timeout): Full retry cycle
   ```

   **iOS Implementation Notes:**
   - Store failed jobs locally with retry metadata (`attempt_count`, `next_retry_at`)
   - Background task retries failed uploads when network available
   - User can manually retry failed jobs from UI
   - After 3 failed attempts, mark job as "needs_attention" and notify user

   ### 6.4 File Constraints

   - **Max file size**: 500MB (HTTP 413 if exceeded)
   - **Supported formats**: m4a (preferred), wav, mp3, flac, ogg
   - **Min duration**: 1 second
   - **Max duration**: 6 hours (processing may be split into chunks)
   - **Timeout**: 300s for upload, 5 minutes for processing (short files), up to 2 hours (long files)
   - **Checksum**: SHA256 required for commit phase (Option A) or validated server-side (Option B)

   ### 6.5 Polling & Notifications

   **Polling Recommendations:**
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
     - Allow manual retry if error is transient
   ```

   **Push Notifications (Future Enhancement):**
   - iOS client registers FCM/APNs token with backend
   - Backend sends push notification on job completion/failure
   - Reduces polling overhead and battery usage

7. **Governance**
   - `conversation-payload.schema.json` in MY-RAG remains authoritative; major changes require version bump and cross-team sign-off.
   - CI validation: Transcript worker validates payload against the schema before packaging; MY-RAG ingestion rejects unknown major versions with actionable logs.
   - ADR updates mirrored across repositories to keep documentation in sync.

## Implementation Notes

### Current State Analysis (2025-10-09)

**mneia-whisper (iOS)**:
- ✅ Local storage captures: `id`, `title`, `audioURL`, `transcription`, `language`, `createdAt`, `duration`, `fileSize`, `gpsLocation` (String format "lat,lon"), `placeName`, `participants[]`, `note`
- ❌ No API client for transcript service (POST /v1/jobs not implemented)
- ❌ Missing metadata fields: `external_event_id`, `timezone`, `device.model/os_version/app_version`, `gps.accuracy_m`, `trace_id`

**transcript (Backend)**:
- ✅ `Job.metadata` field exists (Dict[str, Any]) but no schema validation
- ✅ Multipart upload infrastructure ready (S3/R2 presigned URLs)
- ❌ No metadata envelope validation on job creation
- ❌ Worker does not map metadata to conversation.json format

**Compatibility Gaps**:
| Field | iOS Status | Backend Status | Action Required |
|-------|-----------|---------------|-----------------|
| `external_event_id` | Missing | Missing | Generate UUID format `rec-<ISO8601>-<UUID>` on iOS |
| `timezone` | Missing | Missing | Capture `TimeZone.current.identifier` on iOS |
| `device.*` | Missing | Missing | Capture from `UIDevice.current` + `Bundle.main` |
| `gps.accuracy_m` | Missing | Missing | Extend GPS capture to include `CLLocation.horizontalAccuracy` |
| `participants_hint` | String[] only | Missing | Map to structured objects `{display_name, role}` |
| `trace_id` | Missing | Missing | Generate UUID for distributed tracing |

### Implementation Phases

**Phase 1: iOS (mneia-whisper)** [Priority: HIGH]
1. Create `MetadataEnvelope.swift` model matching section 2 structure
2. Extend `RecordingData` with missing fields (`externalEventId`, `timezone`, `deviceInfo`, `traceId`)
3. Improve GPS capture: parse "lat,lon" to structured object, add accuracy
4. Implement `APIKeyManager.swift`:
   - Store/retrieve API keys from iOS Keychain with biometric protection
   - Track key expiration and trigger renewal notifications
   - Handle key rotation with grace period
5. Implement `TranscriptAPIClient.swift`:
   - Authentication: `Authorization: ApiKey <token>` header
   - `GET /auth/new?never_expires=true` - Create new API key (initial setup)
   - `GET /auth/renew?never_expires=true` - Rotate key periodically (recommended every 90 days)
   - `GET /auth/revoke?api_key=<key>` - Revoke compromised key
   - `GET /auth/logs` - Monitor API key usage
   - `POST /v1/jobs/init` - Initialize upload with presigned URL
   - `PUT <presigned_url>` - Upload audio to S3/R2
   - `POST /v1/jobs/{job_id}/commit` - Commit job for processing
   - `POST /v1/jobs` - Direct multipart upload (fallback)
   - `GET /v1/jobs/{job_id}` - Poll for status
   - Error handling with exponential backoff retry
6. Update `RecordingModel.swift` to persist API job status and key metadata

**Phase 2: Backend (transcript)** [Priority: MEDIUM - COMPLETED 2025-10-16]
1. ✅ Implement fastapi_simple_security authentication integration (`server/auth.py`)
   - SQLite database storage for API keys (`data/api_keys.sqlite3`)
   - `GET /auth/new` - Create API keys (non-expiring by default)
   - `GET /auth/revoke` - Revoke keys immediately
   - `GET /auth/renew` - Rotate keys (old key automatically revoked)
   - `GET /auth/logs` - View API key usage logs
   - API key verification dependency with request-level validation
2. ✅ Add security headers middleware (`server/security_headers.py`)
   - HSTS, CSP, X-Frame-Options, X-Content-Type-Options, etc.
3. ✅ Update OpenAPI specification with authentication endpoints
4. ✅ Add comprehensive documentation (API_KEY_SETUP.md, IOS_AUTHENTICATION_SPEC.md, MIGRATION_GUIDE.md)
5. ✅ Add soft validation for `Job.metadata` against envelope schema (log warnings)
6. ✅ Document expected metadata structure in API spec
7. ⏳ Update worker to map `Job.metadata` → `conversation.json`:
   - `metadata.device` → `metadata.device` (passthrough)
   - `metadata.capture.gps` → `meeting_metadata.location`
   - `metadata.participants_hint` → `participants[]`
   - `metadata.recorded_at_iso` → `meeting_metadata.scheduled_start`
   - `metadata.trace_id` → root-level `metadata.trace_id`

**Phase 3: Integration (my-RAG)** [Priority: LOW]
1. Verify conversation.json from transcript matches schema
2. Add validation tests for metadata → meeting_metadata mapping
3. Update Redis message schema to include `metadata.trace_id`

### Schema Governance

- **Source of Truth**: `my-RAG/docs/design/conversation-payload.schema.json`
- **Validation Points**:
  1. iOS: Client-side validation before POST (optional, for early error detection)
  2. Transcript API: Soft validation on job creation (warn only)
  3. Transcript Worker: Strict validation before packaging (fail + DLQ)
  4. my-RAG Ingestion: Final validation on unpack (reject + alert)
- **Version Bumps**: Major version change requires sign-off from all three teams (iOS, transcript, my-RAG)
- **CI Enforcement**: Add JSON Schema validation to transcript worker tests

## Consequences
- ✅ Simplifies downstream ingestion (single schema, no custom parsers).
- ✅ Improves traceability across mobile, backend, and RAG via shared IDs and metrics.
- ✅ Establishes clear protocol (HTTPS/REST + multipart) leveraging existing infrastructure.
- ⚠️ Requires incremental work in Transcript worker (schema-compliant segments, tarball builder) and iOS metadata capture (API client implementation).
- ⚠️ Creates dependency on schema governance process; teams must coordinate on breaking changes.
- ✅ Unlocks automation for retries, audits, and distributed tracing.
- ✅ Establishes a governance loop for schema evolution to prevent breaking changes.

## References
- `docs/api/transcript-api.openapi.yaml` — Complete OpenAPI 3.0 specification
- `docs/adr/ADR-2025-10-16-006-authentication-authorization-architecture.md` — Authentication & authorization architecture
- `docs/API_KEY_SETUP.md` — API key setup guide
- `docs/IOS_AUTHENTICATION_SPEC.md` — iOS authentication implementation specification
- `docs/MIGRATION_GUIDE.md` — Migration guide for authentication changes
- `transcript/docs/spec/Iphone-app-spec.md`
- `transcript/workers/transcriber/app.py`
- `my-RAG/docs/design/cross-cutting-concern.md`
- `my-RAG/docs/design/conversation-payload.schema.json`
- `mneia-whisper/docs/adr/0003-20250830-recording-result-split-gps-and-jobs.md`
