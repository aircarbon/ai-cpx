---
# Technology Stack
**Analysis Date:** 2026-07-10
## Languages
**Primary:** Python 3.12.3 - entire application (`app/`, `scripts/`), Docker base image `python:3.12.3` (`docker/Dockerfile.api`, `docker/Dockerfile.test-setup`), `requires-python = ">=3.12"` (`pyproject.toml`)
**Secondary:** None (no TypeScript/JS code; `jupyter` listed only as dev dependency for notebooks)
## Runtime
**Environment:** Python 3.12.3 (CPython), ASGI served by Uvicorn (`requirements.txt`: `uvicorn==0.20.0`); multi-service processes run via module entrypoints (`python -m app.services.doc_parser.doc_parser`, `python -m app.services.risk_calculator.risk_calculator`)
**Package Manager:** pip (installs from `requirements.txt`) / `uv` available via `uv.lock` (534KB lockfile present, though `pyproject.toml` is the declared project manifest) / Lockfile: present (`uv.lock`), plus pinned `requirements.txt`
## Frameworks
**Core:** FastAPI `0.109.1` (API service, `app/services/api/main.py`), Beanie ODM `2.0.0` + PyMongo `4.11.0` (MongoDB models, `app/core/database.py`, `app/core/models.py`), LangChain `0.3.0` / `langchain-core` / `langchain-community` / `langchain-openai 0.2.0` (LLM via `app/core/llm_service.py`), APScheduler `3.9.0` (AsyncIOScheduler interval polling in `doc_parser.py` and `risk_calculator.py`), Pydantic `>=2.7.0,<2.9.0` (schemas/types), boto3 `1.39.0` (S3/MinIO client, `app/core/s3_client.py`), pypdf `5.9.0` (PDF text extraction, `app/services/doc_parser/pdf_parser.py`)
**Testing:** No dedicated test framework (no pytest). Test data is seeded via a `test-setup` container running `scripts/test/test_setup.py` (`docker/Dockerfile.test-setup`); `jupyter` available for ad-hoc exploration
**Build/Dev:** Docker (single reusable image `docker/Dockerfile.api` reused for api/docparser/risk-calculator/db-init via CMD override; `docker/docker-compose.yml`), GitHub Actions (`build-push.yml`), Ruff `>=0.11.0` linter/formatter (`pyproject.toml` `[tool.ruff]`)
## Key Dependencies
**Critical:** langchain-openai + ChatOpenAI (`app/core/llm_service.py`) - drives all evidence extraction and summary generation; Beanie/PyMongo - persistence of projects, chunks, evidences, risk assessments, scores (`app/core/database.py`); boto3 - reads source PDFs from MinIO/S3; FastAPI - REST API for risk data; APScheduler - keeps doc-parser and risk-calculator polling S3/Mongo continuously
**Infrastructure:** MongoDB async client `pymongo.AsyncMongoClient` via Beanie (`app/core/database.py`); MinIO/S3 via `boto3.client('s3')` (`app/core/s3_client.py`); Langfuse `3.2.2` tracing via `langfuse.langchain.CallbackHandler` (`app/core/langfuse_tracer.py`)
## Configuration
**Environment:** `.env` loaded via `python-dotenv` (template `.env.example`); in Docker, `/app/.env` is mounted/checked first (`app/core/database.py`); CI uses `.env.test` (referenced in CLAUDE.md, not committed)
**Build:** `docker/Dockerfile.api` (canonical image), `docker/Dockerfile.test-setup`, `docker/docker-compose.yml`; `pyproject.toml` with Hatchling build backend and Ruff config
## Platform Requirements
**Development:** Python >=3.12, MongoDB, MinIO/S3 bucket, OpenAI API key, optional Langfuse keys; `.env` file (copy from `.env.example`); `pip install -r requirements.txt`
**Production:** Docker images pushed to `ghcr.io/aircarbon/ai-cpx` via GitHub Actions (`build-push.yml`), deployed to Kubernetes (per Dockerfile comment: "reused by all AI CPX components with overridden commands in Kubernetes")
---
