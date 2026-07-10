# External Integrations
**Analysis Date:** 2026-07-10
## APIs & External Services
- **OpenAI API:** `app/core/llm_service.py` uses `langchain_openai.ChatOpenAI` for evidence extraction, risk summaries, and project summaries. It requires `OPENAI_API_KEY` and reads `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`, and `OPENAI_TIMEOUT` from `.env.example`.
- **LLM workflows:** `app/services/risk_calculator/risk_analyzer.py` sends document chunks plus risk type/dimension prompts to the LLM and expects strict JSON; `app/services/risk_calculator/risk_assessment_summary_processor.py` and `app/services/risk_calculator/project_summary_processor.py` call the same LLM service for narrative summaries.
- **S3-compatible object APIs:** `app/core/s3_client.py` uses `boto3` to list objects, check existence, and download PDFs from `S3_BUCKET_NAME` via `S3_ENDPOINT`. `README.md` documents using AWS S3, Google Cloud Storage/S3-compatible storage, or MinIO.
- **Public document URLs:** `app/core/s3_client.py` constructs document URLs with `S3_PUBLIC_ENDPOINT`; `app/services/api/routers/risk.py` only returns those URLs when `AI_CPX_PUBLIC_DOCUMENT_URLS=true`.
- **No other outbound business APIs found:** Searches of `app/`, `scripts/`, `config/`, `docker/`, `.github/`, `README.md`, and `.env.example` found no Stripe, email, payment, mapping, OAuth, webhook, or custom third-party business API integrations beyond OpenAI, Langfuse, MongoDB, and S3-compatible storage.

## Data Storage (Databases, File Storage, Caching)
- **MongoDB primary database:** `app/core/database.py` connects with `pymongo.AsyncMongoClient`, pings admin, and initializes Beanie against `MONGO_DATABASE`. Environment variables are `MONGO_HOST`, `MONGO_PORT`, `MONGO_DATABASE`, `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, and optional `MONGO_AUTH_SOURCE` from `.env.example`.
- **MongoDB collections:** `app/core/models.py` defines Beanie collections `projects`, `documents`, `chunks`, `risk_types`, `risk_dimensions`, `evidence_ratings`, `evidences`, `risk_assessments`, `project_scores`, and `processing_state`.
- **MongoDB initialization:** `scripts/init_db.py` initializes all Beanie models, reports collection status, and calls `app/core/data_loader.py` to seed risk dimensions/types from `config/database/risk_dimensions.json` and `config/database/risk_types.json`.
- **S3/MinIO file storage:** `app/services/doc_parser/doc_parser.py` lists first-level S3 folders as projects, processes PDF objects, and stores source metadata/content in MongoDB. `app/services/doc_parser/pdf_parser.py` downloads each PDF into memory using `download_file_to_buffer()` and parses text/metadata using PyPDF.
- **Local object storage:** `README.md` documents MinIO (`quay.io/minio/minio`) on Docker network `internal`, with API/console ports from `.env.example` and `mc anonymous set download` to make files publicly downloadable.
- **Caching:** No Redis, Memcached, or application cache integration was found. In-process reuse is limited to module globals such as the Mongo client in `app/core/database.py` and singleton LLM service in `app/core/llm_service.py`.
- **Test data storage:** `docker/Dockerfile.test-setup`, `scripts/test/test_setup.py`, and `scripts/test/test_data_loader.py` populate MongoDB from JSON fixtures in `scripts/test/data/`; test MongoDB examples use container `mongodb-test` and port `27018` in `README.md` and `CLAUDE.md`.

## Authentication & Identity
- **API authentication:** None found. `app/services/api/main.py` creates a public FastAPI app with no auth dependencies, no API key middleware, no OAuth/OIDC provider, and permissive CORS (`allow_origins=["*"]`, `allow_credentials=True`, all methods/headers).
- **Database authentication:** MongoDB username/password authentication is configured through `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, and optional `MONGO_AUTH_SOURCE` in `.env.example` and `app/core/database.py`.
- **S3 authentication:** S3-compatible credentials use `S3_ROOT_USER` and `S3_ROOT_PASSWORD` as AWS access key/secret for `boto3.client("s3")` in `app/core/s3_client.py`.
- **OpenAI authentication:** `OPENAI_API_KEY` is mandatory in `app/core/llm_service.py`; missing key raises an initialization error.
- **Langfuse authentication:** `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` enable tracing in `app/core/langfuse_tracer.py`; missing keys disable tracing with a warning.
- **CI registry authentication:** `.github/workflows/build-push.yml` logs into GitHub Container Registry using `${{ github.actor }}` and `${{ secrets.GITHUB_TOKEN }}`.

## Monitoring & Observability
- **Langfuse:** `app/core/langfuse_tracer.py` optionally creates `langfuse.langchain.CallbackHandler` when Langfuse keys exist; `app/core/llm_service.py` passes these callbacks to LangChain `ainvoke()` calls for LLM tracing.
- **Langfuse host:** `.env.example` sets `LANGFUSE_HOST=https://cloud.langfuse.com`; `README.md` notes Langfuse Cloud and self-hosted Langfuse as options and says the app continues without Langfuse.
- **Health checks:** `app/services/api/main.py` exposes `/health`, returning HTTP 503 if `get_database_status()` reports a disconnected database and healthy JSON when MongoDB is connected.
- **Logging:** Services use stdout `print()` statements for status, progress, and errors across `app/services/doc_parser/`, `app/services/risk_calculator/`, and `app/core/database.py`; no structured logging service was found.
- **OpenTelemetry:** `uv.lock` includes `opentelemetry-*` packages transitively, likely from Langfuse, but there is no direct OpenTelemetry setup in application code.
- **Metrics/APM:** No Prometheus endpoints, Sentry, Datadog, New Relic, or custom metrics integrations were found.

## CI/CD & Deployment
- **GitHub Actions:** `.github/workflows/build-push.yml` builds and pushes the Docker image to GitHub Container Registry (`ghcr.io/aircarbon/ai-cpx`) on pushes to `main` and manual `workflow_dispatch`.
- **Image build:** The workflow uses `actions/checkout@v4`, `docker/setup-buildx-action@v3`, `docker/login-action@v3`, and `docker/build-push-action@v6`, with GHA cache and `linux/amd64` platform.
- **Image tags:** `.github/workflows/build-push.yml` creates `sha-<shortsha>` tags and pushes `latest` on `main` or when `workflow_dispatch` input `push_latest=true`.
- **Local build/push:** `justfile` provides `build`, `build-check`, and `push` recipes using `docker buildx build` with `docker/Dockerfile.api` and tags under `ghcr.io/aircarbon/ai-cpx`.
- **Deployment topology:** `docker/docker-compose.yml` defines three app services (`api`, `docparser`, `risk-calculator`) from the same Dockerfile and `.env`, all attached to `internal`. `README.md` states MongoDB and MinIO are intentionally kept outside compose for deployment flexibility.
- **Kubernetes readiness:** `docker/Dockerfile.api` comments mention the image is reused by all components with overridden commands in Kubernetes, and `app/services/api/main.py` documents `/health` as a Kubernetes liveness/readiness probe endpoint.

## Environment Configuration
- **S3/MinIO variables:** `.env.example` includes `S3_PUBLIC_ENDPOINT`, `S3_ENDPOINT`, `S3_BUCKET_NAME`, `S3_ROOT_USER`, `S3_ROOT_PASSWORD`, `S3_API_PORT`, and `S3_CONSOLE_PORT`; consumed mainly by `app/core/s3_client.py` and local setup commands in `README.md`.
- **MongoDB variables:** `.env.example` includes `MONGO_HOST`, `MONGO_PORT`, `MONGO_DATABASE`, `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, and optional `MONGO_AUTH_SOURCE`; consumed by `app/core/database.py`.
- **Langfuse variables:** `.env.example` includes `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_HOST`; consumed by `app/core/langfuse_tracer.py`.
- **OpenAI variables:** `.env.example` includes `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`, and `OPENAI_TIMEOUT`; consumed by `app/core/llm_service.py`.
- **API/security variables:** `.env.example` includes `AI_CPX_PUBLIC_DOCUMENT_URLS`, used by `app/services/api/routers/risk.py` to hide or expose document URLs.
- **Risk/config variables:** `.env.example` includes `RISK_TYPES_VERSION=1.0.0`; this value was documented but no code reference was found in the searched files.
- **Development limits:** `.env.example` includes `APP_MODE`, `DEV_MAX_PROJECTS`, `DEV_MAX_DOCUMENTS_PER_PROJECT`, `DEV_MAX_CHUNKS_PER_PROJECT`, `DEV_MAX_RISK_TYPES`, `DEV_SKIP_PROJECT_SUMMARIES`, and `DEV_SKIP_RISK_ASSESSMENT_SUMMARIES`; consumed by risk calculator modules under `app/services/risk_calculator/`.
- **Container environment:** `docker/docker-compose.yml` supplies `../.env` via `env_file`; `docker/Dockerfile.test-setup` copies `.env.test` to `/app/.env`; `app/core/database.py` explicitly detects `/app/.env` before falling back to default dotenv loading.

## Webhooks & Callbacks
- **Incoming webhooks:** None found. FastAPI routers in `app/services/api/routers/` expose read-oriented GET endpoints such as `/health`, `/config/risk-types`, `/config/dimension-specs`, `/methodology`, `/projects`, `/projects/{project_id}`, and `/risk-assessments/{risk_assessment_id}/top-evidences`; no webhook receiver routes were present.
- **Outgoing webhooks:** None found in `app/`, `scripts/`, `config/`, `docker/`, `.github/`, `README.md`, or `.env.example`.
- **LLM callbacks:** The only callback-style integration is Langfuse's LangChain callback handler in `app/core/langfuse_tracer.py`, passed to OpenAI model calls in `app/core/llm_service.py`; this is observability, not a business webhook.
- **Schedulers:** Background polling/processing is internal rather than webhook-driven: document parsing runs every 10 minutes in `app/services/doc_parser/doc_parser.py`, and risk calculation schedules every 24 hours in `app/services/risk_calculator/risk_calculator.py` after its immediate run.
