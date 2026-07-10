import os

from beanie import Document, init_beanie
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

# Load environment variables - check for mounted .env first, then default
if os.path.exists("/app/.env"):
    load_dotenv("/app/.env")
else:
    load_dotenv()

# Global state
_client: AsyncMongoClient | None = None
_database = None
_initialized_models: set = set()


def _get_connection_uri() -> str:
    """Build MongoDB connection URI from environment variables.

    Supports dedicated Mongo users via MONGO_AUTH_SOURCE. When set,
    ?authSource=<value> is appended to the URI so the driver authenticates
    against a different database than the one being accessed.
    """
    host = os.getenv("MONGO_HOST", "localhost")
    port = int(os.getenv("MONGO_PORT", "27017"))
    username = os.getenv("MONGO_INITDB_ROOT_USERNAME", "mongoadmin")
    password = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "strongpassword123")
    auth_source = os.getenv("MONGO_AUTH_SOURCE")

    if username and password:
        uri = f"mongodb://{username}:{password}@{host}:{port}"
    else:
        uri = f"mongodb://{host}:{port}"

    if auth_source:
        uri += f"?authSource={auth_source}"

    return uri


async def init_database(document_models: list[type[Document]] | None = None) -> AsyncMongoClient:
    global _client, _database

    # Connect if not already connected
    if _client is None:
        try:
            database_name = os.getenv("MONGO_DATABASE", "ai_cpx")
            _client = AsyncMongoClient(_get_connection_uri())

            # Test the connection
            await _client.admin.command("ping")
            _database = _client[database_name]
            print(f"🗄️  Database: Connected to {database_name}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    # Initialize models if provided
    if document_models:
        # Only initialize models that haven't been initialized yet
        new_models = [model for model in document_models if model.__name__ not in _initialized_models]

        if new_models:
            await init_beanie(database=_database, document_models=new_models)
            for model in new_models:
                _initialized_models.add(model.__name__)
            print(f"🗄️  Beanie: Initialized models {[m.__name__ for m in new_models]}")

    return _client


async def close_database():
    global _client, _database, _initialized_models

    if _client:
        await _client.close()
        _client = None
        _database = None
        _initialized_models.clear()
        print("🗄️  Database: Disconnected")


async def ensure_database_connection(
    document_models: list[type[Document]] | None = None, test_connection: bool = False
) -> bool:
    try:
        if _client is None:
            await init_database(document_models)
        else:
            # Initialize additional models if provided
            if document_models:
                new_models = [model for model in document_models if model.__name__ not in _initialized_models]
                if new_models:
                    await init_beanie(database=_database, document_models=new_models)
                    for model in new_models:
                        _initialized_models.add(model.__name__)

        # Test connection if requested
        if test_connection:
            await _client.admin.command("ping")

        return True

    except Exception as e:
        if test_connection:
            print(f"❌ Database connection test failed: {e}")
        return False


async def get_database_status() -> dict:
    try:
        # Ensure connection exists
        if not await ensure_database_connection():
            return {"connected": False, "error": "Could not establish connection"}

        collections = await _database.list_collection_names()
        status = {
            "connected": True,
            "database_name": _database.name,
            "collections": collections,
            "collection_counts": {},
        }

        # Get document counts for each collection
        for collection_name in collections:
            try:
                count = await _database[collection_name].count_documents({})
                status["collection_counts"][collection_name] = count
            except Exception:
                status["collection_counts"][collection_name] = "error"

        return status

    except Exception as e:
        return {"connected": False, "error": str(e)}


async def test_database_connection() -> bool:
    return await ensure_database_connection(test_connection=True)


# For backward compatibility with scripts/init_db.py
class _DatabaseManager:
    @property
    def database(self):
        return _database

    @property
    def client(self):
        return _client

    @property
    def initialized_models(self):
        return _initialized_models.copy()


db_manager = _DatabaseManager()
