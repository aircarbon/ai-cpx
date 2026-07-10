import asyncio
import os
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Import shared infrastructure from core
sys.path.append(os.path.abspath(os.path.join("..", "..", "..")))
from app.core.database import close_database, init_database
from app.core.models import Chunk as ChunkModel
from app.core.models import Evidence as EvidenceModel
from app.core.models import EvidenceRating as EvidenceRatingModel
from app.core.models import ProcessingState as ProcessingStateModel
from app.core.models import Project as ProjectModel
from app.core.models import ProjectScore as ProjectScoreModel
from app.core.models import RiskAssessment as RiskAssessmentModel
from app.core.models import RiskDimensionSpec as RiskDimensionSpecModel
from app.core.models import RiskType as RiskTypeModel
from app.core.models import SourceDocument as SourceDocumentModel
from app.core.types import Project
from app.repositories.project_repository import ProjectRepository

from .chunk_processor import process_project_chunks
from .project_score_processor import process_project_total_score
from .project_summary_processor import process_project_summary_generation
from .risk_analyzer import get_all_risk_types, process_project_risk_analysis
from .risk_assessment_processor import process_project_risk_assessments
from .risk_assessment_summary_processor import process_project_risk_assessment_summaries

# Load environment variables from .env file
load_dotenv()

# Constants
CHECKING_INTERVAL_HOURS = 24  # Running every N hours


async def get_all_projects() -> list[Project]:
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

        # Apply DEV mode project limits
        total_projects = len(projects)
        if os.getenv("APP_MODE") == "DEV":
            max_projects = int(os.getenv("DEV_MAX_PROJECTS", "999"))
            if max_projects < total_projects:
                # Sort projects deterministically by name for consistent selection across resumes
                projects = sorted(projects, key=lambda p: p.name)[:max_projects]
                print(
                    f"🧪 DEV MODE: Processing {len(projects)} of {total_projects} projects "
                    f"(limited by DEV_MAX_PROJECTS={max_projects})"
                )
                print(f"    Selected projects: {', '.join([p.name for p in projects])}")

        # Load risk types once (cache for performance)
        print("🎯 Loading risk types...")
        risk_types = await get_all_risk_types()
        if not risk_types:
            print("⚠️  No risk types found in database")
            return
        print(f"⚡ Loaded {len(risk_types)} risk types")

        # Process each project in six phases with granular skip logic
        for i, project in enumerate(projects):
            print(f"\n🔄 Processing project {i + 1}/{len(projects)}: {project.name}")

            # STEP 1: Process chunking
            print("  📋 Phase 1: Chunking")
            chunk_count = await process_project_chunks(project)
            print(f"  ✅ Chunks processed: {chunk_count}")

            # STEP 2: Process evidence extraction
            print("  📊 Phase 2: Evidence extraction")
            processed_evidences = await process_project_risk_analysis(project, risk_types, i + 1, len(projects))
            print(f"  ✅ Evidence combinations processed: {processed_evidences}")

            # STEP 3: Process risk assessments
            print("  📊 Phase 3: Risk assessment calculation")
            risk_scores = await process_project_risk_assessments(project, risk_types)
            print(f"  ✅ Risk assessments processed: {len(risk_scores)}")

            # STEP 4: Process risk assessment summaries
            print("  📝 Phase 4: Risk assessment summary generation")
            summary_count = await process_project_risk_assessment_summaries(project, risk_types)
            print(f"  ✅ Risk assessment summaries processed: {summary_count}")

            # STEP 5: Process total project score
            print("  🏆 Phase 5: Project score calculation")
            total_score = await process_project_total_score(project)
            print(f"  ✅ Project score calculated: {total_score:.3f}")

            # STEP 6: Process project summary generation
            print("  📝 Phase 6: Project summary generation")
            summary_success = await process_project_summary_generation(project)
            print(f"  ✅ Project summary {'generated' if summary_success else 'failed'}")

        print("\n✅ Risk calculation completed successfully")
        print("🔚 TEMPORARY: Exiting after one run for testing")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Error in scheduled task: {str(e)}")


async def main():
    try:
        print("🔌 Initializing database connection...")
        models = [
            ProjectModel,
            SourceDocumentModel,
            ChunkModel,
            RiskTypeModel,
            RiskDimensionSpecModel,
            EvidenceRatingModel,
            EvidenceModel,
            RiskAssessmentModel,
            ProjectScoreModel,
            ProcessingStateModel,
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
