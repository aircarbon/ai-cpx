# Intro and architecture
This is a comprehensive system for risk calculation and analysis of carbon projects. The system processes documents from various carbon projects, extracts relevant information, and calculates associated risks to help stakeholders make informed decisions.

## Architecture

The system follows a microservices architecture with the following components:

### Core Services
- **Document Parser**: A worker service that monitors and processes documents from different carbon projects. It extracts structured information from various document formats and stores the processed data in the MongoDB database.

- **Risk Calculator**: A processing service that retrieves project information from the database, applies risk assessment algorithms, and calculates comprehensive risk scores and metrics for carbon projects.

- **API Service**: A FastAPI server that provides RESTful endpoints to serve calculated risks, project data, and other relevant information to end users and external applications.

### Data Storage
- **MongoDB**: The primary database for storing structured project data, extracted document information, calculated risk metrics, and system metadata.

- **SeaweedFS / S3**: Object storage for handling raw documents, processed files, and any binary assets associated with carbon projects.

- **LangFuse**: Observability and tracing platform for Large Language Model (LLM) interactions, providing detailed insights into model performance, token usage, and request flows for debugging and optimization.

### Deployment Architecture
The three core services can be deployed independently or together using the provided Docker Compose configuration. MongoDB and SeaweedFS are intentionally kept separate from the Docker Compose file to provide flexibility for different deployment environments - whether using managed cloud services (like MongoDB Atlas or AWS S3) or local instances. For development and testing purposes, commands are provided below to run MongoDB and SeaweedFS locally.


# PROD
### Get started
1. Install Docker
2. Clone the project:
```bash
git clone https://github.com/atesluks/ai-cpx
```
3. Create `.env` file from `.env.example` and fill required values.
```bash
cp .env.example .env
```
4. Setup S3-compatible Object Storage: For document and file storage:
   - Cloud: Use AWS S3, Google Cloud Storage, or other S3-compatible service
   - Local: Run SeaweedFS locally with Docker (see [SeaweedFS setup command](#seaweedfs-s3-compatible-object-storage))

   Add your storage credentials to the `.env` file.
5. Setup MongoDB Database: For data persistence:
   - Cloud: Use MongoDB Atlas or other managed MongoDB service
   - Local: Run MongoDB locally with Docker (see [MongoDB setup command](#mongodb-database))

   Add your database credentials to the `.env` file.
6. In the beginning (or when there are any changes in data models) you will need to initialize MongoDB database or migrate latest changes. Check [scripts/README.md](scripts/README.md) for more details.
7. Setup LangFuse (Optional but Recommended): For LLM observability and tracing:
   - Cloud: Add your LangFuse credentials to `.env` file (get them from [cloud.langfuse.com](https://cloud.langfuse.com))
   - Self-hosted: Clone and run locally with Docker: `git clone https://github.com/langfuse/langfuse && cd langfuse && docker compose up -d`
   - See [LangFuse self-hosting guide](https://langfuse.com/docs/deployment/self-host) for details

   The application will function without LangFuse, but you'll miss valuable LLM performance insights.
8. Build and run everything (MongoDB and SeaweedFS not included):
```bash
docker compose -f docker/docker-compose.yml up -d --build
```
9. To stop everything, run the following (MongoDB and SeaweedFS not included):
```
docker compose -f docker/docker-compose.yml down
```

# Development

### Adding dependencies
When adding dependencies, don't forget to add them in `dependencies.txt` file.


## Running all services
To run all services (MongoDB and SeaweedFS not included), you can use the same docker compose command as when running production.

## Run individual services

### If "internal" network is not yet created, create it:
```bash
docker network create internal
```

# MongoDB database:
```bash
source ./.env
docker run -d --name mongodb \
  --network internal \
  -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmin} \
  -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
  -p ${MONGO_PORT:-27017}:27017 \
  -v mongo-data:/data/db \
  --restart unless-stopped \
  mongo:noble
```

### SeaweedFS S3-compatible object storage
```bash
source ./.env
docker run -d --name seaweedfs \
  --network internal \
  -p ${S3_API_PORT:-8333}:8333 \
  -p 9333:9333 -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=${S3_ROOT_USER:-aicpx_s3_access} \
  -e AWS_SECRET_ACCESS_KEY=${S3_ROOT_PASSWORD:-change-me-strong-secret} \
  -v seaweedfs-data:/data \
  chrislusf/seaweedfs server -s3 -s3.port=8333 -volume.port=8080 -master.port=9333 -ip=seaweedfs
```


### FastAPI service
```bash
docker build -t api -f docker/Dockerfile.api .
docker run -d --name api -p 8001:8001 --network internal api
```

### Document parsing service
```bash
docker build -t doc-parser -f docker/Dockerfile.api .
docker run -d --name doc-parser --network internal doc-parser \
  python -m app.services.doc_parser.doc_parser
```

### Risk calculation service
```bash
docker build -t risk-calculator -f docker/Dockerfile.api .
docker run -d --name risk-calculator --network internal risk-calculator \
  python -m app.services.risk_calculator.risk_calculator
```

<!-- # Testing
For testing purposes (mostly for claud to be able to spin on a quick testing environment to test and debug), you can setup temporary MongoDB and api, doc-parser and risk-calculation containers. They can stay in the `internal` network to be able to connect to SeaweedFS bucket (the SeaweedFS bucket can be reused because it just serves the files and is not affected by the code).

Create `.env.test` file with different credentials than in the `.env` file to avoid confusion (especially ports).

# MongoDB database:
```bash
source ./.env.test
docker run -d --name mongodb-test \
  --network internal \
  -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
  -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
  -p 27018:27017 \
  --rm \
  mongo:noble
```

### FastAPI service
```bash
docker build -t api-test -f docker/Dockerfile.api .
docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test
```

### Document parsing service
```bash
docker build -t doc-parser-test -f docker/Dockerfile.api .
docker run -d --rm --name doc-parser-test -v $(pwd)/.env.test:/app/.env --network internal doc-parser-test \
  python -m app.services.doc_parser.doc_parser
```

### Risk calculation service
```bash
docker build -t risk-calculator-test -f docker/Dockerfile.api .
docker run -d --rm --name risk-calculator-test -v $(pwd)/.env.test:/app/.env --network internal risk-calculator-test \
  python -m app.services.risk_calculator.risk_calculator
```

To run test setup:

```bash
# Build the database initialization container
docker build -t test-setup -f docker/Dockerfile.test-setup .

# Run database initialization
docker run --rm --network internal test-setup
```

You can also run with the following commands:
```
empty-db
init-db
init-projects
init-docs
init-chunks
load-evidences
load-risk-assessments
load-project-scores
load-project-score-summaries
```

So command would look something like this:
```bash
docker run --rm --network internal test-setup init-chunks
``` -->
