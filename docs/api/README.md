# API Documentation

This directory contains OpenAPI (Swagger) specifications for the Transcript service API.

## Files

- `transcript-api.openapi.yaml` - Complete OpenAPI 3.0 specification for the Transcript API

## Viewing the Documentation

### Option 1: Online Swagger Editor (Quickest)

1. Go to https://editor.swagger.io
2. Copy the content of `transcript-api.openapi.yaml`
3. Paste into the editor

### Option 2: Local Swagger UI

```bash
# Install swagger-ui-watcher (one-time setup)
npm install -g swagger-ui-watcher

# Launch interactive documentation
swagger-ui-watcher docs/api/transcript-api.openapi.yaml
```

Then open http://localhost:8000 in your browser.

### Option 3: VS Code Extension

1. Install the "OpenAPI (Swagger) Editor" extension
2. Open `transcript-api.openapi.yaml`
3. Click "Preview" in the top-right corner

### Option 4: Docker (Swagger UI)

```bash
# Run Swagger UI in Docker
docker run -p 8080:8080 \
  -e SWAGGER_JSON=/api/transcript-api.openapi.yaml \
  -v $(pwd)/docs/api:/api \
  swaggerapi/swagger-ui
```

Then open http://localhost:8080

## API Features

The Transcript API supports two upload flows:

1. **Two-Phase Upload (Recommended)** - Better for large files
   - `POST /v1/jobs/init` - Get presigned URL
   - `PUT <presigned_url>` - Upload audio
   - `POST /v1/jobs/{job_id}/commit` - Commit for processing
   - `GET /v1/jobs/{job_id}` - Poll for status

2. **Single Multipart Upload** - Simpler for small files
   - `POST /v1/jobs` - Upload metadata + audio in one request
   - `GET /v1/jobs/{job_id}` - Poll for status

## Authentication

All endpoints (except `/v1/health/*`) require API key authentication:

```http
Authorization: ApiKey <your-api-key>
```

## Rate Limits

- 10 job creations per minute per device
- 100 status checks per minute per device

## Related Documentation

- ADR-2025-10-03-003 - Cross-Cutting Contract for Audio → Transcript → RAG
- `docs/design/conversation-payload.schema.json` - Output payload schema
