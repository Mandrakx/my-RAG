# API Documentation Changelog

## 2025-10-16 - Authentication & Security Update

### Added

#### Authentication Endpoints
- **POST /auth/new** - Create a new API key
  - Requires root API key or admin credentials
  - Returns API key (shown only once), key ID, and expiration date
  - Supports custom expiration periods (1-365 days, default 90)
  - Includes optional metadata for device tracking

- **POST /auth/revoke** - Revoke an API key
  - Immediately invalidates a key
  - Can revoke by key ID or the actual key value
  - Returns revocation timestamp

- **POST /auth/renew** - Renew an expiring API key
  - Creates a new key to replace an expiring one
  - Old key remains valid for 7-day grace period
  - Returns new key and grace period end date

#### Security Documentation
- Added comprehensive security headers documentation
  - Strict-Transport-Security (HSTS)
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Content-Security-Policy
  - Referrer-Policy

- Added API key management best practices
  - Secure storage guidelines (iOS Keychain)
  - Key rotation recommendations
  - Expiration monitoring
  - Revocation procedures

#### Rate Limits
- Added rate limit for authentication operations: 5 per minute per device
- Documented rate limit headers (X-RateLimit-*)

### Updated

#### OpenAPI Specification (transcript-api.openapi.yaml)
- Added new "Authentication" tag for auth endpoints
- Updated description with Unkey integration details
- Added security headers documentation in API description
- Validated YAML syntax

#### README.md
- Expanded authentication section with detailed explanations
- Added authentication endpoints table
- Included curl examples for API key creation
- Added security best practices section
- Documented security headers
- Enhanced rate limits section with header information
- Added references to new documentation files:
  - ADR-2025-10-16-006 (Authentication Architecture)
  - API_KEY_SETUP.md
  - IOS_AUTHENTICATION_SPEC.md
  - MIGRATION_GUIDE.md

### Implementation Details

#### Authentication Provider
- Integration with **Unkey** (unkey.com) for API key management
- Automatic key expiration after configurable period
- Support for key rotation with grace periods
- Revocation support for compromised keys

#### Security Enhancements
- All responses include security headers via middleware
- API keys transmitted via Authorization header only
- HTTPS enforcement through HSTS
- Content Security Policy to prevent XSS attacks

### Migration Notes

For existing API clients:
1. No breaking changes to existing endpoints
2. All `/v1/*` endpoints continue to work as before
3. Authentication header format unchanged: `Authorization: ApiKey <key>`
4. New authentication endpoints available for key management
5. Existing keys continue to work (check expiration dates)

### Related ADRs
- ADR-2025-10-16-006 - Authentication & Authorization Architecture
- ADR-2025-10-03-003 - Cross-Cutting Contract for Audio → Transcript → RAG

### Version Information
- OpenAPI Specification Version: 3.0.3
- API Version: 1.2.3
- Last Updated: 2025-10-16
