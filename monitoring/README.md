# Monitoring Setup - my-RAG Audio Ingestion

This directory contains the monitoring configuration for the my-RAG audio ingestion pipeline, implementing observability requirements from ADR-2025-10-16-004.

## Overview

The monitoring stack includes:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **15 Custom Metrics**: Ingestion pipeline observability

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start all services including Prometheus and Grafana
docker-compose up -d

# Or start only monitoring services
docker-compose up -d prometheus grafana
```

### 2. Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

### 3. View Ingestion Metrics

1. Open Grafana at http://localhost:3000
2. Navigate to **Dashboards** → **Audio Ingestion** folder
3. Open **Audio Ingestion Metrics - my-RAG** dashboard

## Metrics Reference

### SLA Metrics

| Metric | Description | SLA Target |
|--------|-------------|------------|
| `audio_ingest_ack_latency_seconds` | Time from message receipt to ack | p95 < 30s |
| `audio_ingest_failures_total` | Failure count by reason | < 1% |

### Processing Metrics

| Metric | Description |
|--------|-------------|
| `audio_ingest_processing_duration_seconds` | Total processing time |
| `audio_ingest_validation_duration_seconds` | Payload validation time |
| `audio_ingest_checksum_validation_duration_seconds` | Checksum verification time |
| `audio_ingest_nlp_duration_seconds` | NLP processing time |

### Observability Metrics

| Metric | Description |
|--------|-------------|
| `audio_ingest_messages_total` | Total messages received |
| `audio_ingest_messages_inflight` | Current in-flight messages |
| `audio_ingest_trace_id_present_total` | Messages with trace_id |
| `audio_ingest_download_size_bytes` | Archive download size |
| `audio_ingest_conversation_segments` | Conversation segment count |
| `audio_ingest_conversation_participants` | Participant count |

### Error Metrics

| Metric | Description |
|--------|-------------|
| `audio_ingest_failures_total{reason}` | Failures by error code |
| `audio_ingest_dlq_published_total` | DLQ publish count |

## Dashboard Panels

The main dashboard includes:

1. **Ack Latency (SLA)**: p95/p99 latency with 30s threshold
2. **Current p95 Ack Latency**: Gauge showing current SLA compliance
3. **Messages In-Flight**: Active processing count
4. **Failure Rate by Reason**: Error breakdown
5. **Processing Stages Duration**: Validation, checksum, processing times
6. **Trace ID Coverage**: % of messages with trace_id
7. **Archive Download Size**: Download size distribution
8. **Conversation Complexity**: Segments and participants

## Prometheus Queries

### Check SLA Compliance

```promql
# p95 ack latency (should be < 30s)
histogram_quantile(0.95, sum(rate(audio_ingest_ack_latency_seconds_bucket[5m])) by (le))

# Failure rate (should be < 1%)
100 * sum(rate(audio_ingest_failures_total[5m])) / sum(rate(audio_ingest_messages_total[5m]))
```

### Trace ID Coverage

```promql
# % of messages with trace_id
100 * sum(audio_ingest_trace_id_present_total) / sum(audio_ingest_messages_total)
```

### Error Analysis

```promql
# Top error reasons
topk(5, sum(rate(audio_ingest_failures_total[5m])) by (reason))
```

## Configuration

### Prometheus Configuration

File: `monitoring/prometheus.yml`

- **Scrape Interval**: 15s (10s for ingestion)
- **Metrics Endpoint**: `http://app:8000/metrics`
- **Data Retention**: 15 days (default)

### Grafana Configuration

Files:
- `monitoring/grafana/datasources/prometheus.yml` - Prometheus datasource
- `monitoring/grafana/dashboards/dashboard.yml` - Dashboard provisioning
- `monitoring/grafana/dashboards/ingestion-metrics.json` - Main dashboard

## Alerting (Optional)

To enable alerting, uncomment the Alertmanager section in `prometheus.yml` and create alert rules:

```yaml
# monitoring/alerts/ingestion.yml
groups:
  - name: ingestion_sla
    interval: 30s
    rules:
      - alert: IngestionLatencyHigh
        expr: histogram_quantile(0.95, sum(rate(audio_ingest_ack_latency_seconds_bucket[5m])) by (le)) > 30
        for: 5m
        annotations:
          summary: "Ingestion p95 latency exceeds SLA (>30s)"

      - alert: IngestionFailureRateHigh
        expr: 100 * sum(rate(audio_ingest_failures_total[5m])) / sum(rate(audio_ingest_messages_total[5m])) > 1
        for: 5m
        annotations:
          summary: "Ingestion failure rate >1%"
```

## Troubleshooting

### Prometheus Not Scraping

1. Check if metrics endpoint is accessible:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify Prometheus targets:
   - Open http://localhost:9090/targets
   - Check if `my-rag-ingestion` target is UP

### Grafana Dashboard Not Loading

1. Verify datasource:
   - Grafana → Configuration → Data Sources
   - Test Prometheus connection

2. Check provisioning:
   ```bash
   docker logs rag-grafana | grep provisioning
   ```

### Missing Metrics

1. Verify metrics are being exported:
   ```bash
   curl http://localhost:8000/metrics | grep audio_ingest
   ```

2. Check if ingestion consumer is running:
   ```bash
   docker logs rag-app | grep "Starting ingestion consumer"
   ```

## Production Recommendations

1. **Data Retention**: Increase Prometheus retention for production
   ```yaml
   command:
     - '--storage.tsdb.retention.time=30d'
   ```

2. **Persistent Storage**: Use named volumes for Prometheus/Grafana data

3. **Authentication**: Enable Grafana LDAP/OAuth for production

4. **Alerting**: Configure Alertmanager for PagerDuty/Slack notifications

5. **Remote Write**: Send metrics to centralized Prometheus/Thanos

## References

- ADR-2025-10-16-004: Cross-cutting contract alignment
- `src/ingestion/metrics.py`: Metrics implementation
- Prometheus: https://prometheus.io/docs/
- Grafana: https://grafana.com/docs/

---

**Last Updated**: 2025-10-17
**Status**: ✅ Complete
