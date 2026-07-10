# Coding Conventions
**Analysis Date:** 2026-07-10
## Naming Patterns (Files, Functions, Variables, Types)
- Python modules and packages use `snake_case` throughout `app/`, for example `app/services/risk_calculator/risk_assessment_processor.py`, `app/repositories/project_score_repository.py`, and `app/services/api/schemas/risk_schemas.py`.
- Repository classes use `PascalCase` plus the `Repository` suffix, such as `ProjectRepository` in `app/repositories/project_repository.py` and `EvidenceRepository` in `app/repositories/evidence_repository.py`.
- Database Beanie documents and API/domain schemas use `PascalCase` singular nouns, for example `Project`, `SourceDocument`, `RiskAssessment`, and `ProjectScore` in `app/core/models.py`.
- Internal business types are dataclasses in `app/core/types.py` and often mirror database model names; imports alias Beanie models as `ProjectModel`, `ChunkModel`, etc. to distinguish persistence types from domain types.
- Async functions are named with verbs that describe the operation: `get_by_id`, `get_all`, `add_or_get_existing`, `process_project_chunks`, `calculate_total_project_score`, and `get_project_risk_breakdown`.
- Environment and module constants are `UPPER_SNAKE_CASE`, for example `CHECKING_INTERVAL_HOURS`, `BATCH_SIZE`, `CHUNK_SIZE`, `OVERLAP_SIZE`, and `MIN_CHUNK_SIZE` in `app/services/risk_calculator/`.
- IDs are generally stored as strings in domain types and converted to `PydanticObjectId` at repository/model boundaries, as shown in `app/core/types.py` and repository files under `app/repositories/`.
- API response field names are descriptive `snake_case` names, for example `total_risk_score`, `risk_breakdowns`, and `chunk_text_fragment` in `app/services/api/schemas/risk_schemas.py`.

## Code Style (Formatting, Linting - ruff, etc.)
- The project targets Python 3.12 via `requires-python = ">=3.12,<3.14"` in `pyproject.toml` and `.python-version`.
- Formatting is Ruff-based: `pyproject.toml` sets `[tool.ruff] target-version = "py312"`, `line-length = 120`, and `[tool.ruff.format] quote-style = "double"`.
- Ruff lint rules selected in `pyproject.toml` are `E`, `F`, `I`, `N`, `W`, `UP`, and `S`, covering pycodestyle/pyflakes, import sorting, naming, pyupgrade, and Bandit-style security checks.
- The `justfile` quality command is `just lint`, which runs `uv run ruff check . --fix` and `uv run ruff format .`.
- `.pre-commit-config.yaml` runs general hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`, YAML/JSON checks, large-file and merge-conflict checks) plus `ruff --fix` and `ruff-format`.
- The code uses modern type syntax (`str | None`, `list[RiskType]`, `dict[str, Any]`) rather than `Optional`/`List`, matching the `UP` pyupgrade configuration.
- Most modules use concise procedural service functions and static repository methods rather than heavy class hierarchies.

## Import Organization
- Imports are top-of-file and grouped as standard library, third-party, then local application imports, as seen in `app/services/api/main.py`, `app/core/database.py`, and `app/services/risk_calculator/risk_analyzer.py`.
- Ruff import sorting (`I`) is the enforced import organiser via `pyproject.toml` and `.pre-commit-config.yaml`.
- Local imports are absolute from `app...` in most modules, for example `from app.repositories.project_repository import ProjectRepository`.
- Service entrypoint modules such as `app/services/risk_calculator/risk_calculator.py`, `app/services/doc_parser/doc_parser.py`, `scripts/init_db.py`, and `scripts/test/test_setup.py` modify `sys.path` to support direct script/container execution.
- Relative imports are used for sibling service modules, for example `from .chunk_processor import process_project_chunks` in `app/services/risk_calculator/risk_calculator.py` and `from .pdf_parser import parse_pdf` in `app/services/doc_parser/doc_parser.py`.
- `TYPE_CHECKING` appears in `app/core/types.py` to handle model imports while still providing conversion methods.

## Error Handling
- Repository lookup methods often return `None` on invalid IDs or missing records, for example `ProjectRepository.get_by_id()` catches exceptions and returns `None` in `app/repositories/project_repository.py`.
- Service processors usually catch broad exceptions around a processing unit, print an error, mark `ProcessingState` as `failed` when applicable, and continue by returning a neutral value (`0`, `{}`, `[]`, or `False`). Examples include `app/services/risk_calculator/chunk_processor.py`, `risk_assessment_processor.py`, and `project_score_processor.py`.
- API routes use `HTTPException` for client-visible errors, notably 404s in `app/services/api/routers/risk.py` when a project, project score, or risk assessment is missing.
- Startup/initialization code raises or exits on unrecoverable failures: `app/core/database.py` re-raises database connection failures, `app/services/api/main.py` raises `RuntimeError` if database setup fails, and `scripts/init_db.py` calls `sys.exit(1)`.
- LLM code raises explicit initialization/query failures in `app/core/llm_service.py`, while higher-level risk-analysis functions catch per-item save/parse issues and continue processing.
- Container/test setup scripts in `scripts/test/test_setup.py` raise exceptions if a stage fails so Docker execution exits non-zero.

## Logging
- Logging is primarily done with `print()` rather than the standard `logging` module.
- Messages are human-readable and emoji-prefixed to show phase/status (`🚀`, `✅`, `❌`, `⚠️`, `⏭️`, `🧪`), as seen in `app/services/doc_parser/doc_parser.py`, `app/services/risk_calculator/risk_calculator.py`, and `scripts/init_db.py`.
- Long-running processors print clear phase boundaries and summaries, for example the six phases in `app/services/risk_calculator/risk_calculator.py`.
- Operational state is persisted separately through `ProcessingStateRepository` calls in risk-calculator processors, rather than relying solely on logs.
- LLM observability is centralized through Langfuse callback setup in `app/core/langfuse_tracer.py` and `app/core/llm_service.py`.

## Comments
- Comments are used sparingly but frequently explain domain intent, processing stages, or implementation trade-offs.
- Model classes in `app/core/models.py` have short comments describing domain purpose, for example `Project`, `Chunk`, `Evidence`, and `ProjectScore`.
- Complex/temporary workarounds are called out inline, such as Beanie Link filtering notes in `app/repositories/evidence_repository.py` and direct script path comments in service entrypoints.
- Docstrings are present for public utility functions and scripts, especially in `app/core/database.py`, `app/core/types.py`, `scripts/test/test_setup.py`, and scoring processors.
- Some comments document future enhancement options, such as alternative aggregation methods in `app/services/risk_calculator/risk_assessment_processor.py`.

## Function Design
- Functions are generally small-to-medium units named around a single workflow step: create chunks, save chunks, fetch project chunks, calculate score, or process one stage.
- Async is the default for database and service operations; repository methods, FastAPI handlers, and pipeline processors are `async def`.
- Pure helpers are synchronous when no I/O is needed, for example `create_text_chunks()` in `app/services/risk_calculator/chunk_processor.py` and `build_risk_analysis_prompt()` / `parse_llm_response()` in `app/services/risk_calculator/risk_analyzer.py`.
- Processing functions return simple primitives or domain dataclasses rather than raw Beanie models, respecting the repository/domain separation described in `CLAUDE.md`.
- Idempotency/resume behavior is handled by checking processing state before work and updating status before/after work in files such as `app/services/risk_calculator/chunk_processor.py`.
- Long orchestration functions are acceptable for entrypoints (`scheduled_task()` and `main()`), but domain work is delegated to processors/repositories.

## Module Design
- The codebase is layered by responsibility: persistence models in `app/core/models.py`, domain types in `app/core/types.py`, repositories in `app/repositories/`, API routers/schemas in `app/services/api/`, document parsing in `app/services/doc_parser/`, and risk calculation in `app/services/risk_calculator/`.
- Database access is intended to go through repository classes; repository files are the main places that import Beanie document models directly.
- API schemas are separated from domain/database models in `app/services/api/schemas/risk_schemas.py`.
- LLM integration is centralized in `app/core/llm_service.py`, with Langfuse tracing in `app/core/langfuse_tracer.py`; risk-analysis modules build prompts and parse responses but do not instantiate LLM clients directly.
- Configuration-driven risk data lives in `config/database/risk_dimensions.json` and `config/database/risk_types.json`, loaded by `app/core/data_loader.py` and `scripts/init_db.py`.
- Docker entrypoints and operational scripts live outside `app/` in `docker/`, `scripts/`, and the `justfile`.
