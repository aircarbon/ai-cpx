import sys
import os
from typing import List
from dotenv import load_dotenv
import asyncio

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import shared infrastructure from core
sys.path.append(os.path.abspath(os.path.join('..', '..', '..')))
from app.core.database import init_database, close_database
from app.core.types import Project
from app.repositories.project_repository import ProjectRepository
from app.core.models import (
    Project as ProjectModel, SourceDocument as SourceDocumentModel,
    Chunk as ChunkModel, RiskType as RiskTypeModel, RiskDimensionSpec as RiskDimensionSpecModel,
    EvidenceRating as EvidenceRatingModel, Evidence as EvidenceModel,
    RiskAssessment as RiskAssessmentModel, ProjectScore as ProjectScoreModel,
    ProcessingState as ProcessingStateModel
)
from .chunk_processor import process_project_chunks
from .risk_analyzer import process_project_risk_analysis, get_all_risk_types
from .risk_assessment_processor import process_project_risk_assessments
from .project_score_processor import process_project_total_score

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
        
        # Process each project in four phases with granular skip logic
        for i, project in enumerate(projects):
            print(f"\n🔄 Processing project {i+1}/{len(projects)}: {project.name}")

            # STEP 1: Process chunking
            print(f"  📋 Phase 1: Chunking")
            chunk_count = await process_project_chunks(project)
            print(f"  ✅ Chunks processed: {chunk_count}")

            # STEP 2: Process evidence extraction
            print(f"  📊 Phase 2: Evidence extraction")
            processed_evidences = await process_project_risk_analysis(project, risk_types, i+1, len(projects))
            print(f"  ✅ Evidence combinations processed: {processed_evidences}")
            
            # STEP 3: Process risk assessments
            print(f"  📊 Phase 3: Risk assessment calculation")
            risk_scores = await process_project_risk_assessments(project, risk_types)
            print(f"  ✅ Risk assessments processed: {len(risk_scores)}")

            # STEP 4: Process total project score
            print(f"  🏆 Phase 4: Project score calculation")
            total_score = await process_project_total_score(project)
            print(f"  ✅ Project score calculated: {total_score:.3f}")
        
        print("\n✅ Risk calculation completed successfully")
        
    except Exception as e:
        print(f"❌ Error in scheduled task: {str(e)}")

async def main():
    try:
        print("🔌 Initializing database connection...")
        models = [
            ProjectModel, SourceDocumentModel, ChunkModel, RiskTypeModel,
            RiskDimensionSpecModel, EvidenceRatingModel, EvidenceModel,
            RiskAssessmentModel, ProjectScoreModel, ProcessingStateModel
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