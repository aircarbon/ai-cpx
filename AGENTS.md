# AI CPX — Carbon Project Risk Assessment

## Quick start (local dev)

```bash
uv sync --frozen            # install deps (uv, not pip)
just lint                   # ruff check + format (120 cols, double quotes)
```

## Service architecture

Single Docker image (`docker/Dockerfile.api`) reused by all services — different entrypoints:

| Service         | Entrypoint                                               |
| --------------- | -------------------------------------------------------- |
| API             | `uvicorn app.services.api.main:app --port 8001`          |
| Doc parser      | `python -m app.services.doc_parser.doc_parser`           |
| Risk calculator | `python -m app.services.risk_calculator.risk_calculator` |
| DB init         | `python scripts/init_db.py`                              |
| Test setup      | `python scripts/test/test_setup.py <stage>`              |

All apps + test containers use the same Dockerfile. `.env` is mounted at `/app/.env` in containers.

## Local run commands

```bash
just api           # uv run uvicorn app.services.api.main:app --reload
just docparser     # uv run python -m app.services.doc_parser.doc_parser
just risk-calc     # uv run python -m app.services.risk_calculator.risk_calculator
just db-init       # uv run python scripts/init_db.py
just db-status     # uv run python scripts/init_db.py status
just build-check   # docker buildx build --check
```

## Project structure

```
app/
  core/                   # database, models, types, llm_service, s3_client, data_loader
  repositories/           # all DB access — repository pattern only
  services/
    api/                  # FastAPI (routers/, schemas/)
    doc_parser/           # PDF monitoring + parsing worker
    risk_calculator/      # chunking → evidence → assessment → scoring pipeline
config/database/          # risk_types.json (13 types) + risk_dimensions.json (6 dims)
scripts/
  init_db.py              # production DB init
  test/
    test_setup.py         # stage-based test data loading
    test_data_loader.py   # JSON fixture loader (MongoDB export format)
    data/                 # test fixtures: chunks.json, documents.json, etc.
```

## Key conventions

- **Repository pattern**: Never access Beanie models directly from services. Always use `app/repositories/*` classes.
- **Type separation**: `core/types.py` holds business-logic dataclasses with `from_model()`/`to_model()` converters. `core/models.py` holds Beanie `Document` classes.
- **LLM gateway**: All LLM calls through `app/core/llm_service.py` — never instantiate `ChatOpenAI` elsewhere.
- **API schemas**: Separate Pydantic models in `app/services/api/schemas/` — not shared with internal types.
- **Langfuse**: Optional — missing keys silently disable tracing (no crash).

## DEV mode limits

When `APP_MODE=DEV`, the risk calculator respects caps to control LLM costs:

- `DEV_MAX_PROJECTS` (default 999) — limited projects (sorted alphabetically)
- `DEV_MAX_DOCUMENTS_PER_PROJECT` (default 999) — limited docs
- `DEV_MAX_CHUNKS_PER_PROJECT` (default 999) — limited chunks
- `DEV_MAX_RISK_TYPES` (default 999) — risk types sorted by weight desc then name
- `DEV_SKIP_PROJECT_SUMMARIES` / `DEV_SKIP_RISK_ASSESSMENT_SUMMARIES` — skip expensive LLM summaries

## Testing (Docker-based, no pytest)

The test setup uses stage-based data loading. Each stage builds on the previous:

```
empty-db → init-db → init-projects → init-docs → init-chunks →
load-evidences → load-risk-assessments → load-project-scores → load-project-score-summaries
```

```bash
just test-setup <stage>   # builds and runs test-setup container
```

Test containers use `mongodb-test` (port 27018), `.env.test` credentials, and the `internal` network. They share the same SeaweedFS instance (read-only static files).

## Processing pipeline

Each project goes through 6 phases in the risk calculator:

1. Chunking (10K chars, 500 overlap, min 2K) → 2. LLM evidence extraction (batch 5 concurrent, max 3 retries) → 3. Risk assessment scoring → 4. Summary generation (LLM per assessment) → 5. Project total score → 6. Project summary (LLM)

The scheduler runs every 24h but exits after one pass (`sys.exit(0)`).

## CI

GitHub Actions runs: `just lint` → `just build-check` → build + push to `ghcr.io/aircarbon/ai-cpx` (tagged by commit SHA).

## Database

MongoDB via Beanie ODM. URI supports `MONGO_AUTH_SOURCE` for managed services (e.g. Atlas). Expected collections match model names: `projects`, `documents`, `chunks`, `risk_types`, `risk_dimensions`, `evidence_ratings`, `evidences`, `risk_assessments`, `project_scores`, `processing_state`.
