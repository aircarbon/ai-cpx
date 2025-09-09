#!/usr/bin/env python3
"""
Test setup script for isolated test environment.
This script handles different stages of data preparation.
"""

import argparse
import asyncio
import sys
import os

# Add path to access app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.core.database import ensure_database_connection, close_database, get_database_status
from app.core.data_loader import initialize_configuration_data
from app.core.models import (
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec,
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
)

# Define all models used in the application
ALL_MODELS = [
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec, 
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, CoverageLedger
]


async def test_database_connection():
    """Test basic database connectivity by connecting and disconnecting."""
    print("🧪 Testing database connection...")
    
    try:
        # Use consolidated function: ensure connection with models + test connectivity
        test_success = await ensure_database_connection(ALL_MODELS, test_connection=True)
        
        if test_success:
            # Get additional status information for verbose output
            status = await get_database_status()
            collections = status.get("collections", [])
            print("✅ Database ping successful!")
            print(f"📂 Available collections: {len(collections)}")
        
        return test_success
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False
    
    finally:
        await close_database()


async def initialize_database_schema():
    """Initialize database schema by connecting and loading configuration data."""
    print("🛠️  Initializing database schema...")
    
    try:
        # Connect to database
        connection_success = await ensure_database_connection(ALL_MODELS)
        if not connection_success:
            print("❌ Failed to connect to database")
            return False
        
        print("✅ Database connection successful!")
        print("✅ Beanie models initialized successfully!")
        
        # Load configuration data using shared data loader
        config_results = await initialize_configuration_data()
        
        print(f"✅ Database schema initialized successfully!")
        print(f"   📊 Risk dimensions: {config_results['risk_dimensions']} loaded")
        print(f"   🎯 Risk types: {config_results['risk_types']} loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Database schema initialization failed: {e}")
        return False
    
    finally:
        await close_database()


def empty_db():
    """Stage 1: Empty database setup"""
    print("🗑️  Stage 1: Setting up empty database...")
    print("   - Testing database connection and basic operations")
    
    # Debug: Check which .env file is being used
    env_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            first_line = f.readline().strip()
            print(f"   🔍 Using .env file: {first_line}")
    else:
        print("   ⚠️  No .env file found")
    
    # Run async database connection test
    success = asyncio.run(test_database_connection())
    
    if success:
        print("   ✅ Database connection verified and ready")
    else:
        print("   ❌ Database connection failed")
        raise Exception("Database connection test failed")

def init_db():
    """Stage 2: Initialize database schema"""
    print("🛠️  Stage 2: Initializing database schema...")
    print("   - Creating tables and loading configuration data")
    
    # Run async database schema initialization
    success = asyncio.run(initialize_database_schema())
    
    if success:
        print("   ✅ Database schema initialized successfully")
    else:
        print("   ❌ Database schema initialization failed")
        raise Exception("Database schema initialization failed")

def init_projects():
    """Stage 3: Initialize projects"""
    print("📁 Stage 3: Initializing projects...")
    print("   - Setting up project configurations and templates")

def init_docs():
    """Stage 4: Initialize documentation"""
    print("📚 Stage 4: Initializing documentation...")
    print("   - Loading documentation and reference materials")

def init_chunks():
    """Stage 5: Initialize data chunks"""
    print("🧩 Stage 5: Initializing data chunks...")
    print("   - Processing and organizing data chunks")

def run_stages_up_to(target_stage):
    """Run all stages up to and including the target stage"""
    stages = [
        ("empty-db", empty_db, "🗑️  Stage 1: Setting up empty database..."),
        ("init-db", init_db, "🛠️  Stage 2: Initializing database schema..."),
        ("init-projects", init_projects, "📁 Stage 3: Initializing projects..."),
        ("init-docs", init_docs, "📚 Stage 4: Initializing documentation..."),
        ("init-chunks", init_chunks, "🧩 Stage 5: Initializing data chunks...")
    ]
    
    if target_stage == "all":
        print("🚀 Running all initialization stages in sequence...\n")
        target_index = len(stages)
    else:
        stage_names = [stage[0] for stage in stages]
        target_index = stage_names.index(target_stage) + 1
        print(f"🚀 Running stages up to '{target_stage}'...\n")
    
    for i in range(target_index):
        _, stage_func, _ = stages[i]
        stage_func()
        if i < target_index - 1:
            print()  # Add spacing between stages
    
    print(f"\n✅ Completed stages up to '{target_stage}' successfully!")

def main():
    parser = argparse.ArgumentParser(
        description="Test environment setup with multiple initialization stages"
    )
    parser.add_argument(
        "stage",
        nargs="?",  # Make argument optional
        default="all",  # Default value when no argument provided
        choices=["empty-db", "init-db", "init-projects", "init-docs", "init-chunks", "all"],
        help="Initialization stage to run (default: all)"
    )
    
    args = parser.parse_args()
    
    print("Test setup container is running...")
    print(f"Executing up to stage: {args.stage}\n")
    
    run_stages_up_to(args.stage)

if __name__ == "__main__":
    main()