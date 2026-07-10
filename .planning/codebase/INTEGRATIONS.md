---
# External Integrations
**Analysis Date:** 2026-07-10
## APIs & External Services
- **OpenAI** - LLM provider. SDK: `langchain-openai` (`ChatOpenAI` in `app/core/llm_service.py`). Auth env var: `OPENAI_API_KEY`; config vars: `OPENAI_MODEL` (default `gpt-4o-mini`), `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`, `OPENAI_TIMEOUT`
- **Langfuse** - LLM observability/tracing. SDK: `langfuse` v3.2.2 (`langfuse.langchain.CallbackHandler` in `app/core/langfuse_tracer.py`). Auth env vars: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (default `https://cloud.langfuse.com`). Tracing is optional (skips gracefully if keys missing)
## Data Storage
**Databases:** MongoDB (async) - connection env vars `MONGO_HOST`, `MONGO_PORT`, `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_DATABASE`, optional `MONGO_AUTH_SOURCE`; accessed via Beanie ODM (`app/core/database.py`). Stores projects, documents, chunks, evidences, evidence_ratings, risk_assessments, risk_dimensions, risk_types, project_scores, processing_state
**File Storage:** MinIO/S3-compatible object storage - env vars `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ROOT_USER`, `S3_ROOT_PASSWORD`; accessed via `boto3.client('s3')` (`app/core/s3_client.py`). Holds raw/processed PDF documents; source of input for doc-parser
**Caching:** None (no Redis/memcached). No caching layer; all reads/writes go directly to MongoDB
## Authentication & Identity
None - no user auth, API keys, or identity provider. The API (FastAPI) has open CORS (`allow_origins=["*"]`, `app/services/api/main.py`) and no authentication middleware. Security is limited to the `AI_CPX_PUBLIC_DOCUMENT_URLS` toggle that hides internal MinIO URLs
## Monitoring & Observability
**Error Tracking:** Langfuse (LLM call tracing only via `get_langchain_callbacks()` in `app/core/langfuse_tracer.py`); no general application error tracking (e.g., Sentry)
**Logs:** Standard `print()` statements with emoji prefixes (e.g., "🗄️ Database:", "🤖 LLM initialized:", "🔍 Langfuse tracing enabled") across `app/core/database.py`, `llm_service.py`, `langfuse_tracer.py`. No structured logging framework (no `logging` module usage for these)
## CI/CD & Deployment
**Hosting:** Docker - single canonical image `docker/Dockerfile.api` (Python 3.12.3 base) reused for api, doc-parser, risk-calculator, and db-init via command override (Kubernetes per Dockerfile comment); registry `ghcr.io/aircarbon/ai-cpx`
**CI Pipeline:** GitHub Actions `build-push.yml` - on push to `main` (or manual) builds `linux/amd64` image with Docker Buildx and pushes to GitHub Container Registry; no test/lint job in pipeline
## Environment Configuration
**Required env vars:** `MONGO_HOST`, `MONGO_PORT`, `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_DATABASE`, `S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ROOT_USER`, `S3_ROOT_PASSWORD`, `OPENAI_API_KEY`, `OPENAI_MODEL`
**Secrets location:** `.env` file (template `.env.example`); in container, `/app/.env` is preferred and loaded via `python-dotenv`. CI pushes images to GHCR using `secrets.GITHUB_TOKEN`
## Webhooks & Callbacks
**Incoming:** None (no webhook receivers; services poll via APScheduler `AsyncIOScheduler` + `IntervalTrigger` in `doc_parser.py` and `risk_calculator.py`)
**Outgoing:** None (no outbound webhooks/notifications; external calls are limited to OpenAI API and Langfuse reporting)
---
