from typing import List
import sys

from app.core.types import Project, Chunk, RiskType
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.core.llm_service import get_llm_service, simple_llm_test


async def get_all_risk_types() -> List[RiskType]:
    """Load all risk types from database. Cache this result to avoid repeated queries."""
    try:
        risk_types = await RiskTypeRepository.get_all()
        return risk_types
    except Exception as e:
        print(f"❌ Error fetching risk types: {str(e)}")
        return []


async def get_project_chunks(project: Project) -> List[Chunk]:
    """Get all chunks for a project by getting chunks from all its documents."""
    try:
        # First, get all documents for this project
        documents = await SourceDocumentRepository.get_by_project(project.id)
        
        if not documents:
            return []
        
        # Then, get all chunks for each document
        all_chunks = []
        for document in documents:
            chunks = await ChunkRepository.get_chunks_by_document(document.id)
            all_chunks.extend(chunks)
        
        return all_chunks
    except Exception as e:
        print(f"❌ Error fetching chunks for project '{project.name}': {str(e)}")
        return []


async def analyze_chunk_for_risk_type(chunk: Chunk, risk_type: RiskType) -> None:
    """Analyze a single chunk for a specific risk type."""
    print(f"    🔍 Analyzing chunk {chunk.chunk_index} for risk type: {risk_type.risk_type}")
    
    try:
        # For now, let's test with a simple query
        if chunk.chunk_index == 0 and risk_type.risk_type:  # Only test on first chunk/risk combo
            print(f"    🤖 Testing LLM with simple query...")
            llm_service = get_llm_service()
            response = await simple_llm_test()
            print(f"    💬 LLM Response: {response}")
            print(response)
            
            # TODO: Later implement actual risk analysis:
            # response = await llm_service.analyze_risk(
            #     chunk_content=chunk.content,
            #     risk_type=risk_type.risk_type,
            #     risk_description=risk_type.description
            # )
            # TODO: Save evidence/assessment to database
        else:
            print(f"    ⏩ Skipping LLM call for this chunk/risk (testing only first)")
            
    except Exception as e:
        print(f"    ❌ Error in LLM analysis: {str(e)}")

    # Debug: Exit after first chunk
    print(f"\n🛑 DEBUG: Exiting after analyzing first chunk (chunk {chunk.chunk_index})")
    sys.exit()


async def analyze_chunk_for_all_risks(chunk: Chunk, risk_types: List[RiskType]) -> None:
    """Analyze a single chunk against all risk types."""
    for risk_type in risk_types:
        await analyze_chunk_for_risk_type(chunk, risk_type)


async def process_project_risk_analysis(project: Project, risk_types: List[RiskType]) -> int:
    """Process risk analysis for all chunks in a project. Returns number of chunks analyzed."""
    print(f"\n🎯 Analyzing risks for project: {project.name}")
    
    try:
        # Get all chunks for this project
        chunks = await get_project_chunks(project)
        
        if not chunks:
            print(f"⚠️  No chunks found for project '{project.name}'")
            return 0
        
        print(f"📝 Found {len(chunks)} chunks to analyze")
        print(f"⚡ Will analyze against {len(risk_types)} risk types")
        
        # Process each chunk against all risk types
        analyzed_count = 0
        for chunk in chunks:
            print(f"  📊 Analyzing chunk {chunk.chunk_index + 1}/{len(chunks)}")
            await analyze_chunk_for_all_risks(chunk, risk_types)
            analyzed_count += 1
        
        print(f"✅ Completed risk analysis for {analyzed_count} chunks in project '{project.name}'")
        return analyzed_count
        
    except Exception as e:
        print(f"❌ Error in risk analysis for project '{project.name}': {str(e)}")
        return 0
