<Description of the project and what is it's goal>
- The application is structured as modules, where each part runs in their own docker container
More Descriptiuon in the README.md file and in scripts/README.md file

# Some guidelines
- Keep the project in an existing style
- All interractions with the database from the application should be handled through the repository.
- Only the repository should Should interract with models
- For business logic, use types
- When making new types, make functions for conversion from and to models
- API uses their own schemas
- LLM related things should be handled in the llm_service.py file and should use Langfuse (in langfuse_tracer.py)


- When writing new code, avoid lengthy comments - good code should be intuitive enough to make comments redundant. Use comments only when absolutely necessary, avoid documentation types of comments (e.g. description of the parameters and return types)
- Put all imports in the same place - on top of the file. Avoid imports inside classes/functions.

# Autonomous testing
When developing a new feature or changing anything in the code, try to test it right away.
Here is an approximate workflow and project stages that will help you better understand how it should be tested:
1. A starting point: There is just an empty database and an S3 bucket with some files.
2. Database initialization: init_db.py is called to initialize the database - it initializes the right collections and imports some config data from config/database/risk_dimensions.json and config/database/risk_types.json
3. A docparser container is launched - it parses and improts PDF documents from an S3 bucket into a MongoDB database. during that process, it identifies project names and creates project records in the MongoDB, as well as documents linked to those project in the documents collection.
4. A risk-calculator contianer is launched. It does the following:
- Iterates through projects and documents, splits each document into chunks and saves them in the chunks collection in mongoDB
- Iterates for each chunk, for each risk type, uses Large Language Models to find evidences. Parses return data from the large language models and creates evidence ratings and evidences records in the MongoDB database.
- Uses those evidence ratings and evidence records to make calculations and create risk_assessments records and save in the mongo DB database.
- Uses the risk assessments records to calculate and create project_score records and save them in the MongoDB database
- Uses evidences to generate summaries for project_scores and update the project_score records in the MongoDB database

It is important that you don't confuse local development containers and MongoDB with the testing ones. Local MongoDB, api, doc-parser and risk-calculation containers are for others to use manually. While `mongodb-test`, `api-test`,`doc-parser-test`, `risk-calculator-test` and `test-setup` are purely for Claude code to autonomously orchestrate them and use them for testing it's code and changes in an isolated environment.

During the development, new features may affect the worflow. That's why there is a test environment that can be easily spinned on locally for testing purposes. You can setup temporary MongoDB and api, doc-parser and risk-calculation containers. They can stay in the `internal` network to be able to connect to MinIO bucket (the MinIO bucket can be reused because it just serves the files and is not affected by the code).

Assume tha the `.env.test` file is already created (or you can check it in advance if you want).

You can spin on a brand new MongoDB database for that prurpose using the following commands:
# MongoDB database:
To create new one:
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
To check logs:
```bash
docker logs mongodb-test
```
To stop and delete it:
```bash
docker stop mongodb-test
```

### FastAPI service
To create new one:
```bash
docker build -t api-test -f docker/Dockerfile.api .
docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test
```
To check logs:
```bash
docker logs api-test
```
To stop and delete it:
```bash
docker stop api-test
```

You can use curl commands to test API calls. For that, you can check what is the port of the api-test container.

### Document parsing service
```bash
docker build -t doc-parser-test -f docker/Dockerfile.docparser .
docker run -d --rm --name doc-parser-test -v $(pwd)/.env.test:/app/.env --network internal doc-parser-test
```
To check logs:
```bash
docker logs doc-parser-test
```
To stop and delete it:
```bash
docker stop doc-parser-test
```

### Risk calculation service
```bash
docker build -t risk-calculator-test -f docker/Dockerfile.risk-calculator .
docker run -d --rm --name risk-calculator-test -v $(pwd)/.env.test:/app/.env --network internal risk-calculator-test
```
To check logs:
```bash
docker logs risk-calculator-test
```
To stop and delete it:
```bash
docker stop risk-calculator-test
```


###
To better test it, you can use the `test-setup` container with different parameters to quickly setup testing envronment. You need to identify how much it should be set up and then to use the respective parameter.
# To run test setup: 

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
```

# Claude autonomous testing workflow examples
## Example 1
Imagine you were asked to create a new API endpoint. You made some changes in the router and maybe added new schemas. Now it can check if there is already running test environment. It can use `docker ps -a` command to see the running containers. If any of the `mongodb-test`, `api-test`,`doc-parser-test`, `risk-calculator-test` or `test-setup` containers are running, it can stop them to make things clean before testing anything. Then it can create a new MongoDB container using the following command (and use `.env.test` env file):
```
source ./.env.test
docker run -d --name mongodb-test \
  --network internal \
  -e MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME:-mongoadmintest} \
  -e MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD:-strongpassword123} \
  -p 27018:27017 \
  --rm \
  mongo:noble
```
It can even check the logs if it wants to double check that it was set up and running properly:
```bash
docker logs mongodb-test
```
Then, it can use the `test-setup` container to populate the database with the test data. Here it should think how much test data it needs. Since we are testing the API, which is the very end of the application stage (the application starts with the file processing, then risk calculation, then when evrything is ready, an API is used to serve all this data), we can use the latest stage of the test data - so we can use the `load-project-score-summaries` parameter. But also we will build the continer first, to have the most recent changes in the code:
```
docker build -t test-setup -f docker/Dockerfile.test-setup .
docker run --rm --network internal test-setup load-project-score-summaries
```

We can monitor the logs to make sure that everything is built and executed correctly. Once it's done, we can run our API container with this command:
```bash
docker build -t api-test -f docker/Dockerfile.api .
docker run -d --rm --name api-test -v $(pwd)/.env.test:/app/.env -p 8002:8001 --network internal api-test
```
Then we can test our new API endpoints with a customly generated curl request to localhost:8002 and check if it is responding an expected value. On top of that, we can query MongoDB directly to compare if the data returned from the APi matches the data that is stored in the MongoDB database. We cna use the MongoDB Shell cli tool for that.

Let's say we got some error. We can check logs of the docker container:
```bash
docker logs api-test
```
For example, we identified the issue, and rebuilt the API container and tested again and now everyhting works well.

Now, since everything is successful, we can clean up our testing environemnt.
We can run this command to stop and delete the api testing container:
```bash
docker stop api-test
```
And also to stop and delete the temporary testing MongoDB container:
```
docker stop mongodb-test
```
Great, the Claude added new endpoint in the API, and tested the end-to-end worflow by creating a temporary MongoDB database for testing, populated it with test data, created a temporary api container for testing, and made some curl calls to it to test it and maybe even compared the results with the data from the test mongodb database using mongo shell and maybe even debugged and made some changes by monitoring logs.


## Example 1
For exmaple, we want to change the way we identify evidences in a chunk. Claude can do the following steps:
Start with creating a new temporary MongoDB for testing.
Then preparing some test data. It identified that for those changes, we need data of projects and documents and chunks, but not the data of evidences, since those are the things that we want to test. For this, we should initilize test database up until the stage "init-chunks". So we will run the command:
```bash
docker run --rm --network internal test-setup init-chunks
```
And then we will build the risk-calculation container and monitor it's logs to see if everything is going as planned. On top of that, we can use MongoDB shell cli tool to query the test database directly and check if it generated evidences and evidence ratings as expected.
After everything is tested and works properly, we can clean up the testing environment by stoping and deleting the temporary MongoDB and risk-calculation container.