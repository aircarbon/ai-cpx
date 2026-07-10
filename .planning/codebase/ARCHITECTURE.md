# Architecture
**Analysis Date:** 2026-07-10
## Pattern Overview
AI-CPX is a Python 3.12 microservice-style carbon project risk assessment platform. The codebase is organised around three independently runnable services under `app/services/`: a scheduled document parser, a scheduled risk calculator, and a FastAPI read API. Shared infrastructure lives under `app/core/`, persistence access is mediated by repositories in `app/repositories/`, and API-specific response contracts live in `app/services/api/schemas/`.

The dominant architectural pattern is a repository-backed processing pipeline over MongoDB/Beanie documents. Beanie `Document` models in `app/core/models.py` represent persisted collections, dataclass types in `app/core/types.py` represent internal business objects, repositories convert between the two, and service processors orchestrate work by stage.

The platform is configuration-driven for risk taxonomy and scoring. `config/database/risk_types.json` defines 13 risk categories and weights, while `config/database/risk_dimensions.json` defines 6 scoring dimensions, scales, numeric mappings, directionality, and dimension weights. `scripts/init_db.py` and `app/core/data_loader.py` load these into MongoDB collections before risk processing.

Deployment uses one Docker image (`docker/Dockerfile.api`) with different commands for the three services. `docker/docker-compose.yml` starts `api`, `docparser`, and `risk-calculator`; MongoDB and S3/MinIO are external dependencies configured through environment variables.

## Layers (API, services, repositories, types, etc.)
- **Configuration and runtime layer**: `.env` / `/app/.env`, `.env.example`, `pyproject.toml`, `docker/docker-compose.yml`, and `docker/Dockerfile.api` define dependencies, ports, service commands, and environment-driven behaviour.
- **Core infrastructure layer** (`app/core/`):
  - `app/core/database.py` owns MongoDB connection construction, Beanie initialisation, lifecycle cleanup, and health/status reporting.
  - `app/core/models.py` defines Beanie persistence models and collection names: `projects`, `documents`, `chunks`, `risk_types`, `risk_dimensions`, `evidence_ratings`, `evidences`, `risk_assessments`, `project_scores`, and `processing_state`.
  - `app/core/types.py` defines dataclass business types plus LLM response types such as `LLMDimensionRating`, `LLMEvidence`, and `LLMRiskAnalysisResponse`.
  - `app/core/s3_client.py` wraps boto3 access for listing PDFs by project folder, downloading PDFs into memory, existence checks, and public document URL generation.
  - `app/core/llm_service.py` centralises OpenAI/LangChain access via `LLMService`, including risk and summary query helpers.
  - `app/core/langfuse_tracer.py` optionally attaches Langfuse callbacks to LangChain calls.
- **Repository layer** (`app/repositories/`): static async repository classes are the intended boundary around Beanie models. Examples include `ProjectRepository`, `SourceDocumentRepository`, `ChunkRepository`, `EvidenceRepository`, `RiskAssessmentRepository`, and `ProjectScoreRepository`.
- **Document parser service layer** (`app/services/doc_parser/`): `app/services/doc_parser/doc_parser.py` is a scheduled worker that discovers project folders/PDFs in S3, parses new PDFs through `app/services/doc_parser/pdf_parser.py`, and persists `Project` and `SourceDocument` records.
- **Risk calculator service layer** (`app/services/risk_calculator/`): processors implement pipeline phases for chunking, evidence extraction, risk assessment aggregation, risk summaries, project score calculation, and project summary generation.
- **API service layer** (`app/services/api/`): `app/services/api/main.py` constructs the FastAPI app and lifecycle; routers in `app/services/api/routers/` expose read endpoints; schemas in `app/services/api/schemas/risk_schemas.py` define response models separate from internal types.
- **Scripts/test data layer** (`scripts/`): `scripts/init_db.py` initialises schema/config data; `scripts/test/test_setup.py`, `scripts/test/test_data_loader.py`, and JSON files in `scripts/test/data/` seed staged test data.

## Data Flow (document pipeline: S3 → parser → chunks → evidence → scores → API)
1. **S3/MinIO input**: raw PDFs are stored in first-level folders in an S3-compatible bucket. `app/core/s3_client.py` uses `list_pdf_files_by_folder()` to group PDFs by folder, where each folder becomes a carbon project.
2. **Parser project discovery**: `app/services/doc_parser/doc_parser.py` runs `scheduled_task()` immediately and then every 10 minutes. It calls `process_project()` to `add_or_get_existing()` a `Project` based on folder name.
3. **PDF extraction**: for each new PDF, `process_documents_for_project()` calls `parse_pdf()` in `app/services/doc_parser/pdf_parser.py`. `parse_pdf()` downloads the PDF from S3 into memory with `download_file_to_buffer()`, extracts page text/metadata/page count using `pypdf.PdfReader`, and returns a success/error result.
4. **Document persistence**: parsed results are saved via `SourceDocumentRepository.add_or_get_existing()` as `SourceDocument` documents with fields for source path, title, extracted content, processing success, error, file size, page count, document URL, and metadata.
5. **Risk calculator scheduling**: `app/services/risk_calculator/risk_calculator.py` initialises all Beanie models, loads all projects via `ProjectRepository.get_all()`, loads risk types via `get_all_risk_types()`, and processes each project in six phases.
6. **Chunking**: `app/services/risk_calculator/chunk_processor.py` retrieves source documents, creates sliding-window text chunks using `CHUNK_SIZE = 10000`, `OVERLAP_SIZE = 500`, and `MIN_CHUNK_SIZE = 2000`, and persists `Chunk` records through `ChunkRepository.save_chunks_bulk()`.
7. **Evidence extraction**: `app/services/risk_calculator/risk_analyzer.py` analyses each chunk against each configured risk type. It builds a JSON-only prompt from the chunk, `RiskType`, and all `RiskDimensionSpec` objects, queries `LLMService`, retries up to `MAX_RETRIES = 3`, parses JSON into `LLMRiskAnalysisResponse`, creates `EvidenceRating` records per dimension, and creates `Evidence` records with weighted rating scores.
8. **Risk assessment calculation**: `app/services/risk_calculator/risk_assessment_processor.py` groups evidences by project and risk type through `EvidenceRepository.get_by_project_and_risk_type()`, averages evidence scores with `statistics.mean()`, and writes one `RiskAssessment` per project/risk type. Risk types with no evidence are represented with `score=None`.
9. **Risk assessment summaries**: `app/services/risk_calculator/risk_assessment_summary_processor.py` takes the top 10 evidences per risk assessment, asks the LLM for a 2-3 sentence summary, and stores it on `RiskAssessment.summary` via `RiskAssessmentRepository.update_summary()`.
10. **Project scoring**: `app/services/risk_calculator/project_score_processor.py` computes the project-level weighted average using risk type weights from MongoDB, ignoring `RiskAssessment` records whose score is `None`, and persists `ProjectScore` through `ProjectScoreRepository.update_or_create_project_score()`.
11. **Project summary**: `app/services/risk_calculator/project_summary_processor.py` synthesises risk assessment scores and summaries into a project-level LLM summary and updates `ProjectScore.summary`.
12. **API serving**: `app/services/api/routers/risk.py` serves `/projects`, `/projects/{project_id}`, `/risk-assessments/{risk_assessment_id}/top-evidences`, and `/methodology`. `app/services/api/routers/config.py` serves `/config/risk-types` and `/config/dimension-specs`.

## Key Abstractions (repository pattern, types, schemas)
- **Beanie document models**: `app/core/models.py` is the persistence schema source of truth. Each class declares collection names and indexes through nested `Settings`; linked relationships use Beanie `Link` and `PydanticObjectId`.
- **Internal dataclass types**: `app/core/types.py` mirrors persisted concepts as dataclasses such as `Project`, `SourceDocument`, `Chunk`, `RiskType`, `RiskDimensionSpec`, `EvidenceRating`, `Evidence`, `RiskAssessment`, `ProjectScore`, and `ProcessingState`. These types provide `from_model()` / `to_model()` conversion where needed and keep business logic away from raw database documents.
- **Repository classes**: files in `app/repositories/` expose static async methods for CRUD/query operations. Services generally call repositories rather than Beanie models directly. Notable examples: `ProjectRepository.add_or_get_existing()`, `SourceDocumentRepository.get_by_project()`, `EvidenceRepository.create_from_llm_evidence()`, `RiskAssessmentRepository.update_or_create_risk_assessment()`, and `ProcessingStateRepository.update_status()`.
- **Processing state abstraction**: `ProcessingState` in `app/core/models.py` and `ProcessingStateRepository` track stage status, optional document/chunk/risk references, timestamps, errors, retry count, results, and processing version. It enables idempotent/resumable chunking, evidence extraction, risk assessment, summary, and scoring stages.
- **LLM response abstractions**: `LLMDimensionRating`, `LLMEvidence`, and `LLMRiskAnalysisResponse` in `app/core/types.py` structure JSON returned by the LLM before persistence.
- **API schema separation**: `app/services/api/schemas/risk_schemas.py` defines Pydantic response models (`ProjectSummary`, `TopEvidence`, `RiskBreakdownItem`, `ProjectRiskBreakdown`) rather than returning database models directly.
- **Configuration records**: risk taxonomy is not hardcoded in processors. `RiskTypeRepository` and `RiskDimensionRepository` read seeded config records from MongoDB, which are originally sourced from `config/database/risk_types.json` and `config/database/risk_dimensions.json`.

## Entry Points (API, doc-parser, risk-calculator)
- **API service**: `app/services/api/main.py` is started by uvicorn in `docker/Dockerfile.api` / `docker/docker-compose.yml`. It initialises Beanie models in FastAPI lifespan and exposes `/health`, `/methodology`, `/projects`, `/projects/{project_id}`, `/risk-assessments/{risk_assessment_id}/top-evidences`, `/config/risk-types`, and `/config/dimension-specs`.
- **Document parser worker**: `python -m app.services.doc_parser.doc_parser` enters `main()` in `app/services/doc_parser/doc_parser.py`. It initialises `Project` and `SourceDocument` models, runs `scheduled_task()` once, then repeats on an APScheduler interval every 10 minutes.
- **Risk calculator worker**: `python -m app.services.risk_calculator.risk_calculator` enters `main()` in `app/services/risk_calculator/risk_calculator.py`. It initialises all processing models, runs `scheduled_task()`, processes projects through six phases, then currently calls `sys.exit(0)` after one successful run with a `TEMPORARY` log message before scheduler continuation.
- **Database initialisation script**: `python scripts/init_db.py` initialises all models and loads risk config data; `python scripts/init_db.py status` reports database collections and config counts.
- **Docker composition**: `docker/docker-compose.yml` defines `api`, `docparser`, and `risk-calculator` services on the `internal` network; MongoDB/S3 are expected to be available separately.

## Error Handling
- Database connection errors in `app/core/database.py` are printed and re-raised during initial connection; health/status methods return dictionaries with `connected=False` and error text when possible.
- S3 helper failures in `app/core/s3_client.py` generally print errors and return safe sentinel values (`None`, `{}`, or `False`).
- PDF parsing in `app/services/doc_parser/pdf_parser.py` captures exceptions and returns a structured result with `success=False` and `error` instead of raising.
- Document parsing service-level failures are caught in `scheduled_task()` in `app/services/doc_parser/doc_parser.py`, logged, and do not crash the scheduler loop.
- Risk calculator stage processors catch exceptions per document/chunk/risk/project stage, update `ProcessingState` to `failed` with `error_message`, log the error, and continue where feasible.
- LLM analysis in `app/services/risk_calculator/risk_analyzer.py` has explicit retry logic for query failures and JSON parsing failures (`MAX_RETRIES = 3`, `RETRY_DELAY = 1`). Bad dimension keys or scale values are skipped with warnings.
- API endpoints in `app/services/api/routers/risk.py` use `HTTPException(status_code=404)` for missing projects, missing project scores, or missing risk assessments.
- Many repositories catch broad exceptions and return empty lists or `None`, especially around Beanie `Link` queries; this makes callers resilient but can hide data/query issues.

## Cross-Cutting Concerns
- **Environment configuration**: `.env` controls MongoDB (`MONGO_HOST`, `MONGO_PORT`, `MONGO_DATABASE`, auth), S3/MinIO (`S3_ENDPOINT`, `S3_PUBLIC_ENDPOINT`, `S3_BUCKET_NAME`), OpenAI (`OPENAI_MODEL`, `OPENAI_API_KEY`, etc.), Langfuse, API URL visibility, and development processing limits.
- **Async execution**: database repositories, FastAPI endpoints, and service processors are async. APScheduler runs asynchronous scheduled tasks in the parser and calculator workers.
- **Idempotency and resumability**: `ProcessingStateRepository.is_completed()` gates repeated work for chunking, evidence extraction, risk assessments, risk summaries, project scoring, and project summaries.
- **LLM centralisation and observability**: all model calls should go through `app/core/llm_service.py`, which obtains optional callbacks from `app/core/langfuse_tracer.py`. Session IDs are used for risk analysis and summary calls.
- **Scoring semantics**: evidence score is a weighted average of dimension scores, adjusted for dimensions where higher values are less risky; risk assessment score is currently the mean of evidence scores; project score is a risk-type-weighted average of non-null risk assessments.
- **Development-mode throttles**: risk calculator processors read `APP_MODE=DEV` and limits such as `DEV_MAX_PROJECTS`, `DEV_MAX_DOCUMENTS_PER_PROJECT`, `DEV_MAX_CHUNKS_PER_PROJECT`, `DEV_MAX_RISK_TYPES`, `DEV_SKIP_RISK_ASSESSMENT_SUMMARIES`, and `DEV_SKIP_PROJECT_SUMMARIES`.
- **CORS and public document URLs**: `app/services/api/main.py` allows all CORS origins. `app/services/api/routers/risk.py` hides document URLs unless `AI_CPX_PUBLIC_DOCUMENT_URLS=true`.
- **Logging style**: services use direct `print()` logging with emoji/status prefixes rather than Python `logging`.
