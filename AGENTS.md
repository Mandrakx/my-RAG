# Repository Guidelines

## Project Structure & Module Organization
The backend lives in `src/` with domain-oriented folders: `api/` for FastAPI routers, `chatbot/` for dialogue flows, `rag/` for retrieval chains, and shared helpers in `models/`, `config/`, and `utils/`. Application entrypoint is `src/main.py`, while documentation sits under `docs/` (design, ADR, API specs). Tests mirror runtime code inside `tests/unit`, `tests/integration`, and `tests/e2e`. Ops assets stay in `infrastructure/` and `monitoring/`; sample mobile clients belong to `mobile/ios/`. Raw and derived corpora should remain in `data/`.

## Build, Test, and Development Commands
Prefer Make targets: `make install` installs base dependencies, `make dev` starts a reloadable API server, and `make run` executes `src/main.py` for quick smoke tests. Use `make docker-build` and `make docker-up` to reproduce the multi-service stack, and `make db-migrate` / `make db-rollback` to manage Alembic migrations. `make docs` builds the MkDocs site; `make docs-serve` previews it locally.

## Coding Style & Naming Conventions
All Python code follows PEP 8 with 4-space indentation. Run `make format` (Black + isort) before committing and `make lint` (flake8, black --check, mypy) to enforce imports, style, and typing. Name modules and functions with `snake_case`, classes with `PascalCase`, constants and environment keys in `UPPER_SNAKE_CASE`. Keep FastAPI routers grouped by feature under `src/api/routes/` and prefer type-hinted request/response models.

## Testing Guidelines
Pytest is the standard harness. Co-locate fixtures in `tests/fixtures/` and name test files `test_<feature>.py`. `make test`, `make test-unit`, and `make test-integration` cover different scopes; `make test-coverage` should stay green for new code, and contributors are expected to add assertions for every bug fix or new endpoint path.

## Commit & Pull Request Guidelines
Write commit subjects in the imperative mood (e.g., `Add ingestion retry logging`) and keep them under ~72 characters. Reference tickets in the body when relevant and summarize notable design decisions or schema changes. Pull requests should describe the impact, list verification steps (lint/tests), and attach screenshots or API responses when altering user-facing flows or documentation. Request review from domain owners when touching `docs/adr` or shared schemas.

## Security & Configuration Tips
Never commit secrets: use `.env` copied from `config/environments/.env.example` and keep overrides in untracked files. Run `make security` (bandit + safety) regularly, especially before releases. Large knowledge-base artefacts belong in `data/indexes/`; scrub personal data from sample uploads. When enabling external access, ensure CORS origins are set via `CORS_ORIGINS` and that Redis/object-storage credentials are stored in the secret manager listed in `infrastructure/scripts/` docs.