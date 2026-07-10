# Technology Stack
**Analysis Date:** 2026-07-10
## Languages (Primary/Secondary)
- **Primary language:** Python, with project metadata requiring `>=3.12,<3.14` in `pyproject.toml`; local tool files pin Python `3.12` in `.python-version` and `3.12.13` in `.mise.toml`.
- **Configuration/data languages:** TOML in `pyproject.toml` and `.mise.toml`, Docker Compose YAML in `docker/docker-compose.yml`, GitHub Actions YAML in `.github/workflows/build-push.yml`, JSON seed/configuration files in `config/database/risk_types.json` and `config/database/risk_dimensions.json`, and dotenv variables in `.env.example`.
- **Application layout:** Python package under `app/` split into `app/core/`, `app/repositories/`, and three service packages: `app/services/api/`, `app/services/doc_parser/`, and `app/services/risk_calculator/`.

## Runtime (Environment, Package Manager, Lockfile)
- **Runtime:** Python 3.12; container images use `python:3.12.3-slim` in both `docker/Dockerfile.api` and `docker/Dockerfile.test-setup`.
- **Package manager:** `uv`; `pyproject.toml` has `[tool.uv] package = false`, `justfile` runs `uv sync`, and Dockerfiles copy `/uv` and `/uvx` from `ghcr.io/astral-sh/uv:latest`.
- **Lockfile:** `uv.lock` is present and records lock metadata `requires-python = ">=3.12, <3.14"` with 168 packages, including transitive packages such as `openai`, `httpx`, `starlette`, `opentelemetry-*`, and `tiktoken`.
- **Service processes:** API defaults to `uvicorn app.services.api.main:app --host 0.0.0.0 --port 8001` in `docker/Dockerfile.api`; worker commands are `python -m app.services.doc_parser.doc_parser` and `python -m app.services.risk_calculator.risk_calculator` in `docker/docker-compose.yml` and `justfile`.
- **Environment loading:** Runtime configuration is loaded via `python-dotenv`; `app/core/database.py` prefers `/app/.env` when mounted in containers, while other modules call `load_dotenv()`.

## Frameworks (Core, Testing, Build/Dev)
- **API framework:** FastAPI in `app/services/api/main.py`, with routers from `app/services/api/routers/config.py` and `app/services/api/routers/risk.py`, OpenAPI metadata, CORS middleware, and `/health` readiness/liveness endpoint.
- **ASGI server:** Uvicorn (`uvicorn==0.20.0`) configured in `docker/Dockerfile.api`, `justfile`, and `pyproject.toml`.
- **Database ODM:** Beanie (`beanie==2.0.0`) over MongoDB/PyMongo; `app/core/database.py` initializes Beanie models and `app/core/models.py` defines `Document` classes and collection names.
- **LLM framework:** LangChain (`langchain==0.3.0`, `langchain-core==0.3.0`, `langchain-openai==0.2.0`) wraps OpenAI chat models in `app/core/llm_service.py`.
- **Scheduling:** APScheduler (`apscheduler>=3.10.0`) drives recurring workers: document parser every 10 minutes in `app/services/doc_parser/doc_parser.py` and risk calculator every 24 hours in `app/services/risk_calculator/risk_calculator.py`.
- **PDF parsing:** PyPDF (`pypdf==5.9.0`) extracts text and metadata from S3/MinIO PDFs in `app/services/doc_parser/pdf_parser.py`.
- **Validation/schemas:** Pydantic (`pydantic>=2.7.0,<2.9.0`) is used by Beanie models and API schemas under `app/services/api/schemas/`.
- **Testing/data setup:** There is no conventional test runner configured in `pyproject.toml`; test support is fixture-driven through `scripts/test/test_setup.py`, `scripts/test/test_data_loader.py`, `docker/Dockerfile.test-setup`, and JSON fixtures in `scripts/test/data/`. Dev tools include `jupyter` and `ruff` in `pyproject.toml`.
- **Lint/format:** Ruff is configured in `pyproject.toml` with target `py312`, line length `120`, selected rule families `E`, `F`, `I`, `N`, `W`, `UP`, `S`, and double-quote formatting; `justfile` exposes `lint` and `prek` recipes.
- **Build/deploy tooling:** Docker Buildx is used by `justfile` (`build`, `build-check`, `push`) and `.github/workflows/build-push.yml` to publish `ghcr.io/aircarbon/ai-cpx` images for `linux/amd64`.

## Key Dependencies (Critical, Infrastructure)
- **Critical app dependencies:** `fastapi`, `uvicorn`, `pydantic`, `beanie`, `pymongo`, `boto3`, `pypdf`, `langchain`, `langchain-openai`, `langchain-core`, `langchain-community`, `langfuse`, `apscheduler`, `python-dotenv`, and `requests` are declared in `pyproject.toml`.
- **Infrastructure clients:** MongoDB uses `pymongo.AsyncMongoClient` in `app/core/database.py`; S3-compatible object storage uses `boto3.client("s3")` in `app/core/s3_client.py`; Langfuse tracing uses `langfuse.langchain.CallbackHandler` in `app/core/langfuse_tracer.py`.
- **Transitive runtime dependencies:** `uv.lock` includes `openai`, `httpx`, `starlette`, `anyio`, `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp*`, `tiktoken`, `orjson`, and `sqlalchemy` through the LangChain/Langfuse stack.
- **Repository pattern:** Data access is centralized in `app/repositories/`; direct Beanie/Mongo model access appears in core initialization and repository classes, matching the project guidance in `CLAUDE.md`.
- **Domain configuration:** Risk scoring is configuration-driven from `config/database/risk_types.json` and `config/database/risk_dimensions.json`, loaded by `app/core/data_loader.py` and `scripts/init_db.py`.

## Configuration (Environment, Build)
- **Environment file:** `.env.example` documents S3/MinIO (`S3_PUBLIC_ENDPOINT`, `S3_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ROOT_USER`, `S3_ROOT_PASSWORD`, ports), MongoDB (`MONGO_HOST`, `MONGO_PORT`, `MONGO_DATABASE`, root credentials, optional `MONGO_AUTH_SOURCE`), Langfuse (`LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_HOST`), OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`, `OPENAI_TIMEOUT`), security (`AI_CPX_PUBLIC_DOCUMENT_URLS`), and DEV limits.
- **MongoDB configuration:** `app/core/database.py` builds a Mongo URI from environment variables and selects `MONGO_DATABASE`, defaulting to `ai_cpx` in code while `.env.example` uses `aicpx`.
- **S3 configuration:** `app/core/s3_client.py` reads endpoint, public endpoint, access key, secret key, and bucket; it generates public-style document URLs from `S3_PUBLIC_ENDPOINT` and bucket/key components.
- **LLM configuration:** `app/core/llm_service.py` requires `OPENAI_API_KEY` and reads `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`, and `OPENAI_TIMEOUT`; `.env.example` defaults to `gpt-4.1-mini` and notes GPT-5 temperature constraints.
- **Mode controls:** `APP_MODE=DEV` enables processing limits in `app/services/risk_calculator/chunk_processor.py`, `app/services/risk_calculator/risk_analyzer.py`, `app/services/risk_calculator/risk_assessment_summary_processor.py`, and `app/services/risk_calculator/project_summary_processor.py` using `DEV_MAX_*` and `DEV_SKIP_*` variables from `.env.example`.
- **Build configuration:** `docker/Dockerfile.api` installs locked production dependencies with `uv sync --frozen --no-dev --no-editable`; `docker/Dockerfile.test-setup` installs dev dependencies with `uv sync --frozen --no-editable` and copies `.env.test` to `/app/.env`.
- **Compose configuration:** `docker/docker-compose.yml` runs `api`, `docparser`, and `risk-calculator` from the same image on an `internal` bridge network, with `.env` mounted as `env_file`; MongoDB and MinIO are intentionally external to this compose file per `README.md`.

## Platform Requirements (Development, Production)
- **Development tools:** Python 3.12, `uv`, Docker, Docker Compose/Buildx, `just`, and optionally `mise`; `README.md` also references Docker-managed local MongoDB, MinIO, and MinIO `mc` for bucket policy setup.
- **Development services:** Local MongoDB container (`mongo:noble`) on `internal` network and local MinIO (`quay.io/minio/minio`) are documented in `README.md`; app services run through `just api`, `just docparser`, `just risk-calc`, or Docker commands.
- **Production services:** Requires a MongoDB-compatible database (MongoDB Atlas or self-hosted), S3-compatible storage (AWS S3, Google Cloud Storage with S3 compatibility, MinIO, or similar), OpenAI API access, and optionally Langfuse Cloud or self-hosted Langfuse as documented in `README.md` and `.env.example`.
- **Container platform:** Canonical image targets `linux/amd64` in `justfile` and `.github/workflows/build-push.yml`; `docker/Dockerfile.api` is a single reusable image for API, document parser, risk calculator, and DB init commands.
- **Network/ports:** API listens on container port `8001`; local MongoDB examples expose `27017`; MinIO API/console examples use `.env.example` ports `9100`/`9101`.
- **Runtime data prerequisites:** Database initialization via `scripts/init_db.py` is required before full operation to create collections and seed risk dimensions/types from `config/database/`; document parsing expects PDF objects arranged under first-level project folders in the S3 bucket.
