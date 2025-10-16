# Implementation Guide - ADR-2025-10-16-004

Guide d'implémentation pour finaliser l'alignement avec le contrat cross-cutting (ADR-2025-10-03-003).

## ✅ Modifications Complétées

### Phase 1: Changements Critiques ✅

1. **`src/ingestion/config.py`** ✅
   - Stream Redis: `audio.ingestion`
   - Consumer group: `rag-ingestion`
   - DLQ stream: `audio.ingestion.deadletter`

2. **`src/ingestion/redis_message_parser.py`** ✅ (NOUVEAU)
   - Parse format: `{external_event_id, package_uri, checksum, schema_version, ...}`
   - Extraction `trace_id`
   - Validation JSON Schema

3. **`src/ingestion/checksum_validator.py`** ✅ (NOUVEAU)
   - Validation format `sha256:...`
   - Vérification tar.gz
   - Vérification `checksums.sha256` interne

4. **`src/ingestion/transcript_validator.py`** ✅
   - Pattern `external_event_id`: `^rec-\d{8}T\d{6}Z-[a-f0-9]{8}$`

### Phase 2: Observabilité ✅

5. **`src/ingestion/error_handler.py`** ✅ (NOUVEAU)
   - Dead Letter Queue
   - Codes d'erreur standardisés
   - Remediation hints

6. **`src/ingestion/metrics.py`** ✅ (NOUVEAU)
   - Métriques Prometheus complètes
   - SLA thresholds documentés

## 🔄 Modifications Restantes

### Finaliser `consumer.py`

Le fichier `src/ingestion/consumer.py` a été partiellement modifié. Voici les étapes pour finaliser :

#### A. Ajouter l'import `time`

```python
# Ligne 8-10
from typing import Dict, Any, Optional, List
from datetime import datetime
import time  # ← AJOUTER
import traceback
```

#### B. Compléter la méthode `process_message`

Le début a été modifié (lignes 89-137). Voici la suite à implémenter :

```python
            # Step 2: Check for duplicate (after line 137)
            existing_job = db.query(IngestionJob).filter_by(external_event_id=external_event_id).first()
            if existing_job and existing_job.status == IngestionStatus.COMPLETED.value:
                logger.info(f"{log_prefix} Job already completed, skipping (duplicate)")
                IngestionMetrics.record_success()
                return True

            # Create or update job
            if existing_job:
                job = existing_job
                job.status = IngestionStatus.DOWNLOADING.value
                job.retry_count = message.retry_count
                job.started_at = datetime.utcnow()
                job.trace_id = trace_id  # AJOUTER trace_id
            else:
                job = IngestionJob(
                    job_id=external_event_id,  # Utiliser external_event_id comme job_id
                    external_event_id=external_event_id,  # AJOUTER ce champ au modèle
                    source_bucket=bucket,
                    source_key=object_key,
                    status=IngestionStatus.DOWNLOADING.value,
                    started_at=datetime.utcnow(),
                    trace_id=trace_id,  # AJOUTER trace_id
                    checksum=message.checksum,  # AJOUTER checksum
                    schema_version=message.schema_version  # AJOUTER schema_version
                )
                db.add(job)

            context.job_id = job.job_id
            db.commit()

            # Step 3: Download from MinIO with timing
            logger.info(f"{log_prefix} Downloading from MinIO: {bucket}/{object_key}")
            with IngestionMetrics.time_processing():
                transcript_data = await self.storage.download_transcript(bucket, object_key)

            if not transcript_data:
                raise Exception("Failed to download transcript from MinIO")

            # Record download size
            if 'file_size' in transcript_data:
                IngestionMetrics.record_download_size(transcript_data['file_size'])

            # Step 4: Verify tar.gz checksum
            logger.info(f"{log_prefix} Validating tar.gz checksum")
            with IngestionMetrics.time_checksum_validation():
                tarball_path = transcript_data.get('tarball_path')  # Path to downloaded file
                if tarball_path:
                    ChecksumValidator.verify_tarball(tarball_path, message.checksum)
                    logger.info(f"{log_prefix} ✓ Tar.gz checksum verified")

            job.status = IngestionStatus.NORMALIZING.value
            db.commit()

            # Step 5: Validate conversation.json
            logger.info(f"{log_prefix} Validating conversation.json")
            conversation_json = transcript_data.get('conversation.json')
            if not conversation_json:
                raise Exception("Missing conversation.json in transcript package")

            with IngestionMetrics.time_validation():
                validated_payload = validate_conversation_from_transcript(conversation_json)

            # Verify internal checksums (checksums.sha256)
            extracted_dir = transcript_data.get('extracted_dir')
            if extracted_dir:
                logger.info(f"{log_prefix} Validating internal checksums.sha256")
                with IngestionMetrics.time_checksum_validation():
                    ChecksumValidator.verify_archive_checksums(extracted_dir)
                    logger.info(f"{log_prefix} ✓ All internal files verified")

            # Record conversation metrics
            IngestionMetrics.record_conversation_metrics(
                num_segments=len(validated_payload.segments),
                num_participants=len(validated_payload.participants)
            )

            logger.info(
                f"{log_prefix} Validation passed: {validated_payload.external_event_id}, "
                f"{len(validated_payload.segments)} segments, {len(validated_payload.participants)} participants"
            )

            # Step 6: Store in database
            logger.info(f"{log_prefix} Storing conversation")
            conversation = await self.storage.store_conversation_from_transcript(
                payload=validated_payload,
                source_metadata={
                    **transcript_data.get('metadata', {}),
                    'trace_id': trace_id,  # Propagate trace_id
                    'checksum': message.checksum,
                    'schema_version': message.schema_version
                }
            )

            job.status = IngestionStatus.EMBEDDING.value
            job.conversation_id = conversation.id
            db.commit()

            # Step 7: NLP Processing (existing code - keep as is)
            nlp_mode = self._detect_nlp_mode(conversation_json)
            logger.info(f"{log_prefix} NLP mode: {nlp_mode}")
            IngestionMetrics.record_nlp_mode(nlp_mode)

            # ... (rest of NLP processing unchanged)

            # Step 8: Mark as completed
            job.status = IngestionStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()

            if job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds() * 1000
                job.processing_duration_ms = int(duration)

            db.commit()

            # Record success metrics
            IngestionMetrics.record_success()
            processing_time = time.time() - start_time
            IngestionMetrics.record_ack_latency(processing_time)

            logger.info(f"{log_prefix} Ingestion completed successfully in {processing_time:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(traceback.format_exc())

            # Classify and handle error
            error_code = self.error_handler.classify_exception(e)
            IngestionMetrics.record_failure(error_code.value)

            # Publish to DLQ
            if context:
                self.error_handler.handle_error(
                    exception=e,
                    original_message=message_data,
                    context=context
                )

            # Update job with error
            try:
                db = clients.get_db_session()
                if external_event_id:
                    job = db.query(IngestionJob).filter_by(external_event_id=external_event_id).first()
                    if job:
                        job.status = IngestionStatus.FAILED.value
                        job.error_message = str(e)
                        job.error_stack = traceback.format_exc()
                        job.error_code = error_code.value  # AJOUTER ce champ
                        job.last_error_at = datetime.utcnow()
                        db.commit()
            except Exception as db_error:
                logger.error(f"Error updating job status: {db_error}")

            return False
```

#### C. Mettre à jour le modèle `IngestionJob` (models.py)

Ajouter les champs manquants dans `src/ingestion/models.py`:

```python
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # AJOUTER ces champs:
    external_event_id = Column(String, unique=True, nullable=False, index=True)
    trace_id = Column(String, nullable=True, index=True)
    checksum = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)
    error_code = Column(String, nullable=True)

    # Champs existants (garder tels quels)
    job_id = Column(String, unique=True, nullable=False, index=True)
    source_bucket = Column(String, nullable=False)
    # ... etc
```

#### D. Mettre à jour `storage.py`

Modifier la méthode `download_transcript` pour retourner plus d'infos :

```python
async def download_transcript(self, bucket: str, object_key: str) -> Dict[str, Any]:
    """
    Download and extract tar.gz from MinIO

    Returns:
        {
            'conversation.json': dict,
            'metadata': dict,
            'tarball_path': Path,  # AJOUTER
            'extracted_dir': Path,  # AJOUTER
            'file_size': int  # AJOUTER
        }
    """
    # ... téléchargement ...

    return {
        'conversation.json': conversation_data,
        'metadata': metadata,
        'tarball_path': local_path,  # Pour validation checksum
        'extracted_dir': extract_dir,  # Pour validation checksums internes
        'file_size': local_path.stat().st_size  # Pour métriques
    }
```

## 📋 Checklist d'Implémentation

### Phase 1 - Critique (FAIT) ✅
- [x] Config Redis updated
- [x] RedisMessageParser créé
- [x] ChecksumValidator créé
- [x] external_event_id pattern renforcé

### Phase 2 - Observabilité (FAIT) ✅
- [x] ErrorHandler créé
- [x] Metrics.py créé

### Phase 3 - Intégration (À FAIRE)
- [ ] Ajouter `import time` dans consumer.py
- [ ] Compléter `process_message` avec nouveau parsing
- [ ] Ajouter champs dans `IngestionJob` model
- [ ] Créer migration DB pour nouveaux champs
- [ ] Mettre à jour `storage.py` pour retourner paths
- [ ] Tests unitaires pour nouveaux modules
- [ ] Tests d'intégration avec messages de test

## 🧪 Tests Recommandés

### 1. Test du Parser Redis

```python
# tests/test_ingestion/test_redis_parser.py
def test_parse_valid_message():
    message_data = {
        b'external_event_id': b'rec-20251016T123000Z-abc12345',
        b'package_uri': b'minio://ingestion/drop/2025/10/16/rec-20251016T123000Z-abc12345.tar.gz',
        b'checksum': b'sha256:' + b'a' * 64,
        b'schema_version': b'1.1',
        b'retry_count': b'0',
        b'produced_at': b'2025-10-16T12:30:00Z',
        b'metadata': b'{"trace_id": "550e8400-e29b-41d4-a716-446655440000"}'
    }

    message = RedisMessageParser.parse(message_data)
    assert message.external_event_id == 'rec-20251016T123000Z-abc12345'
    assert message.get_trace_id() == '550e8400-e29b-41d4-a716-446655440000'
    bucket, key = message.parse_package_uri()
    assert bucket == 'ingestion'
    assert 'drop/2025/10/16' in key
```

### 2. Test Checksum Validation

```python
# tests/test_ingestion/test_checksum.py
def test_verify_tarball_checksum():
    # Créer un fichier de test
    test_file = Path('/tmp/test.tar.gz')
    test_file.write_text('test content')

    # Calculer checksum
    checksum = ChecksumValidator.calculate_file_sha256(test_file)

    # Vérifier
    assert ChecksumValidator.verify_tarball(test_file, checksum)
```

### 3. Test Error Handler

```python
# tests/test_ingestion/test_error_handler.py
def test_classify_checksum_error():
    handler = ErrorHandler(redis_client=mock_redis, dlq_stream='test.dlq')
    exception = ValueError('Checksum mismatch')

    error_code = handler.classify_exception(exception)
    assert error_code == ErrorCode.CHECKSUM_MISMATCH
    assert handler.is_retryable(error_code) == True
```

## 🚀 Déploiement

### 1. Migration Base de Données

```sql
-- Add new columns to ingestion_jobs
ALTER TABLE ingestion_jobs
ADD COLUMN external_event_id VARCHAR UNIQUE NOT NULL,
ADD COLUMN trace_id VARCHAR,
ADD COLUMN checksum VARCHAR,
ADD COLUMN schema_version VARCHAR,
ADD COLUMN error_code VARCHAR;

CREATE INDEX idx_ingestion_jobs_external_event_id ON ingestion_jobs(external_event_id);
CREATE INDEX idx_ingestion_jobs_trace_id ON ingestion_jobs(trace_id);
```

### 2. Variables d'Environnement

Mettre à jour `.env`:

```bash
# Redis (updated names)
REDIS_STREAM_INGESTION=audio.ingestion
REDIS_CONSUMER_GROUP=rag-ingestion
REDIS_DLQ_STREAM=audio.ingestion.deadletter

# Prometheus (new)
PROMETHEUS_PORT=9090
```

### 3. Docker Compose

Ajouter Prometheus:

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
```

## 📚 Documentation

### Fichiers créés
1. `docs/adr/ADR-2025-10-16-004-alignment-cross-cutting-contract.md` ✅
2. `src/ingestion/redis_message_parser.py` ✅
3. `src/ingestion/checksum_validator.py` ✅
4. `src/ingestion/error_handler.py` ✅
5. `src/ingestion/metrics.py` ✅

### Fichiers modifiés
1. `src/ingestion/config.py` ✅
2. `src/ingestion/transcript_validator.py` ✅
3. `src/ingestion/consumer.py` 🔄 (en cours)
4. `src/ingestion/models.py` ⏳ (à faire)
5. `src/ingestion/storage.py` ⏳ (à faire)

## 🎯 Résultat Attendu

Une fois complété :
- ✅ Messages Redis conformes au contrat
- ✅ Validation checksums triple niveau
- ✅ Distributed tracing avec trace_id
- ✅ Dead Letter Queue fonctionnel
- ✅ Métriques Prometheus exposées
- ✅ SLA monitoring ready

---

**Date**: 2025-10-16
**Statut**: Phase 1 & 2 complètes, Phase 3 en cours
