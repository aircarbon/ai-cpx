---
# Codebase Structure
**Analysis Date:** 2026-07-10
## Directory Layout (ascii tree)
```
aircarbon-ai-cpx/
├── app/                          # Main Python package (shared core + services)
│   ├── __init__.py
│   ├── core/                     # Shared infrastructure (used by all services)
│   │   ├── database.py           # Beanie/Mongo async connection + lifecycle
│   │   ├── models.py             # Beanie Document models (DB schema)
│   │   ├── types.py              # @dataclass business types + conversions
│   │   ├── llm_service.py        # Centralized LangChain LLM client
│   │   ├── langfuse_tracer.py    # LLM observability callbacks
│   │   ├── s3_client.py          # MinIO/S3 client wrappers
│   │   └── data_loader.py        # Load config JSON -> DB
│   ├── repositories/             # Repository pattern data-access layer
│   │   ├── project_repository.py
│   │   ├── source_document_repository.py
│   │   ├── chunk_repository.py
│   │   ├── risk_type_repository.py
│   │   ├── risk_dimension_repository.py
│   │   ├── evidence_rating_repository.py
│   │   ├── evidence_repository.py
│   │   ├── risk_assessment_repository.py
│   │   ├── project_score_repository.py
│   │   └── processing_state_repository.py
│   └── services/                 # Domain services / entry processes
│       ├── doc_parser/           # PDF ingestion service
│       │   ├── doc_parser.py     # Main loop + scheduler
│       │   └── pdf_parser.py     # pypdf extraction
│       ├── risk_calculator/      # Risk scoring pipeline
│       │   ├── risk_calculator.py# Orchestrator (6 phases)
│       │   ├── chunk_processor.py
│       │   ├── risk_analyzer.py  # LLM evidence extraction
│       │   ├── risk_assessment_processor.py
│       │   ├── risk_assessment_summary_processor.py
│       │   ├── project_score_processor.py
│       │   └── project_summary_processor.py
│       └── api/                  # FastAPI service
│           ├── main.py           # App factory + lifespan
│           ├── routers/          # API routes
│           │   ├── risk.py
│           │   └── config.py
│           └── schemas/          # Pydantic API schemas
│               └── risk_schemas.py
├── config/
│   ├── database/                 # Risk config JSON (loaded at init)
│   │   ├── risk_types.json
│   │   └── risk_dimensions.json
│   └── README.md
├── docker/                       # Container definitions
│   ├── docker-compose.yml        # api / docparser / risk-calculator
│   ├── Dockerfile.api
│   ├── Dockerfile.docparser
│   ├── Dockerfile.risk-calculator
│   ├── Dockerfile.db-init
│   └── Dockerfile.test-setup
├── scripts/                      # Bootstrap & test tooling
│   ├── init_db.py                # DB + config initialization
│   └── test/                     # Test fixtures & setup
│       ├── test_setup.py
│       ├── test_data_loader.py
│       └── data/
├── .planning/codebase/           # Generated analysis docs (this dir)
├── requirements.txt
├── .env.example
├── README.md
└── CLAUDE.md
```

## Directory Purposes
**app/core/:** / Shared foundation for every service / Contains DB connection, models, types, LLM, S3, data loader / Key files: `database.py`, `models.py`, `types.py`, `llm_service.py`, `s3_client.py`
**app/repositories/:** / Data-access layer / Contains one repository per MongoDB collection / Key files: `project_repository.py`, `evidence_repository.py`, `processing_state_repository.py`
**app/services/doc_parser/:** / S3->PDF->Document ingestion / Contains polling loop and PDF text extraction / Key files: `doc_parser.py`, `pdf_parser.py`
**app/services/risk_calculator/:** / Risk scoring pipeline / Contains orchestrator + per-phase processors / Key files: `risk_calculator.py`, `risk_analyzer.py`, `chunk_processor.py`
**app/services/api/:** / REST API / Contains FastAPI app, routers, Pydantic schemas / Key files: `main.py`, `routers/risk.py`, `schemas/risk_schemas.py`
**config/database/:** / Risk taxonomy config / Contains `risk_types.json`, `risk_dimensions.json` / Key files: both JSON files
**docker/:** / Deployment / Contains compose + per-service Dockerfiles / Key files: `docker-compose.yml`, `Dockerfile.api`
**scripts/:** / Tooling / Contains DB init and test data population / Key files: `init_db.py`, `test/test_setup.py`

## Key File Locations
**Entry Points:** `app/services/api/main.py` (API), `app/services/doc_parser/doc_parser.py` (parser), `app/services/risk_calculator/risk_calculator.py` (calculator), `scripts/init_db.py` (init)
**Configuration:** `config/database/risk_types.json`, `config/database/risk_dimensions.json`, `.env.example`, `requirements.txt`
**Core Logic:** `app/core/llm_service.py` (LLM), `app/core/models.py` (schema), `app/core/types.py` (types), `app/services/risk_calculator/risk_analyzer.py` (evidence), `app/services/risk_calculator/project_score_processor.py` (scoring)
**Testing:** `scripts/test/test_setup.py`, `scripts/test/test_data_loader.py`, `scripts/test/data/`, `docker/Dockerfile.test-setup`

## Naming Conventions
**Files:** Snake_case module names (`doc_parser.py`, `chunk_processor.py`, `risk_analyzer.py`). Repository files named `<entity>_repository.py` (`project_repository.py`). Routers named by domain (`risk.py`, `config.py`). Config files are `<entity>.json`.
**Directories:** Snake_case (`app/core`, `app/repositories`, `app/services`). Services live under `app/services/<service_name>/`.
**Classes:** `PascalCase` repository classes (`ProjectRepository`, `EvidenceRepository`); `PascalCase` Beanie models (`Project`, `SourceDocument`, `RiskAssessment`); `@dataclass` types mirror model names (`Project`, `Chunk`, `Evidence`); process classes named `<X>Processor` (`ChunkProcessor`/`chunk_processor.py`).
**Functions:** `snake_case` async coroutines; repository methods are `staticmethod` (`get_by_id`, `add_or_get_existing`, `is_completed`, `update_status`). Entity model/type pair share `from_model()`/`to_model()`.
**LLM types:** `LLM*`-prefixed dataclasses in `types.py` (`LLMEvidence`, `LLMRiskAnalysisResponse`).

## Where to Add New Code
**New Feature:** Add a router under `app/services/api/routers/` and register it in `app/services/api/main.py` (`main.py:74`); add corresponding Pydantic schema in `app/services/api/schemas/`. If it touches data, add a repository in `app/repositories/`.
**New Component/Module:** For a new background process, create `app/services/<name>/` with a `main()`-style entry and a `docker/Dockerfile.<name>` + compose entry. Reuse `app.core` and `app.repositories`.
**Utilities:** Shared helpers go in `app/core/` (e.g. `data_loader.py`, `s3_client.py`). Risk taxonomy changes go in `config/database/*.json` + `app/core/data_loader.py`, not code.

## Special Directories
**Directory:** `.planning/` / **Purpose:** Generated project analysis & planning docs / **Generated:** Yes (this doc set) / **Committed:** Yes (tracked in git)
**Directory:** `config/database/` / **Purpose:** Risk scoring configuration JSON / **Generated:** No (authored) / **Committed:** Yes (drives DB init)
**Directory:** `scripts/test/data/` / **Purpose:** Test fixture data for stage population / **Generated:** No / **Committed:** Yes
**Directory:** `.env` / **Purpose:** Runtime secrets/connection strings (`.env.example` is the template) / **Generated:** No / **Committed:** No (gitignored)
**Directory:** MongoDB collections / **Purpose:** Runtime state (`projects`, `documents`, `chunks`, `risk_types`, `risk_dimensions`, `evidence_ratings`, `evidences`, `risk_assessments`, `project_scores`, `processing_state`) / **Generated:** Yes at runtime / **Committed:** No
