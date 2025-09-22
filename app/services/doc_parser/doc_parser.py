import sys
import os
import asyncio
from typing import Dict, List, Any

from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import shared infrastructure from core
sys.path.append(os.path.abspath(os.path.join('..', '..', '..')))
from app.core.database import init_database, close_database
from app.core.models import Project, SourceDocument
from app.core.types import Project as ProjectType, SourceDocument as SourceDocumentType
from app.core.s3_client import (
    list_pdf_files_by_folder,
    generate_document_url,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from .pdf_parser import parse_pdf

# Constants
CHECKING_INTERVAL_MINUTES = 10 # Running every N minutes

def count_total_pdfs(folder_files: Dict[str, List[Dict[str, Any]]]) -> int:
    return sum(len(files) for files in folder_files.values())

async def process_project(folder_name: str, files: List[Dict[str, Any]]) -> ProjectType:
    project_data = ProjectType(
        name=folder_name,
        folder_path=folder_name
    )
    
    # Check if project exists and save
    is_new_project = not await ProjectRepository.is_existing(folder_name)
    saved_project = await ProjectRepository.add_or_get_existing(project_data)
    
    # Print project info - more concise
    status = "new" if is_new_project else "existing"
    print(f"📁 {folder_name}: {len(files)} files ({status})")
    
    return saved_project

async def process_documents_for_project(project: ProjectType, files: List[Dict[str, Any]]) -> tuple[int, int]:
    total_processed = 0
    new_documents = 0
    skipped_existing = 0
    
    for file_info in files:
        file_name = file_info['filename']
        is_new_document = not await SourceDocumentRepository.is_existing(file_name)
        
        if not is_new_document:
            total_processed += 1
            skipped_existing += 1
            continue
        
        # Parse PDF content
        parsing_result = parse_pdf(file_info['key'])
        
        # Determine success and content based on parsing result
        success = parsing_result['success']
        content = parsing_result['text'] if parsing_result['success'] else ""
        error = parsing_result['error'] if not parsing_result['success'] else None
        page_count = parsing_result['page_count']
        metadata = parsing_result['metadata'] or {}

        document_url = generate_document_url(project.name, file_name)

        document_data = SourceDocumentType(
            project_id=project.id,
            file_name=file_name,
            source_type="pdf",
            source_path=file_info['key'],
            title=file_name,
            content=content,
            success=success,
            error=error,
            file_size=file_info['size'],
            page_count=page_count,
            document_url=document_url,
            metadata=metadata
        )
        
        saved_document = await SourceDocumentRepository.add_or_get_existing(document_data)
        
        # Concise status logging
        if success:
            print(f"   ✅ {file_name} ({page_count}p)")
        else:
            print(f"   ❌ {file_name}: {error}")
        
        total_processed += 1
        new_documents += 1
    
    # Show batch summary for this project if there were documents to process
    if new_documents > 0 or skipped_existing > 0:
        summary_parts = []
        if new_documents > 0:
            summary_parts.append(f"{new_documents} processed")
        if skipped_existing > 0:
            summary_parts.append(f"{skipped_existing} skipped")
        print(f"   📊 {', '.join(summary_parts)}")
    
    return total_processed, new_documents

def print_sample_files(files: List[Dict[str, Any]], max_show: int = 2):
    for file_info in files[:max_show]:
        size_mb = file_info['size'] / (1024 * 1024)
        print(f"   └── {file_info['filename']} ({size_mb:.1f}MB)")
    if len(files) > max_show:
        print(f"   └── (+{len(files) - max_show} more)")

async def scheduled_task() -> None:
    print("=" * 50)
    print("🚀 PDF PARSING TASK")
    print("=" * 50)
    
    try:
        folder_files = list_pdf_files_by_folder()
        
        if not folder_files:
            print("📭 No PDF files found")
            return
        
        # Calculate totals
        total_folders = len(folder_files)
        total_pdfs = count_total_pdfs(folder_files)
        
        print(f"📊 Found: {total_folders} folders, {total_pdfs} PDFs")
        print()
        
        total_projects = 0
        total_documents_processed = 0
        total_new_documents = 0
        
        for folder_name, files in folder_files.items():
            # Process project and documents
            project = await process_project(folder_name, files)
            total_projects += 1
            
            # Show sample files
            print_sample_files(files)
            
            # Process documents for this project
            processed, new_docs = await process_documents_for_project(project, files)
            total_documents_processed += processed
            total_new_documents += new_docs
            print()
        
        print(f"✅ Summary: {total_projects} projects, {total_new_documents} new docs, {total_documents_processed - total_new_documents} existing")
        
    except Exception as e:
        print(f"❌ ERROR PROCESSING PDF FILES: {e}")

async def main():
    # Initialize database connection
    print("🚀 Initializing database...")
    mongo_client = await init_database([Project, SourceDocument])
    if not mongo_client:
        print("❌ Database initialization failed")
        return
    print("✅ Database connected")
    
    try:
        # Run the task once immediately
        await scheduled_task()

        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduled_task, IntervalTrigger(minutes=CHECKING_INTERVAL_MINUTES))

        print(f"⏰ Scheduler started (every {CHECKING_INTERVAL_MINUTES}min)")
        scheduler.start()
        # Keep the script running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Shutting down...")
        scheduler.shutdown()
    finally:
        # Close database connection on shutdown
        await close_database()
        print("🗄️ Database closed")

if __name__ == "__main__":
    asyncio.run(main())