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

### API Key Management

API keys are managed through **fastapi_simple_security** (stored in SQLite database) and provide the following features:

- **Persistent storage**: Keys stored in `data/api_keys.sqlite3`
- **Non-expiring keys**: Keys do not expire by default (configurable with `never_expires` parameter)
- **Rotation support**: Use `GET /auth/renew` to create a new key (old key automatically revoked)
- **Revocation**: Immediately invalidate keys using `GET /auth/revoke`
- **Usage tracking**: Monitor key usage with `GET /auth/logs`

### Authentication Endpoints

| Endpoint | Method | Purpose | Authentication Required |
|----------|--------|---------|------------------------|
| `/auth/new` | GET | Create a new API key | Yes |
| `/auth/revoke` | GET | Revoke an existing key | Yes |
| `/auth/renew` | GET | Renew/rotate key (old key revoked) | Yes |
| `/auth/logs` | GET | View API key usage logs | Yes |

**Example: Creating a new API key**

```bash
curl -X GET "https://api.transcript.example.com/auth/new?never_expires=true" \
  -H "Authorization: ApiKey <existing-api-key>"
```

**Response:**

```json
{
  "api_key": "abc123-def456-ghi789"
}
```

⚠️ **Important**: The API key is only shown once during creation. Store it securely in iOS Keychain.

**Example: Rotating an existing API key**

```bash
curl -X GET "https://api.transcript.example.com/auth/renew?never_expires=true" \
  -H "Authorization: ApiKey <current-api-key>"
```

**Response:**

```json
{
  "api_key": "xyz789-uvw456-rst123"
}
```

The old key is automatically revoked after renewal.

### Security Best Practices

1. **Store keys securely**: Use iOS Keychain for API key storage with biometric protection
2. **Periodic rotation**: Rotate keys periodically (e.g., every 90 days) using `GET /auth/renew`
3. **Revoke compromised keys**: Immediately revoke any leaked or compromised keys using `GET /auth/revoke`
4. **Monitor usage**: Regularly check `GET /auth/logs` for suspicious activity
5. **Use HTTPS only**: API keys should never be transmitted over unencrypted connections
6. **Limit key scope**: Create separate keys for different devices/applications

## Security Headers

All API responses include the following security headers:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains` - Forces HTTPS for 1 year
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `X-XSS-Protection: 1; mode=block` - Enables XSS filtering in older browsers
- `Content-Security-Policy: default-src 'self'` - Restricts resource loading
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information

## Rate Limits

- 10 job creations per minute per device
- 100 status checks per minute per device
- 5 authentication operations per minute per device

Rate limit information is included in response headers:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when limit resets
- `Retry-After`: Seconds to wait before retrying (when rate limited)

## Related Documentation

- ADR-2025-10-03-003 - Cross-Cutting Contract for Audio → Transcript → RAG
- ADR-2025-10-16-006 - Authentication & Authorization Architecture
- `docs/API_KEY_SETUP.md` - Detailed API key setup guide
- `docs/IOS_AUTHENTICATION_SPEC.md` - iOS client authentication implementation
- `docs/MIGRATION_GUIDE.md` - Migration guide for authentication changes
- `docs/design/conversation-payload.schema.json` - Output payload schema
