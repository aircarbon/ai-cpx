# Testing Patterns
**Analysis Date:** 2026-07-10
## Test Framework
- There is no conventional Python unit-test framework configured in `pyproject.toml`: no `pytest`, `pytest-asyncio`, `coverage`, or test runner settings are present.
- The only development dependencies in `pyproject.toml` are `jupyter` and `ruff`; quality gates are lint/format hooks rather than automated unit tests.
- Current testing is script- and container-oriented. The main test harness is `scripts/test/test_setup.py`, executed through `docker/Dockerfile.test-setup` and the `just test-setup` recipe in `justfile`.
- The project relies on Docker, MongoDB test containers, seeded JSON fixtures, and manual/API checks described in `CLAUDE.md`.

## Test File Organization
- Test support files live under `scripts/test/`, not a top-level `tests/` package.
- `scripts/test/test_setup.py` is a stage runner for preparing database state.
- `scripts/test/test_data_loader.py` contains fixture loading helpers for MongoDB/Beanie documents.
- Static fixture data is stored as JSON in `scripts/test/data/`, including `projects.json`, `documents.json`, `chunks.json`, `evidence_ratings.json`, `evidences.json`, `risk_assessments.json`, and `project_scores.json`.
- Container setup for the test harness is in `docker/Dockerfile.test-setup`.
- No `test_*.py` files currently contain pytest-style `test_...` functions; files named `test_setup.py` and `test_data_loader.py` are executable/support scripts.

## Test Structure
- Tests are organized around pipeline stages rather than test cases/assertions.
- `scripts/test/test_setup.py` exposes staged functions: `empty_db`, `init_db`, `init_projects`, `init_docs`, `init_chunks`, `load_evidences`, `load-risk-assessments`, `load-project-scores`, and `load-project-score-summaries`.
- Each stage defines an inner async function, calls `ensure_database_connection(ALL_MODELS)`, performs setup/loading work, closes the database in `finally`, and raises an exception if the stage failed.
- `justfile` provides `just test-setup stage="init-projects"`, which builds `docker/Dockerfile.test-setup` and runs `test-setup {{stage}}` on the `internal` Docker network.
- `CLAUDE.md` defines higher-level workflows for API endpoint testing, evidence extraction testing, and document parser testing using fresh containers and staged fixture loading.

## Mocking
- There is no formal mocking library or monkeypatch pattern in the repository.
- External dependencies are isolated with real test containers/services rather than mocks: `mongodb-test` for MongoDB, `api-test` for FastAPI, `doc-parser-test`, `risk-calculator-test`, and `test-setup`.
- LLM behavior is not mocked in a unit-test sense. Evidence-extraction changes are intended to run in `risk-calculator-test` against staged chunks, per `CLAUDE.md`.
- S3/MinIO is treated as an existing static file source for integration testing; `CLAUDE.md` says test containers can reuse the existing MinIO instance.
- Fixture data in `scripts/test/data/*.json` acts as a substitute for rerunning expensive earlier pipeline stages when testing API/scoring behavior.

## Fixtures and Factories
- Fixtures are MongoDB export-style JSON files under `scripts/test/data/`.
- `scripts/test/test_data_loader.py` has `load_test_json()` to read fixture files and `clean_mongodb_fields()` to convert Mongo export fields (`$oid`, `$date`, `$ref`, `$id`) into values Beanie accepts.
- Fixture loader functions are per-collection (`load_test_projects`, `load_test_documents`, `load_test_chunks`, `load_test_evidence_ratings`, `load_test_evidences`, `load_test_risk_assessments`, `load_test_project_scores`, and summary loaders).
- Loaders are idempotent: they check for existing records by fixed IDs before inserting and print skipped/created counts.
- There are no factory libraries such as Factory Boy; object creation is either direct dataclass/model construction in application code or JSON fixture insertion in test setup.

## Coverage
- No coverage tool is configured in `pyproject.toml`, `justfile`, or `.pre-commit-config.yaml`.
- There are no coverage thresholds, reports, or CI coverage artefacts visible in the inspected files.
- Quality validation currently focuses on Ruff lint/format and manual/container verification rather than measured test coverage.

## Test Types (Unit, Integration, E2E/container-based)
- Unit tests: not currently present as a formal suite. Pure functions such as `create_text_chunks()` in `app/services/risk_calculator/chunk_processor.py` and scoring helpers in `app/services/risk_calculator/project_score_processor.py` are candidates but have no pytest coverage.
- Integration tests: the primary pattern. `scripts/test/test_setup.py` initializes Beanie models, loads configuration, and seeds MongoDB test data through real repositories/models.
- API/container tests: `CLAUDE.md` documents building `api-test` from `docker/Dockerfile.api`, running it on port `8002`, and checking endpoints such as `/health`, `/projects`, and `/projects/{project_id}` with `curl`.
- Pipeline/container tests: `CLAUDE.md` documents running `doc-parser-test` and `risk-calculator-test` containers against staged database states to test document ingestion, chunking/evidence extraction, risk assessments, project scores, and summaries.
- Database inspection is part of the test workflow using `mongosh` against `mongodb-test` on port `27018` and querying collections such as `projects`, `documents`, `chunks`, `evidences`, `risk_assessments`, and `project_scores`.

## Common Patterns
- Start from a clean test environment by stopping `mongodb-test`, `api-test`, `doc-parser-test`, and `risk-calculator-test` before a run, as described in `CLAUDE.md`.
- Use `.env.test` mounted as `/app/.env` for test containers, as shown in `docker/Dockerfile.test-setup` and the `CLAUDE.md` Docker commands.
- Load only the minimum stage needed for the behavior under test: `init-db` for parser changes, `init-chunks` for evidence extraction, and `load-project-score-summaries` for API endpoint testing.
- Build fresh Docker images before running tests to include local code changes (`docker build -t test-setup -f docker/Dockerfile.test-setup .`, `docker build -t api-test -f docker/Dockerfile.api .`).
- Verify behavior through logs (`docker logs`, `docker logs -f`), HTTP requests (`curl`), and direct MongoDB inspection (`mongosh`).
- Clean up test containers after verification with `docker stop ...`; test containers are run with `--rm` where documented.
