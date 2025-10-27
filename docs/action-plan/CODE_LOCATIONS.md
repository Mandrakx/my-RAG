# Code Locations & File References

Quick reference for where to implement each action item.

---

## 🍎 MNEIA-LAB (iOS - mneia-lab)

### Theme A: Identifier & Metadata Generation

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| ExternalEventIdGenerator | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Identifiers\ExternalEventIdGenerator.swift` | NEW | 📝 To Create |
| TraceIdGenerator | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Tracing\TraceIdGenerator.swift` | NEW | 📝 To Create |
| RecordingData model (extend) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\ExternalEventIdGeneratorTests.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\TraceIdGeneratorTests.swift` | NEW | 📝 To Create |

### Theme B: Device Information Capture

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| DeviceInfoCapture | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Device\DeviceInfoCapture.swift` | NEW | 📝 To Create |
| RecordingMetadata (add device) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| StorageService | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\DeviceInfoCaptureTests.swift` | NEW | 📝 To Create |

### Theme C: GPS Enhancement

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| LocationData model | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| LocationService | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Location\LocationService.swift` | MODIFY | 📝 Pending |
| LocationValidator | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Location\LocationValidator.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\LocationDataTests.swift` | NEW | 📝 To Create |

### Theme D: Participants Management

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| ParticipantHint model | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| RecordingMetadata (update) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| StorageService | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift` | MODIFY | 📝 Pending |
| UI updates | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Presentation\Recording\RecordingFormView.swift` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\ParticipantHintTests.swift` | NEW | 📝 To Create |

### Theme E: Metadata Envelope

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| MetadataEnvelope model | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataEnvelope.swift` | NEW | 📝 To Create |
| MetadataValidator | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataValidator.swift` | NEW | 📝 To Create |
| MetadataBuilder | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\MetadataBuilder.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\MetadataEnvelopeTests.swift` | NEW | 📝 To Create |

### Theme F: API Key Management

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| APIKeyManager | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Security\APIKeyManager.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\APIKeyManagerTests.swift` | NEW | 📝 To Create |

### Theme G: Transcript API Client

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| TranscriptAPIClient | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift` | NEW | 📝 To Create |
| TranscriptAPIClientProtocol | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClientProtocol.swift` | NEW | 📝 To Create |
| ErrorModels | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\ErrorModels.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\TranscriptAPIClientTests.swift` | NEW | 📝 To Create |
| Unit tests (Auth) | `F:\MesDevs\mneia-lab\Tests\TranscriptAuthTests.swift` | NEW | 📝 To Create |

### Theme H: Retry & Error Handling

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| RetryStrategy | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\RetryStrategy.swift` | NEW | 📝 To Create |
| TranscriptAPIClient (integrate) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\TranscriptAPIClient.swift` | MODIFY | 📝 Pending |
| ErrorMessages | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\API\ErrorMessages.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\RetryStrategyTests.swift` | NEW | 📝 To Create |

### Theme I: Job Tracking & Local Persistence

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| TranscriptJobEntity | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\ManagedObjects\TranscriptJobEntity.swift` | NEW | 📝 To Create |
| RecordingData (add relationship) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Shared\Models\CoreModels.swift` | MODIFY | 📝 Pending |
| StorageService (add methods) | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Storage\StorageService.swift` | MODIFY | 📝 Pending |
| TranscriptJobProcessor | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Background\TranscriptJobProcessor.swift` | NEW | 📝 To Create |
| NotificationManager | `F:\MesDevs\mneia-lab\mneia-ios\mneia\Core\Notifications\NotificationManager.swift` | NEW | 📝 To Create |
| Unit tests | `F:\MesDevs\mneia-lab\Tests\StorageServiceTests.swift` | MODIFY | 📝 Pending |

### Theme J: Integration Testing

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Metadata tests | `F:\MesDevs\mneia-lab\Tests\MetadataGenerationTests.swift` | NEW | 📝 To Create |
| API client tests | `F:\MesDevs\mneia-lab\Tests\TranscriptAPIClientTests.swift` | NEW | 📝 To Create |
| Retry tests | `F:\MesDevs\mneia-lab\Tests\RetryStrategyTests.swift` | NEW | 📝 To Create |
| Storage tests | `F:\MesDevs\mneia-lab\Tests\TranscriptJobStorageTests.swift` | NEW | 📝 To Create |
| E2E test script | `F:\MesDevs\mneia-lab\Scripts\test-e2e-upload.swift` | NEW | 📝 To Create |
| Error scenario script | `F:\MesDevs\mneia-lab\Scripts\test-error-scenarios.swift` | NEW | 📝 To Create |
| Retry test script | `F:\MesDevs\mneia-lab\Scripts\test-retries.swift` | NEW | 📝 To Create |

### Theme K: Documentation

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| API client guide | `F:\MesDevs\mneia-lab\docs\TRANSCRIPT_API_CLIENT.md` | NEW | 📝 To Create |
| Metadata guide | `F:\MesDevs\mneia-lab\docs\METADATA_ENVELOPE.md` | NEW | 📝 To Create |
| Keychain guide | `F:\MesDevs\mneia-lab\docs\API_KEY_MANAGEMENT.md` | NEW | 📝 To Create |
| Developer setup | `F:\MesDevs\mneia-lab\docs\DEVELOPER_SETUP.md` | NEW | 📝 To Create |
| Testing guide | `F:\MesDevs\mneia-lab\docs\TESTING_GUIDE.md` | NEW | 📝 To Create |

---

## 🏗️ TRANSCRIPT SERVICE

### Theme A: Documentation & Setup

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| iOS auth guide | `F:\MesDevs\transcript\docs\IOS_AUTHENTICATION_GUIDE.md` | NEW | 📝 To Create |
| OpenAPI spec (update) | `F:\MesDevs\transcript\docs\api\transcript-api.openapi.yaml` | MODIFY | 📝 Pending |
| API key setup guide | `F:\MesDevs\transcript\docs\API_KEY_SETUP.md` | NEW | 📝 To Create |

### Theme B: Security Enhancements

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| APIKey model (add scopes) | `F:\MesDevs\transcript\server\models.py` | MODIFY | 📝 Pending |
| Auth middleware | `F:\MesDevs\transcript\server\auth.py` | MODIFY | 📝 Pending |
| Authorization tests | `F:\MesDevs\transcript\tests\test_authorization.py` | NEW | 📝 To Create |
| Audit logger | `F:\MesDevs\transcript\server\audit_logger.py` | NEW | 📝 To Create |

### Theme C: Production Hardening

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Rate limiter | `F:\MesDevs\transcript\server\rate_limiter.py` | NEW | 📝 To Create |
| Rate limit middleware | `F:\MesDevs\transcript\server\main.py` | MODIFY | 📝 Pending |
| Rate limit tests | `F:\MesDevs\transcript\tests\test_rate_limiting.py` | NEW | 📝 To Create |

---

## 📦 MY-RAG INGESTION PIPELINE

### Theme A: Alignment Fixes

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Redis message parser (strengthen) | `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:49` | MODIFY | ✅ DONE |
| Transcript validator (update pattern) | `F:\MesDevs\my-RAG\src\ingestion\transcript_validator.py:130` | MODIFY | ✅ DONE |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_external_event_id.py` | NEW | 📝 To Create |
| trace_id enforcement | `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:34` | MODIFY | 📝 Pending |

### Theme B: Distributed Locking

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| DistributedLock helper | `F:\MesDevs\my-RAG\src\ingestion\distributed_lock.py` | NEW | 📝 To Create |
| Consumer (integrate lock) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:180-210` | MODIFY | 📝 Pending |
| Consumer (release lock) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:370-380` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_distributed_lock.py` | NEW | 📝 To Create |

### Theme C: Retry Backoff

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| RetryScheduler | `F:\MesDevs\my-RAG\src\ingestion\retry_scheduler.py` | NEW | 📝 To Create |
| Consumer (integrate retry) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:300-320` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_retry_scheduler.py` | NEW | 📝 To Create |

### Theme D: NLP Mode Detection

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Consumer (use schema_version) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:254-283` | MODIFY | 📝 Pending |
| Redis message parser (validate version) | `F:\MesDevs\my-RAG\src\ingestion\redis_message_parser.py:47` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_nlp_mode_detection.py` | NEW | 📝 To Create |

### Theme E: Producer Metadata

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| IngestionJob model (add fields) | `F:\MesDevs\my-RAG\src\ingestion\models.py` | MODIFY | 📝 Pending |
| Consumer (extract producer) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:110-120` | MODIFY | 📝 Pending |
| Metrics (add producer tracking) | `F:\MesDevs\my-RAG\src\ingestion\metrics.py` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_producer_metadata.py` | NEW | 📝 To Create |

### Theme F: SLA Monitoring

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Prometheus alerts | `F:\MesDevs\my-RAG\prometheus\alerts.yml` | NEW | 📝 To Create |
| Grafana dashboard | `F:\MesDevs\my-RAG\grafana\dashboards\ingestion-sla.json` | NEW | 📝 To Create |
| Alert manager config | `F:\MesDevs\my-RAG\prometheus\alertmanager.yml` | NEW | 📝 To Create |

### Theme G: Archive Validation

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Archive validator (enhance) | `F:\MesDevs\my-RAG\src\ingestion\archive_validator.py:50-200` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_archive_structure.py` | NEW | 📝 To Create |

### Theme H: Checksum Validation

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Checksum validator (enhance) | `F:\MesDevs\my-RAG\src\ingestion\checksum_validator.py:100-120` | MODIFY | 📝 Pending |
| Consumer (integrate recovery) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py:200-210` | MODIFY | 📝 Pending |
| Metrics (add checksum tracking) | `F:\MesDevs\my-RAG\src\ingestion\metrics.py` | MODIFY | 📝 Pending |
| Unit tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_checksum_validation.py` | NEW | 📝 To Create |

### Theme I: Observability

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Consumer (enhance logging) | `F:\MesDevs\my-RAG\src\ingestion\consumer.py` | MODIFY | 📝 Pending |
| Logging config | `F:\MesDevs\my-RAG\src\ingestion\logging_config.py` | NEW | 📝 To Create |
| OpenTelemetry config | `F:\MesDevs\my-RAG\src\ingestion\otel_config.py` | NEW | 📝 To Create |

### Theme J: Documentation

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Pipeline overview | `F:\MesDevs\my-RAG\docs\ingestion\PIPELINE_OVERVIEW.md` | MODIFY | 📝 Pending |
| Troubleshooting guide | `F:\MesDevs\my-RAG\docs\ingestion\TROUBLESHOOTING.md` | NEW | 📝 To Create |
| Operations runbook | `F:\MesDevs\my-RAG\docs\operations\INGESTION_RUNBOOK.md` | NEW | 📝 To Create |
| Contract reference | `F:\MesDevs\my-RAG\docs\ingestion\CONTRACT_REFERENCE.md` | NEW | 📝 To Create |
| Redis message format | `F:\MesDevs\my-RAG\docs\ingestion\REDIS_MESSAGE_FORMAT.md` | NEW | 📝 To Create |

### Theme K: Testing

| Item | File Location | Type | Status |
|------|---------------|------|--------|
| Transcript integration tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_transcript_integration.py` | NEW | 📝 To Create |
| Error scenario tests | `F:\MesDevs\my-RAG\tests\test_ingestion\test_error_scenarios.py` | NEW | 📝 To Create |
| E2E integration script | `F:\MesDevs\my-RAG\scripts\test-e2e-integration.sh` | NEW | 📝 To Create |

---

## 📝 Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Already done / completed |
| 📝 | To do / needs implementation |
| 🔄 | In progress |
| 🚨 | Blocked / urgent |

---

**Last Updated**: 2025-10-26
**Next Update**: Weekly (every Friday)
