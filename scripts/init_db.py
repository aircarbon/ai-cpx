import asyncio
import sys
import os

# Add path for app imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import ensure_database_connection, close_database, get_database_status
from app.core.data_loader import initialize_configuration_data
from app.core.models import (
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec,
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, ProcessingState
)

# Define all models used in the application
ALL_MODELS = [
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec,
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, ProcessingState
]


async def init_database():
    """Initialize the database connection and load configuration data."""
    
    print("🚀 Starting database initialization...")
    print("=" * 60)
    
    try:
        # Ensure database connection and initialize models
        print("📄 Connecting to database...")
        connection_success = await ensure_database_connection(ALL_MODELS)
        
        if not connection_success:
            print("❌ Failed to connect to database")
            sys.exit(1)
        
        print("✅ Database connection successful!")
        print("✅ Beanie models initialized successfully!")
        
        # Initialize database schema with configuration data
        print("\n🛠️  Initializing database schema...")
        print("   - Loading configuration data (risk types and dimensions)")
        
        config_results = await initialize_configuration_data()
        
        print(f"✅ Database schema initialized successfully!")
        print(f"   📊 Risk dimensions: {config_results['risk_dimensions']} loaded")
        print(f"   🎯 Risk types: {config_results['risk_types']} loaded")
        
        print("\n🎉 Database initialization completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        await close_database()


async def check_database_status():
    """Check the current status of the database and collections."""
    
    print("🔍 Checking database status...")
    print("=" * 60)
    
    try:
        # Ensure database connection
        connection_success = await ensure_database_connection(ALL_MODELS)
        
        if not connection_success:
            print("❌ Failed to connect to database")
            return
        
        print("✅ Database connection successful!")
        
        # Get database status
        status = await get_database_status()
        
        if not status.get("connected"):
            print(f"❌ Database status check failed: {status.get('error')}")
            return
        
        # List all collections
        collections = status.get("collections", [])
        print(f"📂 Collections found: {collections}")
        
        # Show collection counts
        collection_counts = status.get("collection_counts", {})
        expected_collections = [
            'projects', 'documents', 'chunks', 'risk_types', 'risk_dimensions',
            'evidence_ratings', 'evidences', 'risk_assessments',
            'project_scores', 'processing_state'
        ]
        
        for collection_name in collections:
            if collection_name in expected_collections:
                count = collection_counts.get(collection_name, 0)
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
        asyncio.run(init_database()) 