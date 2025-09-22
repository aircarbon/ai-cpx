import sys
import os
from datetime import datetime, UTC
from typing import Optional, List
import requests
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
import asyncio
import random

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import shared infrastructure from core
sys.path.append(os.path.abspath(os.path.join('..', '..', '..')))
from app.core.database import init_database, close_database
from app.core.types import Project, RiskType
from app.repositories.project_repository import ProjectRepository
from app.core.models import (
    Project as ProjectModel, SourceDocument as SourceDocumentModel, 
    Chunk as ChunkModel, RiskType as RiskTypeModel, RiskDimensionSpec as RiskDimensionSpecModel,
    EvidenceRating as EvidenceRatingModel, Evidence as EvidenceModel, 
    RiskAssessment as RiskAssessmentModel, ProjectScore as ProjectScoreModel,
    CoverageLedger as CoverageLedgerModel
)
from .chunk_processor import process_project_chunks
from .risk_analyzer import process_project_risk_analysis, get_all_risk_types
from .risk_assessment_processor import process_project_risk_assessments, get_project_evidence_summary
from .project_score_processor import process_project_total_score
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository

# Load environment variables from .env file
load_dotenv()

# Constants
CHECKING_INTERVAL_HOURS = 24 # Running every N hours


async def get_all_projects() -> List[Project]:
    try:
        projects = await ProjectRepository.get_all()
        print(f"📂 Found {len(projects)} projects to process")
        return projects
    except Exception as e:
        print(f"❌ Error fetching projects: {str(e)}")
        return []

async def scheduled_task() -> None:
    print("=" * 60)
    print("🚀 STARTING RISK CALCULATION TASK")
    print("=" * 60)
    
    try:
        # Get all projects
        projects = await get_all_projects()
        if not projects:
            print("⚠️  No projects found to process")
            return
        
        # Load risk types once (cache for performance)
        print("🎯 Loading risk types...")
        risk_types = await get_all_risk_types()
        if not risk_types:
            print("⚠️  No risk types found in database")
            return
        print(f"⚡ Loaded {len(risk_types)} risk types")
        
        # Check application mode for processing behavior
        app_mode = os.getenv('APP_MODE', 'DEV').upper()
        
        if app_mode == 'DEV':
            print(f"🔧 DEV MODE: Processing all {len(projects)} projects with chunk limits per project")
        else:
            print(f"🚀 PROD MODE: Processing all {len(projects)} projects without limits")
        
        # Process each project in three phases with granular skip logic
        for i, project in enumerate(projects):
            print(f"\n{'='*80}")
            print(f"🔄 PROCESSING PROJECT {i+1}/{len(projects)}: {project.name}")
            print(f"{'='*80}")
            
            # STEP 1: Check if chunks exist - if yes, skip chunking
            has_chunks = await ChunkRepository.project_has_chunks(project.id)
            if has_chunks:
                print(f"\n{'='*50}")
                print(f"✅ PHASE 1 SKIPPED: CHUNKING - {project.name}")
                print(f"{'='*50}")
                print(f"⏩ Project already has chunks - skipping chunking phase")
            else:
                print(f"\n{'='*50}")
                print(f"📋 PHASE 1: CHUNKING - {project.name}")
                print(f"{'='*50}")
                chunk_count = await process_project_chunks(project)
                print(f"📝 Created {chunk_count} chunks for project")
            
            # STEP 2: Check if evidences exist - if yes, skip evidence extraction
            has_evidences = await EvidenceRepository.project_has_evidences(project.id)
            if has_evidences:
                print(f"\n{'='*50}")
                print(f"✅ PHASE 2 SKIPPED: EVIDENCE EXTRACTION - {project.name}")
                print(f"{'='*50}")
                print(f"⏩ Project already has evidences - skipping evidence extraction phase")
            else:
                print(f"\n{'='*50}")
                print(f"🎯 PHASE 2: EVIDENCE EXTRACTION - {project.name}")
                print(f"{'='*50}")
                
                # Process all chunks for all risk types
                processed_evidences = await process_project_risk_analysis(project, risk_types)
                print(f"📈 Total evidences processed: {processed_evidences}")
            
            # STEP 3: Process risk assessments - skip if ANY risk assessments exist
            print(f"\n{'='*50}")
            print(f"📊 PHASE 3: RISK ASSESSMENT CALCULATION - {project.name}")
            print(f"{'='*50}")
            
            # Check if project has any risk assessments
            has_risk_assessments = await RiskAssessmentRepository.project_has_risk_assessments(project.id)
            if has_risk_assessments:
                print(f"✅ PHASE 3 SKIPPED: RISK ASSESSMENT CALCULATION - {project.name}")
                print(f"⏩ Project already has risk assessments - skipping risk assessment calculation")
                
                # Still display summary for existing assessments
                evidence_summary = await get_project_evidence_summary(project)
                existing_risk_assessments = await RiskAssessmentRepository.get_by_project(project.id)
                print(f"📊 Found {len(existing_risk_assessments)} existing risk assessments")
                
                # Create risk_scores dict for display
                risk_scores = {}
                for assessment in existing_risk_assessments:
                    # Get risk type name - we'll need to look this up
                    pass  # We'll display the count instead of names for now
                
            else:
                # Get evidence summary first
                evidence_summary = await get_project_evidence_summary(project)
                total_evidences = sum(evidence_summary.values())
                
                if total_evidences > 0:
                    # Process risk assessments
                    risk_scores = await process_project_risk_assessments(project)
                    print(f"📈 Processed {len(risk_scores)} risk assessment scores")
                    
                    # Display summary
                    print(f"📋 Risk Assessment Summary:")
                    # Sort with null scores at the end
                    sorted_scores = sorted(risk_scores.items(), key=lambda x: (x[1] is None, x[1] or 0), reverse=True)
                    for risk_type_name, score in sorted_scores:
                        evidence_count = evidence_summary.get(risk_type_name, 0)
                        if score is None:
                            print(f"  • {risk_type_name}: null (no evidences)")
                        else:
                            print(f"  • {risk_type_name}: {score:.3f} (based on {evidence_count} evidences)")
                else:
                    print(f"⚠️  No evidences found for project '{project.name}' - skipping risk assessment calculation")
            
            # STEP 4: Process total project score - skip if project score exists
            print(f"\n{'='*50}")
            print(f"🏆 PHASE 4: TOTAL PROJECT SCORE CALCULATION - {project.name}")
            print(f"{'='*50}")
            
            # Check if project already has a total score
            has_project_score = await ProjectScoreRepository.project_has_score(project.id)
            if has_project_score:
                print(f"✅ PHASE 4 SKIPPED: PROJECT SCORE CALCULATION - {project.name}")
                print(f"⏩ Project already has total score - skipping total score calculation")
                existing_score = await ProjectScoreRepository.get_by_project(project.id)
                print(f"📊 Existing total project score: {existing_score.total_score:.3f}")
            else:
                # Check if we have risk assessments to calculate from
                has_risk_assessments = await RiskAssessmentRepository.project_has_risk_assessments(project.id)
                if has_risk_assessments:
                    # Process total project score
                    project_score_result = await process_project_total_score(project)
                    total_score = project_score_result.get("total_score", 0.0)
                    print(f"🏆 Final project score: {total_score:.3f}")
                else:
                    print(f"⚠️  No risk assessments found for project '{project.name}' - cannot calculate total score")
        
        print("\n" + "="*60)
        print("✅ Risk calculation task completed successfully")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error in scheduled task: {str(e)}")

async def main():
    try:
        print("🔌 Initializing database connection...")
        models = [
            ProjectModel, SourceDocumentModel, ChunkModel, RiskTypeModel, 
            RiskDimensionSpecModel, EvidenceRatingModel, EvidenceModel, 
            RiskAssessmentModel, ProjectScoreModel, CoverageLedgerModel
        ]
        await init_database(models)
        print("✅ Database connection established")
        
        await scheduled_task()

        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduled_task, IntervalTrigger(hours=CHECKING_INTERVAL_HOURS))
        
        try:
            scheduler.start()
            # Keep the script running
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            print("\n🛑 Shutting down scheduler...")
            scheduler.shutdown()
            
    except Exception as e:
        print(f"❌ Error in main function: {str(e)}")
    finally:
        print("🔌 Closing database connection...")
        await close_database()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())