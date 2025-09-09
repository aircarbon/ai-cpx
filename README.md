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

- **MinIO/S3**: Object storage for handling raw documents, processed files, and any binary assets associated with carbon projects.

- **LangFuse**: Observability and tracing platform for Large Language Model (LLM) interactions, providing detailed insights into model performance, token usage, and request flows for debugging and optimization.

### Deployment Architecture
The three core services can be deployed independently or together using the provided Docker Compose configuration. MongoDB and MinIO are intentionally kept separate from the Docker Compose file to provide flexibility for different deployment environments - whether using managed cloud services (like MongoDB Atlas or AWS S3) or local instances. For development and testing purposes, commands are provided below to run MongoDB and MinIO locally.


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
4. Setup MinIO/S3 Storage: For document and file storage:
   - Cloud: Use AWS S3, Google Cloud Storage, or other S3-compatible service
   - Local: Run MinIO locally with Docker (see [MinIO setup command](#minio-s3-storage))
   
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
8. Build and run everything (MongoDB and MinIO not included): 
```bash
docker compose -f docker/docker-compose.yml up -d --build
```
9. To stop everything, run the following (MongoDB and MinIO not included):
```
docker compose -f docker/docker-compose.yml down
```

# Development

### Adding dependencies
When adding dependencies, don't forget to add them in `dependencies.txt` file.


## Running all services
To run all services (MongoDB and MinIO not included), you can use the same docker compose command as when running production.

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

### MinIO S3 storage
```bash
source ./.env
docker run -d --name minio \
  --network internal \
  -e MINIO_ROOT_USER=${S3_ROOT_USER:-minioadmin} \
  -e MINIO_ROOT_PASSWORD=${S3_ROOT_PASSWORD:-minioadmin} \
  -p ${MINIO_API_PORT:-9100}:9000 -p ${MINIO_CONSOLE_PORT:-9101}:9001 \
  -v minio-data:/data \
  quay.io/minio/minio server /data --console-address ":9001"
```

### FastAPI service
```bash
docker build -t api -f docker/Dockerfile.api .
docker run -d --name api -p 8001:8001 --network internal api
```

### Document parsing service
```bash
docker build -t doc-parser -f docker/Dockerfile.docparser .
docker run -d --name doc-parser --network internal doc-parser
```

### Risk calculation service
```bash
docker build -t risk-calculator -f docker/Dockerfile.risk-calculator .
docker run -d --name risk-calculator --network internal risk-calculator
```

# Testing
For testing purposes (mostly for claud to be able to spin on a quick testing environment to test and debug), you can setup temporary MongoDB and api, doc-parser and risk-calculation containers. They can stay in the `internal` network to be able to connect to MinIO bucket (the MinIO bucket can be reused because it just serves the files and is not affected by the code).

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
docker run -d --rm --name api-test -p 8001:8001 --network internal api-test
```

### Document parsing service
```bash
docker build -t doc-parser-test -f docker/Dockerfile.docparser .
docker run -d --rm --name doc-parser-test --network internal doc-parser-test
```

### Risk calculation service
```bash
docker build -t risk-calculator-test -f docker/Dockerfile.risk-calculator .
docker run -d --rm --name risk-calculator-test --network internal risk-calculator-test
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
```

So command would look something like this:
```bash
docker run --rm --network internal test-setup init-db
```