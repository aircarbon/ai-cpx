# Database Scripts

This folder contains scripts for database initialization and management. Make sure your `.env` file contains MongoDB variables.

## Scripts

### `init_db.py`

Database initialization script that sets up MongoDB connection, initializes Beanie with our models, and populates the database with configuration data from JSON files.

## Usage

The database scripts are executed from temporary Docker containers for isolation and consistency.

#### Initialize Database

```bash
# Build the database initialization container
docker build -t db-init -f docker/Dockerfile.db-init .

# Run database initialization
docker run --rm --network internal db-init
```

#### Check Database Status

```bash
# Check database status (shows collection counts and config data summary)
docker run --rm --network internal db-init status
```

## What it does

1. **Connects to MongoDB** using environment variables
2. **Initializes Beanie** with all models: `Project`, `SourceDocument`, `Chunk`, `RiskType`, `RiskDimensionSpec`, `EvidenceRating`, `Evidence`, `RiskAssessment`, `ProjectScore`, `CoverageLedger`
3. **Populates configuration data** from `config/database/`:
   - Loads 13 risk types from `risk_types.json`
   - Loads 6 risk dimensions from `risk_dimensions.json`
   - Skips existing entries to prevent duplicates
4. **Creates indexes** for efficient queries
5. **Tests the setup** by creating and deleting sample documents using real config data
6. **Provides detailed status checking** showing collection counts and configuration summary

## Configuration Dependencies

The initialization script depends on configuration files in `config/database/`:

- **`risk_types.json`**: Defines 13 carbon project risk types with descriptions and weights
- **`risk_dimensions.json`**: Defines 6 risk assessment dimensions (impact, certainty, scope, recency, evidence quality, controllability) with scales and mappings

These files must be present for successful database initialization.

## Future Migration Scripts

This structure allows for easy addition of migration scripts:

```
scripts/
├── __init__.py
├── init_db.py          # Initial setup
├── migration_001.py    # Future migration
├── migration_002.py    # Future migration
└── README.md
```

Each migration script can be run independently to update the database schema as needed. 