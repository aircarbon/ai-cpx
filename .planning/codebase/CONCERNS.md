---
# Codebase Concerns
**Analysis Date:** 2026-07-10
## Tech Debt
**Area/Component:** Fragile `sys.path` import hacks / Files: `app/services/risk_calculator/risk_calculator.py:11`, `app/services/doc_parser/doc_parser.py:10`, `app/services/doc_parser/pdf_parser.py:8`, `scripts/init_db.py:6`, `scripts/test/test_data_loader.py:14`, `scripts/test/test_setup.py:13` / Impact: Breaks when the package is installed normally or when tests run from a different CWD; relies on relative path traversal instead of a proper install/PYTHONPATH. / Fix approach: Install `app` as a package (pyproject/setup), drop `sys.path.append`, run with `python -m`.

**Area/Component:** In-memory full-collection filtering instead of DB queries / Files: `app/repositories/evidence_repository.py:71` (`get_by_project_and_risk_type` loads ALL evidences then filters Python-side), `app/repositories/risk_assessment_repository.py:35,51,91,123` (`get_by_project_and_risk_type`, `get_by_project`, `project_has_risk_assessments`, `update_summary`), `app/repositories/project_score_repository.py:23-31` (`get_by_project` loads ALL project scores) / Impact: O(total documents) per query; degrades badly as data grows. Comments admit this is a workaround for unreliable Beanie Link queries. / Fix approach: Use proper Beanie/Link queries or aggregation pipelines; add indexed compound queries.

**Area/Component:** Unused `processing_version` / Files: `app/core/models.py:268`, `app/core/types.py:415`, `app/repositories/processing_state_repository.py` / Impact: Scoring/algorithm changes never invalidate cached "completed" ProcessingState rows, so re-runs skip reprocessing. / Fix approach: Compare stored `processing_version` against current; force re-run on mismatch.

**Area/Component:** Non-deterministic LLM config for structured extraction / Files: `app/core/llm_service.py:17` (default `temperature=1`), `.env.example:28` (OPENAI_TEMPERATURE=1, comment claims GPT-5 ignores it) / Impact: High temperature reduces JSON-extraction reliability and reproducibility of risk scores. / Fix approach: Use temperature 0 (or model default) for JSON/extraction calls; separate generation vs. extraction model params.

**Area/Component:** Repeated work / N+1 DB calls in processing loop / Files: `app/services/risk_calculator/risk_analyzer.py:341` (`get_all_risk_dimensions()` called per chunk), `app/repositories/evidence_repository.py:91-101` (`get_by_ids` sequential awaits) / Impact: Redundant DB round-trips. / Fix approach: Fetch dimensions/risk-types once per project; batch `get_by_ids` via `In(...)` query.

**Area/Component:** Stale/misleading hardcoded API copy / Files: `app/services/api/routers/risk.py:17-29` / Impact: Methodology text claims "four dimensions (impact severity, likelihood certainty, timing, reversibility)" but config defines 6 dimensions (`config/database/risk_dimensions.json` count=6) and 13 risk types (matches `risk_types.json` count=13). / Fix approach: Derive counts/descriptions from DB config; remove hardcoded claims.

**Area/Component:** Print-based diagnostics / Files: pervasive `print(...)` across services, repos, and core / Impact: No log levels, no structured logging, hard to monitor in production / Fix approach: Adopt `logging`/`structlog`.

## Known Bugs
**Bug description:** Risk-calculator scheduled re-runs never execute (dead scheduler). `scheduled_task()` ends with `sys.exit(0)` at `app/services/risk_calculator/risk_calculator.py:111`, so the process terminates before the `AsyncIOScheduler` is even created in `main()` (`risk_calculator.py:127-130`). / Symptoms: Despite `CHECKING_INTERVAL_HOURS = 24`, the service runs once and exits; ongoing S3 changes are never re-processed. / Files: `app/services/risk_calculator/risk_calculator.py:110-111,127-130` / Trigger: Every run. / Workaround: Remove the `sys.exit(0)`; rely on scheduler loop. (Note: `doc_parser.py` does NOT have this bug and schedules correctly every 10 min.)

**Bug description:** `get_database_status` counts collections with a non-awaited coroutine. / Symptoms: `status["collection_counts"][...]` holds coroutine objects, not ints, so counts are wrong/garbage. / Files: `app/core/database.py:117` (`_database[collection_name].count_documents({})` missing `await`) / Trigger: Status endpoint/CLI. / Workaround: `await` the async `count_documents`.

**Bug description:** Document de-duplication keyed only on global `file_name`, not `(project, file_name)`. / Symptoms: Two projects sharing a filename are treated as the same document; docs can be skipped or misattributed to the wrong project. / Files: `app/repositories/source_document_repository.py:25,31` (`is_existing`, `add_or_get_existing`), consumed by `app/services/doc_parser/doc_parser.py:51` / Trigger: Duplicate filenames across S3 folders. / Workaround: Add `project_id` to the uniqueness check.

**Bug description:** Duplicate evidences on crash-resume. Resume is blocked only by `status == "completed"`; if a run saves evidences but then fails before marking the chunk+risk_type `completed`, the next run re-inserts duplicates. / Symptoms: Inflated evidence counts / scores. / Files: `app/services/risk_calculator/risk_analyzer.py:356-364` (marks completed only after save), `app/repositories/evidence_repository.py:14-43` (no upsert/dedup) / Trigger: Partial failure mid-batch. / Workaround: Idempotent upsert keyed on (chunk_id, risk_type_id, title) or mark `in_progress` atomically with a claim.

**Bug description:** Invalid project/risk-assessment IDs raise 500, not 400/422. / Symptoms: `PydanticObjectId(bad)` throws in `app/services/api/routers/risk.py:54,69,107` and repository queries. / Files: `app/services/api/routers/risk.py`, `app/repositories/risk_assessment_repository.py` / Trigger: Malformed path param. / Workaround: Validate with Pydantic `ObjectId` type / try-except returning 404/422.

**Bug description:** S3 `list_objects_v2` returns at most 1000 keys per call and is not paginated. / Symptoms: Projects/folders beyond the first 1000 objects are silently ignored. / Files: `app/core/s3_client.py:61` / Trigger: Buckets with >1000 objects. / Workaround: Loop with `ContinuationToken`.

**Bug description:** Silent LLM JSON failure. After `MAX_RETRIES=3`, `analyze_with_retry` returns 0 with only a printed error; no persisted failure record. / Symptoms: Missing evidences with no trace. / Files: `app/services/risk_calculator/risk_analyzer.py:277-292` / Trigger: LLM returns non-JSON / malformed JSON. / Workaround: Persist failed extraction in ProcessingState; surface failure counts.

**Bug description:** Test fixture loader references a non-existent field. `test_data_loader.py:214` reads `clean_data['claim_text']` but `Evidence` model (`app/core/models.py:174`) has `evidence_description`, not `claim_text`. / Symptoms: `KeyError` if `evidences.json` fixtures are loaded via this path. / Files: `scripts/test/test_data_loader.py:214` / Trigger: Loading evidences in the test harness. / Workaround: Use `evidence_description`.

## Security Considerations
**Area:** CORS / API exposure / Risk: `app/services/api/main.py:65-71` sets `allow_origins=["*"]` together with `allow_credentials=True` (an invalid, ignored-by-browsers combination) and there is NO authentication/authorization on any endpoint (`risk.py`, `config.py`). All project, evidence, and document-URL data is publicly readable. / Files: `app/services/api/main.py`, `app/services/api/routers/risk.py`, `app/services/api/routers/config.py` / Current mitigation: None (network isolation only in Docker `internal` network). / Recommendations: Add auth (API key/OAuth), restrict CORS origins, separate public vs. internal endpoints; do not combine wildcard origin with credentials.

**Area:** Default credentials hardcoded / Risk: Weak/default secrets baked into code paths. / Files: `app/core/database.py:23-24` (`mongoadmin`/`strongpassword123`), `app/core/s3_client.py:15-16` (`minioadmin`/`minioadmin`) / Current mitigation: Overridable via env; `.env.example` provides stronger values. / Recommendations: Remove default credentials; fail fast if not provided in non-dev modes.

**Area:** LLM prompt injection from untrusted documents / Risk: PDF text is concatenated directly into prompts (`app/services/risk_calculator/risk_analyzer.py:49-132`, `app/core/llm_service.py:72-85`). Malicious/garbage content can skew ratings, inject instructions, or manipulate generated summaries. / Files: `app/services/risk_calculator/risk_analyzer.py`, `app/core/llm_service.py`, `app/services/risk_calculator/project_summary_processor.py`, `risk_assessment_summary_processor.py` / Current mitigation: None (relies on "respond with ONLY JSON" instruction). / Recommendations: Sanitize/limit extracted text, add output schema validation, constrain model privileges, treat scores as advisory.

**Area:** Secret handling / Risk: `.env` is mounted into containers (`app/core/database.py:9` checks `/app/.env`). / Files: `.env.example`, Dockerfiles / Current mitigation: `.gitignore` (unverified). / Recommendations: Confirm secrets never committed; use a secret manager in prod; avoid plain `.env` mounts.

## Performance Bottlenecks
**Slow operation:** In-memory full-collection scans on every lookup / Problem: Repeated `find(fetch_links=True).to_list()` of entire collections then Python filtering. / Files: `app/repositories/evidence_repository.py:71`, `app/repositories/risk_assessment_repository.py:35,51,91,123`, `app/repositories/project_score_repository.py:27` / Cause: Unreliable Beanie Link queries worked around with full loads. / Improvement path: Indexed queries / aggregation; never load full collections in request paths.

**Slow operation:** N+1 queries in API endpoints / Problem: Loops issue one query per item. / Files: `app/services/api/routers/risk.py:68-69` (per risk_score `get_by_id`), `app/services/api/routers/risk.py:127` (per evidence `ChunkRepository.get_by_id`), `app/repositories/evidence_repository.py:91-101` (`get_by_ids` sequential) / Cause: Fetching by ID in a loop. / Improvement path: Batch fetch with `In([...])`; join/aggregate; build maps once.

**Slow operation:** LLM fan-out for evidence extraction / Problem: One LLM call per (chunk × risk_type); chunks processed serially, only 5 risk-types batched concurrently (`BATCH_SIZE=5`). For a large PDF (hundreds of chunks) × 13 risk types this is thousands of calls. / Files: `app/services/risk_calculator/risk_analyzer.py:21,384-419`, `app/core/llm_service.py:49-70` / Cause: Cartesian product of chunks × risk types with low concurrency. / Improvement path: Higher concurrency with rate-limit awareness, larger chunk sizes, batch multiple risk types into one prompt, caching, batch embedding/retrieval.

**Slow operation:** Whole-PDF text extraction in memory / Problem: Entire PDF downloaded and all pages extracted into one string before chunking. / Files: `app/services/doc_parser/pdf_parser.py:30-48`, `app/core/s3_client.py:97-120` / Cause: No streaming / page-wise handling; no OCR. / Improvement path: Stream/paginate; add OCR fallback for scanned PDFs; cap memory.

## Fragile Areas
**Component/Module:** Beanie Link-field querying / Files: `app/repositories/risk_assessment_repository.py`, `app/repositories/evidence_repository.py`, `app/repositories/project_score_repository.py` / Why fragile: Team already abandoned Link queries in favor of full-collection loads + in-memory filtering; any refactor risks reintroducing subtle mismatches. / Safe modification: Add integration tests around Link queries before changing; keep a single query helper. / Test coverage: None.

**Component/Module:** Resume / idempotency logic (`ProcessingState`) / Files: `app/repositories/processing_state_repository.py`, `app/services/risk_calculator/*` / Why fragile: Correctness depends on side-effect ordering and exception swallowing; crashes can leave inconsistent states and duplicates. / Safe modification: Add atomic claim + upsert; verify with crash-injection tests. / Test coverage: None.

**Component/Module:** LLM JSON contract / Files: `app/services/risk_calculator/risk_analyzer.py:135-164,249-292` / Why fragile: Parsing relies on best-effort markdown/json stripping; model can deviate. / Safe modification: Use structured outputs / function-calling / JSON schema enforcement; add parser unit tests. / Test coverage: None.

**Component/Module:** Import bootstrapping / Files: multiple `sys.path.append` sites (see Tech Debt) / Why fragile: Depends on CWD and relative traversal. / Safe modification: Package install + `python -m`. / Test coverage: None.

## Scaling Limits
**Resource/System:** MongoDB query pattern / Current capacity: Works for small datasets / Limit: O(N) full scans per request; does not scale to many projects/evidences. / Scaling path: Indexed compound queries, aggregation pipelines, pagination.

**Resource/System:** S3 listing / Current capacity: <1000 objects / Limit: `list_objects_v2` truncation at 1000 keys, no pagination (`app/core/s3_client.py:61`). / Scaling path: ContinuationToken pagination.

**Resource/System:** Single-process scheduler services / Current capacity: One worker / Limit: No horizontal scaling; running multiple `risk-calculator`/`doc-parser` instances causes duplicate LLM work and duplicate DB rows (no distributed lock). / Scaling path: Leader election / task queue (e.g., Celery/Redis) + idempotent upserts.

**Resource/System:** LLM cost & rate limits / Current capacity: DEV caps only (`DEV_MAX_*`) / Limit: Cost/latency scale linearly with chunks×risk types; no global rate limiting → risk of 429s and budget overruns. / Scaling path: Concurrency control, caching, batching, model tiering, cost monitoring.

**Resource/System:** DB connection / Current capacity: Single global `AsyncMongoClient` / Limit: No explicit pool sizing/tuning; global singleton (`app/core/database.py:15,34-37`). / Scaling path: Configure `maxPoolSize`; per-service clients.

## Dependencies at Risk
**Package:** `langchain==0.3.0` / `langchain-openai==0.2.0` / `langfuse==3.2.2` / Risk: Fast-moving, frequent breaking changes; Langfuse v3 API churn can break tracing (`app/core/langfuse_tracer.py`). / Impact: Future upgrades may break LLM/observability layer. / Migration plan: Pin and track releases; isolate behind `app/core/llm_service.py`; add smoke test for tracing.

**Package:** `beanie==2.0.0` / Risk: Link-query semantics and `find/fetch_links` behavior change across minor versions; current code already works around it with full loads. / Impact: Upgrades could change query results or performance. / Migration plan: Add integration tests on Link queries before bumping.

**Package:** `pypdf==5.9.0` / Risk: No OCR; scanned/image-only PDFs yield empty text → empty chunks → no evidences. / Impact: Silent coverage gaps for real-world carbon docs. / Migration plan: Add OCR (e.g., tesseract/cloud vision) fallback.

**Package:** `apscheduler==3.9.0` / Risk: 3.x is effectively maintenance-mode; 4.x is the current line. / Impact: Long-term maintenance. / Migration plan: Plan migration to APScheduler 4 or asyncio-native scheduler.

**Package:** `fastapi==0.109.1` / `uvicorn==0.20.0` / Risk: Older releases; missing recent security/perf fixes. / Impact: Lower-level maintenance. / Migration plan: Bump within 0.11x/0.3x lines and test.

**Package:** Model mismatch / Risk: `.env.example` default `OPENAI_MODEL=gpt-4.1-mini` while `app/core/llm_service.py:16` defaults to `gpt-4o-mini`; cost/reliability depend on chosen model. / Impact: Confusing defaults, unpredictable token cost. / Migration plan: Single source of truth for model name.

## Missing Critical Features
**Feature gap:** API authentication/authorization / Problem: All data endpoints are unauthenticated (`app/services/api/main.py`, `routers/risk.py`, `routers/config.py`). / Blocks: Safe production exposure, multi-tenant use.

**Feature gap:** Failure handling / DLQ for LLM extraction / Problem: Failed/empty extractions are silently dropped (`risk_analyzer.py:277-292`). / Blocks: Trustworthy audit of risk scores; reprocessing.

**Feature gap:** Processing-version / schema migration / Problem: `processing_version` exists but unused (`app/core/models.py:268`); config changes to dimensions/risk-types won't trigger recompute. / Blocks: Safe algorithm evolution.

**Feature gap:** LLM rate limiting & cost controls / Problem: No global limiter; concurrency only `BATCH_SIZE=5` (`risk_analyzer.py:21`). / Blocks: Predictable spend; avoiding 429s at scale.

**Feature gap:** OCR for scanned PDFs / Problem: `pypdf` text-only (`pdf_parser.py`). / Blocks: Coverage of image-based carbon docs.

**Feature gap:** API pagination/sorting/filtering / Problem: List endpoints load everything (`routers/risk.py:32-49`, `source_document_repository.get_all`). / Blocks: Usable UI at scale.

**Feature gap:** Health/readiness endpoints / Problem: `CLAUDE.md` references `/health` but `app/services/api/main.py` defines none. / Blocks: Orchestration/liveness probes.

**Feature gap:** Config hot-reload / Problem: Risk types/dimensions changes require manual DB re-init; resume logic ignores version. / Blocks: Iterating on scoring methodology.

## Test Coverage Gaps
**Untested area:** Core business logic / What's not tested: Scoring (`risk_assessment_processor.py:10-25`, `project_score_processor.py:10-40`), chunking (`chunk_processor.py:15-41`), prompt building (`risk_analyzer.py:49-132`), JSON parsing (`risk_analyzer.py:135-164`), repository filtering. / Files: `app/services/risk_calculator/*`, `app/repositories/*`, `app/core/types.py` / Risk: Silent regressions in scoring math and LLM contract. / Priority: High.

**Untested area:** Repository query correctness (in-memory filtering fixes) / What's not tested: `get_by_project_and_risk_type`, `get_by_project`, `update_summary`, `get_by_project` score lookups. / Files: `app/repositories/evidence_repository.py`, `risk_assessment_repository.py`, `project_score_repository.py` / Risk: Incorrect filtering → wrong risk scores at scale. / Priority: High.

**Untested area:** API layer / What's not tested: Endpoint responses, 404/422 handling, N+1 behavior. / Files: `app/services/api/routers/risk.py`, `config.py`, `main.py` / Risk: Broken contracts in prod. / Priority: High.

**Untested area:** End-to-end pipeline with real LLM/S3/Mongo / What's not tested: Only fixture loaders exist (`scripts/test/test_data_loader.py`, `scripts/test/test_setup.py`); no pytest, no CI (no `.github`), no `pytest.ini`/`pyproject` test config. / Files: `scripts/test/*` / Risk: No automated verification of the documented Docker staging flow. / Priority: Medium.

**Untested area:** Resume/idempotency & duplicate suppression / What's not tested: Crash-resume scenarios, concurrent-run dedupe. / Files: `app/repositories/processing_state_repository.py`, `risk_analyzer.py` / Risk: Data corruption/duplicates in production. / Priority: High.
---
