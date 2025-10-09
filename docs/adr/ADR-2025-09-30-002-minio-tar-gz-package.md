# ADR-2025-09-30-002-minio-tar-gz-package

## Status
Accepted

## Context
The audio analysis project delivers transcripts, speaker metadata, and optional media files that our RAG ingestion service must consume through a MinIO drop. We need a standard archive format for the payload so producers and consumers can interoperate, validate checksums, and retry deliveries without ambiguity. The choice impacts tooling on both sides, observability of packages, and future portability to cloud object stores.

## Decision
Use a `tar.gz` archive as the mandatory packaging format for every conversation payload dropped on MinIO. Each archive will contain `conversation.json` plus optional media assets following the agreed directory layout and naming convention `<external_event_id>.tar.gz`.

## Rationale
- `tar.gz` supports streaming extraction and preserves file metadata, simplifying server-side processing on Linux.
- Compression ratios are better than plain zip for large JSON or text segments, reducing storage and transfer costs.
- Tooling required on the producer side (GNU tar, libarchive) is available in the current audio project deployment environment.
- Standardising now avoids a future migration once volumes grow and automation is in place.

## Alternatives Considered

### Option 1: tar.gz (selected)
**Description**: Package transcript and media into a tar archive compressed with gzip.
**Pros**:
- Efficient compression for text-heavy payloads.
- Stream-friendly and preserves POSIX metadata.
- Well supported in containerised Linux environments.

**Cons**:
- Windows users need additional tooling for manual inspection.
- Random access to a single file requires reading the archive sequentially.

### Option 2: zip
**Description**: Package payload using the ZIP file format with built-in index.
**Pros**:
- Native support on Windows and macOS for manual debugging.
- Random access and selective extraction built into the format.

**Cons**:
- Slightly worse compression for JSON/audio mixes.
- Does not preserve extended POSIX metadata and streams, limiting parity with Linux tooling.

## Consequences

### Positive
- Consistent processing pipeline with deterministic archive handling.
- Lower storage footprint on MinIO and cloud object stores.
- Easier automation for validation, checksum, and unpacking inside containers.

### Negative
- Manual inspection on Windows requires 7-Zip or WSL tooling.
- Onboarding must document the command-line workflow for producers unfamiliar with tar.

### Neutral
- Monitoring and checksum strategies remain unchanged regardless of the archive format.

## Implementation

### Action Plan
1. Update integration specifications to state tar.gz as the required format (done in `docs/design/RAG-initial-design.md`).
2. Provide sample tar.gz package and CLI instructions to the audio project team.
3. Add validation logic in the ingestion service ensuring the `.tar.gz` suffix and archive structure.
4. Extend automated tests to unpack tar.gz fixtures during CI.

### Teams Impacted
- Audio capture/transcription team (produces packages).
- RAG ingestion and platform team (consumes packages).

### Timeline
- Phase 2 alignment: 2025-10-07 target.
- Validation tooling ready: 2025-10-14.
- Enforcement in ingestion pipeline: 2025-10-21.

## References
- docs/design/RAG-initial-design.md
- docs/action-plan/README.md

## Notes
Revisit the decision if the producer environment loses access to GNU tar or if interoperability with third-party systems requires an alternative format.

---
**Date**: 2025-09-30
**Author**: Codex Assistant
**Reviewers**: TBD
