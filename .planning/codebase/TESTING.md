---
# Testing Patterns
**Analysis Date:** 2026-07-10
## Test Framework
**Runner:** No automated test runner is configured or used. Grep across the repo found zero occurrences of `pytest`, `unittest`, `@pytest`, `import mock`, `MagicMock`, `AsyncMock`, or `monkeypatch`. There is no `conftest.py`, `pytest.ini`, `pyproject.toml`, or `tox.ini`.
**Assertion Library:** None. There are no assertion-based tests; verification is performed by inspecting printed counts and by manually querying the database / API.
**Run Commands:** "Test" execution is driven by Docker-based stage scripts and manual checks (documented in `CLAUDE.md` and `README.md`):
- Local: `python scripts/test/test_setup.py <stage>` (stages: `empty-db`, `init-db`, `init-projects`, `init-docs`, `init-chunks`, `load-evidences`, `load-risk-assessments`, `load-project-scores`, `load-project-score-summaries`, `all`) — see `scripts/test/test_setup.py:401-418`.
- Docker: `docker build -t test-setup -f docker/Dockerfile.test-setup . && docker run --rm --network internal test-setup <stage>` (see `CLAUDE.md` Example workflows, `README.md:132-166`).
- API/E2E checks via `curl` against the `api-test` container on port `8002` (e.g. `curl "http://localhost:8002/projects"`); DB inspection via `mongosh` against `mongodb-test` on port `27018`.
## Test File Organization
**Location:** `scripts/test/` (alongside `scripts/init_db.py` and `scripts/README.md`). There is no `tests/` directory inside `app/`.
**Naming:** `test_setup.py` (stage orchestrator) and `test_data_loader.py` (fixture loader). Note: despite `test_` prefixes, these are data-seeding/setup scripts, NOT assertion-based unit tests.
**Structure:** JSON fixtures live in `scripts/test/data/` — `projects.json`, `documents.json`, `chunks.json`, `evidence_ratings.json`, `evidences.json`, `risk_assessments.json`, `project_scores.json`.
## Test Structure
**Suite Organization:** `test_setup.py` defines one function per pipeline stage (`empty_db`, `init_db`, `init_projects`, `init_docs`, `init_chunks`, `load_evidences`, `load_risk_assessments`, `load_project_scores`, `load_project_score_summaries`). A master list maps stage name to function in `run_stages_up_to(target_stage)` (`test_setup.py:371-399`). Each stage function wraps its async work in `asyncio.run(...)` and prints success/error status.
Pattern (from `scripts/test/test_setup.py`):
```python
def init_db():
    """Stage 2: Initialize database schema - same as main init_db.py"""
    async def initialize_schema():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            ...
            config_results = await initialize_configuration_data()
            return True
        except Exception as e:
            print(f"Database schema initialization failed: {e}")
            return False
        finally:
            await close_database()
    success = asyncio.run(initialize_schema())
    if not success:
        raise Exception("Database schema initialization failed")
```
**Patterns:** Stages connect to a real test Mongo, load JSON fixtures via `test_data_loader.py`, verify affected-collection counts, and close. `test_data_loader.py:20-28` (`load_test_json`) and `:31-72` (`clean_mongodb_fields`) convert MongoDB export formats (`$oid`, `$date`, `$ref`) into Beanie-compatible fields; per-entity async loaders (`load_test_projects`, `load_test_documents`, `load_test_chunks`, `load_test_evidence_ratings`, `load_test_evidences`, `load_test_risk_assessments`, `load_test_project_scores`, `load_test_project_score_summaries`) upsert records and skip existing IDs.
## Mocking
**Framework:** None configured (no `unittest.mock`, `pytest-mock`, or `responses`).
**Patterns:** No mocking is used. The stage scripts run against a real `mongodb-test` instance and (where applicable) live MinIO/S3 and the real OpenAI LLM.
**What to Mock:** If automated tests were added, the natural seams to mock are: LLM calls (`app/core/llm_service.py` `LLMService.query`/`analyze_risk`), S3/boto3 access (`app/core/s3_client.py`), and the OpenAI network layer. Langfuse already self-disables when keys are absent (`app/core/langfuse_tracer.py:15-17`).
**What NOT to Mock:** Repository/DB access is the system under test in the stage scripts — they intentionally hit a real Mongo instance. Do not mock `app.repositories.*` when using the Docker stage flow.
## Fixtures and Factories
- JSON fixture files under `scripts/test/data/` (MongoDB export shape with `$oid`/`$ref`/`$date`).
- `test_data_loader.py` provides loader factories that build Beanie models and upsert them; `clean_mongodb_fields` (`test_data_loader.py:31-72`) is the field-transformation factory. There is no `factory_boy`/`faker`.
- Config-driven data: risk dimensions and risk types are loaded from `config/database/risk_dimensions.json` and `config/database/risk_types.json` via `app/core/data_loader.py` (`populate_risk_dimensions`, `populate_risk_types`).
## Coverage
**Requirements:** No coverage tooling configured (no `pytest-cov`, `.coveragerc`, or coverage step in CI).
**View Coverage:** Manual verification only — `mongosh` count queries (`db.projects.countDocuments()`, `db.evidences.countDocuments()`, etc., see `CLAUDE.md` MongoDB Inspection section) and `curl` comparisons against the API. No line-coverage metric exists.
## Test Types
**Unit Tests:** None present. No isolated, fast, assertion-based unit tests exist in the repo.
**Integration Tests:** The closest equivalent is the Docker stage flow — `test-setup` + the real `mongodb-test` (port `27018`) + existing MinIO — populating data through the actual persistence/repository layer (`scripts/test/test_setup.py`, `CLAUDE.md` "Test Environment Setup").
**E2E Tests:** API-level E2E is done manually with `curl` against the `api-test` container (port `8002`) and compared to DB state (`CLAUDE.md` Example 1). Full pipeline E2E is exercised by running `doc-parser-test` and `risk-calculator-test` containers against `mongodb-test` (`CLAUDE.md` Examples 2-3).
## Common Patterns
**Async Testing:** Async is handled by wrapping stage coroutines in `asyncio.run(...)` inside synchronous stage functions (`test_setup.py`); `test_data_loader.py` exposes `async` loaders. No async test framework (e.g. `pytest-asyncio`) is used.
**Error Testing:** Stage functions use `try/except`, print an error message, and `raise Exception(...)` on failure (`test_setup.py:65,104,141,178,215,255,293,331,369`). Fixture loaders catch `FileNotFoundError` and skip gracefully (`test_data_loader.py:126-128` etc.). Pipeline services record failures into `ProcessingState.error_message` rather than raising (`risk_analyzer.py:369-378`).
**Dev-mode acceleration:** `APP_MODE=DEV` plus env flags `DEV_MAX_RISK_TYPES`, `DEV_MAX_CHUNKS_PER_PROJECT`, `DEV_SKIP_RISK_ASSESSMENT_SUMMARIES` limit processing for faster local iteration (`risk_analyzer.py:31-37,227-232`, `risk_assessment_summary_processor.py:78`).
**Container separation:** Strict dev vs. test isolation — dev containers (`mongodb`, `api`, `doc-parser`, `risk-calculator`) vs. test containers (`mongodb-test`, `api-test`, `doc-parser-test`, `risk-calculator-test`, `test-setup`) on the `internal` network (`CLAUDE.md` "Container Separation"). Test containers are always stopped/removed before a new run.
---
