# AI-CPX: Carbon Project Risk Assessment Platform

## Project Overview
AI-CPX is a comprehensive system for risk calculation and analysis of carbon projects. The platform processes documents from various carbon projects, extracts relevant information using Large Language Models (LLMs), and calculates associated risks to help stakeholders make informed investment and development decisions.

The system transforms unstructured carbon project documentation into structured risk assessments through automated document processing, evidence extraction, and multi-dimensional risk scoring.

## Architecture & Data Flow
The system follows a microservices architecture with three core services that process data through distinct stages:

### Core Services
1. **Document Parser** - Monitors S3/MinIO for new documents, extracts text, identifies projects, creates structured records
2. **Risk Calculator** - Chunks documents, uses LLMs to find evidence, calculates risk scores and project summaries
3. **API Service** - FastAPI server providing RESTful access to calculated risks and project data

### Data Storage
- **MongoDB** - Primary database storing projects, documents, chunks, evidences, risk assessments, and scores
- **MinIO/S3** - Object storage for raw PDF documents and processed files
- **LangFuse** - LLM observability platform for tracing model interactions and performance

### Processing Pipeline
```
S3 Documents → Document Parser → Projects/Documents → Risk Calculator →
Chunks → Evidence Extraction (LLM) → Risk Assessments → Project Scores → API
```

## Configuration System
The system uses configuration-driven risk assessment through JSON files in `config/database/`:

- **risk_dimensions.json** - Defines scoring dimensions (e.g., additionality, permanence) with scales, weights, and mapping rules
- **risk_types.json** - Defines risk categories (e.g., technical, regulatory) that can be identified in projects
- These configurations are loaded during database initialization and drive the LLM evidence extraction and scoring processes

# Development Guidelines

## Architecture Patterns
- **Repository Pattern** - All database interactions must go through repository classes. Only repositories should interact with MongoDB models directly
- **Type-Driven Business Logic** - Use Python types for business logic. When creating new types, always provide conversion functions to/from database models
- **Schema Separation** - API endpoints use their own Pydantic schemas, separate from internal types and database models
- **LLM Centralization** - All LLM interactions must be handled in `llm_service.py` with Langfuse tracing via `langfuse_tracer.py`

## Code Style & Structure
- **Consistency First** - Always match the existing code style in the file/module you're working on
- **Minimal Comments** - Write self-documenting code. Only add comments when the logic is unavoidably complex
- **Import Organization** - All imports at the top of the file. No imports inside functions or classes
- **Dependency Management** - When adding dependencies, update `dependencies.txt`

## Data Layer Understanding
Understand the data flow stages when making changes:
1. **Raw Documents** (S3/MinIO) → PDF files uploaded by users
2. **Projects & Documents** (MongoDB) → Structured metadata extracted from PDFs
3. **Chunks** (MongoDB) → Documents split into smaller pieces for LLM processing
4. **Evidences** (MongoDB) → LLM-extracted evidence linked to risk types and dimensions
5. **Risk Assessments** (MongoDB) → Calculated risk scores based on evidence
6. **Project Scores** (MongoDB) → Aggregated project-level risk scores with summaries

<!--
# Autonomous Testing Strategy

## Testing Philosophy
Always test changes immediately after implementation. Use isolated test environments to avoid interfering with development containers. The system has distinct processing stages, and you should test at the appropriate stage for your changes.

## Processing Stages & Test Data Requirements
Understanding the processing pipeline helps determine what test data you need:

1. **Empty Database** → Fresh start with S3 files ready for processing
2. **Database Initialization** → Collections created, risk dimensions and types loaded from config files
3. **Document Processing** → Projects identified, documents parsed and stored in MongoDB
4. **Document Chunking** → Documents split into chunks for LLM processing
5. **Evidence Extraction** → LLMs analyze chunks, create evidence ratings and evidence records
6. **Risk Assessment** → Evidence aggregated into risk assessment scores
7. **Project Scoring** → Project-level scores calculated from risk assessments
8. **Summary Generation** → LLM-generated summaries added to project scores

## Test Data Stages
Use `test-setup` container with these commands to populate data up to different stages:
- `empty-db` → Clean slate
- `init-db` → Database schema + configurations
- `init-projects` → Projects are loaded
- `init-docs` → Documents are loaded
- `init-chunks` → Documents chunked and ready for evidence extraction
- `load-evidences` → Evidence extraction completed
- `load-risk-assessments` → Risk assessments calculated
- `load-project-scores` → Project scores calculated
- `load-project-score-summaries` → Complete pipeline with summaries

## Container Separation
**CRITICAL**: Never confuse development and test containers:
- **Development**: `mongodb`, `api`, `doc-parser`, `risk-calculator` → For manual use by developers
- **Testing**: `mongodb-test`, `api-test`, `doc-parser-test`, `risk-calculator-test`, `test-setup` → For automated testing only

All test containers use the `internal` network and can reuse the existing MinIO instance since it only serves static files.

## Debugging & Troubleshooting Tools

### Essential Commands for Testing
1. **Container Status**: `docker ps -a` → See all containers and their states
2. **Log Monitoring**: `docker logs <container-name>` → Check container output and errors
3. **Real-time Logs**: `docker logs -f <container-name>` → Follow logs in real-time
4. **MongoDB Shell**: Connect directly to test database to inspect data
5. **API Testing**: Use `curl` commands to test endpoints (test API typically runs on port 8002)
6. **Clean Environment**: Always stop and remove test containers before starting new tests

### MongoDB Inspection
Access the test MongoDB to verify data:
```bash
# Connect to test database using environment variables
source ./.env.test
mongosh "mongodb://${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest}:${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123}@localhost:27018/admin?authSource=admin"

# Switch to application database
use aicpx-test

# Common inspection queries
db.projects.countDocuments()
db.documents.countDocuments()
db.chunks.countDocuments()
db.evidences.countDocuments()
db.risk_assessments.countDocuments()
db.project_scores.countDocuments()

# Get actual IDs for API testing
db.projects.find({}, {_id: 1, name: 1}).limit(3)
db.risk_assessments.find({}, {_id: 1}).limit(3)
db.evidence_ratings.find({}, {_id: 1}).limit(3)
db.chunks.find({}, {_id: 1}).limit(3)
```

### API Testing Examples
**Important**: Always check the current FastAPI code for up-to-date endpoints. Look in the API router files to see available endpoints and their exact paths.

```bash
# Get all projects with total scores
curl -X 'GET' 'http://localhost:8002/projects'

# Get detailed project information (use actual project ID from database)
curl -X 'GET' 'http://localhost:8002/projects/{project_id}'
```

To find current endpoints and get real IDs for testing:
1. Check FastAPI router files in the codebase for available endpoints
2. Query MongoDB to get actual IDs:
   ```bash
   source ./.env.test
   mongosh "mongodb://${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest}:${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123}@localhost:27018/admin?authSource=admin"
   use aicpx-test
   ```
3. Use FastAPI's auto-generated docs: `http://localhost:8002/docs`

## Test Environment Setup

Assume the `.env.test` file exists (verify with `ls .env.test` if needed).

You can spin on a brand new MongoDB database for that prurpose using the following commands:
### Test Container Commands

#### MongoDB Test Database
```bash
# Create test database
source ./.env.test
docker run -d --name mongodb-test \
  --network internal \
  -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
  -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
  -p 27018:27017 \
  --rm \
  mongo:noble

# Monitor startup
docker logs mongodb-test

# Stop and cleanup
docker stop mongodb-test
```

#### API Test Service
```bash
# Build and run API test container
docker build -t api-test -f docker/Dockerfile.api .
docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test

# Monitor logs and test with curl
docker logs api-test
curl "http://localhost:8002/health"  # Test API is responding
```

#### Document Parser Test Service
```bash
docker build -t doc-parser-test -f docker/Dockerfile.api .
docker run -d --rm --name doc-parser-test -v $(pwd)/.env.test:/app/.env --network internal doc-parser-test \
  python -m app.services.doc_parser.doc_parser
docker logs doc-parser-test  # Monitor document processing
```

#### Risk Calculator Test Service
```bash
docker build -t risk-calculator-test -f docker/Dockerfile.api .
docker run -d --rm --name risk-calculator-test -v $(pwd)/.env.test:/app/.env --network internal risk-calculator-test \
  python -m app.services.risk_calculator.risk_calculator
docker logs risk-calculator-test  # Monitor LLM processing and scoring
```

### Test Data Population
Use `test-setup` container to populate database with test data:
```bash
# Build test setup container
docker build -t test-setup -f docker/Dockerfile.test-setup .

# Populate to specific stage (choose appropriate level for your test)
docker run --rm --network internal test-setup <stage>
```
**Available stages**: `empty-db`, `init-db`, `init-projects`, `init-docs`, `init-chunks`, `load-evidences`, `load-risk-assessments`, `load-project-scores`, `load-project-score-summaries`

# Testing Workflow Examples

## Example 1: Testing a New API Endpoint

**Scenario**: You've added a new API endpoint and need to test it end-to-end.

**Testing Strategy**: Since APIs serve processed data, you need the complete dataset including summaries.

### Step-by-Step Workflow:

1. **Clean Environment**
   ```bash
   # Check for existing test containers
   docker ps -a

   # Stop any running test containers
   docker stop mongodb-test api-test doc-parser-test risk-calculator-test 2>/dev/null || true
   ```

2. **Setup Test Database**
   ```bash
   # Create fresh test MongoDB
   source ./.env.test
   docker run -d --name mongodb-test \
     --network internal \
     -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
     -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
     -p 27018:27017 \
     --rm \
     mongo:noble

   # Verify database is ready
   docker logs mongodb-test
   ```

3. **Load Complete Test Dataset**
   ```bash
   # Build test setup with latest code
   docker build -t test-setup -f docker/Dockerfile.test-setup .

   # Load full dataset including summaries (needed for API testing)
   docker run --rm --network internal test-setup load-project-score-summaries
   ```

4. **Deploy and Test API**
   ```bash
   # Build and run API with your changes
   docker build -t api-test -f docker/Dockerfile.api .
   docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test

   # Test your new endpoint
   curl "http://localhost:8002/your-new-endpoint"

   # Compare API response with database data
   source ./.env.test
   mongosh "mongodb://${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest}:${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123}@localhost:27018/admin?authSource=admin"
   use aicpx-test
   ```

5. **Debug if Needed**
   ```bash
   # Check API logs for errors
   docker logs api-test

   # Rebuild and retry if needed
   docker stop api-test
   docker build -t api-test -f docker/Dockerfile.api .
   docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test
   ```

6. **Cleanup**
   ```bash
   docker stop api-test mongodb-test
   ```

## Example 2: Testing Evidence Extraction Changes

**Scenario**: You've modified the LLM evidence extraction logic in the risk calculator.

**Testing Strategy**: You need data up to chunks stage, then test evidence generation.

### Step-by-Step Workflow:

1. **Setup Environment**
   ```bash
   # Clean and create test database
   docker stop mongodb-test risk-calculator-test 2>/dev/null || true
   source ./.env.test
   docker run -d --name mongodb-test \
     --network internal \
     -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
     -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
     -p 27018:27017 \
     --rm \
     mongo:noble
   ```

2. **Load Prerequisites Only**
   ```bash
   # Load data up to chunks (but not existing evidence)
   docker build -t test-setup -f docker/Dockerfile.test-setup .
   docker run --rm --network internal test-setup init-chunks
   ```

3. **Test Evidence Generation**
   ```bash
   # Build risk calculator with your changes
   docker build -t risk-calculator-test -f docker/Dockerfile.api .
   docker run -d --rm --name risk-calculator-test -v $(pwd)/.env.test:/app/.env --network internal risk-calculator-test \
     python -m app.services.risk_calculator.risk_calculator

   # Monitor evidence extraction process
   docker logs -f risk-calculator-test
   ```

4. **Validate Results**
   ```bash
   # Check generated evidence in database
   source ./.env.test
   mongosh "mongodb://${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest}:${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123}@localhost:27018/admin?authSource=admin"
   use aicpx-test
   db.evidences.find().limit(5)
   db.evidence_ratings.find().limit(5)

   # Verify evidence quality and structure
   ```

5. **Cleanup**
   ```bash
   docker stop risk-calculator-test mongodb-test
   ```

## Example 3: Testing Document Parser Changes

**Scenario**: You've modified the document parsing logic.

**Testing Strategy**: Start fresh and test document ingestion from S3.

### Step-by-Step Workflow:

1. **Setup Clean Environment**
   ```bash
   docker stop mongodb-test doc-parser-test 2>/dev/null || true
   source ./.env.test
   docker run -d --name mongodb-test \
     --network internal \
     -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
     -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
     -p 27018:27017 \
     --rm \
     mongo:noble
   ```

2. **Initialize Database Only**
   ```bash
   docker build -t test-setup -f docker/Dockerfile.test-setup .
   docker run --rm --network internal test-setup init-db
   ```

3. **Test Document Processing**
   ```bash
   # Build and run document parser with your changes
   docker build -t doc-parser-test -f docker/Dockerfile.api .
   docker run -d --rm --name doc-parser-test -v $(pwd)/.env.test:/app/.env --network internal doc-parser-test \
     python -m app.services.doc_parser.doc_parser

   # Monitor document processing
   docker logs -f doc-parser-test
   ```

4. **Validate Results**
   ```bash
   # Check parsed projects and documents
   source ./.env.test
   mongosh "mongodb://${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest}:${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123}@localhost:27018/admin?authSource=admin"
   use aicpx-test
   db.projects.find()
   db.documents.find().limit(3)
   ```

5. **Cleanup**
   ```bash
   docker stop doc-parser-test mongodb-test
   ```
-->
