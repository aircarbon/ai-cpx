import asyncio
import sys

from utils import (
    connect_database, disconnect_database, initialize_database_schema, create_test_data
)
from app.core.models import (
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec
)


async def init_database_with_test():
    """Initialize the database connection and test with sample documents."""
    
    print("🚀 Starting database initialization...")
    print("=" * 60)
    
    try:
        # Initialize database with all models
        client = await connect_database()
        
        if not client:
            print("❌ Failed to connect to database")
            sys.exit(1)
        
        # Initialize database schema
        await disconnect_database()  # Close connection from connect_database()
        
        schema_success = await initialize_database_schema()
        if not schema_success:
            print("❌ Database schema initialization failed")
            sys.exit(1)
        
        # Create and test sample data
        test_success = await create_test_data()
        if not test_success:
            print("❌ Test data creation failed")
            sys.exit(1)
        
        
        print("\n🎉 Database initialization completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        # Database connections are handled by the utility functions
        pass


async def check_database_status():
    """Check the current status of the database and collections."""
    
    print("🔍 Checking database status...")
    print("=" * 60)
    
    try:
        # Initialize database connection
        client = await connect_database()
        
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
        await disconnect_database()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        asyncio.run(check_database_status())
    else:
        asyncio.run(init_database_with_test()) 