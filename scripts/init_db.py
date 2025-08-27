import asyncio
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

def load_config_file(filename: str) -> dict:
    """Load a JSON configuration file from the config/database directory."""
    config_path = Path(__file__).parent.parent / "config" / "database" / filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as file:
        return json.load(file)

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

async def init_database_with_test():
    """Initialize the database connection and test with sample documents."""
    
    print("🚀 Starting database initialization...")
    print("=" * 60)
    
    try:
        # Initialize database with all models
        print("📄 Connecting to database...")
        models = [
            Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec, 
            EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
        ]
        client = await init_database(models)
        
        if not client:
            print("❌ Failed to connect to database")
            sys.exit(1)
        
        print("✅ Database connection successful!")
        print("✅ Beanie models initialized successfully!")
        
        # Populate database with configuration data
        print("\n🔧 Populating database with configuration data...")
        await populate_risk_dimensions()
        await populate_risk_types()
        print("✅ Configuration data loaded successfully!")
        
        # Test creating sample data with the new model structure
        print("\n🧪 Testing database operations...")
        
        # Create a test project
        test_project = Project(
            name="test_project",
            folder_path="test_folder/"
        )
        await test_project.insert()
        print("✅ Sample project created successfully!")
        
        # Get an existing risk type and dimension for testing (from the config data)
        test_risk_type = await RiskType.find_one()
        test_dimension = await RiskDimensionSpec.find_one()
        
        if not test_risk_type or not test_dimension:
            print("⚠️  No risk types or dimensions found for testing - using fallback test data")
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
            should_cleanup_test_config = False
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
        
        print("\n🎉 Database initialization completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Close database connection
        await close_database()
        print("🔌 Database connection closed")


async def check_database_status():
    """Check the current status of the database and collections."""
    
    print("🔍 Checking database status...")
    print("=" * 60)
    
    try:
        # Initialize database connection
        models = [
            Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec, 
            EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
        ]
        client = await init_database(models)
        
        if not client:
            print("❌ Failed to connect to database")
            return
        
        # Get database instance
        from app.core.database import db_manager
        database = db_manager.database
        
        # List all collections
        collections = await database.list_collection_names()
        print(f"📂 Collections found: {collections}")
        
        # Check document counts for new collections
        expected_collections = [
            'projects', 'documents', 'chunks', 'risk_types', 'risk_dimensions',
            'evidence_ratings', 'evidences', 'risk_assessments', 
            'project_scores', 'coverage_ledger'
        ]
        for collection_name in collections:
            if collection_name in expected_collections:
                count = await database[collection_name].count_documents({})
                print(f"   📄 {collection_name}: {count} documents")
        
        # Show detailed configuration data
        print("\n📊 Configuration Data Summary:")
        risk_types_count = await RiskType.count()
        risk_dimensions_count = await RiskDimensionSpec.count()
        print(f"   🎯 Risk Types: {risk_types_count}")
        print(f"   📊 Risk Dimensions: {risk_dimensions_count}")
        
        if risk_types_count > 0:
            print("   📝 Risk Types loaded:")
            async for risk_type in RiskType.find().limit(5):
                print(f"      • {risk_type.risk_type} (weight: {risk_type.weight})")
            if risk_types_count > 5:
                print(f"      ... and {risk_types_count - 5} more")
        
        if risk_dimensions_count > 0:
            print("   📏 Risk Dimensions loaded:")
            async for dimension in RiskDimensionSpec.find().limit(3):
                print(f"      • {dimension.key}: {dimension.label} (weight: {dimension.weight})")
            if risk_dimensions_count > 3:
                print(f"      ... and {risk_dimensions_count - 3} more")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error checking database status: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await close_database()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        asyncio.run(check_database_status())
    else:
        asyncio.run(init_database_with_test()) 