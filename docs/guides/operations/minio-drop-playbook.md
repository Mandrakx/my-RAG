# Playbook - MinIO Drop Workflow

## Purpose
Standard operating procedure for handling transcript packages delivered via MinIO tar.gz drop, including ingestion validation, retries, and incident response.

## Audience
- Audio capture/transcription team
- RAG ingestion/platform team

## Prerequisites
- Access to MinIO console/CLI with permissions on `ingestion/drop/`
- Redis CLI or monitoring dashboard for `audio.ingestion` streams
- JSON schema validator (`ajv`, `jsonschema`, or internal tool)
- Tar/gzip utilities (`tar`, `gzip`, `7z`)

## Normal Operation Checklist
1. Audio pipeline generates `<external_event_id>.tar.gz` with top-level folder `<external_event_id>/` and layout defined in `docs/design/cross-cutting-concern.md`.
2. Compute SHA-256 checksums and update `checksums.sha256` inside the archive (include every file, relative paths, newline at end).
3. Upload archive to `minio://ingestion/drop/<date>/<external_event_id>.tar.gz`.
4. Publish notification to Redis Streams `audio.ingestion` with JSON payload conforming to `docs/design/audio-redis-message-schema.json`.
5. Monitor ingestion dashboard: expect acknowledgement within 5 seconds and processing status within 1 minute; warning triggered at 3 seconds.

## Responsibility Hand-offs
| Phase | Owner | Support | Expected outcome |
|-------|-------|---------|------------------|
| Package creation | Audio team | RAG ingestion | Archive validates locally (`tar -tzf`, schema check). |
| Upload and notify | Audio team | Platform SRE | Object visible in MinIO and message published within 2 seconds. |
| Ack and validation | RAG ingestion | Platform SRE | Ack < 5s, validation < 60s, status pushed to dashboard. |
| Deadletter triage | Joint | Incident commander | Root cause shared within 15 minutes. |
| Retry execution | Audio team | RAG ingestion | Max 5 attempts (5/10/20/40/55s backoff). |

## Validation Steps (RAG Team)
- Confirm message arrival (`xreadgroup GROUP rag-team rag-consumer`).
- Verify checksum by downloading `checksums.sha256` and running `sha256sum -c`.
- Ensure archive root folder equals `external_event_id` inside `conversation.json`.
- Validate `conversation.json` structure (schema version, UTF-8) using `jsonschema` tool.
- If validations succeed, trigger orchestration flow (Prefect/Dagster) and mark notification as processed.

## Retry Policy
- Producer retries up to **5** times with exponential backoff (5s, 10s, 20s, 40s, 55s).
- Include `retry_count` in notification; stop retrying if `retry_count >= 5` or response indicates non-recoverable error.
- Maintain archives in MinIO for 72 hours; keep stream entries for 48 hours.
- Deadletter queue `audio.ingestion.deadletter` retains messages 7 days.

## Failure Scenarios & Response

### Validation Failure (checksum/schema)
- **Detection**: Error logged in ingestion service; message routed to deadletter with reason `validation_error`.
- **Action**: Audio team fixes payload, rebuilds archive, republishes message with incremented `retry_count`.
- **Communication**: Notify shared channel within 15 minutes, link to log snippet.

### Incorrect Archive Layout
- **Detection**: Validation step spots missing root folder, unexpected files, or incomplete `checksums.sha256`.
- **Action**: Audio team repackages archive following layout; rerun local validation checklist.
- **Communication**: Share updated package diff and confirmation of local checks.

### Ingestion Service Downtime
- **Detection**: Ack latency > 5s alerts; Redis backlog grows.
- **Action**: Platform team restores service, replays messages via `xreadgroup` or reprocesses from MinIO within 2 hours.
- **Communication**: Incident channel opened; reference postmortem template if downtime > 30 minutes.

### Partial Processing (pipeline crash after ack)
- **Detection**: Orchestration job fails; status not updated.
- **Action**: Platform team restarts job using archived package; update processing status API.
- **Communication**: Share resolution ETA and affected conversation IDs.

## Tools & Commands
- Download archive: `mc cp minio/ingestion/drop/.../<event>.tar.gz .`
- Extract for inspection: `tar -xzf <event>.tar.gz`
- Verify checksums: `sha256sum -c checksums.sha256`
- Validate JSON: `ajv validate -s docs/design/conversation-payload.schema.json -d conversation.json`

## Escalation Matrix
- Audio pipeline lead: <contact/email>
- RAG ingestion on-call: <contact/email>
- Platform SRE: <contact/email>

## Documentation References
- `docs/design/cross-cutting-concern.md`
- `docs/design/RAG-initial-design.md`
- `docs/adr/ADR-2025-09-30-002-minio-tar-gz-package.md`
- `docs/action-plan/README.md`

## Revision History
- 2025-10-01 - Added detailed responsibilities, layout validation, and ack SLA reminders.
- 2025-09-30 - Initial version
