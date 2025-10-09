# Module d'Ingestion

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/environments/.env.example .env
# Edit .env with your settings

# Initialize database
python src/ingestion/init_db.py init
```

### 2. Start Consumer

```bash
# Development
python -m src.ingestion.consumer

# Or use Make
make ingestion-start
```

### 3. Test Upload

```bash
# Simulate MinIO drop (for testing)
make minio-upload-test
```

## Architecture

```
Redis Events → Consumer → Normalizer → Storage
                  ↓           ↓          ↓
             Track Job   Validate   PostgreSQL
                                        ↓
                                     MinIO
```

## Components

- **RedisStreamConsumer** (`consumer.py`) - Event consumer
- **TranscriptNormalizer** (`normalizer.py`) - Data normalization
- **IngestionStorage** (`storage.py`) - Persistence layer
- **SchemaValidator** (`schemas.py`) - JSON Schema validation

## Data Flow

1. **Input** - Transcript from MinIO
```json
{
  "metadata": {"job_id": "...", "timestamp": "..."},
  "segments": [...]
}
```

2. **Normalized Output** - Conversation
```json
{
  "metadata": {...},
  "turns": [...],
  "participants": [...],
  "statistics": {...}
}
```

3. **Storage**:
   - PostgreSQL: Metadata + turns
   - MinIO: `conversation.jsonl`

## Configuration

Key environment variables:

```env
# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_STREAM_INGESTION=ingestion:events
REDIS_CONSUMER_GROUP=rag-processors

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://raguser:ragpassword@localhost:5432/ragdb
```

## Monitoring

### Status Check

```bash
# View ingestion jobs
make db-shell
SELECT job_id, status, retry_count, error_message
FROM ingestion_jobs
ORDER BY created_at DESC
LIMIT 10;
```

### Logs

```bash
# Consumer logs
make ingestion-logs

# PostgreSQL logs
docker logs rag-postgres

# MinIO logs
make minio-logs
```

## Error Handling

| Status | Description | Action |
|--------|-------------|--------|
| `pending` | Waiting to process | Auto-start |
| `downloading` | Fetching from MinIO | Auto-retry 3x |
| `normalizing` | Parsing data | Fails on invalid |
| `completed` | Success | Done |
| `failed` | Max retries reached | Manual fix |

## Common Issues

### Consumer not receiving events

```bash
# Check Redis stream
make redis-cli
XINFO STREAM ingestion:events

# Check consumer group
XINFO GROUPS ingestion:events
```

### Database connection error

```bash
# Test connection
make db-shell

# Reset database
python src/ingestion/init_db.py reset
```

### MinIO download fails

```bash
# Check bucket
make minio-buckets

# Verify object
make minio-console
# Navigate to http://localhost:9001
```

## Testing

```bash
# Run all tests
pytest tests/test_ingestion/

# Specific tests
pytest tests/test_ingestion/test_normalizer.py -v

# With coverage
pytest --cov=src/ingestion tests/test_ingestion/
```

## API Integration

### Trigger Ingestion (from Transcript service)

```python
import redis

client = redis.from_url("redis://localhost:6379/0")

# Publish event
client.xadd(
    "ingestion:events",
    {
        "job_id": "abc123",
        "bucket": "ingestion",
        "object_key": "abc123/transcript.json",
        "event_type": "put",
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

### Query Conversation (from API)

```python
from src.ingestion.storage import IngestionStorage

storage = IngestionStorage()

# Get conversation
conversation = await storage.get_conversation("conv-id-123")

# Get turns
turns = await storage.get_conversation_turns("conv-id-123")
```

## Documentation

- [Pipeline Overview](./pipeline-overview.md) - Architecture détaillée
- [JSON Schemas](../../src/ingestion/schemas/) - Validation schemas
- [ADR 003](../adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md) - Architecture decisions

## Next Steps

**Phase 5 - Embeddings & NLP**:
1. Chunk conversations for embedding
2. Generate vectors with OpenAI/local model
3. Index in Qdrant
4. Add NER and sentiment analysis

**Commands to add**:
```bash
make ingestion-embed <conversation_id>
make ingestion-analyze <conversation_id>
```
