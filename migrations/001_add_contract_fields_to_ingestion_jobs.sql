-- Migration: Add cross-cutting contract fields to ingestion_jobs table
-- Date: 2025-10-16
-- ADR: ADR-2025-10-16-004-alignment-cross-cutting-contract
-- Description: Add fields required by audio-redis-message-schema (external_event_id, trace_id, checksum, schema_version, error_code)

-- Step 1: Add new columns
ALTER TABLE ingestion_jobs
ADD COLUMN IF NOT EXISTS external_event_id VARCHAR(128),
ADD COLUMN IF NOT EXISTS trace_id VARCHAR(128),
ADD COLUMN IF NOT EXISTS checksum VARCHAR(256),
ADD COLUMN IF NOT EXISTS schema_version VARCHAR(16),
ADD COLUMN IF NOT EXISTS error_code VARCHAR(64);

-- Step 2: Backfill external_event_id from job_id for existing rows (if any)
-- This ensures existing data doesn't break UNIQUE constraint
UPDATE ingestion_jobs
SET external_event_id = job_id
WHERE external_event_id IS NULL;

-- Step 3: Make external_event_id NOT NULL after backfill
ALTER TABLE ingestion_jobs
ALTER COLUMN external_event_id SET NOT NULL;

-- Step 4: Add unique constraint on external_event_id
ALTER TABLE ingestion_jobs
ADD CONSTRAINT unique_external_event_id UNIQUE (external_event_id);

-- Step 5: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_external_event_id ON ingestion_jobs(external_event_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_trace_id ON ingestion_jobs(trace_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_error_code ON ingestion_jobs(error_code);

-- Step 6: Add comments for documentation
COMMENT ON COLUMN ingestion_jobs.external_event_id IS 'Stable identifier from transcript service (format: rec-YYYYMMDDTHHMMSSZ-<uuid>)';
COMMENT ON COLUMN ingestion_jobs.trace_id IS 'Distributed tracing ID (UUID v4) propagated from iOS → Transcript → RAG';
COMMENT ON COLUMN ingestion_jobs.checksum IS 'SHA-256 checksum of tar.gz archive (format: sha256:<64 hex chars>)';
COMMENT ON COLUMN ingestion_jobs.schema_version IS 'Conversation payload schema version (e.g., 1.0, 1.1)';
COMMENT ON COLUMN ingestion_jobs.error_code IS 'Standardized error code (e.g., validation_error, checksum_mismatch) for DLQ routing';

-- Verification query (uncomment to run after migration)
-- SELECT
--     COUNT(*) as total_jobs,
--     COUNT(DISTINCT external_event_id) as unique_events,
--     COUNT(trace_id) as jobs_with_trace_id,
--     COUNT(checksum) as jobs_with_checksum,
--     COUNT(error_code) as failed_jobs
-- FROM ingestion_jobs;
