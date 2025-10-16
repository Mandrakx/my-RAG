-- Initial schema creation for my-RAG ingestion database
-- Includes all cross-cutting contract fields from ADR-2025-10-16-004
-- Date: 2025-10-17

-- Table: ingestion_jobs
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id VARCHAR(255) PRIMARY KEY,

    -- Source information
    job_id VARCHAR(255) UNIQUE NOT NULL,
    external_event_id VARCHAR(128) UNIQUE NOT NULL,  -- Format: rec-YYYYMMDDTHHMMSSZ-<uuid>
    source_bucket VARCHAR(255) NOT NULL,
    source_key VARCHAR(512) NOT NULL,

    -- Cross-cutting contract fields (ADR-2025-10-03-003)
    trace_id VARCHAR(128),  -- Distributed tracing UUID
    checksum VARCHAR(256),  -- SHA-256 checksum (format: sha256:<64 hex>)
    schema_version VARCHAR(16),  -- Payload schema version (e.g., 1.0, 1.1)

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Timing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_error_at TIMESTAMP,

    -- Error handling
    error_message TEXT,
    error_stack TEXT,
    error_code VARCHAR(64),  -- Standardized error code
    processing_metadata JSONB DEFAULT '{}',

    -- Results
    conversation_id VARCHAR(255),
    normalized_key VARCHAR(512),

    -- Metrics
    file_size_bytes INTEGER,
    processing_duration_ms INTEGER
);

-- Indexes for ingestion_jobs
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_job_id ON ingestion_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_external_event_id ON ingestion_jobs(external_event_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_trace_id ON ingestion_jobs(trace_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_error_code ON ingestion_jobs(error_code);

-- Table: conversations
CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,

    -- Basic metadata
    title VARCHAR(255),
    date TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    language VARCHAR(10) DEFAULT 'fr',

    -- Classification
    conversation_type VARCHAR(50),  -- meeting, one_to_one, monologue, etc.
    interaction_type VARCHAR(50),   -- professional, personal, mixed

    -- Location
    location_name VARCHAR(255),
    location_address VARCHAR(512),
    location_gps JSONB,  -- {lat: float, lon: float}
    location_type VARCHAR(50),

    -- Content
    transcript TEXT NOT NULL,
    summary TEXT,

    -- Participants (JSON array)
    participants JSONB DEFAULT '[]',

    -- Tags and topics
    tags JSONB DEFAULT '[]',
    main_topics JSONB DEFAULT '[]',

    -- Quality metrics
    confidence_score FLOAT DEFAULT 1.0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Vector storage reference
    qdrant_collection VARCHAR(255) DEFAULT 'conversations',
    qdrant_point_id VARCHAR(255),

    -- User ownership (multi-tenancy)
    user_id VARCHAR(255)
);

-- Indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_date ON conversations(date);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Table: conversation_turns
CREATE TABLE IF NOT EXISTS conversation_turns (
    id VARCHAR(255) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,

    -- Turn details
    turn_index INTEGER NOT NULL,
    speaker VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    timestamp_ms INTEGER,  -- Position in audio

    -- Sentiment
    sentiment VARCHAR(20),  -- positive, negative, neutral
    sentiment_score FLOAT,
    emotion VARCHAR(50),

    -- Vector reference
    qdrant_point_id VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign key
    CONSTRAINT fk_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations(id)
        ON DELETE CASCADE
);

-- Indexes for conversation_turns
CREATE INDEX IF NOT EXISTS idx_conversation_turns_conversation_id ON conversation_turns(conversation_id);

-- Foreign key for ingestion_jobs -> conversations
ALTER TABLE ingestion_jobs
ADD CONSTRAINT fk_ingestion_conversation
    FOREIGN KEY (conversation_id)
    REFERENCES conversations(id)
    ON DELETE SET NULL;

-- Comments for documentation
COMMENT ON TABLE ingestion_jobs IS 'Tracks ingestion jobs from Transcript service to RAG pipeline';
COMMENT ON COLUMN ingestion_jobs.external_event_id IS 'Stable identifier from transcript service (format: rec-YYYYMMDDTHHMMSSZ-<uuid>)';
COMMENT ON COLUMN ingestion_jobs.trace_id IS 'Distributed tracing ID (UUID v4) propagated from iOS → Transcript → RAG';
COMMENT ON COLUMN ingestion_jobs.checksum IS 'SHA-256 checksum of tar.gz archive (format: sha256:<64 hex chars>)';
COMMENT ON COLUMN ingestion_jobs.schema_version IS 'Conversation payload schema version (e.g., 1.0, 1.1)';
COMMENT ON COLUMN ingestion_jobs.error_code IS 'Standardized error code (e.g., validation_error, checksum_mismatch) for DLQ routing';

COMMENT ON TABLE conversations IS 'Conversation metadata and content';
COMMENT ON TABLE conversation_turns IS 'Individual turns/segments within a conversation';

-- Verification query
SELECT
    'ingestion_jobs' as table_name,
    COUNT(*) as row_count
FROM ingestion_jobs
UNION ALL
SELECT
    'conversations' as table_name,
    COUNT(*) as row_count
FROM conversations
UNION ALL
SELECT
    'conversation_turns' as table_name,
    COUNT(*) as row_count
FROM conversation_turns;
