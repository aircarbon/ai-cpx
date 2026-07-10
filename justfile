# ─── AI CPX ───────────────────────────────────────────────────────────────────
# Modern Python project using uv for package management.
# See pyproject.toml for dependencies and ruff config.
# ───────────────────────────────────────────────────────────────────────────────

_default:
    @just --list

# ─── Setup ──────────────────────────────────────────────────────────────────

# Install production dependencies
install:
    uv sync --no-dev --frozen

# Install all dependencies including dev (ruff, jupyter)
install-dev:
    uv sync --frozen

# ─── Quality ────────────────────────────────────────────────────────────────

# Run ruff linter and formatter
lint:
    uv run ruff check . --fix
    uv run ruff format .

# Run prek hooks on all files
prek:
    prek run --all-files

# ─── Build ──────────────────────────────────────────────────────────────────

# Build canonical image (override image tag with TAG=...)
build tag="latest":
    docker buildx build --platform linux/amd64 \
        -f docker/Dockerfile.api \
        -t ghcr.io/aircarbon/ai-cpx:{{tag}} \
        .

# Build check (syntax validation, no push)
build-check:
    docker buildx build --check -f docker/Dockerfile.api .

# Build and push to GHCR (tag defaults to sha-<commit>)
push tag="sha-$(git rev-parse --short HEAD)":
    docker buildx build --platform linux/amd64 \
        -f docker/Dockerfile.api \
        -t ghcr.io/aircarbon/ai-cpx:{{tag}} \
        -t ghcr.io/aircarbon/ai-cpx:latest \
        --push .

# ─── Run (local) ────────────────────────────────────────────────────────────

# Start API server
api:
    uv run uvicorn app.services.api.main:app --host 0.0.0.0 --port 8001 --reload

# Run docparser once
docparser:
    uv run python -m app.services.doc_parser.doc_parser

# Run risk calculator once
risk-calc:
    uv run python -m app.services.risk_calculator.risk_calculator

# Run database init
db-init:
    uv run python scripts/init_db.py

# Check database status
db-status:
    uv run python scripts/init_db.py status

# ─── Test ───────────────────────────────────────────────────────────────────

# Build test setup image and populate to a given stage (default: init-projects)
test-setup stage="init-projects":
    docker build -t test-setup -f docker/Dockerfile.test-setup .
    docker run --rm --network internal test-setup {{stage}}

# ─── Cleanup ────────────────────────────────────────────────────────────────

# Remove uv virtual environment and caches
clean:
    rm -rf .venv/ .ruff_cache/
    uv cache clean
