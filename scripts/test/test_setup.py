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
from test_data_loader import load_test_projects, load_test_documents, load_test_chunks, load_test_evidence_ratings, load_test_evidences, load_test_risk_assessments, load_test_project_scores, load_test_project_score_summaries
from app.core.models import (
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec,
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, ProcessingState
)

# Define all models used in the application  
ALL_MODELS = [
    Project, SourceDocument, Chunk, RiskType, RiskDimensionSpec,
    EvidenceRating, Evidence, RiskAssessment, ProjectScore, ProcessingState
]




def empty_db():
    """Stage 1: Empty database setup - test connection only"""
    print("🗑️  Stage 1: Setting up empty database...")
    print("   - Testing database connection and basic operations")
    
    async def test_connection():
        try:
            print("🧪 Testing database connection...")
            test_success = await ensure_database_connection(test_connection=True)
            
            if test_success:
                print("✅ Database ping successful!")
                # Get basic status
                status = await get_database_status()
                collections = status.get("collections", [])
                print(f"📂 Available collections: {len(collections)}")
            
            return test_success
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async database connection test
    success = asyncio.run(test_connection())
    
    if success:
        print("   ✅ Database connection verified and ready")
    else:
        print("   ❌ Database connection failed")
        raise Exception("Database connection test failed")

def init_db():
    """Stage 2: Initialize database schema - same as main init_db.py"""
    print("🛠️  Stage 2: Initializing database schema...")
    print("   - Creating tables and loading configuration data")
    
    async def initialize_schema():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            print("✅ Beanie models initialized successfully!")
            
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
    
    # Run async database schema initialization
    success = asyncio.run(initialize_schema())
    
    if success:
        print("   ✅ Database schema initialized successfully")
    else:
        print("   ❌ Database schema initialization failed")
        raise Exception("Database schema initialization failed")

def init_projects():
    """Stage 3: Initialize projects - load test project data only"""
    print("📁 Stage 3: Initializing projects...")
    print("   - Loading test projects from JSON fixtures")
    
    async def load_projects():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            projects_count = await load_test_projects()
            
            print(f"✅ Test projects initialized successfully!")
            print(f"   📁 Projects: {projects_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test projects initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async test data loading
    success = asyncio.run(load_projects())
    
    if success:
        print("   ✅ Test projects initialized successfully")
    else:
        print("   ❌ Test projects initialization failed")
        raise Exception("Test projects initialization failed")

def init_docs():
    """Stage 4: Initialize documents - load test document data"""
    print("📚 Stage 4: Initializing documents...")
    print("   - Loading test documents from JSON fixtures")
    
    async def load_documents():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            documents_count = await load_test_documents()
            
            print(f"✅ Test documents initialized successfully!")
            print(f"   📄 Documents: {documents_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test documents initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async test data loading
    success = asyncio.run(load_documents())
    
    if success:
        print("   ✅ Test documents initialized successfully")
    else:
        print("   ❌ Test documents initialization failed")
        raise Exception("Test documents initialization failed")

def init_chunks():
    """Stage 5: Initialize chunks - load test chunk data"""
    print("🧩 Stage 5: Initializing data chunks...")
    print("   - Loading test chunks from JSON fixtures")
    
    async def load_chunks():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            chunks_count = await load_test_chunks()
            
            print(f"✅ Test chunks initialized successfully!")
            print(f"   🧩 Chunks: {chunks_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test chunks initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async test data loading
    success = asyncio.run(load_chunks())
    
    if success:
        print("   ✅ Test chunks initialized successfully")
    else:
        print("   ❌ Test chunks initialization failed")
        raise Exception("Test chunks initialization failed")

def load_evidences():
    """Stage 6: Load evidences - load test evidence ratings and evidences data"""
    print("🔍 Stage 6: Loading evidences...")
    print("   - Loading test evidence ratings and evidences from JSON fixtures")
    
    async def load_evidence_data():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            # Load evidence ratings first (they are referenced by evidences)
            ratings_count = await load_test_evidence_ratings()
            evidences_count = await load_test_evidences()
            
            print(f"✅ Test evidences initialized successfully!")
            print(f"   📊 Evidence ratings: {ratings_count} loaded")
            print(f"   🔍 Evidences: {evidences_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test evidences initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async evidence data loading
    success = asyncio.run(load_evidence_data())
    
    if success:
        print("   ✅ Test evidences initialized successfully")
    else:
        print("   ❌ Test evidences initialization failed")
        raise Exception("Test evidences initialization failed")

def load_risk_assessments():
    """Stage 7: Load risk assessments - load test risk assessments data"""
    print("📊 Stage 7: Loading risk assessments...")
    print("   - Loading test risk assessments from JSON fixtures")
    
    async def load_risk_assessment_data():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            # Load risk assessments
            assessments_count = await load_test_risk_assessments()
            
            print(f"✅ Test risk assessments initialized successfully!")
            print(f"   📊 Risk assessments: {assessments_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test risk assessments initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async risk assessment data loading
    success = asyncio.run(load_risk_assessment_data())
    
    if success:
        print("   ✅ Test risk assessments initialized successfully")
    else:
        print("   ❌ Test risk assessments initialization failed")
        raise Exception("Test risk assessments initialization failed")

def load_project_scores():
    """Stage 8: Load project scores - load test project scores data"""
    print("🏆 Stage 8: Loading project scores...")
    print("   - Loading test project scores from JSON fixtures")
    
    async def load_project_score_data():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            # Load project scores
            scores_count = await load_test_project_scores()
            
            print(f"✅ Test project scores initialized successfully!")
            print(f"   🏆 Project scores: {scores_count} loaded")
            
            return True
            
        except Exception as e:
            print(f"❌ Test project scores initialization failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async project score data loading
    success = asyncio.run(load_project_score_data())
    
    if success:
        print("   ✅ Test project scores initialized successfully")
    else:
        print("   ❌ Test project scores initialization failed")
        raise Exception("Test project scores initialization failed")

def load_project_score_summaries():
    """Stage 9: Load project score summaries - update summary fields in existing project scores"""
    print("📝 Stage 9: Loading project score summaries...")
    print("   - Updating summary fields in existing project scores from JSON fixtures")
    
    async def load_project_score_summary_data():
        try:
            connection_success = await ensure_database_connection(ALL_MODELS)
            if not connection_success:
                print("❌ Failed to connect to database")
                return False
            
            print("✅ Database connection successful!")
            
            # Load project score summaries
            updated_count = await load_test_project_score_summaries()
            
            print(f"✅ Test project score summaries updated successfully!")
            print(f"   📝 Project score summaries: {updated_count} updated")
            
            return True
            
        except Exception as e:
            print(f"❌ Test project score summaries update failed: {e}")
            return False
        
        finally:
            await close_database()
    
    # Run async project score summary data loading
    success = asyncio.run(load_project_score_summary_data())
    
    if success:
        print("   ✅ Test project score summaries updated successfully")
    else:
        print("   ❌ Test project score summaries update failed")
        raise Exception("Test project score summaries update failed")

def run_stages_up_to(target_stage):
    """Run all stages up to and including the target stage"""
    stages = [
        ("empty-db", empty_db, "🗑️  Stage 1: Setting up empty database..."),
        ("init-db", init_db, "🛠️  Stage 2: Initializing database schema..."),
        ("init-projects", init_projects, "📁 Stage 3: Loading test projects..."),
        ("init-docs", init_docs, "📚 Stage 4: Loading test documents..."),
        ("init-chunks", init_chunks, "🧩 Stage 5: Loading test chunks..."),
        ("load-evidences", load_evidences, "🔍 Stage 6: Loading test evidences..."),
        ("load-risk-assessments", load_risk_assessments, "📊 Stage 7: Loading test risk assessments..."),
        ("load-project-scores", load_project_scores, "🏆 Stage 8: Loading test project scores..."),
        ("load-project-score-summaries", load_project_score_summaries, "📝 Stage 9: Loading test project score summaries...")
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
        choices=["empty-db", "init-db", "init-projects", "init-docs", "init-chunks", "load-evidences", "load-risk-assessments", "load-project-scores", "load-project-score-summaries", "all"],
        help="Initialization stage to run (default: all)"
    )
    
    args = parser.parse_args()
    
    print("Test setup container is running...")
    print(f"Executing up to stage: {args.stage}\n")
    
    run_stages_up_to(args.stage)

if __name__ == "__main__":
    main()