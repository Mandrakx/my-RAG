# Actions Restantes - Plan d'Action Cross-Cutting

**Date**: 2025-10-29
**Basé sur**: `docs/action-plan/2025-10-26-fix-alignment-cross.md`
**Status**: 📊 En cours de suivi

---

## 📊 Vue d'Ensemble Globale

| Projet | Total Actions | Complétées | Restantes | % Complet |
|--------|---------------|------------|-----------|-----------|
| **iOS (mneia-lab)** | ~120 | 0 | ~120 | 0% |
| **Transcript** | 15 | 6 | 9 | 40% |
| **my-RAG** | 80 | 8 | 72 | 10% |
| **Cross-Project** | 12 | 0 | 12 | 0% |
| **TOTAL** | ~227 | 14 | ~213 | 6% |

---

## 🍎 PROJECT 1: MNEIA-LAB (iOS) - 120 Actions Restantes

### Statut Global: 🔴 BLOQUANT CRITIQUE - 0% Complete

**Timeline**: Semaines 1-2 (26 oct - 9 nov 2025)
**Priorité**: P0 - CRITIQUE (Bloque tout le reste)

### Actions par Thème

#### Theme A: Identifier & Metadata Generation (8 actions)
- [ ] A.1.1: Create ExternalEventIdGenerator.swift
- [ ] A.1.2: Integrate into RecordingData model
- [ ] A.1.3: Unit test suite
- [ ] A.2.1: Create TraceIdGenerator.swift
- [ ] A.2.2: Add trace_id to RecordingData
- [ ] A.2.3: Logging integration
- [ ] A.3.1: Add timezone field
- [ ] A.3.2: Test timezone capture

#### Theme B: Device Information (4 actions)
- [ ] B.1.1: Create DeviceInfoCapture.swift
- [ ] B.1.2: Add device info to metadata envelope
- [ ] B.1.3: Persist to Core Data
- [ ] B.1.4: Unit tests

#### Theme C: GPS Enhancement (4 actions)
- [ ] C.1.1: Update LocationData model with accuracy_m
- [ ] C.1.2: Update LocationService
- [ ] C.1.3: Validate GPS coordinates
- [ ] C.1.4: Unit tests

#### Theme D: Participants Management (5 actions)
- [ ] D.1.1: Create ParticipantHint model
- [ ] D.1.2: Update RecordingMetadata
- [ ] D.1.3: Update storage/persistence
- [ ] D.1.4: UI updates
- [ ] D.1.5: Unit tests

#### Theme E: Metadata Envelope (5 actions)
- [ ] E.1.1: Create MetadataEnvelope.swift
- [ ] E.1.2: Validation logic
- [ ] E.1.3: Encoding to JSON
- [ ] E.1.4: Integration with RecordingData
- [ ] E.1.5: Unit tests

#### Theme F: API Key Management (4 actions)
- [ ] F.1.1: Create APIKeyManager.swift (Keychain)
- [ ] F.1.2: Key rotation support
- [ ] F.1.3: Keychain error handling
- [ ] F.1.4: Unit tests

#### Theme G: Transcript API Client (20 actions)
🚨 **CHEMIN CRITIQUE** - 3-4 jours de travail
- [ ] G.1.1: Create TranscriptAPIClient.swift
- [ ] G.1.2: Create protocol for testability
- [ ] G.2.1: Implement /auth/new endpoint
- [ ] G.2.2: Implement /auth/renew endpoint
- [ ] G.2.3: Implement /auth/revoke endpoint
- [ ] G.2.4: Implement /auth/logs endpoint
- [ ] G.2.5: Unit tests
- [ ] G.3.1: Implement /v1/jobs/init endpoint
- [ ] G.3.2: Implement presigned URL upload
- [ ] G.3.3: Implement /v1/jobs/{id}/commit endpoint
- [ ] G.3.4: SHA-256 checksum calculation
- [ ] G.4.1: Implement multipart upload (fallback)
- [ ] G.4.2: Fallback logic
- [ ] G.5.1: Implement /v1/jobs/{id} status polling
- [ ] G.5.2: Polling strategy
- [ ] G.5.3: Health check

#### Theme H: Retry & Error Handling (4 actions)
- [ ] H.1.1: Implement RetryStrategy.swift
- [ ] H.1.2: Integrate with API client
- [ ] H.1.3: Special case handling (429, 503)
- [ ] H.1.4: Unit tests

#### Theme I: Job Tracking (5 actions)
- [ ] I.1.1: Create TranscriptJobEntity (Core Data)
- [ ] I.1.2: Update RecordingData model
- [ ] I.1.3: StorageService methods
- [ ] I.1.4: Unit tests
- [ ] I.2.1: Create TranscriptJobProcessor.swift
- [ ] I.2.2: Polling & retry logic
- [ ] I.2.3: User notifications

#### Theme J: Integration Testing (7 actions)
- [ ] J.1.1: Metadata generation tests
- [ ] J.1.2: API client tests
- [ ] J.1.3: Retry logic tests
- [ ] J.1.4: Storage tests
- [ ] J.2.1: Setup Transcript staging
- [ ] J.2.2: End-to-end upload test
- [ ] J.2.3: Error scenario testing
- [ ] J.2.4: Retry testing

#### Theme K: Documentation (5 actions)
- [ ] K.1.1: API client guide
- [ ] K.1.2: Metadata guide
- [ ] K.1.3: Keychain integration guide
- [ ] K.2.1: Developer setup guide
- [ ] K.2.2: Testing guide

#### Theme L: Code Review & Quality (2 actions)
- [ ] L.1.1: Self-review checklist
- [ ] L.1.2: Code style & best practices

**⚠️ IMPACT**: iOS bloque Transcript et my-RAG. Sans iOS, pas de test E2E possible.

---

## 🏗️ PROJECT 2: TRANSCRIPT - 9 Actions Restantes

### Statut Global: 🟢 STABLE - 40% Complete (6/15 done)

**Timeline**: Semaines 2-3 (2-16 nov 2025)
**Priorité**: P1 - AMÉLIORATIONS (Optionnel)

### ✅ Complété (6 actions)
- [x] A.1.1: iOS authentication guide (existe: IOS_AUTHENTICATION_SPEC.md)
- [x] A.1.3: API key setup guide (existe: API_KEY_SETUP.md)
- [x] A.2.1: Verify external_event_id format (validé dans metadata_schema.py)
- [x] A.2.2: Verify trace_id propagation (validé dans redis_notifier.py)
- [x] A.2.3: Verify archive structure (validé dans archive_builder.py)
- [x] Documentation ADR (à créer)

### 🚧 Restant (9 actions)

#### Theme A: Documentation (3 actions)
- [ ] A.1.2: Update OpenAPI spec with auth endpoints
  - Ajouter documentation /auth/* endpoints
  - Ajouter rate limiting info
  - Ajouter exemples
  - **Fichier**: `docs/api/transcript-api.openapi.yaml`

#### Theme B: Security Enhancements (3 actions) - OPTIONNEL
- [ ] B.1.1: Add scope support to API keys
- [ ] B.1.2: Scope validation middleware
- [ ] B.1.3: Tests for authorization
- [ ] B.2.1: Log API key operations (audit)
- [ ] B.2.2: Log job operations
- [ ] B.2.3: Query audit logs

#### Theme C: Production Hardening (3 actions) - OPTIONNEL
- [ ] C.1.1: Implement Redis-based rate limiting
- [ ] C.1.2: Rate limit middleware
- [ ] C.1.3: Tests

**✅ IMPACT**: Transcript est fonctionnel. Les actions restantes sont des améliorations optionnelles.

---

## 📦 PROJECT 3: MY-RAG - 72 Actions Restantes

### Statut Global: 🟡 EN COURS - 10% Complete (8/80 done)

**Timeline**: Semaines 3-4 (9-23 nov 2025)
**Priorité**: P2 - ROBUSTESSE

### ✅ Complété - Theme A: Alignment Fixes (8 actions)
- [x] A.1.1: Strengthen external_event_id validation (pattern strict)
- [x] A.1.2: Update consumer validation (timestamp)
- [x] A.2.1: Make trace_id REQUIRED
- [x] A.2.3: Metrics for trace_id presence (déjà présent)
- [x] B.1.1: Create DistributedLock module
- [x] C.1.1: Create RetryScheduler module
- [x] Documentation ADR-2025-10-29-001
- [x] Implementation Summary

### 🚧 Restant (72 actions)

#### Theme A: Alignment Fixes - Suite (1 action)
- [ ] A.1.3: Unit tests for external_event_id validation
  - **Fichier**: `tests/test_ingestion/test_external_event_id.py`

#### Theme B: Distributed Locking - Intégration (3 actions)
- [ ] B.1.2: Acquire lock before processing
  - Intégrer dans consumer.py:180-210
- [ ] B.1.3: Release lock on completion
  - Intégrer dans consumer.py:370-380
- [ ] B.1.4: Unit tests
  - **Fichier**: `tests/test_ingestion/test_distributed_lock.py`

#### Theme C: Retry Backoff - Intégration (2 actions)
- [ ] C.1.2: Integrate with message requeue
  - Intégrer dans consumer.py:300-320
- [ ] C.1.3: Unit tests
  - **Fichier**: `tests/test_ingestion/test_retry_scheduler.py`

#### Theme D: NLP Mode Detection (4 actions)
- [ ] D.1.1: Use schema_version field
  - Modifier consumer.py:254-283
- [ ] D.1.2: Fallback to heuristic if missing
- [ ] D.1.3: Validate version format
  - Pattern: `^\d+\.\d+$`
- [ ] D.1.4: Unit tests
  - **Fichier**: `tests/test_ingestion/test_nlp_mode_detection.py`

#### Theme E: Producer Metadata (4 actions)
- [ ] E.1.1: Extend IngestionJob model
  - Ajouter producer_name, producer_version
  - **Fichier**: `src/ingestion/models.py`
- [ ] E.1.2: Extract producer metadata
  - Parser de Redis message
- [ ] E.1.3: Metrics for producer tracking
  - Counter par producer
- [ ] E.1.4: Unit tests

#### Theme F: SLA Monitoring & Alerts (3 actions)
- [ ] F.1.1: Create Prometheus alert rules
  - AudioIngestAckLatencyHigh
  - AudioIngestValidationFailureRate
  - AudioIngestRedisPendingHigh
  - AudioIngestDLQBacklog
  - **Fichier**: `prometheus/alerts.yml`
- [ ] F.1.2: Create Grafana dashboard
  - **Fichier**: `grafana/dashboards/ingestion-sla.json`
- [ ] F.1.3: Configure alerting channels
  - Email, Slack, PagerDuty
  - **Fichier**: `prometheus/alertmanager.yml`

#### Theme G: Archive Structure Validation (4 actions)
- [ ] G.1.1: Validate after extraction
  - Root folder = external_event_id
  - conversation.json exists
  - checksums.sha256 exists
- [ ] G.1.2: Validate file sizes
  - Each file < 2GB
  - Total < 5GB
- [ ] G.1.3: Validate directory structure
  - Optional dirs: media/, artifacts/, logs/
- [ ] G.1.4: Unit tests
  - **Fichier**: `tests/test_ingestion/test_archive_structure.py`

#### Theme H: Checksum Validation Enhancements (4 actions)
- [ ] H.1.1: Log checksum mismatches
  - Include file path, expected/actual hash
- [ ] H.1.2: Implement corruption recovery
  - Retry once, then DLQ
- [ ] H.1.3: Metrics for checksum validation
- [ ] H.1.4: Unit tests
  - **Fichier**: `tests/test_ingestion/test_checksum_validation.py`

#### Theme I: Observability Enhancements (5 actions)
- [ ] I.1.1: Add context to all logs
  - external_event_id, trace_id, job_id
- [ ] I.1.2: Structured logging format
  - JSON for ELK/Splunk
  - **Fichier**: `src/ingestion/logging_config.py`
- [ ] I.1.3: Log levels (INFO/WARNING/ERROR)
- [ ] I.2.1: Add OpenTelemetry instrumentation
  - Trace E2E pipeline
- [ ] I.2.2: Export to tracing backend
  - OTLP exporter (Jaeger)
  - **Fichier**: `src/ingestion/otel_config.py`

#### Theme J: Documentation (5 actions)
- [ ] J.1.1: Update pipeline overview
  - **Fichier**: `docs/ingestion/PIPELINE_OVERVIEW.md`
- [ ] J.1.2: Create troubleshooting guide
  - **Fichier**: `docs/ingestion/TROUBLESHOOTING.md`
- [ ] J.1.3: Create runbook for operators
  - **Fichier**: `docs/operations/INGESTION_RUNBOOK.md`
- [ ] J.2.1: Reference ADR-2025-10-03-003
  - **Fichier**: `docs/ingestion/CONTRACT_REFERENCE.md`
- [ ] J.2.2: Document Redis message format
  - **Fichier**: `docs/ingestion/REDIS_MESSAGE_FORMAT.md`

#### Theme K: Quality & Testing (3 actions)
- [ ] K.1.1: Test with mock Transcript messages
  - **Fichier**: `tests/test_ingestion/test_transcript_integration.py`
- [ ] K.1.2: Test error scenarios
  - **Fichier**: `tests/test_ingestion/test_error_scenarios.py`
- [ ] K.1.3: Test with real Transcript (staging)
  - **Script**: `scripts/test-e2e-integration.sh`

**✅ IMPACT**: my-RAG modules core sont prêts. Intégration et tests restants.

---

## 🔄 CROSS-PROJECT - 12 Actions Restantes

### Statut Global: ⏳ EN ATTENTE - 0% Complete

**Timeline**: Tout au long du projet
**Priorité**: P1 - COORDINATION

### Theme A: Integration Testing (7 actions)
- [ ] A.1: Setup staging environment
  - iOS → staging.transcript
  - Transcript → staging deployment
  - my-RAG → staging Redis/MinIO
  - **Timeline**: Semaine 2
- [ ] A.2: E2E test flow
  - Record audio (iOS)
  - Upload via API
  - Verify Transcript processing
  - Check Redis message
  - Verify my-RAG ingestion
  - Check trace_id E2E
  - **Timeline**: Semaine 3
- [ ] A.3: Failure scenario testing
  - Network failures
  - Invalid metadata
  - Checksum mismatches
  - Server errors
  - **Timeline**: Semaine 4

### Theme B: Documentation Sync (2 actions)
- [ ] B.1: Maintain single source of truth
  - Primary: my-RAG ADR
  - Mirror in Transcript
  - Mirror in iOS
  - **Timeline**: Ongoing
- [ ] B.2: Version API contract
  - Semantic versioning
  - Backward compatibility
  - Deprecation warnings
  - **Timeline**: Semaine 4

### Theme C: Monitoring & Alerts (3 actions)
- [ ] C.1: Prometheus/Grafana setup
  - Deploy if not exists
  - Configure scrapers for all 3 services
  - **Timeline**: Semaine 2
- [ ] C.2: SLA dashboards
  - iOS → Transcript latency
  - Transcript processing
  - Transcript → Redis latency
  - my-RAG E2E ingestion
  - **Timeline**: Semaine 3
- [ ] C.3: Alert rules deployment
  - Deploy for all 3 projects
  - Configure notifications
  - Test alert firing
  - **Timeline**: Semaine 4

---

## 🎯 Priorités Immédiates (Top 10)

### 🔴 Critiques (Bloquants)

1. **iOS Theme G: API Client** (20 actions)
   - **Impact**: Bloque tout test E2E
   - **Effort**: 3-4 jours
   - **Assigné à**: iOS Team
   - **Deadline**: 8 nov 2025

2. **iOS Theme A: Identifiers** (8 actions)
   - **Impact**: Bloque API client
   - **Effort**: 1-2 jours
   - **Deadline**: 1 nov 2025

3. **iOS Theme E: Metadata Envelope** (5 actions)
   - **Impact**: Bloque upload
   - **Effort**: 1 jour
   - **Deadline**: 6 nov 2025

### 🟡 Importantes (Non-bloquantes)

4. **my-RAG: Consumer Integration** (B.1.2, B.1.3, C.1.2)
   - **Impact**: Active distributed locking + retry
   - **Effort**: 1 jour
   - **Deadline**: 12 nov 2025

5. **my-RAG: Unit Tests** (A.1.3, B.1.4, C.1.3)
   - **Impact**: Couverture >80%
   - **Effort**: 2 jours
   - **Deadline**: 15 nov 2025

6. **Cross: Staging Setup** (A.1)
   - **Impact**: Permet tests E2E
   - **Effort**: 1 jour
   - **Deadline**: 8 nov 2025

7. **my-RAG: SLA Monitoring** (F.1.1, F.1.2)
   - **Impact**: Visibilité production
   - **Effort**: 1 jour
   - **Deadline**: 18 nov 2025

### 🟢 Souhaitables (Optionnelles)

8. **Transcript: Security Enhancements** (Theme B)
   - **Impact**: Améliore sécurité
   - **Effort**: 2 jours
   - **Deadline**: 20 nov 2025 (optionnel)

9. **my-RAG: OpenTelemetry** (I.2.1, I.2.2)
   - **Impact**: Tracing distribué
   - **Effort**: 1 jour
   - **Deadline**: 22 nov 2025

10. **my-RAG: Documentation** (Theme J)
    - **Impact**: Opérabilité
    - **Effort**: 2 jours
    - **Deadline**: 25 nov 2025

---

## 📅 Timeline Révisée

```
Semaine 1 (26 oct - 1 nov) - EN COURS
├─ my-RAG: Theme A, B, C modules ✅ FAIT
└─ iOS: Themes A-C (Metadata, Device, GPS) ⏳ EN ATTENTE

Semaine 2 (2-8 nov)
├─ iOS: Themes D-F (Participants, Envelope, API Keys) ⏳
├─ my-RAG: Consumer integration ⏳
└─ Cross: Staging setup ⏳

Semaine 3 (9-15 nov) - CRITIQUE
├─ iOS: Theme G (API Client) ⏳ CHEMIN CRITIQUE
├─ my-RAG: Unit tests ⏳
└─ Cross: First E2E test ⏳

Semaine 4 (16-23 nov)
├─ iOS: Themes H-L (Testing, Docs) ⏳
├─ my-RAG: Themes D-K (NLP, Monitoring, Docs) ⏳
└─ Cross: Full E2E validation ⏳
```

---

## 🚨 Risques Identifiés

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| **iOS API Client delay** | 🔴 CRITIQUE | Moyen | Allouer 2+ développeurs iOS |
| **Transcript staging unavailable** | 🟡 MAJEUR | Faible | Backup environment early |
| **my-RAG test failures** | 🟡 MAJEUR | Faible | Run unit tests continuously |
| **Network/connectivity issues** | 🟠 MOYEN | Faible | Use mocking + staging |
| **Scope creep** | 🟠 MOYEN | Moyen | Strict change control via ADR |

---

## 📞 Ownership & Contacts

| Composant | Owner | Actions Restantes | Slack |
|-----------|-------|-------------------|-------|
| **iOS** | iOS Team | 120 | @ios-team |
| **Transcript** | Backend Team | 9 | @transcript-team |
| **my-RAG** | RAG Team | 72 | @rag-team |
| **Integration** | Staff Architect | 12 | @staff-arch |

**Weekly Sync**: Lundi 10:00 UTC
**Escalation**: #engineering-urgent

---

## ✅ Critères de Succès

### Phase 1 (my-RAG) - ✅ COMPLET
- [x] Validation stricte external_event_id
- [x] trace_id REQUIS
- [x] Module DistributedLock
- [x] Module RetryScheduler
- [x] Documentation ADR

### Phase 2 (Integration) - ⏳ EN ATTENTE
- [ ] Consumer intégration complète
- [ ] Background retry worker déployé
- [ ] Tests unitaires >80% coverage
- [ ] Tests d'intégration passent

### Phase 3 (E2E) - ⏳ EN ATTENTE
- [ ] iOS API client fonctionnel
- [ ] Premier test E2E (iOS → Transcript)
- [ ] Test E2E complet (iOS → Transcript → my-RAG)
- [ ] trace_id visible bout-en-bout
- [ ] Zero doublons en production
- [ ] p95 latency < 5s maintenu

---

**Dernière Mise à Jour**: 2025-10-29
**Prochaine Révision**: 2025-11-02 (Weekly sync)
**Status**: 📊 6% Complete (14/227 actions)
