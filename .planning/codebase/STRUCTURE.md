# Codebase Structure
**Analysis Date:** 2026-07-10
## Directory Layout (tree)
```text
.
├── .env.example
├── .github/
├── .mise.toml
├── .planning/
│   └── codebase/
│       ├── ARCHITECTURE.md
│       └── STRUCTURE.md
├── .pre-commit-config.yaml
├── .python-version
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_loader.py
│   │   ├── database.py
│   │   ├── langfuse_tracer.py
│   │   ├── llm_service.py
│   │   ├── models.py
│   │   ├── s3_client.py
│   │   └── types.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── chunk_repository.py
│   │   ├── evidence_rating_repository.py
│   │   ├── evidence_repository.py
│   │   ├── processing_state_repository.py
│   │   ├── project_repository.py
│   │   ├── project_score_repository.py
│   │   ├── risk_assessment_repository.py
│   │   ├── risk_dimension_repository.py
│   │   ├── risk_type_repository.py
│   │   └── source_document_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config.py
│   │   │   │   └── risk.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       └── risk_schemas.py
│   │   ├── doc_parser/
│   │   │   ├── __init__.py
│   │   │   ├── doc_parser.py
│   │   │   └── pdf_parser.py
│   │   └── risk_calculator/
│   │       ├── __init__.py
│   │       ├── chunk_processor.py
│   │       ├── project_score_processor.py
│   │       ├── project_summary_processor.py
│   │       ├── risk_analyzer.py
│   │       ├── risk_assessment_processor.py
│   │       ├── risk_assessment_summary_processor.py
│   │       └── risk_calculator.py
│   └── utils/
│       └── prompts/
│           ├── risk_dimension_prompt
│           └── risk_type_prompt
├── CLAUDE.md
├── README.md
├── config/
│   ├── README.md
│   └── database/
│       ├── risk_dimensions.json
│       └── risk_types.json
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   └── Dockerfile.test-setup
├── justfile
├── pyproject.toml
├── scripts/
│   ├── __init__.py
│   ├── init_db.py
│   ├── README.md
│   └── test/
│       ├── data/
│       │   ├── chunks.json
│       │   ├── documents.json
│       │   ├── evidence_ratings.json
│       │   ├── evidences.json
│       │   ├── project_scores.json
│       │   ├── projects.json
│       │   └── risk_assessments.json
│       ├── test_data_loader.py
│       └── test_setup.py
└── uv.lock
```

## Directory Purposes
- `app/`: main Python package for shared core code, repositories, and all runtime services.
- `app/core/`: cross-service infrastructure, persistence models, business dataclasses, S3 access, database lifecycle, LLM access, Langfuse tracing, and config data loading.
- `app/repositories/`: repository pattern boundary around MongoDB/Beanie operations. Service code should prefer these classes over direct model access.
- `app/services/api/`: FastAPI application, routers, and response schemas for serving project scores, breakdowns, top evidence, methodology text, and config metadata.
- `app/services/doc_parser/`: S3 PDF ingestion worker. It discovers project folders, parses PDFs, and creates `Project` / `SourceDocument` records.
- `app/services/risk_calculator/`: scheduled processing worker split into phase-specific processors for chunking, LLM evidence extraction, scoring, and summaries.
- `app/utils/prompts/`: prompt reference files for risk dimensions and risk types. Current executable prompt construction primarily occurs in `app/services/risk_calculator/risk_analyzer.py` and summary processors.
- `config/database/`: JSON seed data for risk dimensions and risk types. This is the canonical editable place for default scoring taxonomy.
- `docker/`: container build and compose definitions. The same API image is reused with different commands for API, parser, calculator, and test setup.
- `scripts/`: operational scripts, especially database initialisation/status, plus staged test dataset loaders.
- `scripts/test/data/`: JSON fixtures representing pipeline stages (`projects`, `documents`, `chunks`, `evidences`, `risk_assessments`, `project_scores`, etc.).
- `.planning/codebase/`: generated planning/analysis documentation, including this architecture and structure report.

## Key File Locations
- Project guidance and architectural constraints: `CLAUDE.md`.
- Runtime overview and manual Docker commands: `README.md`.
- Python dependency and lint settings: `pyproject.toml`.
- Service composition: `docker/docker-compose.yml`.
- API Docker image: `docker/Dockerfile.api`.
- Test setup Docker image: `docker/Dockerfile.test-setup`.
- MongoDB/Beanie connection management: `app/core/database.py`.
- Persistence collection models: `app/core/models.py`.
- Internal business dataclasses and LLM response dataclasses: `app/core/types.py`.
- S3/MinIO helpers: `app/core/s3_client.py`.
- OpenAI/LangChain gateway: `app/core/llm_service.py`.
- Langfuse integration: `app/core/langfuse_tracer.py`.
- Config seed loading: `app/core/data_loader.py` and `scripts/init_db.py`.
- Risk type definitions: `config/database/risk_types.json`.
- Risk dimension/scoring definitions: `config/database/risk_dimensions.json`.
- Document parser entry point: `app/services/doc_parser/doc_parser.py`.
- PDF parser: `app/services/doc_parser/pdf_parser.py`.
- Risk calculator entry point: `app/services/risk_calculator/risk_calculator.py`.
- Chunking logic: `app/services/risk_calculator/chunk_processor.py`.
- Evidence extraction and LLM risk prompt logic: `app/services/risk_calculator/risk_analyzer.py`.
- Risk assessment aggregation: `app/services/risk_calculator/risk_assessment_processor.py`.
- Risk assessment summary generation: `app/services/risk_calculator/risk_assessment_summary_processor.py`.
- Project score aggregation: `app/services/risk_calculator/project_score_processor.py`.
- Project summary generation: `app/services/risk_calculator/project_summary_processor.py`.
- FastAPI app/lifespan/health: `app/services/api/main.py`.
- Risk API endpoints: `app/services/api/routers/risk.py`.
- Config API endpoints: `app/services/api/routers/config.py`.
- API response schemas: `app/services/api/schemas/risk_schemas.py`.
- Project repository: `app/repositories/project_repository.py`.
- Source document repository: `app/repositories/source_document_repository.py`.
- Chunk repository: `app/repositories/chunk_repository.py`.
- Evidence and rating repositories: `app/repositories/evidence_repository.py` and `app/repositories/evidence_rating_repository.py`.
- Risk assessment repository: `app/repositories/risk_assessment_repository.py`.
- Project score repository: `app/repositories/project_score_repository.py`.
- Processing state repository: `app/repositories/processing_state_repository.py`.

## Naming Conventions
- Python modules use `snake_case`, for example `risk_assessment_processor.py`, `project_score_repository.py`, and `source_document_repository.py`.
- Repository classes use singular domain names with `Repository` suffix, for example `ProjectRepository`, `ChunkRepository`, and `ProcessingStateRepository`.
- Beanie model classes use PascalCase domain names in `app/core/models.py`, for example `SourceDocument`, `RiskDimensionSpec`, and `ProjectScore`.
- Internal dataclass types in `app/core/types.py` generally mirror Beanie model names (`Project`, `Chunk`, `Evidence`) and expose `from_model()` / `to_model()` conversion methods where applicable.
- API schema classes use PascalCase response-oriented names, for example `ProjectSummary`, `TopEvidence`, `RiskBreakdownItem`, and `ProjectRiskBreakdown`.
- Processing stage identifiers are lower-case strings with underscores: `chunking`, `evidence_extraction`, `risk_assessment`, `risk_assessment_summary`, `project_scoring`, and `project_summary`.
- MongoDB collection names are lower-case plural snake_case, configured in model `Settings.name`, for example `projects`, `documents`, `risk_assessments`, and `processing_state`.
- Risk type config keys use snake_case strings in `config/database/risk_types.json`, for example `policy_regulatory`, `mrv_data_integrity`, and `finance_counterparty`.
- Risk dimension config keys use lower-case/hyphenated identifiers in `config/database/risk_dimensions.json`, for example `impact`, `certainty`, and `scope-extent`.
- Environment variables use upper-case snake case such as `MONGO_DATABASE`, `S3_BUCKET_NAME`, `OPENAI_MODEL`, and `DEV_MAX_PROJECTS`.

## Where to Add New Code
- **New MongoDB collection/entity**: add a Beanie `Document` to `app/core/models.py`, add a matching dataclass/conversion logic to `app/core/types.py`, include the model in service/database initialisation lists (`app/services/api/main.py`, `app/services/risk_calculator/risk_calculator.py`, `scripts/init_db.py`), then add a repository under `app/repositories/`.
- **New database query or mutation**: add it to the relevant repository in `app/repositories/`. Avoid scattering direct Beanie queries through services unless initialisation/config scripts require it.
- **New parser behaviour**: extend `app/services/doc_parser/doc_parser.py` for orchestration or `app/services/doc_parser/pdf_parser.py` for PDF-specific extraction.
- **New risk calculator pipeline phase**: add a focused processor module under `app/services/risk_calculator/`, wire it into `app/services/risk_calculator/risk_calculator.py`, and track idempotency through `ProcessingStateRepository` with a new stage name.
- **New evidence extraction prompt or parsing logic**: update `app/services/risk_calculator/risk_analyzer.py` and the LLM dataclasses in `app/core/types.py` if the response shape changes.
- **New LLM task**: add a method or helper around `LLMService` in `app/core/llm_service.py` or call `get_llm_service().query()` from a service processor with a clear `session_id`; keep Langfuse tracing centralised.
- **New API route**: add to `app/services/api/routers/risk.py` for risk/project data or `app/services/api/routers/config.py` for metadata/config, then add/adjust schemas in `app/services/api/schemas/risk_schemas.py`.
- **New API router category**: create a new file under `app/services/api/routers/`, import/include it in `app/services/api/main.py`, and add schemas under `app/services/api/schemas/`.
- **New scoring dimension or default risk category**: update `config/database/risk_dimensions.json` or `config/database/risk_types.json`, then run `scripts/init_db.py` to seed missing records.
- **New operational script**: place it in `scripts/`, following the existing pattern in `scripts/init_db.py` for project-root imports and async database lifecycle.
- **New staged fixture/test data**: add JSON fixture files under `scripts/test/data/` and loader support in `scripts/test/test_data_loader.py` / `scripts/test/test_setup.py`.

## Special Directories
- `.planning/codebase/`: analysis output directory requested for architecture/structure documentation. It is not part of runtime code.
- `.github/`: GitHub automation/configuration directory.
- `.venv/`, `.ruff_cache/`, and `uv.lock`: local environment, lint cache, and locked dependency state.
- `config/database/`: special because it is application data/configuration rather than Python source; changes here alter risk assessment semantics after database initialisation.
- `scripts/test/data/`: special because files are pipeline-stage snapshots used to seed test databases to known states.
- `docker/`: special because service roles are selected by container command; `api`, `docparser`, and `risk-calculator` use the same code/image but different entry points.
- `app/utils/prompts/`: prompt asset location; current code primarily builds prompts inline, so check both this directory and risk calculator processors before changing prompt behaviour.
