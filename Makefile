# Variables
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
APP_NAME := rag-app
PORT := 8000

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help
help: ## Show this help message
	@echo "$(GREEN)RAG Application - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Development
.PHONY: install
install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements-dev.txt

.PHONY: run
run: ## Run the application locally
	@echo "$(GREEN)Starting application on port $(PORT)...$(NC)"
	$(PYTHON) src/main.py

.PHONY: dev
dev: ## Run in development mode with hot reload
	@echo "$(GREEN)Starting development server...$(NC)"
	uvicorn src.main:app --reload --host 0.0.0.0 --port $(PORT)

# Docker
.PHONY: docker-build
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(APP_NAME) .

.PHONY: docker-run
docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run -p $(PORT):$(PORT) --env-file .env $(APP_NAME)

.PHONY: docker-up
docker-up: ## Start all services with docker-compose
	@echo "$(GREEN)Starting all services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Waiting for services to be ready...$(NC)"
	@sleep 5
	@$(MAKE) status

.PHONY: docker-down
docker-down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	$(DOCKER_COMPOSE) down

.PHONY: docker-restart
docker-restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(NC)"
	$(DOCKER_COMPOSE) restart

.PHONY: docker-logs
docker-logs: ## Show logs from all services
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-logs-app
docker-logs-app: ## Show logs from main app only
	$(DOCKER_COMPOSE) logs -f app

.PHONY: docker-clean
docker-clean: ## Clean Docker resources
	@echo "$(RED)Cleaning Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

.PHONY: docker-rebuild
docker-rebuild: ## Rebuild and restart all services
	@echo "$(GREEN)Rebuilding all services...$(NC)"
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d

.PHONY: status
status: ## Show status of all services
	@echo "$(GREEN)Service Status:$(NC)"
	@echo ""
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "$(GREEN)Quick Access URLs:$(NC)"
	@echo "  Application API:    http://localhost:8000"
	@echo "  MinIO Console:      http://localhost:9001"
	@echo "  Qdrant Dashboard:   http://localhost:6333/dashboard"
	@echo "  Grafana:            http://localhost:3000"
	@echo "  Prometheus:         http://localhost:9090"

# MinIO Operations
.PHONY: minio-init
minio-init: ## Initialize MinIO buckets and policies
	@echo "$(GREEN)Initializing MinIO...$(NC)"
	docker exec rag-minio-init sh /scripts/init-minio.sh

.PHONY: minio-console
minio-console: ## Open MinIO console in browser
	@echo "$(GREEN)Opening MinIO console...$(NC)"
	@echo "URL: http://localhost:9001"
	@echo "Credentials: minioadmin / minioadmin"

.PHONY: minio-buckets
minio-buckets: ## List MinIO buckets
	@docker exec rag-minio mc ls myminio

.PHONY: minio-upload-test
minio-upload-test: ## Upload a test file to ingestion bucket
	@echo "$(GREEN)Uploading test file to ingestion bucket...$(NC)"
	@echo "Test file content" > /tmp/test-upload.txt
	@docker exec -i rag-minio mc cp - myminio/ingestion/test-upload.txt < /tmp/test-upload.txt
	@rm /tmp/test-upload.txt
	@echo "$(GREEN)Test file uploaded successfully$(NC)"

.PHONY: minio-logs
minio-logs: ## Show MinIO logs
	$(DOCKER_COMPOSE) logs -f minio

# Qdrant Operations
.PHONY: qdrant-dashboard
qdrant-dashboard: ## Open Qdrant dashboard in browser
	@echo "$(GREEN)Opening Qdrant dashboard...$(NC)"
	@echo "URL: http://localhost:6333/dashboard"

.PHONY: qdrant-collections
qdrant-collections: ## List Qdrant collections
	@curl -s http://localhost:6333/collections | python -m json.tool

.PHONY: qdrant-health
qdrant-health: ## Check Qdrant health
	@curl -s http://localhost:6333/healthz && echo " $(GREEN)✓ Qdrant is healthy$(NC)" || echo " $(RED)✗ Qdrant is down$(NC)"

.PHONY: qdrant-logs
qdrant-logs: ## Show Qdrant logs
	$(DOCKER_COMPOSE) logs -f qdrant

# Redis Operations
.PHONY: redis-cli
redis-cli: ## Open Redis CLI
	@docker exec -it rag-redis redis-cli

.PHONY: redis-monitor
redis-monitor: ## Monitor Redis commands in real-time
	@docker exec -it rag-redis redis-cli MONITOR

.PHONY: redis-streams
redis-streams: ## Show Redis streams info
	@echo "$(GREEN)Redis Streams Information:$(NC)"
	@docker exec -it rag-redis redis-cli XINFO STREAMS ingestion:events 2>/dev/null || echo "No streams found"

.PHONY: redis-logs
redis-logs: ## Show Redis logs
	$(DOCKER_COMPOSE) logs -f redis

# Database
.PHONY: db-migrate
db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	alembic upgrade head

.PHONY: db-rollback
db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	alembic downgrade -1

.PHONY: db-reset
db-reset: ## Reset database
	@echo "$(RED)Resetting database...$(NC)"
	alembic downgrade base
	alembic upgrade head

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	@docker exec -it rag-postgres psql -U raguser -d ragdb

.PHONY: db-backup
db-backup: ## Backup PostgreSQL database
	@echo "$(GREEN)Backing up database...$(NC)"
	@mkdir -p ./backups
	@docker exec rag-postgres pg_dump -U raguser ragdb > ./backups/ragdb_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup completed: ./backups/ragdb_$(shell date +%Y%m%d_%H%M%S).sql$(NC)"

# Testing
.PHONY: test
test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	pytest tests/

.PHONY: test-unit
test-unit: ## Run unit tests
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest tests/unit/

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest tests/integration/

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	@echo "$(GREEN)Running E2E tests...$(NC)"
	pytest tests/e2e/

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest --cov=src --cov-report=html --cov-report=term tests/

# Code quality
.PHONY: lint
lint: ## Run linting
	@echo "$(GREEN)Running linters...$(NC)"
	flake8 src/ tests/
	black --check src/ tests/
	mypy src/

.PHONY: format
format: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	black src/ tests/
	isort src/ tests/

.PHONY: security
security: ## Run security checks
	@echo "$(GREEN)Running security checks...$(NC)"
	bandit -r src/
	safety check

# Documentation
.PHONY: docs
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	cd docs && mkdocs build

.PHONY: docs-serve
docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation...$(NC)"
	cd docs && mkdocs serve

# Deployment
.PHONY: deploy-staging
deploy-staging: ## Deploy to staging
	@echo "$(GREEN)Deploying to staging...$(NC)"
	./infrastructure/scripts/deploy-staging.sh

.PHONY: deploy-production
deploy-production: ## Deploy to production
	@echo "$(RED)Deploying to production...$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	./infrastructure/scripts/deploy-production.sh

# Utilities
.PHONY: clean
clean: ## Clean temporary files
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

.PHONY: setup
setup: ## Initial project setup
	@echo "$(GREEN)Setting up project...$(NC)"
	cp config/environments/.env.example .env
	$(MAKE) install
	$(MAKE) docker-build
	@echo "$(GREEN)Setup complete! Edit .env file and run 'make docker-up' to start.$(NC)"

.PHONY: shell
shell: ## Open Python shell with app context
	@echo "$(GREEN)Opening Python shell...$(NC)"
	$(PYTHON) -i -c "from src.main import app; print('App loaded as: app')"

.PHONY: logs
logs: ## Tail application logs
	tail -f logs/app.log

.PHONY: monitoring
monitoring: ## Open monitoring dashboard
	@echo "$(GREEN)Opening monitoring dashboards...$(NC)"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"

.PHONY: backup
backup: ## Backup data and database
	@echo "$(GREEN)Creating backup...$(NC)"
	./infrastructure/scripts/backup.sh

# Default target
.DEFAULT_GOAL := help