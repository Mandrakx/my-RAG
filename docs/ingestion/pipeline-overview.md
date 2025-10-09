# Pipeline d'Ingestion - Vue d'ensemble

## Introduction

Le pipeline d'ingestion est responsable de la réception, normalisation et stockage des transcripts audio provenant du service Transcript (backend). Il transforme les transcripts bruts en conversations structurées, prêtes pour l'indexation vectorielle et l'analyse NLP.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Transcript Service (Backend)                   │
│                                                              │
│  1. iOS Upload → 2. Transcription → 3. MinIO Drop          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 4. Publish Event
                         ▼
              ┌──────────────────────┐
              │   Redis Streams      │
              │  ingestion:events    │
              └──────────┬───────────┘
                         │
                         │ 5. Consume
                         ▼
        ┌────────────────────────────────────┐
        │   RAG Ingestion Pipeline           │
        │                                    │
        │  ┌──────────────────────────────┐  │
        │  │  RedisStreamConsumer         │  │
        │  │  - Reads events              │  │
        │  │  - Tracks jobs               │  │
        │  └──────────┬───────────────────┘  │
        │             │                       │
        │             ▼                       │
        │  ┌──────────────────────────────┐  │
        │  │  IngestionStorage            │  │
        │  │  - Downloads from MinIO      │  │
        │  └──────────┬───────────────────┘  │
        │             │                       │
        │             ▼                       │
        │  ┌──────────────────────────────┐  │
        │  │  TranscriptNormalizer        │  │
        │  │  - Parses formats            │  │
        │  │  - Normalizes data           │  │
        │  │  - Validates schema          │  │
        │  └──────────┬───────────────────┘  │
        │             │                       │
        │             ▼                       │
        │  ┌──────────────────────────────┐  │
        │  │  IngestionStorage            │  │
        │  │  - Stores in PostgreSQL      │  │
        │  │  - Uploads to MinIO          │  │
        │  └──────────────────────────────┘  │
        └────────────────────────────────────┘
                         │
         ┌───────────────┴──────────────┐
         ▼                              ▼
  ┌─────────────┐              ┌────────────────┐
  │ PostgreSQL  │              │     MinIO      │
  │             │              │                │
  │ - Metadata  │              │ - Normalized   │
  │ - Turns     │              │   JSONL        │
  └─────────────┘              └────────────────┘
```

## Flux de Données

### Étape 1: Événement Redis

Le service Transcript publie un événement dans le stream Redis `ingestion:events`:

```json
{
  "job_id": "abc123-def456",
  "bucket": "ingestion",
  "object_key": "abc123-def456/transcript.json",
  "event_type": "put",
  "timestamp": "2025-10-10T10:00:00Z",
  "file_size": 15420
}
```

### Étape 2: Téléchargement MinIO

Le consumer télécharge le transcript depuis MinIO:

```python
# Formats supportés:
# - .json (JSON simple)
# - .json.gz (JSON compressé)
# - .tar.gz (Archive contenant transcript.json)
```

### Étape 3: Normalisation

Le transcript est normalisé vers un format standard:

**Format d'entrée (exemple)**:
```json
{
  "metadata": {
    "job_id": "abc123",
    "timestamp": "2025-10-10T10:00:00Z",
    "duration_seconds": 125.3,
    "language": "fr"
  },
  "segments": [
    {
      "speaker": "John",
      "text": "Bonjour, comment allez-vous?",
      "start_time": 0.0,
      "end_time": 2.5,
      "confidence": 0.95
    },
    {
      "speaker": "Marie",
      "text": "Très bien merci!",
      "start_time": 2.5,
      "end_time": 4.0,
      "confidence": 0.92
    }
  ]
}
```

**Format normalisé (sortie)**:
```json
{
  "metadata": {
    "job_id": "abc123",
    "date": "2025-10-10T10:00:00Z",
    "duration_seconds": 125.3,
    "language": "fr",
    "source": "transcript-service"
  },
  "turns": [
    {
      "turn": 0,
      "speaker": "John",
      "text": "Bonjour, comment allez-vous?",
      "timestamp_ms": 0,
      "confidence": 0.95
    },
    {
      "turn": 1,
      "speaker": "Marie",
      "text": "Très bien merci!",
      "timestamp_ms": 2500,
      "confidence": 0.92
    }
  ],
  "participants": [
    {
      "speaker": "John",
      "role": "participant",
      "turn_count": 1
    },
    {
      "speaker": "Marie",
      "role": "participant",
      "turn_count": 1
    }
  ],
  "statistics": {
    "total_turns": 2,
    "total_speakers": 2,
    "avg_confidence": 0.935
  }
}
```

### Étape 4: Persistence

#### PostgreSQL

Trois tables principales:

1. **ingestion_jobs** - Suivi des jobs d'ingestion
```sql
CREATE TABLE ingestion_jobs (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR UNIQUE NOT NULL,
    source_bucket VARCHAR NOT NULL,
    source_key VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    conversation_id VARCHAR REFERENCES conversations(id),
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

2. **conversations** - Métadonnées des conversations
```sql
CREATE TABLE conversations (
    id VARCHAR PRIMARY KEY,
    title VARCHAR,
    date TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    language VARCHAR DEFAULT 'fr',
    conversation_type VARCHAR,
    transcript TEXT NOT NULL,
    participants JSON,
    tags JSON,
    main_topics JSON,
    confidence_score FLOAT,
    qdrant_point_id VARCHAR,
    created_at TIMESTAMP
);
```

3. **conversation_turns** - Tours de parole individuels
```sql
CREATE TABLE conversation_turns (
    id VARCHAR PRIMARY KEY,
    conversation_id VARCHAR REFERENCES conversations(id),
    turn_index INTEGER NOT NULL,
    speaker VARCHAR NOT NULL,
    text TEXT NOT NULL,
    timestamp_ms INTEGER,
    sentiment VARCHAR,
    sentiment_score FLOAT,
    qdrant_point_id VARCHAR
);
```

#### MinIO

Le transcript normalisé est stocké au format JSONL:

**Bucket**: `results`
**Key**: `{job_id}/conversation.jsonl`

```jsonl
{"type":"metadata","job_id":"abc123","date":"2025-10-10T10:00:00Z","language":"fr"}
{"type":"turn","turn":0,"speaker":"John","text":"Bonjour, comment allez-vous?"}
{"type":"turn","turn":1,"speaker":"Marie","text":"Très bien merci!"}
{"type":"participants","data":[{"speaker":"John","role":"participant"}]}
{"type":"statistics","total_turns":2,"total_speakers":2}
```

## Composants Principaux

### 1. RedisStreamConsumer

**Fichier**: `src/ingestion/consumer.py`

**Responsabilités**:
- Écouter le stream Redis `ingestion:events`
- Consommer les messages par batch
- Orchestrer le pipeline d'ingestion
- Gérer les erreurs et retries
- Acknowledger les messages traités

**Configuration**:
```python
REDIS_STREAM_INGESTION=ingestion:events
REDIS_CONSUMER_GROUP=rag-processors
REDIS_CONSUMER_NAME=consumer-1
REDIS_BATCH_SIZE=10
REDIS_BLOCK_MS=5000
```

**Démarrage**:
```bash
python -m src.ingestion.consumer
```

### 2. TranscriptNormalizer

**Fichier**: `src/ingestion/normalizer.py`

**Responsabilités**:
- Parser différents formats de transcript
- Normaliser les noms de speakers
- Extraire les participants
- Calculer les statistiques
- Convertir vers JSONL

**Formats supportés**:
- Structured JSON (avec `segments` ou `turns`)
- Plain text (format "Speaker: texte")

### 3. IngestionStorage

**Fichier**: `src/ingestion/storage.py`

**Responsabilités**:
- Télécharger depuis MinIO
- Uploader vers MinIO
- Persister dans PostgreSQL
- Gérer les archives
- Générer les titres

### 4. SchemaValidator

**Fichier**: `src/ingestion/schemas.py`

**Responsabilités**:
- Valider les transcripts entrants
- Valider les conversations normalisées
- Valider les événements Redis
- Schémas JSON Schema complets

## Gestion des Erreurs

### Statuts d'Ingestion

| Status | Description | Transition |
|--------|-------------|------------|
| `pending` | Job créé, en attente | → `downloading` |
| `downloading` | Téléchargement depuis MinIO | → `normalizing` |
| `normalizing` | Normalisation en cours | → `embedding` |
| `embedding` | Création embeddings (Phase 5) | → `completed` |
| `completed` | Terminé avec succès | - |
| `failed` | Échec après retries | → `retry` ou stop |
| `retry` | En attente de retry | → `downloading` |

### Retry Logic

```python
max_retries = 3
retry_delay = 5  # secondes
backoff_factor = 2.0

# Délais: 5s, 10s, 20s
```

### Gestion des Erreurs

1. **Erreur de téléchargement MinIO**:
   - Retry automatique (3x)
   - Stockage du stack trace
   - Notification en logs

2. **Erreur de validation**:
   - Échec immédiat
   - Pas de retry
   - Alerte pour investigation

3. **Erreur de persistence**:
   - Retry automatique
   - Rollback transaction
   - Archivage des données brutes

## Monitoring

### Métriques Prometheus

```python
# Durée de traitement
ingestion_processing_duration_seconds

# Nombre de jobs par statut
ingestion_jobs_total{status="completed|failed|pending"}

# Erreurs
ingestion_errors_total{type="download|normalize|persist"}

# Taille des fichiers
ingestion_file_size_bytes
```

### Logs Structurés

```python
logger.info(
    "Ingestion completed",
    extra={
        "job_id": job_id,
        "conversation_id": conversation.id,
        "duration_ms": duration,
        "turns_count": len(turns),
        "status": "completed"
    }
)
```

### Correlation IDs

Tous les logs utilisent `job_id` comme correlation ID pour tracer le parcours complet.

## Installation et Déploiement

### 1. Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Variables d'environnement
cp config/environments/.env.example .env
# Éditer .env
```

### 2. Initialiser la Base de Données

```bash
# Créer les tables
python src/ingestion/init_db.py init

# Ou reset complet
python src/ingestion/init_db.py reset
```

### 3. Démarrer le Consumer

```bash
# En développement
python -m src.ingestion.consumer

# En production (avec systemd/supervisor)
[Unit]
Description=RAG Ingestion Consumer
After=network.target

[Service]
Type=simple
User=rag
WorkingDirectory=/app
ExecStart=/app/venv/bin/python -m src.ingestion.consumer
Restart=always

[Install]
WantedBy=multi-user.target
```

## Tests

### Exécuter les Tests

```bash
# Tous les tests
pytest tests/test_ingestion/

# Tests spécifiques
pytest tests/test_ingestion/test_normalizer.py
pytest tests/test_ingestion/test_schemas.py

# Avec couverture
pytest --cov=src/ingestion tests/test_ingestion/
```

### Tests Disponibles

- `test_normalizer.py` - Tests de normalisation
- `test_schemas.py` - Tests de validation
- Couverture: ~85%

## Commandes Make

```bash
# Démarrer le consumer
make ingestion-start

# Voir les logs
make ingestion-logs

# Status des jobs
make ingestion-status

# Retry failed jobs
make ingestion-retry-failed
```

## Prochaines Étapes (Phase 5)

1. **Embeddings**:
   - Chunking des tours de parole
   - Génération embeddings (OpenAI/local)
   - Indexation dans Qdrant

2. **NLP Enrichment**:
   - NER (Named Entity Recognition)
   - Extraction relations familiales
   - Sentiment analysis

3. **Semantic Search**:
   - Hybrid search (dense + sparse)
   - Reranking
   - Context expansion

## Références

- [ADR 003 - Contrat Audio → Transcript → RAG](../adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md)
- [API Transcript OpenAPI](../api/transcript-api.openapi.yaml)
- [Setup Infrastructure](../infrastructure/setup-guide.md)
- [Action Plan](../action-plan/README.md)
