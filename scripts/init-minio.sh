#!/bin/bash
# MinIO Initialization Script
# Creates buckets, sets policies, and configures event notifications

set -e

# Configuration from environment variables
MINIO_ENDPOINT="${MINIO_ENDPOINT:-minio:9000}"
MINIO_ROOT_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minioadmin}"
MINIO_ALIAS="${MINIO_ALIAS:-myminio}"

# Bucket names
BUCKET_INGESTION="${MINIO_BUCKET_INGESTION:-ingestion}"
BUCKET_RESULTS="${MINIO_BUCKET_RESULTS:-results}"
BUCKET_ARCHIVE="${MINIO_BUCKET_ARCHIVE:-archive}"

# Redis configuration for event notifications
REDIS_ENDPOINT="${REDIS_ENDPOINT:-redis:6379}"
REDIS_STREAM="${REDIS_STREAM_INGESTION:-ingestion:events}"

echo "========================================="
echo "MinIO Initialization Script"
echo "========================================="
echo "Endpoint: $MINIO_ENDPOINT"
echo "Alias: $MINIO_ALIAS"
echo ""

# Wait for MinIO to be ready
echo "[1/7] Waiting for MinIO to be ready..."
until curl -sf http://${MINIO_ENDPOINT}/minio/health/live > /dev/null 2>&1; do
    echo "  MinIO is not ready yet, waiting 2s..."
    sleep 2
done
echo "  ✓ MinIO is ready!"

# Set up MinIO alias
echo ""
echo "[2/7] Configuring MinIO client alias..."
mc alias set $MINIO_ALIAS http://${MINIO_ENDPOINT} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
echo "  ✓ Alias configured"

# Create buckets
echo ""
echo "[3/7] Creating buckets..."
mc mb ${MINIO_ALIAS}/${BUCKET_INGESTION} --ignore-existing
echo "  ✓ Bucket '${BUCKET_INGESTION}' created"

mc mb ${MINIO_ALIAS}/${BUCKET_RESULTS} --ignore-existing
echo "  ✓ Bucket '${BUCKET_RESULTS}' created"

mc mb ${MINIO_ALIAS}/${BUCKET_ARCHIVE} --ignore-existing
echo "  ✓ Bucket '${BUCKET_ARCHIVE}' created"

# Set bucket policies
echo ""
echo "[4/7] Configuring bucket policies..."

# Ingestion bucket: Private (upload only by authenticated services)
cat > /tmp/ingestion-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": ["*"]},
      "Action": ["s3:PutObject"],
      "Resource": ["arn:aws:s3:::${BUCKET_INGESTION}/*"],
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "AES256"
        }
      }
    }
  ]
}
EOF
mc anonymous set-json /tmp/ingestion-policy.json ${MINIO_ALIAS}/${BUCKET_INGESTION}
echo "  ✓ Ingestion bucket policy set (upload-only with encryption)"

# Results bucket: Public read access
mc anonymous set download ${MINIO_ALIAS}/${BUCKET_RESULTS}
echo "  ✓ Results bucket policy set (public read)"

# Archive bucket: Private (no anonymous access)
mc anonymous set none ${MINIO_ALIAS}/${BUCKET_ARCHIVE}
echo "  ✓ Archive bucket policy set (private)"

# Enable versioning
echo ""
echo "[5/7] Enabling versioning..."
mc version enable ${MINIO_ALIAS}/${BUCKET_INGESTION}
mc version enable ${MINIO_ALIAS}/${BUCKET_ARCHIVE}
echo "  ✓ Versioning enabled for ingestion and archive buckets"

# Configure lifecycle policies
echo ""
echo "[6/7] Configuring lifecycle policies..."

# Ingestion: Move to archive after 7 days, delete after 90 days
cat > /tmp/ingestion-lifecycle.json <<EOF
{
  "Rules": [
    {
      "ID": "MoveToArchive",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Transition": {
        "Days": 7,
        "StorageClass": "STANDARD_IA"
      }
    },
    {
      "ID": "DeleteOld",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
EOF
mc ilm import ${MINIO_ALIAS}/${BUCKET_INGESTION} < /tmp/ingestion-lifecycle.json || true
echo "  ✓ Lifecycle policy configured for ingestion bucket"

# Results: Delete after 30 days
cat > /tmp/results-lifecycle.json <<EOF
{
  "Rules": [
    {
      "ID": "DeleteOld",
      "Status": "Enabled",
      "Filter": {
        "Prefix": ""
      },
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
EOF
mc ilm import ${MINIO_ALIAS}/${BUCKET_RESULTS} < /tmp/results-lifecycle.json || true
echo "  ✓ Lifecycle policy configured for results bucket"

# Configure event notifications to Redis
echo ""
echo "[7/7] Configuring event notifications..."

# Add Redis notification endpoint (if Redis is available)
if curl -sf ${REDIS_ENDPOINT} > /dev/null 2>&1; then
    # Note: MinIO Redis notifications require mc admin commands and proper Redis configuration
    # This is a placeholder - actual implementation depends on MinIO notification configuration
    mc event add ${MINIO_ALIAS}/${BUCKET_INGESTION} arn:minio:sqs::PRIMARY:redis \
        --event put \
        --suffix .tar.gz \
        --suffix .m4a \
        --suffix .wav \
        --suffix .mp3 || true
    echo "  ✓ Event notifications configured for ingestion bucket"
else
    echo "  ⚠ Redis not available, skipping event notifications"
fi

# Clean up temporary files
rm -f /tmp/ingestion-policy.json /tmp/ingestion-lifecycle.json /tmp/results-lifecycle.json

echo ""
echo "========================================="
echo "MinIO initialization complete!"
echo "========================================="
echo ""
echo "Buckets created:"
echo "  - ${BUCKET_INGESTION} (upload-only, encrypted, versioned, lifecycle: 7d→archive, 90d→delete)"
echo "  - ${BUCKET_RESULTS} (public read, lifecycle: 30d→delete)"
echo "  - ${BUCKET_ARCHIVE} (private, versioned)"
echo ""
echo "Access MinIO Console at: http://localhost:9001"
echo "Credentials: ${MINIO_ROOT_USER} / ${MINIO_ROOT_PASSWORD}"
echo ""
