# Action Plan: Fix Alignment Cross-Cutting Integration
**Date**: 2025-10-26
**Status**: 🟠 IN PROGRESS - iOS BLOCKED
**Owner**: Staff Integration Platform Architect
**Duration**: 4 weeks (iOS critical path)
**Next Review**: 2025-11-02

---

## 📊 EXECUTIVE SUMMARY

| Component | Status | Blocker | Priority | ETA |
|-----------|--------|---------|----------|-----|
| **mneia-lab (iOS)** | 🔴 INCOMPLETE | ✅ YES | P0 | 2025-11-09 |
| **Transcript** | 🟢 STABLE | ❌ NO | P1 | 2025-10-31 |
| **my-RAG** | 🟢 STABLE | ❌ NO | P2 | 2025-11-02 |

**Critical Path**: iOS → Transcript → my-RAG
**E2E Readiness**: 🟠 40% (Blocked by iOS layer)

---

# 🍎 PROJECT 1: MNEIA-LAB (iOS Transmission Client)

## Priority Level: 🔴 P0 - CRITICAL BLOCKER

### Timeline: Week 1-2 (Oct 26 - Nov 9, 2025)

---

## THEME A: Identifier & Metadata Generation

### A.1: external_event_id Generation

- [ ] **A.1.1** Create `ExternalEventIdGenerator.swift` utility
  - [ ] Generate format: `rec-YYYYMMDDTHHMMSSZ-<8hex-chars>`
  - [ ] Pattern validation: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
  - [ ] Use UUID v4 last 8 chars (hex) for uniqueness
  - [ ] Unit tests: Valid/invalid patterns, collision resistance
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Identifiers\ExternalEventIdGenerator.swift`

- [ ] **A.1.2** Integrate into RecordingData model
  - [ ] Add `externalEventId: String` field to RecordingData
  - [ ] Generate on recording creation (not edit)
  - [ ] Persist to Core Data
  - [ ] Include in API payload (metadata.external_event_id)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **A.1.3** Unit test suite
  - [ ] Test format generation
  - [ ] Test pattern matching
  - [ ] Test persistence to Core Data
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\ExternalEventIdGeneratorTests.swift`

---

### A.2: trace_id (Distributed Tracing)

- [ ] **A.2.1** Create `TraceIdGenerator.swift` utility
  - [ ] Generate UUID v4 for each upload session
  - [ ] Include in all API requests (header: `X-Trace-Id`)
  - [ ] Propagate through logs (structured JSON)
  - [ ] Store in job metadata for correlation
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Tracing\TraceIdGenerator.swift`

- [ ] **A.2.2** Add trace_id to RecordingData
  - [ ] Add `traceId: String` field
  - [ ] Generate fresh trace_id per upload attempt (for retry correlation)
  - [ ] Store in metadata
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **A.2.3** Logging integration
  - [ ] Add trace_id to all log statements
  - [ ] Format: `[{externalEventId}][trace_id={traceId}]`
  - [ ] Include in network request logging
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Logging\LoggingService.swift`

---

### A.3: Timezone Capture

- [ ] **A.3.1** Add timezone field to RecordingData
  - [ ] Add `timezone: String` field (IANA timezone ID)
  - [ ] Capture via `TimeZone.current.identifier` at recording creation
  - [ ] Examples: `Europe/Paris`, `America/New_York`, `UTC`
  - [ ] Validate against IANA database
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **A.3.2** Test timezone capture
  - [ ] Unit tests for IANA timezone format
  - [ ] Test on different device locales
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\TimezoneCapturingTests.swift`

---

## THEME B: Device Information Capture

### B.1: Device Model & OS Version

- [ ] **B.1.1** Create `DeviceInfoCapture.swift`
  - [ ] Capture `UIDevice.current.model` (e.g., "iPhone16,2")
  - [ ] Capture `UIDevice.current.systemVersion` (e.g., "18.0")
  - [ ] Capture `Bundle.main.infoDictionary["CFBundleShortVersionString"]` (app version)
  - [ ] Store in metadata structure
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Device\DeviceInfoCapture.swift`

- [ ] **B.1.2** Add device info to metadata envelope
  - [ ] Create DeviceInfo struct: `{model, os_version, app_version}`
  - [ ] Integrate with RecordingMetadata
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **B.1.3** Persist to Core Data
  - [ ] Store device info in recording entity
  - [ ] Include in API payload (metadata.device)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift`

- [ ] **B.1.4** Unit tests
  - [ ] Test device info capture
  - [ ] Test format validation
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\DeviceInfoCaptureTests.swift`

---

## THEME C: GPS Enhancement

### C.1: Extend GPS with Accuracy

- [ ] **C.1.1** Update LocationData model
  - [ ] Add `accuracy_m: Double` field (horizontal accuracy in meters)
  - [ ] Extract from `CLLocation.horizontalAccuracy`
  - [ ] Include in GPS object: `{lat, lon, accuracy_m, altitude, altitude_accuracy}`
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **C.1.2** Update LocationService
  - [ ] Extract horizontal accuracy on location update
  - [ ] Store in LocationData
  - [ ] Handle GPS unavailable gracefully
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Location\LocationService.swift`

- [ ] **C.1.3** Validate GPS coordinates
  - [ ] Latitude: -90 to 90
  - [ ] Longitude: -180 to 180
  - [ ] Accuracy: > 0
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Location\LocationValidator.swift`

- [ ] **C.1.4** Unit tests
  - [ ] Test accuracy extraction
  - [ ] Test coordinate validation
  - [ ] Test edge cases (no GPS, low accuracy)
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\LocationDataTests.swift`

---

## THEME D: Participants Management

### D.1: Structured Participant Hints

- [ ] **D.1.1** Create ParticipantHint model
  - [ ] Fields: `{display_name: String, role: Optional<String>}`
  - [ ] Example: `{display_name: "Camille", role: "client"}`
  - [ ] Optional roles: "client", "consultant", "observer"
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **D.1.2** Update RecordingMetadata to use structured participants
  - [ ] Change from `participants: [String]` to `participants_hint: [ParticipantHint]`
  - [ ] Preserve existing string data migration path
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **D.1.3** Update storage/persistence
  - [ ] Update Core Data to store structured participants
  - [ ] Migration from old string format
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift`

- [ ] **D.1.4** UI updates for participant input
  - [ ] Update recording editor to capture role
  - [ ] Validation: display_name required if participant provided
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Presentation\Recording\RecordingFormView.swift`

- [ ] **D.1.5** Unit tests
  - [ ] Test participant struct encoding/decoding
  - [ ] Test Core Data migration
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\ParticipantHintTests.swift`

---

## THEME E: Metadata Envelope Construction

### E.1: Complete MetadataEnvelope

- [ ] **E.1.1** Create `MetadataEnvelope.swift` model
  - [ ] Align exactly with ADR-2025-10-03-003 section 2
  - [ ] Required fields:
    - `external_event_id`
    - `recorded_at_iso` (ISO 8601)
    - `timezone`
    - `device` (model, os_version, app_version)
    - `capture` (language, duration_ms, file_size_bytes, gps, place_name, on_device_transcription)
    - `trace_id`
  - [ ] Optional fields:
    - `participants_hint`
    - `user_note`
    - `checksum_sha256`
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataEnvelope.swift`

- [ ] **E.1.2** Validation logic
  - [ ] Validate all required fields present
  - [ ] Validate formats (ISO 8601, timezone, UUID patterns)
  - [ ] Validate GPS coordinates (if present)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataValidator.swift`

- [ ] **E.1.3** Encoding to JSON
  - [ ] JSONEncoder with ISO8601 date formatting
  - [ ] Validate JSON structure matches contract
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataEnvelope.swift`

- [ ] **E.1.4** Integration with RecordingData
  - [ ] Build MetadataEnvelope from RecordingData
  - [ ] Pre-upload validation
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataBuilder.swift`

- [ ] **E.1.5** Unit tests
  - [ ] Test envelope construction
  - [ ] Test validation (required/optional fields)
  - [ ] Test JSON encoding
  - [ ] Test with various locales/timezones
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\MetadataEnvelopeTests.swift`

---

## THEME F: API Key Management

### F.1: Keychain Integration

- [ ] **F.1.1** Create `APIKeyManager.swift`
  - [ ] Store API keys in iOS Keychain
  - [ ] Encrypt with biometric protection (Face ID / Touch ID)
  - [ ] Methods:
    - `save(key: String) -> Bool`
    - `retrieve() -> String?`
    - `delete() -> Bool`
    - `exists() -> Bool`
  - [ ] Use SecureEnclave when available
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Security\APIKeyManager.swift`

- [ ] **F.1.2** Key rotation support
  - [ ] Store key creation timestamp
  - [ ] Track key expiration (if applicable)
  - [ ] Methods:
    - `rotate(newKey: String) -> Bool` (old key revoked server-side)
    - `lastRotatedAt() -> Date?`
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Security\APIKeyManager.swift`

- [ ] **F.1.3** Keychain error handling
  - [ ] Handle biometric auth failures
  - [ ] Handle Keychain unavailable
  - [ ] Graceful fallback (prompt re-auth)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Security\APIKeyManager.swift`

- [ ] **F.1.4** Unit tests (Keychain mocking)
  - [ ] Test save/retrieve cycle
  - [ ] Test biometric protection
  - [ ] Test rotation
  - [ ] Test error cases
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\APIKeyManagerTests.swift`

---

## THEME G: Transcript API Client

### G.1: TranscriptAPIClient Structure

- [ ] **G.1.1** Create `TranscriptAPIClient.swift`
  - [ ] Base URL configuration (staging/prod)
  - [ ] Authentication header: `Authorization: ApiKey <token>`
  - [ ] HTTP client (URLSession with custom delegate)
  - [ ] Error handling with StandardErrorResponse
  - [ ] Timeout: 300s for upload, 2min for processing
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.1.2** Create protocol
  - [ ] Define `TranscriptAPIClientProtocol` for testability
  - [ ] Dependency injection support
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClientProtocol.swift`

---

### G.2: Authentication Endpoints

- [ ] **G.2.1** Implement `/auth/new` endpoint
  - [ ] Method: `GET /auth/new?never_expires=true`
  - [ ] Response: API key token
  - [ ] Purpose: Initial setup / new device
  - [ ] Error handling: 401 (invalid), 429 (rate limit)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.2.2** Implement `/auth/renew` endpoint
  - [ ] Method: `GET /auth/renew?never_expires=true`
  - [ ] Response: New API key (old key revoked)
  - [ ] Purpose: Key rotation (recommended every 90 days)
  - [ ] Error handling: 401 (expired key)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.2.3** Implement `/auth/revoke` endpoint
  - [ ] Method: `GET /auth/revoke?api_key=<key>`
  - [ ] Purpose: Immediate revocation on compromise
  - [ ] Error handling: 400 (invalid key)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.2.4** Implement `/auth/logs` endpoint
  - [ ] Method: `GET /auth/logs`
  - [ ] Response: Recent API key usage logs
  - [ ] Purpose: Security audit / usage monitoring
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.2.5** Unit tests
  - [ ] Test successful auth flows
  - [ ] Test error responses
  - [ ] Test rate limiting (429)
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\TranscriptAuthTests.swift`

---

### G.3: Two-Phase Upload Flow (Option A)

- [ ] **G.3.1** Implement `/v1/jobs/init` endpoint
  - [ ] Method: `POST /v1/jobs/init`
  - [ ] Request: MetadataEnvelope JSON
  - [ ] Response: `{job_id, upload_url (presigned), expires_at, max_file_size_bytes}`
  - [ ] Headers: `Authorization: ApiKey <token>`, `Content-Type: application/json`
  - [ ] Error handling:
    - `400` validation_error (metadata validation failed)
    - `400` missing_required_field
    - `401` unauthorized (invalid API key)
    - `429` rate_limit_exceeded (>10/min)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.3.2** Implement presigned URL upload
  - [ ] Method: `PUT <presigned_url>`
  - [ ] Request: Binary audio file
  - [ ] Headers: `Content-Type: audio/m4a`, `Content-MD5: <base64-md5>`
  - [ ] Supported formats: m4a (preferred), wav, mp3, flac, ogg
  - [ ] Max size: 500MB (error 413 if exceeded)
  - [ ] Timeout: 300s
  - [ ] Upload progress tracking (for UI)
  - [ ] Error handling:
    - `400` invalid_audio_format
    - `413` payload_too_large
    - `408` request_timeout
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.3.3** Implement `/v1/jobs/{job_id}/commit` endpoint
  - [ ] Method: `POST /v1/jobs/{job_id}/commit`
  - [ ] Request: `{checksum_sha256, file_size_bytes}`
  - [ ] Response: `{status: "queued", estimated_completion_at}`
  - [ ] Headers: `Authorization: ApiKey <token>`
  - [ ] Error handling:
    - `422` checksum_mismatch (retry once)
    - `422` invalid_presigned_url
    - `404` job not found
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.3.4** SHA-256 checksum calculation
  - [ ] Create `SHA256Calculator.swift`
  - [ ] Calculate SHA256 before upload (on device)
  - [ ] Format: hexadecimal string (lowercase)
  - [ ] Use CommonCrypto or CryptoKit
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Security\SHA256Calculator.swift`

---

### G.4: Alternative: Multipart Upload (Option B - Fallback)

- [ ] **G.4.1** Implement `/v1/jobs` multipart endpoint
  - [ ] Method: `POST /v1/jobs`
  - [ ] Request: multipart/form-data with metadata + audio_file
  - [ ] Response: `{job_id, status, checksum_sha256}`
  - [ ] Supported as fallback if presigned URL unavailable
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.4.2** Fallback logic
  - [ ] Try two-phase upload first
  - [ ] On 5xx errors, fall back to multipart
  - [ ] Log fallback usage
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

---

### G.5: Job Status Polling

- [ ] **G.5.1** Implement `/v1/jobs/{job_id}` endpoint
  - [ ] Method: `GET /v1/jobs/{job_id}`
  - [ ] Response: `{job_id, external_event_id, status, progress_percent, created_at, updated_at, completed_at, package_uri, error}`
  - [ ] Status values: `queued`, `processing`, `completed`, `failed`
  - [ ] Headers: `Authorization: ApiKey <token>`
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.5.2** Polling strategy
  - [ ] Status "queued" or "processing":
    - Poll every 5s for first minute
    - Then every 15s for next 5 minutes
    - Then every 30s until completion or timeout
    - Max polling duration: 3 hours
  - [ ] Status "completed":
    - Retrieve `package_uri`
    - Download result if needed
    - Mark job as completed
  - [ ] Status "failed":
    - Check error code for remediation
    - Allow manual retry
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **G.5.3** Health check
  - [ ] Implement `/v1/health/ready` endpoint
  - [ ] Call before job creation
  - [ ] Cache result for 30s to avoid excessive calls
  - [ ] If 503: display user-friendly message with retry estimate
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

---

## THEME H: Retry & Error Handling

### H.1: Exponential Backoff Strategy

- [ ] **H.1.1** Implement `RetryStrategy.swift`
  - [ ] Max retries: 3
  - [ ] Backoff formula: `min(max_delay, base_delay * 2^attempt) + random(0, jitter)`
  - [ ] Attempt 1: immediate
  - [ ] Attempt 2: 2s + random(0-1s)
  - [ ] Attempt 3: 4s + random(0-2s)
  - [ ] Attempt 4: 8s + random(0-4s)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\RetryStrategy.swift`

- [ ] **H.1.2** Integrate with TranscriptAPIClient
  - [ ] Apply retry logic to all network calls
  - [ ] Non-retryable errors: 400, 401, 403, 413, 422
  - [ ] Retryable errors: 408, 429, 500, 502, 503, 504
  - [ ] Network errors (DNS, timeout): Full retry cycle
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

- [ ] **H.1.3** Special case handling
  - [ ] 429 (Rate Limit): Respect `Retry-After` header, max 3 retries
  - [ ] 503 (Maintenance): Respect `Retry-After` header, max 1 retry then queue locally
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\RetryStrategy.swift`

- [ ] **H.1.4** Unit tests
  - [ ] Test backoff calculation
  - [ ] Test retry decision logic
  - [ ] Test special cases (rate limit, maintenance)
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\RetryStrategyTests.swift`

---

### H.2: Error Response Handling

- [ ] **H.2.1** Create error models
  - [ ] `StandardErrorResponse`: `{error: {code, message, details, trace_id, retry_after, documentation_url}}`
  - [ ] Map HTTP status → error code
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\ErrorModels.swift`

- [ ] **H.2.2** User-friendly error messages
  - [ ] Map error codes to localized strings
  - [ ] 400: "Invalid data — check your input"
  - [ ] 401: "Authentication failed — please sign in again"
  - [ ] 408: "Upload timed out — please retry"
  - [ ] 429: "Too many requests — please wait before retrying"
  - [ ] 500+: "Server error — please try again later"
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\ErrorMessages.swift`

- [ ] **H.2.3** Logging error context
  - [ ] Log error code, message, details
  - [ ] Include trace_id for support debugging
  - [ ] Include request/response headers (sanitized)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift`

---

## THEME I: Job Tracking & Local Persistence

### I.1: Job Status Tracking

- [ ] **I.1.1** Create `TranscriptJob` Core Data entity
  - [ ] Fields:
    - `jobId` (UUID, primary key)
    - `externalEventId` (String, indexed)
    - `recordingId` (FK to RecordingData)
    - `status` (String: queued/processing/completed/failed)
    - `statusDetails` (optional)
    - `createdAt`, `updatedAt`, `completedAt` (Dates)
    - `packageUri` (optional)
    - `errorCode`, `errorMessage` (optional)
    - `lastPolledAt`, `nextPollAt` (for retry scheduling)
    - `attemptCount` (Int16)
    - `uploadedBytes`, `totalBytes` (for progress)
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\ManagedObjects\TranscriptJobEntity.swift`

- [ ] **I.1.2** Update RecordingData model
  - [ ] Add relationship: `transcriptJobs` (one-to-many)
  - [ ] Track job status with recording
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift`

- [ ] **I.1.3** StorageService methods
  - [ ] `saveTranscriptJob(_ job: TranscriptJob) -> Bool`
  - [ ] `getTranscriptJob(by jobId: String) -> TranscriptJob?`
  - [ ] `getTranscriptJob(by externalEventId: String) -> TranscriptJob?`
  - [ ] `updateTranscriptJobStatus(_ jobId: String, status: String) -> Bool`
  - [ ] `getPendingTranscriptJobs() -> [TranscriptJob]`
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift`

- [ ] **I.1.4** Unit tests
  - [ ] Test job creation and persistence
  - [ ] Test status updates
  - [ ] Test fetching by jobId/externalEventId
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\StorageServiceTests.swift`

---

### I.2: Background Job Processing

- [ ] **I.2.1** Create `TranscriptJobProcessor.swift`
  - [ ] Scheduled task to poll pending jobs
  - [ ] Background URL session support
  - [ ] Run every 30 seconds when jobs pending
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Background\TranscriptJobProcessor.swift`

- [ ] **I.2.2** Polling & retry logic
  - [ ] Fetch job status via `/v1/jobs/{job_id}`
  - [ ] Update local job status
  - [ ] On completion: store package_uri (if available)
  - [ ] On failure: check error code, mark as "needs_attention"
  - [ ] Respect nextPollAt for scheduled retries
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Background\TranscriptJobProcessor.swift`

- [ ] **I.2.3** User notifications
  - [ ] On completion: Local notification "Transcription ready"
  - [ ] On failure: Local notification "Transcription failed"
  - [ ] Show retry option
  - [ ] File: `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Notifications\NotificationManager.swift`

---

## THEME J: Integration Testing

### J.1: Unit Test Suite

- [ ] **J.1.1** Metadata generation tests
  - [ ] external_event_id format
  - [ ] trace_id UUID format
  - [ ] timezone IANA format
  - [ ] Device info capture
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\MetadataGenerationTests.swift`

- [ ] **J.1.2** API client tests
  - [ ] Mock URLSession
  - [ ] Test /auth/new, /auth/renew, /auth/revoke
  - [ ] Test /v1/jobs/init (success + error cases)
  - [ ] Test /v1/jobs/{id}/commit
  - [ ] Test /v1/jobs/{id} polling
  - [ ] Test /v1/health/ready
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\TranscriptAPIClientTests.swift`

- [ ] **J.1.3** Retry logic tests
  - [ ] Exponential backoff calculation
  - [ ] Error classification (retryable vs non-retryable)
  - [ ] Rate limit handling
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\RetryStrategyTests.swift`

- [ ] **J.1.4** Storage tests
  - [ ] Job persistence
  - [ ] Status updates
  - [ ] Fetch queries
  - [ ] File: `F:\MesDevs\mneia-lab\Tests\TranscriptJobStorageTests.swift`

---

### J.2: Integration Tests (with Transcript Staging)

- [ ] **J.2.1** Setup Transcript staging environment
  - [ ] Deploy Transcript to staging.example.com
  - [ ] Generate test API key
  - [ ] Configure in iOS app (environment variable or config)
  - [ ] File: `F:\MesDevs\mneia-lab\.env.staging`

- [ ] **J.2.2** End-to-end upload test
  - [ ] Create recording with full metadata
  - [ ] Generate API key via /auth/new
  - [ ] Call /v1/jobs/init → get presigned URL
  - [ ] Upload audio to presigned URL
  - [ ] Call /v1/jobs/{id}/commit with checksum
  - [ ] Poll /v1/jobs/{id} until completion
  - [ ] Verify response includes external_event_id + trace_id
  - [ ] Script: `F:\MesDevs\mneia-lab\Scripts\test-e2e-upload.swift`

- [ ] **J.2.3** Error scenario testing
  - [ ] Invalid metadata → 400 validation_error
  - [ ] Expired API key → 401 unauthorized
  - [ ] Rate limit exceeded → 429 + Retry-After
  - [ ] Checksum mismatch → 422 + retry
  - [ ] Server error → 500 + retry
  - [ ] Script: `F:\MesDevs\mneia-lab\Scripts\test-error-scenarios.swift`

- [ ] **J.2.4** Retry testing
  - [ ] Simulate transient failures (503)
  - [ ] Verify exponential backoff
  - [ ] Verify success after retries
  - [ ] Script: `F:\MesDevs\mneia-lab\Scripts\test-retries.swift`

---

## THEME K: Documentation & Guides

### K.1: Implementation Documentation

- [ ] **K.1.1** Create API client guide
  - [ ] Overview of TranscriptAPIClient
  - [ ] Authentication flow
  - [ ] Upload flow (two-phase)
  - [ ] Error handling & retry strategy
  - [ ] File: `F:\MesDevs\mneia-lab\docs\TRANSCRIPT_API_CLIENT.md`

- [ ] **K.1.2** Create metadata guide
  - [ ] MetadataEnvelope structure
  - [ ] Field requirements (required vs optional)
  - [ ] Examples with real data
  - [ ] File: `F:\MesDevs\mneia-lab\docs\METADATA_ENVELOPE.md`

- [ ] **K.1.3** Keychain integration guide
  - [ ] API key storage best practices
  - [ ] Biometric protection
  - [ ] Key rotation workflow
  - [ ] File: `F:\MesDevs\mneia-lab\docs\API_KEY_MANAGEMENT.md`

---

### K.2: Developer Guide

- [ ] **K.2.1** Setup guide for developers
  - [ ] Clone repo
  - [ ] Install dependencies
  - [ ] Configure staging environment
  - [ ] Run unit tests
  - [ ] File: `F:\MesDevs\mneia-lab\docs\DEVELOPER_SETUP.md`

- [ ] **K.2.2** Testing guide
  - [ ] Running unit tests
  - [ ] Running integration tests with staging
  - [ ] Debugging API issues
  - [ ] File: `F:\MesDevs\mneia-lab\docs\TESTING_GUIDE.md`

---

## THEME L: Code Review & Quality

### L.1: Code Review Checklist

- [ ] **L.1.1** Self-review before submission
  - [ ] All metadata fields captured per ADR-2025-10-03-003
  - [ ] Checksum calculated and passed
  - [ ] trace_id and external_event_id included
  - [ ] Error handling for all HTTP status codes
  - [ ] Unit tests written (>80% coverage)
  - [ ] No hardcoded API URLs (use config)
  - [ ] Keychain used for API key storage
  - [ ] Logging includes trace_id

- [ ] **L.1.2** Code style & best practices
  - [ ] SwiftLint compliance
  - [ ] No force unwraps (unless documented)
  - [ ] No capture of self without [weak self]
  - [ ] Memory leak testing
  - [ ] Battery/network efficiency reviewed

---

---

# 🏗️ PROJECT 2: TRANSCRIPT SERVICE

## Priority Level: 🟢 P1 - ENHANCEMENTS (Already Stable)

### Timeline: Week 2-3 (Nov 2-16, 2025)

---

## THEME A: Documentation & Setup Guides

### A.1: iOS Integration Documentation

- [ ] **A.1.1** Create iOS authentication guide
  - [ ] Overview of /auth/new, /auth/renew, /auth/revoke, /auth/logs
  - [ ] Rate limiting (5/min)
  - [ ] Key format and storage
  - [ ] Examples with curl + Swift
  - [ ] File: `F:\MesDevs\transcript\docs\IOS_AUTHENTICATION_GUIDE.md`

- [ ] **A.1.2** Update OpenAPI spec
  - [ ] Ensure /auth/* endpoints documented
  - [ ] Add rate limiting info
  - [ ] Add examples
  - [ ] File: `F:\MesDevs\transcript\docs\api\transcript-api.openapi.yaml`

- [ ] **A.1.3** Create API key setup guide
  - [ ] How to obtain first API key
  - [ ] How to rotate keys
  - [ ] How to monitor usage
  - [ ] File: `F:\MesDevs\transcript\docs\API_KEY_SETUP.md`

---

### A.2: Contract Verification

- [ ] **A.2.1** Verify external_event_id format
  - [ ] Check validation: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`
  - [ ] Document format in API docs
  - [ ] File: `F:\MesDevs\transcript\server\metadata_schema.py:60-66`

- [ ] **A.2.2** Verify trace_id propagation
  - [ ] trace_id extracted from metadata
  - [ ] trace_id included in Redis messages
  - [ ] trace_id included in logs
  - [ ] File: `F:\MesDevs\transcript\server\redis_notifier.py`

- [ ] **A.2.3** Verify archive structure
  - [ ] Root folder: `<external_event_id>`
  - [ ] Files: `conversation.json`, `checksums.sha256`
  - [ ] Directories: `media/`, `artifacts/`
  - [ ] File: `F:\MesDevs\transcript\server\archive_builder.py:64-151`

---

## THEME B: Security Enhancements (Optional)

### B.1: Advanced Authorization (Scope-based)

- [ ] **B.1.1** Add scope support to API keys
  - [ ] Define scopes: `job:create`, `job:read`, `job:delete`, `admin:*`
  - [ ] Update APIKey model to support scopes
  - [ ] File: `F:\MesDevs\transcript\server\models.py`

- [ ] **B.1.2** Scope validation middleware
  - [ ] Check required scope per endpoint
  - [ ] Return 403 Forbidden if scope missing
  - [ ] File: `F:\MesDevs\transcript\server\auth.py`

- [ ] **B.1.3** Tests for authorization
  - [ ] Test endpoint access with wrong scope
  - [ ] Test endpoint access with correct scope
  - [ ] File: `F:\MesDevs\transcript\tests\test_authorization.py`

---

### B.2: Audit Logging

- [ ] **B.2.1** Log API key operations
  - [ ] /auth/new: log key creation
  - [ ] /auth/renew: log key rotation
  - [ ] /auth/revoke: log key revocation
  - [ ] /auth/logs: query operations
  - [ ] File: `F:\MesDevs\transcript\server\audit_logger.py`

- [ ] **B.2.2** Log job operations
  - [ ] POST /v1/jobs/init: log by external_event_id
  - [ ] POST /v1/jobs/{id}/commit: log by job_id
  - [ ] Errors logged with trace_id
  - [ ] File: `F:\MesDevs\transcript\server\audit_logger.py`

- [ ] **B.2.3** Query audit logs
  - [ ] Extend /auth/logs to include job operations
  - [ ] Filter by date, error code, external_event_id
  - [ ] File: `F:\MesDevs\transcript\server\auth.py`

---

## THEME C: Production Hardening (Optional)

### C.1: Rate Limiting

- [ ] **C.1.1** Implement Redis-based rate limiting
  - [ ] 10 requests/min per API key (for /v1/jobs*)
  - [ ] 5 requests/min for /auth/* endpoints
  - [ ] Custom limits per key (if tier-based pricing)
  - [ ] File: `F:\MesDevs\transcript\server\rate_limiter.py`

- [ ] **C.1.2** Rate limit middleware
  - [ ] Check limit on each request
  - [ ] Return 429 with Retry-After header
  - [ ] File: `F:\MesDevs\transcript\server\main.py`

- [ ] **C.1.3** Tests
  - [ ] Test rate limit enforcement
  - [ ] Test Retry-After header
  - [ ] File: `F:\MesDevs\transcript\tests\test_rate_limiting.py`

---

---

# 📦 PROJECT 3: MY-RAG INGESTION PIPELINE

## Priority Level: 🟢 P2 - ROBUSTNESS IMPROVEMENTS

### Timeline: Week 3-4 (Nov 9-23, 2025)

---

## THEME A: Critical Alignment Fixes

### A.1: external_event_id Validation

- [x] **A.1.1** Strengthen Redis message validation ✅ DONE (2025-10-29)
  - [x] Current: `^[A-Za-z0-9._:-]+$`
  - [x] Target: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$` (strict pattern)
  - [x] Validate ISO8601 timestamp component
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:49`

- [x] **A.1.2** Update consumer validation ✅ DONE (2025-10-29)
  - [x] Parse timestamp from external_event_id
  - [x] Validate timestamp is within reasonable range (not future)
  - [x] Reject if pattern doesn't match
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:125-160` (validator added)

- [ ] **A.1.3** Unit tests
  - [ ] Test strict pattern matching
  - [ ] Test timestamp validation
  - [ ] Test rejection of invalid patterns
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_external_event_id.py`

---

### A.2: trace_id Enforcement

- [x] **A.2.1** Make trace_id REQUIRED ✅ DONE (2025-10-29)
  - [x] Current: Optional in RedisMessageParser
  - [x] Target: Required (enforce in validation)
  - [x] UUID validation added
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:34-47`

- [x] **A.2.2** Propagate trace_id consistently ✅ VERIFIED (2025-10-29)
  - [x] Include in all logs (already done ✓)
  - [x] Include in all Qdrant metadata (verified ✓)
  - [x] Include in database job records (already done ✓)
  - [x] Include in DLQ messages (already done ✓)
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py`

- [x] **A.2.3** Metrics for trace_id presence ✅ VERIFIED (2025-10-29)
  - [x] Count by presence: with trace_id vs without
  - [x] Alert if > 10% missing trace_id
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\metrics.py:107-111,204-206` (already implemented)

---

## THEME B: Distributed Locking for Duplicate Detection

### B.1: Redis-based Distributed Lock

- [x] **B.1.1** Create `DistributedLock` helper ✅ DONE (2025-10-29)
  - [x] Use Redis SET with NX + EX (expire)
  - [x] Key format: `lock:external_event_id:<external_event_id>`
  - [x] Lock duration: 5 minutes (configurable)
  - [x] Context manager support added
  - [x] Fail-open on Redis errors
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\distributed_lock.py` (246 lines created)

- [ ] **B.1.2** Acquire lock before processing
  - [ ] Try to acquire lock
  - [ ] If lock fails: message already being processed elsewhere
  - [ ] Queue for retry in 30 seconds
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:180-210` (integration pending)

- [ ] **B.1.3** Release lock on completion
  - [ ] Release after successful ingestion
  - [ ] Release on error (with backoff for retry)
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:370-380` (integration pending)

- [ ] **B.1.4** Tests
  - [ ] Test lock acquisition
  - [ ] Test lock release
  - [ ] Test concurrent processing prevention
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_distributed_lock.py`

---

## THEME C: Retry Backoff Strategy

### C.1: Implement Exponential Backoff

- [x] **C.1.1** Create `RetryScheduler.py` ✅ DONE (2025-10-29)
  - [x] Calculate next retry time based on retry_count
  - [x] Formula: `min(max_delay, base_delay * 2^retry_count) + jitter`
  - [x] Base delay: 5 seconds
  - [x] Max delay: 300 seconds (5 minutes)
  - [x] Jitter: random(0, base_delay)
  - [x] Max retries: 10
  - [x] Redis Sorted Set implementation
  - [x] Background worker ready
  - [x] File: `F:\MesDevs\my-RAG\src\ingestion\retry_scheduler.py` (278 lines created)

- [ ] **C.1.2** Integrate with message requeue
  - [ ] Current: Immediately re-processes failed messages
  - [ ] Target: Queue for retry at calculated time
  - [ ] Use Redis sorted set: `key = message_id`, `score = next_retry_timestamp`
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:300-320` (integration pending)

- [ ] **C.1.3** Tests
  - [ ] Test backoff calculation
  - [ ] Test retry scheduling
  - [ ] Test jitter randomness
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_retry_scheduler.py`

---

## THEME D: NLP Mode Detection Improvements

### D.1: Schema Version-based Detection

- [ ] **D.1.1** Use schema_version field
  - [ ] Current: Heuristic detection (look for NLP annotations)
  - [ ] Target: Use schema_version from Redis message
  - [ ] schema_version "1.0" → legacy mode
  - [ ] schema_version "1.1" → enriched mode (sentiment + NER)
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:254-283`

- [ ] **D.1.2** Fallback to heuristic if version missing
  - [ ] If schema_version not in message, use heuristic
  - [ ] Log warning about missing version
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:254-283`

- [ ] **D.1.3** Validate version format
  - [ ] Pattern: `^\d+\.\d+$` (semantic versioning)
  - [ ] Reject invalid versions
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:47`

- [ ] **D.1.4** Tests
  - [ ] Test v1.0 detection
  - [ ] Test v1.1 detection
  - [ ] Test heuristic fallback
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_nlp_mode_detection.py`

---

## THEME E: Producer Metadata Tracking

### E.1: Store Producer Information

- [ ] **E.1.1** Extend IngestionJob model
  - [ ] Add `producer_name: Optional[str]` field
  - [ ] Add `producer_version: Optional[str]` field
  - [ ] Add to database schema
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\models.py`

- [ ] **E.1.2** Extract producer metadata
  - [ ] Parse from Redis message: `message.producer`
  - [ ] Store in job record
  - [ ] Include in logs
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:110-120`

- [ ] **E.1.3** Metrics for producer tracking
  - [ ] Counter: `audio_ingest_by_producer{producer="transcript"}`
  - [ ] Histogram: `audio_ingest_latency_by_producer{producer="transcript"}`
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\metrics.py`

- [ ] **E.1.4** Tests
  - [ ] Test producer info extraction
  - [ ] Test persistence
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_producer_metadata.py`

---

## THEME F: SLA Monitoring & Alerts

### F.1: Prometheus Alert Rules

- [ ] **F.1.1** Create alert rules file
  - [ ] Alert: `AudioIngestAckLatencyHigh` (p95 > 3s warning, > 5s critical)
  - [ ] Alert: `AudioIngestValidationFailureRate` (> 5% over 15 min)
  - [ ] Alert: `AudioIngestRedisPendingHigh` (> 500 entries for > 10 min)
  - [ ] Alert: `AudioIngestDLQBacklog` (> 100 entries for > 5 min)
  - [ ] File: `F:\MesDevs\my-RAG\prometheus\alerts.yml`

- [ ] **F.1.2** Create Grafana dashboard
  - [ ] Panel: Ack latency (p50, p95, p99)
  - [ ] Panel: Success/failure rate
  - [ ] Panel: Messages in-flight
  - [ ] Panel: DLQ backlog
  - [ ] Panel: Checksum validation timing
  - [ ] File: `F:\MesDevs\my-RAG\grafana\dashboards\ingestion-sla.json`

- [ ] **F.1.3** Configure alerting channels
  - [ ] Email to on-call engineer
  - [ ] Slack integration (critical alerts)
  - [ ] PagerDuty for P0 SLA violations
  - [ ] File: `F:\MesDevs\my-RAG\prometheus\alertmanager.yml`

---

## THEME G: Archive Structure Validation

### G.1: Pre-flight Validation

- [ ] **G.1.1** Validate after extraction
  - [ ] Root folder name matches external_event_id
  - [ ] conversation.json exists and is valid
  - [ ] checksums.sha256 exists
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\archive_validator.py:50-120`

- [ ] **G.1.2** Validate file sizes
  - [ ] Each file < 2GB
  - [ ] Total archive < 5GB
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\archive_validator.py:130-160`

- [ ] **G.1.3** Validate directory structure
  - [ ] Optional dirs: `media/`, `artifacts/`, `logs/`
  - [ ] Warn if unexpected directories
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\archive_validator.py:170-200`

- [ ] **G.1.4** Tests
  - [ ] Test valid archive structure
  - [ ] Test missing required files
  - [ ] Test invalid root folder name
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_archive_structure.py`

---

## THEME H: Checksum Validation Enhancements

### H.1: Improve Error Handling

- [ ] **H.1.1** Log checksum mismatches
  - [ ] Include file path
  - [ ] Include expected vs actual hash
  - [ ] Include file size for diagnostics
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\checksum_validator.py:100-120`

- [ ] **H.1.2** Implement corruption recovery
  - [ ] On checksum mismatch: Try once more
  - [ ] If still fails: Route to DLQ
  - [ ] Include file metadata in DLQ for diagnosis
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py:200-210`

- [ ] **H.1.3** Metrics for checksum validation
  - [ ] Counter: `audio_ingest_checksum_failures_total{reason="..."}`
  - [ ] Histogram: `audio_ingest_checksum_duration_seconds`
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\metrics.py`

- [ ] **H.1.4** Tests
  - [ ] Test checksum validation
  - [ ] Test retry on mismatch
  - [ ] Test DLQ routing
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_checksum_validation.py`

---

## THEME I: Observability Enhancements

### I.1: Enhanced Logging

- [ ] **I.1.1** Add context to all logs
  - [ ] Include external_event_id
  - [ ] Include trace_id
  - [ ] Include job_id
  - [ ] Include duration/latency
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py`

- [ ] **I.1.2** Structured logging format
  - [ ] JSON format for ELK/Splunk integration
  - [ ] Timestamp, level, component, message
  - [ ] Metadata (external_event_id, trace_id, job_id)
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\logging_config.py`

- [ ] **I.1.3** Log levels
  - [ ] INFO: Job created, processed, completed
  - [ ] WARNING: Missing optional fields, non-standard schemas
  - [ ] ERROR: Validation failures, retryable errors
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py`

---

### I.2: Distributed Tracing Integration

- [ ] **I.2.1** Add OpenTelemetry instrumentation
  - [ ] Trace ingestion pipeline end-to-end
  - [ ] Include external_event_id as span attribute
  - [ ] Include trace_id as OpenTelemetry trace_id
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\consumer.py`

- [ ] **I.2.2** Export to tracing backend
  - [ ] Configure OTLP exporter (Jaeger or similar)
  - [ ] Verify traces visible in UI
  - [ ] File: `F:\MesDevs\my-RAG\src\ingestion\otel_config.py`

---

## THEME J: Documentation

### J.1: Ingestion Pipeline Documentation

- [ ] **J.1.1** Update pipeline overview
  - [ ] Architecture diagram (input → validation → storage)
  - [ ] Data flow (Redis → Parser → Validator → Qdrant)
  - [ ] Error handling (DLQ routing)
  - [ ] Observability (traces, metrics, logs)
  - [ ] File: `F:\MesDevs\my-RAG\docs\ingestion\PIPELINE_OVERVIEW.md`

- [ ] **J.1.2** Create troubleshooting guide
  - [ ] Common errors and solutions
  - [ ] How to query DLQ
  - [ ] How to replay failed messages
  - [ ] How to check metrics/logs
  - [ ] File: `F:\MesDevs\my-RAG\docs\ingestion\TROUBLESHOOTING.md`

- [ ] **J.1.3** Create runbook for operators
  - [ ] How to monitor ingestion SLAs
  - [ ] How to handle alerts
  - [ ] How to scale consumer
  - [ ] How to perform maintenance
  - [ ] File: `F:\MesDevs\my-RAG\docs\operations\INGESTION_RUNBOOK.md`

---

### J.2: API Contract Documentation

- [ ] **J.2.1** Reference ADR-2025-10-03-003
  - [ ] Link to official contract
  - [ ] Highlight key requirements
  - [ ] Provide examples
  - [ ] File: `F:\MesDevs\my-RAG\docs\ingestion\CONTRACT_REFERENCE.md`

- [ ] **J.2.2** Document Redis message format
  - [ ] Example messages
  - [ ] Field descriptions
  - [ ] Validation rules
  - [ ] File: `F:\MesDevs\my-RAG\docs\ingestion\REDIS_MESSAGE_FORMAT.md`

---

## THEME K: Quality & Testing

### K.1: Integration Test Enhancements

- [ ] **K.1.1** Test with mock Transcript messages
  - [ ] Generate sample messages per ADR spec
  - [ ] Test parsing, validation, storage
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_transcript_integration.py`

- [ ] **K.1.2** Test error scenarios
  - [ ] Missing trace_id
  - [ ] Invalid external_event_id format
  - [ ] Checksum mismatch
  - [ ] Archive structure errors
  - [ ] File: `F:\MesDevs\my-RAG\tests\test_ingestion\test_error_scenarios.py`

- [ ] **K.1.3** Test with real Transcript service (staging)
  - [ ] Upload audio from iOS client
  - [ ] Verify Redis message published
  - [ ] Consume and validate in my-RAG
  - [ ] Verify E2E trace
  - [ ] Script: `F:\MesDevs\my-RAG\scripts\test-e2e-integration.sh`

---

---

# 🔄 CROSS-PROJECT COORDINATION

## THEME A: Integration Testing

- [ ] **A.1** Setup staging environment
  - [ ] iOS: Point to staging.transcript.example.com
  - [ ] Transcript: Deploy to staging
  - [ ] my-RAG: Connect to staging Redis/MinIO
  - [ ] Timeline: Week 2

- [ ] **A.2** E2E test flow
  - [ ] Record audio on iOS (mneia-lab)
  - [ ] Upload via TranscriptAPIClient
  - [ ] Verify Transcript processing
  - [ ] Check Redis message published
  - [ ] Verify my-RAG ingestion
  - [ ] Check trace_id flowing E2E
  - [ ] Timeline: Week 3

- [ ] **A.3** Failure scenario testing
  - [ ] Network failures (retry logic)
  - [ ] Invalid metadata (error messages)
  - [ ] Checksum mismatches (recovery)
  - [ ] Server errors (SLA compliance)
  - [ ] Timeline: Week 4

---

## THEME B: Documentation Synchronization

- [ ] **B.1** Maintain single source of truth
  - [ ] Primary ADR: `my-RAG/docs/adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md`
  - [ ] Mirror in Transcript: Link + copy relevant sections
  - [ ] Mirror in mneia-lab: Link + implementation details
  - [ ] Timeline: Ongoing

- [ ] **B.2** Version API contract
  - [ ] Semantic versioning (major.minor)
  - [ ] Backward compatibility policy
  - [ ] Deprecation warnings
  - [ ] Timeline: Week 4

---

## THEME C: Monitoring & Alerts Setup

- [ ] **C.1** Prometheus/Grafana setup
  - [ ] Deploy Prometheus (if not already done)
  - [ ] Deploy Grafana (if not already done)
  - [ ] Configure scrapers for all three services
  - [ ] Timeline: Week 2

- [ ] **C.2** SLA dashboards
  - [ ] iOS → Transcript latency
  - [ ] Transcript processing latency
  - [ ] Transcript → Redis publish latency
  - [ ] my-RAG ingestion latency (E2E)
  - [ ] Timeline: Week 3

- [ ] **C.3** Alert rules deployment
  - [ ] Deploy alert rules for all projects
  - [ ] Configure notification channels
  - [ ] Test alert firing
  - [ ] Timeline: Week 4

---

---

# 📅 TIMELINE SUMMARY

```
WEEK 1 (Oct 26 - Nov 1)
├─ mneia-lab: Theme A-C (Metadata, device info, GPS)
├─ Transcript: Theme A (Documentation review)
└─ my-RAG: Theme A (external_event_id validation)

WEEK 2 (Nov 2 - Nov 8)
├─ mneia-lab: Theme D-E (Participants, metadata envelope)
├─ Transcript: Theme A (Setup guides)
├─ my-RAG: Theme B (Distributed locking)
└─ Cross: Theme C.1 (Prometheus/Grafana setup)

WEEK 3 (Nov 9 - Nov 15)
├─ mneia-lab: Theme F-G (API key management, API client)
├─ Transcript: Theme B (Security enhancements)
├─ my-RAG: Theme C-D (Retry backoff, NLP detection)
└─ Cross: Theme A.2 (E2E testing setup)

WEEK 4 (Nov 16 - Nov 23)
├─ mneia-lab: Theme H-L (Error handling, testing, review)
├─ Transcript: Theme C (Production hardening - optional)
├─ my-RAG: Theme E-K (Producer tracking, SLA, docs)
└─ Cross: Theme A.3 + B + C (Full E2E + monitoring)

DEPLOYMENT & VALIDATION (Nov 24 - Nov 30)
├─ Stage 1: iOS to Transcript (staging)
├─ Stage 2: Transcript to my-RAG (staging)
├─ Stage 3: Full E2E validation
└─ Stage 4: Production rollout
```

---

---

# 🎯 SUCCESS CRITERIA

## For iOS (mneia-lab):
- [ ] Audio uploads successfully to Transcript staging
- [ ] external_event_id + trace_id generated and included
- [ ] All metadata fields populated per contract
- [ ] API key stored securely in Keychain
- [ ] Retry logic working with exponential backoff
- [ ] >80% unit test coverage
- [ ] Integration tests pass with Transcript staging

## For Transcript:
- [ ] All iOS uploads processed correctly
- [ ] Redis messages published in correct format
- [ ] Archives generated with correct structure
- [ ] external_event_id + trace_id + checksums present
- [ ] No breaking changes to API

## For my-RAG:
- [ ] Consumes all Transcript messages correctly
- [ ] Validation passes for all valid messages
- [ ] DLQ routes invalid/failed messages
- [ ] Metrics show SLA compliance (p95 < 5s)
- [ ] Distributed tracing works E2E
- [ ] Alert rules firing correctly

## Overall E2E:
- [ ] Audio → Transcript → my-RAG → Qdrant complete
- [ ] trace_id flows through all layers (logs visible)
- [ ] Checksum validation passes
- [ ] Error scenarios handled gracefully
- [ ] Production deployment plan documented

---

---

# 📞 CONTACTS & ESCALATION

| Component | Owner | Slack | GitHub |
|-----------|-------|-------|--------|
| mneia-lab (iOS) | iOS Team | @ios-team | mneia-lab repo |
| Transcript | Backend Team | @transcript-team | transcript repo |
| my-RAG | RAG Team | @rag-team | my-RAG repo |
| Integration | Staff Arch | @staff-arch | Integration docs |

**Weekly Sync**: Monday 10:00 UTC (Teams/Slack)
**Escalation**: If blocked, flag in #engineering-urgent
**Review Cycle**: Every Friday 15:00 UTC

---

**Last Updated**: 2025-10-26
**Next Review**: 2025-11-02
**Status**: 🟠 IN PROGRESS - iOS Phase 1 BLOCKED (awaiting implementation)
