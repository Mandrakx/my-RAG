# Infrastructure Documentation

## Documents Disponibles

### [Setup Guide](./setup-guide.md) 📘
Guide complet d'installation et de configuration de l'infrastructure locale et production.

**Contenu**:
- Architecture des services
- Procédures d'installation
- Configuration détaillée
- Commandes Make
- Troubleshooting
- Sécurité et maintenance

## Quick Start

```bash
# 1. Setup initial
make setup

# 2. Configurer .env
cp config/environments/.env.example .env
# Éditer .env avec vos credentials

# 3. Démarrer l'infrastructure
make docker-up

# 4. Initialiser MinIO
make minio-init

# 5. Vérifier le status
make status
```

## Services Stack

```
┌─────────────────────────────────────────────────────┐
│                   Application (8000)                 │
│                     FastAPI + RAG                    │
└──────────────┬──────────┬──────────┬────────────────┘
               │          │          │
         ┌─────▼──┐  ┌────▼───┐  ┌──▼────────┐
         │Postgres│  │ Qdrant │  │   MinIO   │
         │ (5432) │  │(6333/  │  │(9000/9001)│
         │        │  │ 6334)  │  │           │
         └────────┘  └────────┘  └───────────┘
               │
         ┌─────▼──────┐
         │   Redis    │
         │   (6379)   │
         │  Streams   │
         └────────────┘
               │
    ┌──────────┴───────────┐
    │                      │
┌───▼──────┐      ┌────────▼─────┐
│Prometheus│      │   Grafana    │
│  (9090)  │      │    (3000)    │
└──────────┘      └──────────────┘
```

## Commandes Essentielles

### Gestion des Services

```bash
make help              # Voir toutes les commandes
make docker-up         # Démarrer tous les services
make docker-down       # Arrêter tous les services
make status            # Status et URLs d'accès
make docker-logs       # Voir les logs
```

### Services Individuels

```bash
# MinIO
make minio-console     # Ouvrir console (http://localhost:9001)
make minio-buckets     # Lister les buckets
make minio-logs        # Logs MinIO

# Qdrant
make qdrant-dashboard  # Ouvrir dashboard (http://localhost:6333/dashboard)
make qdrant-health     # Check health
make qdrant-logs       # Logs Qdrant

# Redis
make redis-cli         # Ouvrir CLI
make redis-streams     # Info streams
make redis-monitor     # Monitor en temps réel

# PostgreSQL
make db-shell          # Ouvrir psql
make db-backup         # Backup DB
make db-migrate        # Run migrations
```

## URLs Quick Access

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| **API Documentation** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | - |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |

## Architecture Highlights

### Object Storage - MinIO

**Buckets**:
- `ingestion/` - Audio files from iOS (encrypted, versioned)
- `results/` - Processed results (public read)
- `archive/` - Long-term archive (private, versioned)

**Lifecycle**:
- Ingestion: 7d → archive, 90d → delete
- Results: 30d → delete

### Vector Database - Qdrant

**Collections**:
- `conversations` - Conversation embeddings (1536 dimensions, Cosine)

**APIs**:
- HTTP: Port 6333
- gRPC: Port 6334

### Event Stream - Redis

**Streams**:
- `ingestion:events` - Audio ingestion notifications
- Consumer Group: `rag-processors`

### Database - PostgreSQL 16

**Schema**:
- Conversation metadata
- Processing status
- User profiles
- Audit logs

## Data Flow

### Ingestion Pipeline

```
iOS App
  ↓ (1) POST /v1/jobs/init
Transcript API
  ↓ (2) Presigned URL
MinIO/S3
  ↓ (3) Upload audio
  ↓ (4) POST /v1/jobs/{id}/commit
Redis Streams (ingestion:events)
  ↓ (5) Consumer processes
RAG Pipeline
  ↓ (6) Download from MinIO
  ↓ (7) Transcribe & Normalize
  ↓ (8) Chunk & Embed
Qdrant (vectors) + PostgreSQL (metadata)
```

## Configuration Files

```
my-RAG/
├── docker-compose.yml              # Services orchestration
├── .env                            # Environment variables
├── config/environments/
│   └── .env.example                # Template de configuration
├── scripts/
│   └── init-minio.sh               # Script init MinIO
├── monitoring/
│   ├── prometheus.yml              # Config Prometheus
│   └── grafana/dashboards/         # Dashboards Grafana
└── Makefile                        # Automation commands
```

## Monitoring & Observability

### Métriques Prometheus

- Application metrics: `http://localhost:8000/metrics`
- MinIO metrics: `http://localhost:9000/minio/v2/metrics/cluster`
- PostgreSQL metrics: Via postgres_exporter
- Redis metrics: Via redis_exporter

### Dashboards Grafana

1. **Application Overview** - Performance globale
2. **Ingestion Pipeline** - Metrics d'ingestion
3. **Vector Search** - Performance Qdrant
4. **Storage** - Utilisation MinIO

### Logs

```bash
# Logs structurés avec correlation IDs
make docker-logs

# Logs par service
make minio-logs
make qdrant-logs
make redis-logs
make docker-logs-app
```

## Troubleshooting Quick Fixes

### Service ne démarre pas
```bash
docker-compose down -v
docker-compose up -d
make status
```

### MinIO buckets manquants
```bash
docker exec rag-minio-init sh /scripts/init-minio.sh
make minio-buckets
```

### Qdrant collection inexistante
```bash
curl -X PUT http://localhost:6333/collections/conversations \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 1536, "distance": "Cosine"}}'
```

### Redis streams non initialisés
```bash
docker exec -it rag-redis redis-cli XGROUP CREATE ingestion:events rag-processors $ MKSTREAM
```

## Sécurité

### ⚠️ Avant de déployer en production

- [ ] Changer tous les mots de passe dans `.env`
- [ ] Générer nouvelles `SECRET_KEY` et `JWT_SECRET_KEY`
- [ ] Activer TLS/SSL sur tous les services
- [ ] Configurer CORS restrictif
- [ ] Mettre en place Secret Manager (Vault, AWS Secrets Manager)
- [ ] Activer audit logging
- [ ] Configurer backups automatiques
- [ ] Tester disaster recovery

## Ressources Additionnelles

- [ADR 003 - Contrat Audio → Transcript → RAG](../adr/ADR-2025-10-03-003-cross-cutting-audio-rag.md)
- [API OpenAPI Specification](../api/transcript-api.openapi.yaml)
- [MinIO Drop Playbook](../guides/operations/minio-drop-playbook.md)
- [Action Plan](../action-plan/README.md)

## Support & Contact

Pour toute question ou problème:
1. Consulter [Setup Guide](./setup-guide.md)
2. Vérifier les logs: `make docker-logs`
3. Consulter les ADRs dans `docs/adr/`
