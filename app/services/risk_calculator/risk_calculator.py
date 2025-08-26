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
from app.core.models import Project as ProjectModel, SourceDocument as SourceDocumentModel, Chunk as ChunkModel, RiskType as RiskTypeModel
from .chunk_processor import process_project_chunks
from .risk_analyzer import process_project_risk_analysis, get_all_risk_types

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
        
        # Process each project in two phases
        for project in projects:
            # Phase 1: Process documents into chunks
            print(f"\n{'='*50}")
            print(f"📋 PHASE 1: CHUNKING - {project.name}")
            print(f"{'='*50}")
            chunk_count = await process_project_chunks(project)
            
            # Phase 2: Analyze chunks for risks
            print(f"\n{'='*50}")
            print(f"🎯 PHASE 2: RISK ANALYSIS - {project.name}")
            print(f"{'='*50}")
            if chunk_count > 0:
                analyzed_count = await process_project_risk_analysis(project, risk_types)
                print(f"📊 Project '{project.name}': {chunk_count} chunks created, {analyzed_count} analyzed")
            else:
                print(f"⚠️  Skipping risk analysis for '{project.name}' - no chunks created")
        
        print("\n" + "="*60)
        print("✅ Risk calculation task completed successfully")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error in scheduled task: {str(e)}")

async def main():
    try:
        print("🔌 Initializing database connection...")
        await init_database([ProjectModel, SourceDocumentModel, ChunkModel, RiskTypeModel])
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