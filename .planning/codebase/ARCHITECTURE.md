---
# Architecture
**Analysis Date:** 2026-07-10
## Pattern Overview
**Overall:** Multi-service pipeline (process-based microservices) built on a shared `app.core` library, with a strict Repository pattern over a MongoDB (Beanie ODM) data layer and typed business logic separated from database models.
**Key Characteristics:**
- Three independent long-running services share the same `app` package: Document Parser (`app/services/doc_parser/doc_parser.py`), Risk Calculator (`app/services/risk_calculator/risk_calculator.py`), and API Service (`app/services/api/main.py`).
- All persistence goes through repository classes in `app/repositories/`; no service code touches Beanie models directly except via repositories.
- Dual type system: Beanie `Document` models in `app/core/models.py` (DB persistence) and `@dataclass` business types in `app/core/types.py` (logic), converted with `from_model()` / `to_model()`.
- API layer uses its own Pydantic schemas (`app/services/api/schemas/risk_schemas.py`), separate from both core types and DB models.
- LLM access is centralized in `app/core/llm_service.py` with Langfuse tracing via `app/core/langfuse_tracer.py`.
- Risk configuration (risk types, dimensions, scales, weights) is externalized to JSON in `config/database/` and loaded at init.
- Resumable / idempotent processing via a `ProcessingState` collection (`app/repositories/processing_state_repository.py`).

## Layers
**Core / Shared Infrastructure:** / Shared foundation used by all services / `app/core/` / Contains DB connection (`database.py`), Beanie models (`models.py`), business types (`types.py`), S3 client (`s3_client.py`), LLM service (`llm_service.py`), Langfuse tracer (`langfuse_tracer.py`), config loader (`data_loader.py`) / Depends on `app.core.models`, `app.core.types` / Used by all repositories, services, and scripts
**Repository Layer:** / Data access abstraction over MongoDB / `app/repositories/` / Contains one repository class per collection: `ProjectRepository`, `SourceDocumentRepository`, `ChunkRepository`, `RiskTypeRepository`, `RiskDimensionRepository`, `EvidenceRatingRepository`, `EvidenceRepository`, `RiskAssessmentRepository`, `ProjectScoreRepository`, `ProcessingStateRepository` / Depends on `app.core.models`, `app.core.types` / Used by services, routers, and scripts
**Service Layer:** / Domain / use-case orchestration / `app/services/` / Contains `doc_parser/` (PDF ingestion), `risk_calculator/` (chunking -> evidence -> assessment -> scoring), `api/` (FastAPI routers + schemas) / Depends on `app.repositories`, `app.core` / Used by entry points (Docker `CMD`, `scripts/`)
**Configuration:** / Risk taxonomy & scoring rules / `config/database/` / Contains `risk_types.json`, `risk_dimensions.json` / Depends on nothing (loaded by `app/core/data_loader.py`) / Consumed by DB init (`scripts/init_db.py`) and risk scoring logic
**Scripts / Entry Tooling:** / Bootstrap & test data / `scripts/` / Contains `init_db.py` (DB + config load), `test/test_setup.py`, `test/test_data_loader.py` / Depends on `app.core`, `app.repositories` / Used by Docker init and CI/test

## Data Flow
**Flow Name:** Document ingestion (Document Parser)
1. `doc_parser.py` polls S3/MinIO every `CHECKING_INTERVAL_MINUTES` (`doc_parser.py:23`) via `app/core/s3_client.py` `list_pdf_files_by_folder()`.
2. For each S3 folder, `ProjectRepository.add_or_get_existing()` upserts a `Project` (`doc_parser.py:28`).
3. For each PDF, `pdf_parser.py` `parse_pdf()` downloads to memory and extracts text with `pypdf` (`pdf_parser.py:12`).
4. `SourceDocumentRepository.add_or_get_existing()` stores the parsed `SourceDocument` (`doc_parser.py:85`).
**Flow Name:** Risk calculation (Risk Calculator) — six phases per project (`risk_calculator.py:75-107`)
1. Phase 1 Chunking: `chunk_processor.py` `process_project_chunks()` splits document text into overlapping chunks (`chunk_processor.py:15` sliding window) and saves via `ChunkRepository`.
2. Phase 2 Evidence extraction: `risk_analyzer.py` `process_project_risk_analysis()` runs LLM (`llm_service.py`) per chunk x risk type, parses JSON, and saves `EvidenceRating` + `Evidence` via repositories. Batched concurrency `BATCH_SIZE=5` (`risk_analyzer.py:21`).
3. Phase 3 Risk assessment: `risk_assessment_processor.py` aggregates evidences per risk type into `RiskAssessment` (mean of evidence scores, `risk_assessment_processor.py:25`).
4. Phase 4 Assessment summaries: `risk_assessment_summary_processor.py` generates LLM summaries.
5. Phase 5 Project score: `project_score_processor.py` computes weighted average of risk assessments -> `ProjectScore` (`project_score_processor.py:10`).
6. Phase 6 Project summary: `project_summary_processor.py` generates LLM project summary.
**Flow Name:** API read path
1. FastAPI route (e.g. `routers/risk.py`) calls repository `get_*` methods, assembles Pydantic schemas (`schemas/risk_schemas.py`), returns JSON.
**State Management:** MongoDB collections are the single source of truth. Resumability is tracked in the `ProcessingState` collection (`models.py:247`), keyed by `stage` + `project_id` (+- `document_id`/`chunk_id`/`risk_type_id`). Each processor calls `ProcessingStateRepository.is_completed()` to skip and `update_status()` to advance (`chunk_processor.py:74`, `risk_analyzer.py:320`, `risk_assessment_processor.py:39`, `project_score_processor.py:46`). Runtime global singletons `get_llm_service()` (`llm_service.py:126`) and DB client globals in `database.py` manage connections.

## Key Abstractions
**Abstraction Name:** Repository / **Purpose:** Encapsulate all MongoDB/Beanie access; only repositories import `models.py` / **Examples:** `app/repositories/project_repository.py`, `app/repositories/evidence_repository.py` / **Pattern:** Static-method classes (`class ProjectRepository:`) with `get_*`, `add_or_get_existing`, `is_completed`, `update_status`.
**Abstraction Name:** Database Model vs Business Type / **Purpose:** Separate persistence (Beanie `Document`) from logic (dataclass) / **Examples:** `app/core/models.py` (`Project`, `SourceDocument`, `Chunk`, `Evidence`, `RiskAssessment`, `ProjectScore`, `ProcessingState`, `RiskType`, `RiskDimensionSpec`, `EvidenceRating`) and `app/core/types.py` (parallel `@dataclass` types with `from_model()`/`to_model()`) / **Pattern:** Dual-representation with conversion methods.
**Abstraction Name:** LLMService / **Purpose:** Centralize LLM calls (LangChain `ChatOpenAI`) and tracing / **Examples:** `app/core/llm_service.py` (`LLMService`, `get_llm_service`) / **Pattern:** Singleton with lazy init and async `query()`.
**Abstraction Name:** ProcessingState / **Purpose:** Resumable, idempotent pipeline stages / **Examples:** `app/core/models.py:247`, `app/repositories/processing_state_repository.py` / **Pattern:** State-machine-style status records (`pending`/`in_progress`/`completed`/`failed`).
**Abstraction Name:** Config-driven scoring / **Purpose:** Risk taxonomy and scoring weights live in JSON, not code / **Examples:** `config/database/risk_types.json`, `config/database/risk_dimensions.json`, `app/core/data_loader.py` / **Pattern:** Externalized configuration loaded into DB at init.

## Entry Points
**Entry Point:** API Service / **Location:** `app/services/api/main.py` (FastAPI `app`), run via `uvicorn app.services.api.main:app` (`docker/Dockerfile.api:24`) / **Triggers:** HTTP requests / **Responsibilities:** Expose risk/project/config endpoints; init DB in `lifespan` (`main.py:20`).
**Entry Point:** Document Parser / **Location:** `app/services/doc_parser/doc_parser.py` `main()` (`doc_parser.py:156`) / **Triggers:** APScheduler interval (`doc_parser.py:170`) / **Responsibilities:** Poll S3, parse PDFs, upsert Projects/SourceDocuments.
**Entry Point:** Risk Calculator / **Location:** `app/services/risk_calculator/risk_calculator.py` `main()` (`risk_calculator.py:116`) / **Triggers:** APScheduler interval `CHECKING_INTERVAL_HOURS=24` (`risk_calculator.py:33`) / **Responsibilities:** Run the 6-phase risk pipeline.
**Entry Point:** DB Init / **Location:** `scripts/init_db.py` `init_database()` (`init_db.py:22`) / **Triggers:** `python -m scripts.init_db` / **Responsibilities:** Connect DB, load risk types/dimensions from config.
**Entry Point:** Test Setup / **Location:** `scripts/test/test_setup.py`, `scripts/test/test_data_loader.py` / **Triggers:** Docker `test-setup` container (`docker/Dockerfile.test-setup`) / **Responsibilities:** Populate DB to a named stage for tests.

## Error Handling
**Strategy:** Defensive / fail-soft at the pipeline level — individual failures are caught, recorded into `ProcessingState.error_message`, and the pipeline continues; LLM calls use bounded retry with backoff.
**Patterns:**
- Repositories swallow exceptions and return `None`/empty (e.g. `project_repository.py:15`, `project_repository.py:37`).
- LLM retry: `MAX_RETRIES=3`, `RETRY_DELAY=1` with JSON-cleaning and `asyncio.gather(..., return_exceptions=True)` in `risk_analyzer.py:240` and `risk_analyzer.py:400`.
- Pipeline phases wrap work in try/except and persist `status="failed"` + `error_message` via `ProcessingStateRepository.update_status` (e.g. `risk_analyzer.py:369`, `chunk_processor.py:131`, `risk_assessment_processor.py:98`).
- DB connection failures raise after logging in `database.py:43`.
- S3/PDF errors degrade gracefully (return success=False, store `error` on `SourceDocument`; `pdf_parser.py:53`).
- No global exception middleware in API; uses FastAPI `HTTPException` for 404s (`routers/risk.py:56`).

## Cross-Cutting Concerns
**Logging:** Print-based logging with emoji-prefixed status messages throughout (`doc_parser.py`, `risk_calculator.py`, `risk_analyzer.py`). No structured logging framework; no centralized logger.
**Validation:** Pydantic used in two places — DB models (`app/core/models.py`) and API response schemas (`app/services/api/schemas/risk_schemas.py`). LLM response validation is manual JSON parsing + scale/key checks (`risk_analyzer.py:167` validates `scale_value` against `dimension_spec.mapping`). DEV-mode limits via env vars (`APP_MODE`, `DEV_MAX_*`) gate token use (`risk_analyzer.py:31`, `chunk_processor.py:154`).
**Authentication:** None in application code. MongoDB auth via env credentials in `database.py:21`; OpenAI/Langfuse keys via env. API has CORS wide open (`main.py:65` `allow_origins=["*"]`) and no auth middleware.
**Observability:** Langfuse tracing is opt-in — `app/core/langfuse_tracer.py` returns `None` callbacks when keys are absent; callbacks injected into LLM calls in `llm_service.py:23`.
**Configuration:** Central `.env` loading via `python-dotenv` in every entry module; `/app/.env` mount point checked first in `database.py:9`.
