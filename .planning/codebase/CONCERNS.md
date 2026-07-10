# Codebase Concerns
**Analysis Date:** 2026-07-10
## Tech Debt
- No `TODO|FIXME|HACK|XXX|BUG` markers were found under `app/`, so known debt is not being tracked inline; operational debt instead appears as comments and behaviour such as the `TEMPORARY` one-shot exit in `app/services/risk_calculator/risk_calculator.py`.
- Large, multi-responsibility modules mix orchestration, prompting, parsing, persistence, retry logic, and logging: `app/services/risk_calculator/risk_analyzer.py` is 479 lines, `app/core/types.py` is 496 lines, and `app/core/models.py` is 277 lines. These files are likely to become merge-conflict and regression hotspots.
- Several service files mutate `sys.path` to make imports work (`app/services/doc_parser/doc_parser.py`, `app/services/doc_parser/pdf_parser.py`, `app/services/risk_calculator/risk_calculator.py`), which indicates packaging/import fragility despite `pyproject.toml` using `package = false`.
- Repository methods sometimes deliberately bypass indexed queries and fetch entire collections because Beanie `Link` queries were unreliable (`app/repositories/evidence_repository.py`, `app/repositories/project_score_repository.py`, `app/repositories/risk_assessment_repository.py`). This is both a debt item and a scaling risk.
- Processing state is represented with free-form string stages/statuses in `app/core/models.py` and `app/repositories/processing_state_repository.py` rather than enums/constants, making typo-driven state bugs easy.
- Business scoring policy is embedded in processor code (`app/services/risk_calculator/risk_assessment_processor.py`, `app/services/risk_calculator/project_score_processor.py`) rather than configuration, even though `CLAUDE.md` describes configuration-driven risk assessment.
- Environment loading is repeated in multiple modules (`app/core/database.py`, `app/core/s3_client.py`, `app/core/llm_service.py`, `app/core/langfuse_tracer.py`, `app/services/api/main.py`), increasing the chance of inconsistent runtime configuration.
- Logs use `print()` throughout services and repositories (`app/services/doc_parser/doc_parser.py`, `app/services/risk_calculator/risk_analyzer.py`, `app/core/database.py`) instead of structured logging with levels, correlation IDs, and redaction.

## Known Bugs
- `app/services/risk_calculator/risk_calculator.py` calls `sys.exit(0)` after one successful scheduled run, so the scheduler code below it is effectively unreachable in normal success cases and the service cannot run continuously as described.
- `db_client.close()` is called without `await` in FastAPI shutdown (`app/services/api/main.py`), while `close_database()` awaits client closure in `app/core/database.py`; this can leave shutdown cleanup incomplete or produce coroutine-related behaviour depending on driver implementation.
- `app/services/doc_parser/doc_parser.py` checks duplicate documents by `file_name` only through `SourceDocumentRepository.is_existing()`, so two projects containing a PDF with the same filename will collide and one will be skipped incorrectly.
- `SourceDocumentRepository.add_or_get_existing()` also de-duplicates only by `file_name` in `app/repositories/source_document_repository.py`, reinforcing the cross-project filename collision bug.
- `app/core/s3_client.py` uses `list_objects_v2()` once without pagination, so buckets with more than one response page will silently omit PDFs after the first page.
- `app/services/doc_parser/pdf_parser.py` annotates `parse_pdf()` as `dict[str, any]`, using the built-in `any` function instead of `typing.Any`; this weakens type checking and would be caught if stricter checks were run.
- `app/services/risk_calculator/chunk_processor.py` bulk-inserts chunks but returns the original type objects without inserted IDs, as acknowledged in the comment in `app/repositories/chunk_repository.py`; downstream code that relies on those returned IDs would be wrong.
- Failed processing states are not automatically retried because most processors only skip `completed` and set `failed`, but there is no retry-count increment or stale `in_progress` recovery path in `app/repositories/processing_state_repository.py` and `app/services/risk_calculator/*_processor.py`.
- The `host` variable is read but unused in `app/core/langfuse_tracer.py`, suggesting Langfuse host configuration may not actually be applied as intended.

## Security Considerations
- The API has no authentication or authorization on any route in `app/services/api/main.py`, `app/services/api/routers/risk.py`, or `app/services/api/routers/config.py`, exposing project names, scores, risk summaries, evidence descriptions, chunk fragments, and configuration to any caller who can reach the service.
- CORS is fully open with credentials enabled (`allow_origins=["*"`, `allow_credentials=True`) in `app/services/api/main.py`; this is unsafe for browser-accessible deployments and conflicts with future authenticated usage.
- `/health` returns database collection names and document counts via `get_database_status()` in `app/services/api/main.py` and `app/core/database.py`, which leaks operational metadata.
- Default MongoDB credentials are hardcoded in application fallbacks (`app/core/database.py`) and documented in examples (`README.md`, `.env.example`); accidental production use would be high impact.
- Default MinIO/S3 credentials are hardcoded in `app/core/s3_client.py` (`minioadmin`/`minioadmin`) and sample credentials appear in `.env.example` and `README.md`.
- `README.md` instructs `mc anonymous set download myminio/test-bucket`, making source PDFs publicly downloadable if copied into shared environments; `app/core/s3_client.py` also persists generated document URLs on every `SourceDocument`.
- Prompt content sent to OpenAI and Langfuse can include full document chunks and derived evidence (`app/services/risk_calculator/risk_analyzer.py`, `app/core/llm_service.py`, `app/core/langfuse_tracer.py`), with no redaction, data classification, tenant control, or opt-out besides missing Langfuse keys.
- Internal document URLs are hidden by default from the top-evidence endpoint via `AI_CPX_PUBLIC_DOCUMENT_URLS` in `app/services/api/routers/risk.py`, but URLs remain stored in MongoDB by `app/services/doc_parser/doc_parser.py`.
- Docker images copy the entire repository into `/app` (`docker/Dockerfile.api`), relying on `.dockerignore`; any local `.env.test`, planning notes, or accidental secrets not ignored could be shipped.

## Performance Bottlenecks
- Evidence extraction is O(projects × documents × chunks × risk types × dimensions) and launches up to `BATCH_SIZE = 5` concurrent LLM calls per chunk in `app/services/risk_calculator/risk_analyzer.py`; there is no adaptive rate limiting, token budget calculation, or global concurrency control.
- Risk dimensions are fetched for every chunk/risk-type combination in `analyze_chunk_for_risk_type()` (`app/services/risk_calculator/risk_analyzer.py`) despite being static per run.
- `EvidenceRepository.get_by_project_and_risk_type()` gathers documents, then chunks per document, then loads all evidences with `fetch_links=True` and filters in memory (`app/repositories/evidence_repository.py`), creating a major N+1 and full-collection scan path.
- `RiskAssessmentRepository.get_by_project()`, `get_by_project_and_risk_type()`, `project_has_risk_assessments()`, and `update_summary()` load all risk assessments with links and filter in Python (`app/repositories/risk_assessment_repository.py`).
- `ProjectScoreRepository.get_by_project()` calls `get_all()` and scans all scores in memory (`app/repositories/project_score_repository.py`), which affects `/projects/{project_id}` and summary generation.
- `get_risk_assessment_top_evidences()` loops over evidence IDs and chunk IDs one by one in `app/services/api/routers/risk.py`, creating N+1 database calls; `EvidenceRepository.get_by_ids()` is sequential in `app/repositories/evidence_repository.py`.
- PDF parsing downloads whole files into memory and extracts all pages into a single string (`app/services/doc_parser/pdf_parser.py`); large PDFs can cause high memory use, and no file-size cap is enforced before parsing.
- Chunking uses fixed 10,000-character windows in `app/services/risk_calculator/chunk_processor.py`, not token-aware splitting, so prompts can exceed model limits when pages contain dense or non-ASCII text.
- `/health` counts documents in every collection on each call (`app/core/database.py`), which can make load balancer health checks expensive as data grows.

## Fragile Areas
- LLM JSON parsing is heuristic string cleanup plus `json.loads()` in `app/services/risk_calculator/risk_analyzer.py`; there is no schema-constrained generation, JSON mode, Pydantic validation, or repair flow beyond retrying the same prompt.
- If the LLM returns invalid dimension keys or scale values, ratings are skipped and evidence may be dropped silently after warnings in `save_evidences_to_database()` (`app/services/risk_calculator/risk_analyzer.py`), biasing scores without surfacing a failed pipeline state.
- The prompt embeds raw chunk content directly inside Markdown fences in `app/services/risk_calculator/risk_analyzer.py`, so prompt injection from project documents can influence extraction instructions.
- Processing skip logic keys off `processing_state` completion rather than the existence and freshness of derived records (`app/services/risk_calculator/chunk_processor.py`, `app/services/risk_calculator/risk_analyzer.py`, `app/services/risk_calculator/project_score_processor.py`); config or prompt changes can leave stale scores unless state is manually cleared.
- `processing_version` exists on `ProcessingState` in `app/core/models.py` but is never used in skip checks in `app/repositories/processing_state_repository.py`.
- Many repository methods swallow exceptions and return `[]`, `None`, or `False` (`app/repositories/project_repository.py`, `app/repositories/source_document_repository.py`, `app/repositories/chunk_repository.py`), making data-loss and query failures hard to distinguish from legitimate empty results.
- `app/services/doc_parser/doc_parser.py` and `app/services/risk_calculator/risk_calculator.py` run scheduled tasks inside single processes with no distributed lock, so multiple replicas can duplicate work.
- `app/core/database.py` keeps global `_client`, `_database`, and `_initialized_models` state; mixed model initialization across service lifecycles can be brittle in tests and long-running processes.
- Project identity is inferred from the first S3 path segment in `app/core/s3_client.py`, which is fragile if bucket layout changes or filenames contain unexpected path structures.

## Scaling Limits
- MongoDB queries frequently avoid indexed link lookups and instead scan full collections in Python (`app/repositories/evidence_repository.py`, `app/repositories/risk_assessment_repository.py`, `app/repositories/project_score_repository.py`), limiting scale well before MongoDB itself is saturated.
- S3 listing in `app/core/s3_client.py` does not paginate, so ingestion is capped by a single `list_objects_v2()` response page.
- The document parser processes PDFs sequentially in one event-loop task (`app/services/doc_parser/doc_parser.py`), and the CPU/blocking PDF extraction in `app/services/doc_parser/pdf_parser.py` runs synchronously.
- The risk calculator processes projects and chunks sequentially, only parallelising risk types within a chunk (`app/services/risk_calculator/risk_analyzer.py`, `app/services/risk_calculator/risk_calculator.py`), so large portfolios will take a long time.
- No job queue, leasing, or distributed worker model exists; `ProcessingState` in `app/core/models.py` tracks state but does not prevent two workers from marking the same combination `in_progress` concurrently.
- Stored `SourceDocument.content` keeps full extracted PDF text in MongoDB (`app/core/models.py`), increasing database storage and backup size; there is no retention or compression strategy.
- API list endpoints return all projects and config records without pagination (`app/services/api/routers/risk.py`, `app/services/api/routers/config.py`).

## Dependencies at Risk
- `fastapi==0.109.1` and `uvicorn==0.20.0` in `pyproject.toml` are relatively old pins for a new Python 3.12 service and may miss security and compatibility fixes.
- `requests==2.32.2` in `pyproject.toml` is pinned below later patch releases; dependency scanning is not present in `.github/workflows/build-push.yml`.
- `langchain==0.3.0`, `langchain-community==0.3.0`, `langchain-core==0.3.0`, and `langchain-openai==0.2.0` in `pyproject.toml` are tightly pinned across a fast-moving ecosystem, raising upgrade and model-compatibility risk.
- `boto3==1.39.0`, `pymongo==4.11.0`, `pypdf==5.9.0`, and `langfuse==3.2.2` are exact pins in `pyproject.toml`; exact pins help reproducibility but require deliberate patch cadence.
- Docker builds copy `uv` from `ghcr.io/astral-sh/uv:latest` in `docker/Dockerfile.api` and `docker/Dockerfile.test-setup`, which undermines reproducibility even though Python dependencies are locked.
- CI only builds and pushes the image (`.github/workflows/build-push.yml`); it does not run linting, tests, dependency vulnerability scans, or container scans.

## Missing Critical Features
- API authentication, authorization, and tenant isolation are missing from `app/services/api/main.py` and all routers under `app/services/api/routers/`.
- API pagination, filtering, and stable ordering are missing for `/projects`, `/config/risk-types`, and `/config/dimension-specs` in `app/services/api/routers/risk.py` and `app/services/api/routers/config.py`.
- There is no public endpoint or admin operation to reprocess a project after config, prompt, model, or source document changes; skip logic is only internal in `app/services/risk_calculator/*`.
- There is no migration/versioning workflow for schema or config changes beyond `scripts/init_db.py`; `processing_version` in `app/core/models.py` is unused.
- No rate-limit handling, cost controls, or token accounting exist for OpenAI calls in `app/core/llm_service.py` and `app/services/risk_calculator/risk_analyzer.py` beyond DEV-mode caps.
- No human review or confidence threshold workflow exists for LLM-generated evidence before it affects risk scores (`app/services/risk_calculator/risk_analyzer.py`, `app/services/risk_calculator/risk_assessment_processor.py`).
- No central error reporting/alerting is wired into service failures; errors are printed in `app/services/doc_parser/doc_parser.py`, `app/services/risk_calculator/risk_calculator.py`, and repositories.
- No deletion/retention controls exist for stored documents, chunks, evidence, summaries, or traces in `app/core/models.py`.

## Test Coverage Gaps
- There is no `tests/` directory and no pytest dependency or test command in `pyproject.toml`; only fixture-loading scripts exist under `scripts/test/`.
- `.github/workflows/build-push.yml` does not run unit tests, integration tests, type checks, or `ruff`, so broken code can still be built and pushed.
- LLM response parsing, invalid JSON handling, invalid dimension values, retry behaviour, and score calculation lack focused tests around `app/services/risk_calculator/risk_analyzer.py` and `app/services/risk_calculator/risk_assessment_processor.py`.
- Repository query behaviour and Beanie `Link` handling lack regression tests, despite multiple comments/workarounds in `app/repositories/evidence_repository.py`, `app/repositories/project_score_repository.py`, and `app/repositories/risk_assessment_repository.py`.
- API routes lack tests for 404s, empty data, hidden/public document URLs, response schemas, and N+1-sensitive cases in `app/services/api/routers/risk.py`.
- S3 ingestion lacks tests for pagination, duplicate filenames across projects, missing credentials, failed downloads, and non-PDF paths in `app/core/s3_client.py` and `app/services/doc_parser/doc_parser.py`.
- PDF parsing lacks tests for encrypted PDFs, image-only PDFs, huge PDFs, extraction failures, and metadata serialization in `app/services/doc_parser/pdf_parser.py`.
- Processing-state resume logic lacks tests for stale `in_progress`, failed retries, version invalidation, duplicate worker races, and partial writes in `app/repositories/processing_state_repository.py` and all processor modules.
