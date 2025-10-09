# Action Plan RAG

## Phase 0 - Preparation & cadrage (terminee)
- [x] Passer en revue `docs/specifications/SPEC_CONVERSATION_RAG.md` et consolider les besoins fonctionnels.
- [x] Verifier `docs/specifications/Spec-analyse-fichiers.md` pour les dependances futures.
- [x] Lister contraintes materiel (RTX 3090) et cibles cloud pour preparer la portabilite.

## Phase 1 - Design initial du POC (terminee)
- [x] Formaliser le plan d''implementation global base sur les specifications.
- [x] Rediger `docs/design/RAG-initial-design.md` avec architecture, pipeline, securite, roadmap.
- [x] Documenter le contrat d''integration audio avec depot MinIO et notifications Redis.

## Phase 2 - Alignement avec le projet audio (terminée)
- [x] Finaliser le workflow drop MinIO avec l''equipe audio (cf. docs/design/cross-cutting-concern.md et docs/guides/operations/minio-drop-playbook.md) :
  - [x] Definir la structure exacte du paquet depose sur MinIO : archive tar.gz obligatoire, arborescence des fichiers, nommage standard et encodage JSON du transcript.
  - [x] Confirmer les delais et retrys (ack <5s, fenetre de retention, procedure de relivraison).
  - [x] Designer les responsabilites: publication notification Redis, suivi deadletters, correction des erreurs.
  - [x] Rediger les playbooks d'exploitation (checklist depot, checklist ingestion) – voir docs/guides/operations/minio-drop-playbook.md.
- [x] Documenter les exigences partagees dans `docs/design/cross-cutting-concern.md`.
- [x] Definir le schema exact de message Redis Streams et les codes d''erreur partages (docs/design/cross-cutting-concern.md + docs/design/audio-redis-message-schema.json).
- [x] Documenter le plan de monitoring ingestion (logs correles, metriques Prometheus, alertes) - voir monitoring/ingestion-monitoring-plan.md.
- [x] **ADR 003 - Contrat cross-cutting Audio → Transcript → RAG (2025-10-10)**
  - [x] Specifier le protocole complet d'upload iOS → Transcript (2 flows: Presigned URL / Direct Upload).
  - [x] Documenter les mecanismes de retry (exponential backoff, 3 tentatives max).
  - [x] Definir le catalogue d'erreurs HTTP complet (13 codes d'erreur avec actions client).
  - [x] Ajouter health checks et service discovery (`/v1/health`, `/v1/health/ready`).
  - [x] Specifier contraintes fichiers (500MB max, formats supportes, timeouts).
  - [x] Documenter strategie de polling (5s → 15s → 30s, max 3h).
  - [x] Synchroniser ADR dans les 3 repos (my-RAG, transcript, mneia-whisper).
- [x] **Specification OpenAPI 3.0 complete de l'API Transcript** (`docs/api/transcript-api.openapi.yaml`)
  - [x] 8 endpoints documentes (health checks, presigned URL flow, direct upload, job operations).
  - [x] Schemas complets avec validation (MetadataEnvelope, JobStatus, Error).
  - [x] Documentation de l'etape 2 (upload S3) avec exemples HTTP et Swift.
  - [x] Clarification terminologie (Presigned URL Flow vs Direct Upload).
  - [x] Exemples de requetes/reponses pour chaque endpoint.
  - [x] Synchroniser spec OpenAPI dans transcript repo.

## Phase 3 - Environnement local & infrastructure (terminée)
- [x] **Infrastructure Docker Compose complète** (`docker-compose.yml`)
  - [x] Remplacer ChromaDB par Qdrant (HTTP 6333, gRPC 6334) avec health checks
  - [x] Ajouter MinIO (API 9000, Console 9001) avec auto-initialisation
  - [x] Configurer Redis pour cache et streams (ingestion:events)
  - [x] PostgreSQL 16 avec credentials configurables
  - [x] Monitoring stack (Prometheus 9090, Grafana 3000)
  - [x] Nginx reverse proxy (production profile)
  - [x] Volumes et réseaux correctement configurés
- [x] **Configuration environnement** (`config/environments/.env.example`)
  - [x] Variables Qdrant (URL, ports, collection, API key)
  - [x] Variables MinIO (endpoints, buckets, credentials, SSL)
  - [x] Variables PostgreSQL synchronisées avec docker-compose
  - [x] Variables Redis Streams (consumer group, retries)
  - [x] Contraintes fichiers mises à jour (500MB max, formats audio)
- [x] **Script d'initialisation MinIO** (`scripts/init-minio.sh`)
  - [x] Création automatique des 3 buckets (ingestion, results, archive)
  - [x] Policies de sécurité (upload-only encrypted, public read, private)
  - [x] Versioning activé sur ingestion et archive
  - [x] Lifecycle policies (ingestion: 7j→archive, 90j→delete; results: 30j→delete)
  - [x] Configuration event notifications Redis (format .tar.gz, .m4a, etc.)
  - [x] Health checks et retry logic
- [x] **Makefile opérationnel** (`Makefile`)
  - [x] Commandes Docker (up, down, restart, rebuild, logs, status)
  - [x] Commandes MinIO (init, console, buckets, upload-test, logs)
  - [x] Commandes Qdrant (dashboard, collections, health, logs)
  - [x] Commandes Redis (cli, monitor, streams, logs)
  - [x] Commandes PostgreSQL (shell, migrate, backup, reset)
  - [x] URLs quick access et status display
- [x] **Documentation infrastructure** (`docs/infrastructure/`)
  - [x] Setup Guide complet (installation, configuration, troubleshooting)
  - [x] README avec quick start et architecture overview
  - [x] Data flow diagrams et topologie services
  - [x] Checklist sécurité et procédures maintenance

## Phase 4 - Pipeline ingestion & stockage (terminée)
- [x] **Module RedisStreamConsumer** (`src/ingestion/consumer.py`)
  - [x] Consumer Redis Streams pour événements d'ingestion
  - [x] Orchestration du pipeline complet (download → normalize → persist)
  - [x] Gestion des retries (3 max) avec exponential backoff
  - [x] Tracking des jobs avec statuts (pending → downloading → normalizing → embedding → completed/failed)
  - [x] Acknowledgement des messages traités
  - [x] Logging structuré avec correlation IDs
- [x] **Module TranscriptNormalizer** (`src/ingestion/normalizer.py`)
  - [x] Parser formats multiples (structured JSON, plain text)
  - [x] Normalisation speakers (cleaning, titling)
  - [x] Extraction participants avec statistiques
  - [x] Conversion vers format conversation.jsonl
  - [x] Calcul métriques (avg confidence, turn counts)
  - [x] Support multilingue (fr, en, es, de, it, pt)
- [x] **Module IngestionStorage** (`src/ingestion/storage.py`)
  - [x] Download depuis MinIO (JSON, .gz, .tar.gz)
  - [x] Upload normalized JSONL vers MinIO bucket results
  - [x] Persistence PostgreSQL (conversations, turns, jobs)
  - [x] Génération automatique titres conversations
  - [x] Archivage données brutes optionnel
  - [x] Méthodes query (get_conversation, get_turns, update_summary)
- [x] **Modèles de données PostgreSQL** (`src/ingestion/models.py`)
  - [x] Table ingestion_jobs (tracking avec retry_count, error_stack)
  - [x] Table conversations (metadata, participants JSON, tags, topics)
  - [x] Table conversation_turns (individual turns, sentiment, embeddings refs)
  - [x] Pydantic models pour validation API
  - [x] Enum pour statuts et types
- [x] **Validations JSON Schema** (`src/ingestion/schemas.py`)
  - [x] Schema transcript_metadata (job_id, timestamp, duration, language)
  - [x] Schema transcript_segment (speaker, text, timestamps, confidence)
  - [x] Schema transcript_document (metadata + segments/turns/transcript)
  - [x] Schema normalized_conversation (metadata, turns, participants, stats)
  - [x] Schema redis_event (job_id, bucket, object_key, event_type)
  - [x] SchemaValidator class avec méthodes de validation
- [x] **Infrastructure et tooling**
  - [x] Script init_db.py (create/drop/reset tables)
  - [x] Configuration centralised (IngestionConfig avec pydantic-settings)
  - [x] ServiceClients singleton (MinIO, Redis, PostgreSQL, Qdrant)
  - [x] Requirements.txt updated (qdrant-client, minio, jsonschema, psycopg2)
- [x] **Tests unitaires** (`tests/test_ingestion/`)
  - [x] test_normalizer.py (12 tests, formats multiples, edge cases)
  - [x] test_schemas.py (10 tests, validation success/failure)
  - [x] Fixtures pytest pour normalizer
  - [x] Tests async avec pytest-asyncio
- [x] **Documentation complète** (`docs/ingestion/`)
  - [x] pipeline-overview.md (architecture, flux, composants, monitoring)
  - [x] README.md (quick start, config, troubleshooting, API)
  - [x] Diagrammes séquence et architecture
  - [x] Guide monitoring et error handling

## Phase 5 - Stack NLP GPU (terminée)
- [x] **Stratégie GPU et sélection modèles** (`docs/nlp/gpu-strategy.md`)
  - [x] Allocation VRAM 24GB optimisée (embeddings 5GB, NER 2GB, sentiment 1.5GB, LLM 6GB)
  - [x] Sélection modèles: e5-large-instruct, camembert-ner, bert-multilingual-sentiment, mistral-7b-4bit
  - [x] Benchmarks RTX 3090 estimés (200 seq/s embeddings, 500 tok/s NER, 40 tok/s LLM)
  - [x] Stratégies batching et mixed precision (FP16, INT8, 4-bit quantization)
- [x] **Module Chunking intelligent** (`src/nlp/chunking.py`)
  - [x] 4 stratégies: turn-based, sliding-window, speaker-grouped, semantic
  - [x] Smart chunking adaptif (détection type conversation, nombre speakers)
  - [x] Préservation contexte conversationnel et overlap configurable
  - [x] Dataclass Chunk avec metadata (speakers, turn_range, chunk_index)
- [x] **Pipeline Embeddings** (`src/nlp/embeddings.py`)
  - [x] Support 3 providers: Local GPU (transformers), OpenAI API, Sentence-Transformers
  - [x] Batching optimisé (batch_size=32 pour GPU)
  - [x] Mean pooling et normalisation embeddings
  - [x] Instruction prefix pour modèles E5 (query: / passage:)
  - [x] EmbeddingPipeline complet (chunk → embed → index)
  - [x] Factory pattern pour sélection provider
- [x] **Qdrant Manager** (`src/nlp/qdrant_manager.py`)
  - [x] Création collections avec VectorParams (size, distance, on_disk)
  - [x] Payload indexes (conversation_id, speakers, turn_range)
  - [x] Upsert par batch avec PointStruct
  - [x] Search avec filtres et score threshold
  - [x] Hybrid search (dense + sparse préparé)
  - [x] Collection management (info, delete, scroll)
- [x] **NER et extraction entités** (`src/nlp/ner.py`)
  - [x] Support transformers (camembert-ner) et SpaCy
  - [x] Extraction 6 types: PERSON, LOCATION, ORG, DATE, TIME, MISC
  - [x] PersonExtractor spécialisé (name, mentions, confidence, first/last turn)
  - [x] Agrégation et déduplication entités
  - [x] Extraction relations familiales par pattern matching
  - [x] Context window autour des entités
- [x] **Analyse de sentiment** (`src/nlp/sentiment.py`)
  - [x] Support multilingue (bert-base-multilingual-uncased-sentiment)
  - [x] 5 labels: very_negative, negative, neutral, positive, very_positive
  - [x] Scoring 1-5 étoiles avec confidence
  - [x] Analyse conversation complète (distribution, shifts, trajectory)
  - [x] Détection moments clés (most positive/negative)
  - [x] EmotionAnalyzer avec 6 émotions (joy, sadness, anger, fear, surprise, disgust)
- [x] **NLP Processor orchestrateur** (`src/nlp/processor.py`)
  - [x] Orchestration pipeline: chunk → embed → index → NER → sentiment
  - [x] Exécution parallèle NER et sentiment (asyncio.gather)
  - [x] NLPProcessingResult avec stats complètes
  - [x] Factory avec 3 configs: local_gpu, openai, lightweight(CPU)
  - [x] Search sémantique avec query embedding
- [x] **Intégration pipeline ingestion** (`src/ingestion/consumer.py`)
  - [x] Import conditionnel NLP (graceful degradation si non disponible)
  - [x] Initialisation NLPProcessor dans RedisStreamConsumer
  - [x] Step 5: NLP processing après normalisation
  - [x] Update conversation avec topics (top persons)
  - [x] Metadata job enrichie (num_chunks, persons, sentiment)
  - [x] Error handling NLP (ne fail pas le job entier)
- [x] **Requirements mis à jour**
  - [x] transformers, sentence-transformers, torch dans requirements.txt
  - [x] spacy, accelerate, tokenizers ajoutés
  - [x] requirements-gpu.txt déjà présent (CUDA 12.1, faiss-gpu, flash-attn)

## Phase 6 - API & experience utilisateur (a faire)
- [ ] Exposer l''API FastAPI v1 (upload external, search, profiles, intelligence, exports) + OpenAPI.
- [ ] Implementer la generation de suggestions et l''export PDF via le backend.
- [ ] Prototyper l''interface POC (Next.js/Tauri) pour recherche, fiches profil, timeline.

## Phase 7 - Qualite, securite, observabilite (a faire)
- [ ] Mettre en place tests unitaires et scenarios end-to-end du pipeline conversationnel.
- [ ] Configurer Prometheus/Grafana, alerting, et journalisation structuree (correlation ids, speakers).
- [ ] Implementer chiffrement des donnees, RBAC, gestion du consentement et audit trail.

## Phase 8 - Preparation migration cloud (a faire)
- [ ] Containeriser l''ensemble des services avec publication sur le registry cible.
- [ ] Rediger les manifests Helm et le socle Terraform (reseau, GPU nodes, services manages).
- [ ] Preparer les scripts de migration de donnees (pg_dump, snapshot Qdrant, sync MinIO -> S3/GCS).
- [ ] Definir la strategie CI/CD (GitHub Actions) pour builds, tests, deploiements.


