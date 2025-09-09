"""
Shared utility functions for all scripts in the ai-cpx project.
Contains common database connection, configuration loading, and other shared operations.
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path for proper imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import init_database, close_database
from app.core.models import (
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec, 
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
)

# Define all models used in the application
ALL_MODELS = [
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec, 
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
]

def load_config_file(filename: str) -> dict:
    """Load a JSON configuration file from the config/database directory."""
    config_path = Path(__file__).parent.parent / "config" / "database" / filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as file:
        return json.load(file)

async def connect_database():
    """
    Connect to the database and initialize Beanie models.
    Returns the database client if successful, None otherwise.
    """
    print("📄 Connecting to database...")
    
    try:
        client = await init_database(ALL_MODELS)
        
        if not client:
            print("❌ Failed to connect to database")
            return None
        
        print("✅ Database connection successful!")
        print("✅ Beanie models initialized successfully!")
        return client
        
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return None

async def disconnect_database():
    """
    Close the database connection.
    """
    try:
        await close_database()
        print("🔌 Database connection closed")
    except Exception as e:
        print(f"⚠️  Error closing database connection: {e}")

async def test_database_connection():
    """
    Test basic database connectivity by connecting and disconnecting.
    Returns True if successful, False otherwise.
    """
    print("🧪 Testing database connection...")
    
    client = await connect_database()
    if not client:
        return False
    
    # Test basic database operations
    try:
        from app.core.database import db_manager
        database = db_manager.database
        
        # Simple ping test
        await database.command("ping")
        print("✅ Database ping successful!")
        
        # List collections to verify access
        collections = await database.list_collection_names()
        print(f"📂 Available collections: {len(collections)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    finally:
        await disconnect_database()

async def populate_risk_dimensions():
    """Populate the database with risk dimensions from config."""
    print("📊 Loading risk dimensions from config...")
    
    try:
        config_data = load_config_file("risk_dimensions.json")
        dimensions = config_data.get("dimensions", [])
        
        created_count = 0
        for dimension_data in dimensions:
            # Check if dimension already exists
            existing = await RiskDimensionSpec.find_one(RiskDimensionSpec.key == dimension_data["key"])
            if existing:
                print(f"   ⚠️  Risk dimension '{dimension_data['key']}' already exists, skipping...")
                continue
            
            # Create new risk dimension
            risk_dimension = RiskDimensionSpec(**dimension_data)
            await risk_dimension.insert()
            created_count += 1
            print(f"   ✅ Created risk dimension: {dimension_data['key']}")
        
        print(f"📊 Risk dimensions loaded: {created_count} created, {len(dimensions) - created_count} already existed")
        return created_count
        
    except Exception as e:
        print(f"❌ Error loading risk dimensions: {e}")
        raise

async def populate_risk_types():
    """Populate the database with risk types from config."""
    print("🎯 Loading risk types from config...")
    
    try:
        config_data = load_config_file("risk_types.json")
        risks = config_data.get("risks", [])
        
        created_count = 0
        for risk_data in risks:
            # Check if risk type already exists
            existing = await RiskType.find_one(RiskType.risk_type == risk_data["risk_type"])
            if existing:
                print(f"   ⚠️  Risk type '{risk_data['risk_type']}' already exists, skipping...")
                continue
            
            # Create new risk type
            risk_type = RiskType(**risk_data)
            await risk_type.insert()
            created_count += 1
            print(f"   ✅ Created risk type: {risk_data['risk_type']}")
        
        print(f"🎯 Risk types loaded: {created_count} created, {len(risks) - created_count} already existed")
        return created_count
        
    except Exception as e:
        print(f"❌ Error loading risk types: {e}")
        raise

async def initialize_database_schema():
    """
    Initialize database schema by connecting and loading configuration data.
    Returns True if successful, False otherwise.
    """
    print("🛠️  Initializing database schema...")
    
    try:
        # Connect to database
        client = await connect_database()
        if not client:
            print("❌ Failed to connect to database")
            return False
        
        # Load configuration data
        print("🔧 Loading configuration data...")
        risk_dims_count = await populate_risk_dimensions()
        risk_types_count = await populate_risk_types()
        
        print(f"✅ Database schema initialized successfully!")
        print(f"   📊 Risk dimensions: {risk_dims_count} loaded")
        print(f"   🎯 Risk types: {risk_types_count} loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Database schema initialization failed: {e}")
        return False
    
    finally:
        await disconnect_database()

async def create_test_data():
    """
    Create test data for validation, then clean it up.
    Returns True if successful, False otherwise.
    """
    print("🧪 Creating test data for validation...")
    
    try:
        # Connect to database
        client = await connect_database()
        if not client:
            print("❌ Failed to connect to database")
            return False
        
        # Create a test project
        test_project = Project(
            name="test_project",
            folder_path="test_folder/"
        )
        await test_project.insert()
        print("✅ Sample project created successfully!")
        
        # Get existing risk type and dimension for testing
        test_risk_type = await RiskType.find_one()
        test_dimension = await RiskDimensionSpec.find_one()
        
        should_cleanup_test_config = False
        if not test_risk_type or not test_dimension:
            print("⚠️  No risk types or dimensions found - creating fallback test data")
            # Create minimal test data if config loading failed
            test_risk_type = RiskType(
                risk_type="TestRisk",
                description="A fallback test risk type",
                weight=1.0
            )
            await test_risk_type.insert()
            
            test_dimension = RiskDimensionSpec(
                key="test_dimension",
                label="Test Dimension", 
                description="A fallback test dimension",
                rationale="Testing purposes",
                guidance="Rate based on test criteria",
                higher_is_riskier=True,
                scale=["low", "medium", "high"],
                mapping={"low": 1.0, "medium": 2.0, "high": 3.0},
                weight=1.0
            )
            await test_dimension.insert()
            should_cleanup_test_config = True
        else:
            print(f"✅ Using existing risk type '{test_risk_type.risk_type}' and dimension '{test_dimension.key}' for testing")
        
        # Create a test source document
        test_document = SourceDocument(
            project_id=test_project.id,
            file_name="test.pdf",
            source_type="file",
            source_path="test_folder/test.pdf",
            title="Test Document",
            content="This is a test document content for validation.",
            success=True,
            file_size=1024,
            page_count=1,
            metadata={"author": "Test Author"}
        )
        await test_document.insert()
        print("✅ Sample source document created successfully!")
        
        # Create a test chunk
        test_chunk = Chunk(
            document_id=test_document.id,
            chunk_index=0,
            page_from=1,
            page_to=1,
            content="This is a test chunk content.",
            size_characters=30
        )
        await test_chunk.insert()
        print("✅ Sample chunk created successfully!")
        
        # Clean up test data
        await test_chunk.delete()
        await test_document.delete()
        
        # Only clean up risk type and dimension if we created them as fallbacks
        if should_cleanup_test_config:
            await test_dimension.delete()
            await test_risk_type.delete()
            print("✅ Fallback test config data cleaned up!")
        
        await test_project.delete()
        print("✅ Test data cleaned up!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test data creation failed: {e}")
        return False
    
    finally:
        await disconnect_database()