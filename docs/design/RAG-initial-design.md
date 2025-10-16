# RAG initial design

## References
- docs/specifications/SPEC_CONVERSATION_RAG.md (sections 1-12)
- docs/specifications/Spec-analyse-fichiers.md

## Scope and objectives
- Build a RAG pipeline dedicated to professional conversations, as detailed in the specification (goals, user stories, requirements).
- Run locally on a workstation with NVIDIA RTX 3090 (24 GB VRAM) while ensuring the design is portable to a managed cloud deployment.
- Reuse transcription, diarization, and speaker identification coming from an external project; start ingestion at the structured transcript level.

## High level architecture
- Container based deployment (Docker Compose) grouping ingestion, processing, vector services, and API; prepare Helm charts and Terraform stubs for later cloud rollout.
- Event driven orchestration (FastAPI services + Redis Streams or RabbitMQ) to decouple ingestion, enrichment, search, and insights.
- Externalized configuration (pydantic Settings, .env, cloud secret manager) to allow environment switching without code changes.

## Data ingestion and normalization
- Expected inputs: cleaned transcripts, speaker labels, timestamps, GPS metadata, optional attachments (notes, calendar events).
- Standardize each conversation into conversation.jsonl with segments, participants, metadata, and quality flags.
- Use Prefect or Dagster for pipeline coordination (retries, observability, scheduling) while keeping the flow deployable as a single process during POC.
- Persist raw transcripts and audio artifacts in MinIO (S3 compatible) so that a future migration to S3 or GCS is trivial.

## Storage strategy
- PostgreSQL for structured entities: conversations, people, interaction timeline, access rights, audit trail.
- Qdrant for dense retrieval (HNSW, 8 bit quantization) to satisfy latency target (<200 ms) and scale to 1M vectors.
- Redis cache for frequently recomputed insights (NER mentions, pending reminders) and rate limiting of API calls.

## NLP and ML processing on RTX 3090
- Chunking with LangChain text splitters tuned for conversation structure (speaker aware windows).
- Embeddings: local inference of bge-large-fr or jina-embeddings-v3 in FP16, batched to reach >1000 chunks per second.
- NER and relation extraction: fine tune CamemBERT or DeBERTa models plus spaCy rules to meet accuracy targets on names, family relations, and dates.
- Reranking: cross encoder bge-reranker-large on GPU for top 10 retrieval refinement.
- Generation: quantized 7B LLM (Llama 3.1 8B Q4_K_M) served via vLLM or TGI; keep an API fallback (OpenAI) for quality benchmarking.
- GPU scheduling: share weights with bitsandbytes, use paged attention, and profile VRAM to keep total usage under 20 GB.

## Profiles, insights, and suggestions
- Automation steps after ingestion: entity aggregation, timeline stitching, project detection, sentiment trend analysis.
- Store per person aggregates in PostgreSQL materialized tables refreshed asynchronously.
- Suggestion engine mixing heuristics (upcoming milestones, sentiment drops) and similarity scores; expose confidence and provenance for transparency.
- PDF export using WeasyPrint or ReactPDF backed by the profile summary API.

## API and user experience
- FastAPI endpoints mirroring section 8 of the specification (upload, search, profiles, intelligence, exports) with OpenAPI documentation.
- Authentication and RBAC using JWT, refresh tokens, and per user isolation as required by security section 4.
- Lightweight POC front end (Next.js or Tauri) for conversation search, profile overview, and timeline exploration.

## Security, compliance, and observability
- Encrypt data at rest (PostgreSQL pgcrypto or native TDE) and enforce TLS 1.3 via Traefik/Caddy reverse proxy.
- Implement detailed access logs, consent tracking, and delete requests to satisfy GDPR obligations.
- Monitoring stack: Prometheus + Grafana for GPU metrics, request latency, RAG answer quality (LLM judge scores).
- Backup and retention policies aligned with specification: daily incremental backup, archival after two years.

## Testing and quality gates
- Unit tests for NER, embedding generation, and metadata parsing using fixtures from representative transcripts.
- Integration tests covering end to end pipeline (transcript to profile) and RAG answer accuracy against curated questions.
- Load scenarios: 100 parallel conversations ingestion, Qdrant search on 10k vectors, GPU memory soak tests.
- CI pipeline running lint, tests, and lightweight performance smoke on every merge request.

## Delivery roadmap
- Weeks 1-2: core ingestion, storage schemas, embeddings, basic semantic search API.
- Weeks 3-4: NER enrichment, profile aggregation, suggestion MVP, front end prototype.
- Weeks 5-6: hardening (security, observability), PDF export, load testing, documentation.

## Cloud migration strategy
- Package all services as OCI images, push to registry; reuse Docker Compose definitions via Helm charts.
- Replace local dependencies with managed equivalents (Cloud PostgreSQL, Qdrant Cloud, S3/GCS, managed Redis).
- Deploy via Terraform (networking, GPU nodes, storage classes) and GitHub Actions for CI/CD automation.
- Plan data migration scripts (pg_dump, Qdrant snapshot, MinIO to S3 sync) for seamless cutover.

## Audio pipeline integration contract

Detailed cross-team requirements are tracked in `docs/design/cross-cutting-concern.md`.

### Integration responsibilities
- Upstream audio project: delivers diarized transcripts, speaker identities, audio asset reference, and context metadata (meeting title, calendar id, GPS, capture quality).
- RAG ingestion service: validates payloads, enriches with internal IDs, stages artifacts in MinIO, and triggers downstream processing via orchestration layer.

### Delivery mode (MinIO drop selected)
- Primary flow: audio project writes transcript package (tar.gz) to `minio://ingestion/drop/<date>/<external_event_id>.tar.gz` and posts a notification message to Redis Streams `audio.ingestion`.
- Optional fallback (future): REST push `POST /api/v1/conversations/external` if MinIO access is not possible for a producer.

Payload schema below applies to either mode.

### Payload schema (JSON)
- `external_event_id` (string, required): stable identifier per conversation to avoid duplicates. Format: `rec-<ISO8601>-<UUID>` (e.g., `rec-20251003T091500Z-3f9c4241`).
- `source_system` (string, required): e.g., "transcript-pipeline-v1".
- `created_at` (ISO 8601, required).
- `meeting_metadata` (object): `title`, `scheduled_start`, `duration_sec`, `location` (GPS lat/lon + display_name), `participants` (array of {`speaker_id`, `display_name`, `email`, `role`} ).
- `segments` (array ordered by time): items with `segment_id`, `speaker_id`, `start_ms`, `end_ms`, `text`, `language`, `confidence`, optional `annotations` (sentiment, entities, topics).
- `attachments` (object, optional): `audio_uri`, `notes_uri`, `calendar_uri` pointing to MinIO/S3 keys.
- `quality_flags` (object): `missing_audio`, `low_confidence`, `overlapping_speech`, `nlp_partial`.
- `analytics` (object, optional): `sentiment_summary`, `entities_summary` for conversation-level insights (v1.1+).

### REST contract specifics
- Request headers: `Authorization: Bearer <token>`, `Content-Type: application/json`, optional `Idempotency-Key` matching `external_event_id`.
- Success response: `202 Accepted` with body `{ "ingestion_id": "uuid", "status": "queued" }`.
- Validation errors: `422` with details (`field`, `message`).
- Authentication failures: `401` (invalid token) or `403` (token lacks `ingest:conversations`).

### Drop folder contract specifics
- Transcript package archived as tar.gz containing `conversation.json` plus optional media files; naming convention `<external_event_id>.tar.gz`.
  - Example: `rec-20251003T091500Z-3f9c4241.tar.gz`
- Notification message payload: `{ "external_event_id": "rec-20251003T091500Z-3f9c4241", "package_uri": "minio://...", "checksum": "sha256:...", "schema_version": "1.1", "metadata": {"trace_id": "550e8400-..."} }`.
- Ingestion service tracks processed ids in Redis set to prevent duplicate pulls; errors push to `audio.ingestion.deadletter` with reason code.

### Error handling and retries
- Upstream retries REST submissions with exponential backoff up to 5 attempts; ingestion service returns deterministic validation errors so producer can fix payload.
- In drop mode, ingestion service deletes package only after successful handoff to orchestration; otherwise leaves file and writes error log to `ingestion/errors/<external_event_id>.log`.

### Observability & SLAs
- Emit structured logs tagged with `external_event_id` and `source_system`.
- Prometheus counters: `audio_ingest_received_total`, `audio_ingest_failed_total`, histogram for end-to-end latency.
- SLA: ack within 5 seconds, downstream processing kickoff within 1 minute under normal load.

### Security considerations
- mTLS or signed JWT between audio project and ingestion endpoint; rotate credentials every 90 days.
- Payload encryption at rest (MinIO SSE) and optional client-side encryption for audio URIs.
- Access control list ensuring only ingestion service can read drop bucket prefix; WORM policy for audit logs.

## Open questions and next steps
- Finalize MinIO drop workflow (notification schema, retention policies, retransmission rules) with the audio project.
- Select final embedding, NER, and LLM models after benchmarking VRAM usage on the RTX 3090 workstation.
- Validate Docker Compose layout and service boundaries with the team before starting implementation.







