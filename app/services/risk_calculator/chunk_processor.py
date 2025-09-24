import os
from typing import List

from app.core.types import Project, SourceDocument, Chunk
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.processing_state_repository import ProcessingStateRepository

# Sliding window parameters
CHUNK_SIZE = 10000  # Size of each chunk in characters
OVERLAP_SIZE = 500  # Overlap between chunks in characters
MIN_CHUNK_SIZE = 2000  # Minimum chunk size to process


def create_text_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap_size: int = OVERLAP_SIZE) -> List[str]:
    if not text:
        return []
    
    if len(text) < MIN_CHUNK_SIZE:
        return [text]
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        
        # Only add chunk if it meets minimum size requirement
        if len(chunk) >= MIN_CHUNK_SIZE or start == 0:
            chunks.append(chunk.strip())
        
        # Calculate next start position with overlap
        start += chunk_size - overlap_size
        
        # Break if we would create a tiny chunk at the end
        if start >= text_length:
            break
    
    return chunks


async def save_chunks_to_database(document_id: str, chunk_texts: List[str]) -> List[Chunk]:
    if not chunk_texts:
        return []
    
    chunks = []
    for i, chunk_text in enumerate(chunk_texts):
        chunk = Chunk(
            document_id=document_id,
            chunk_index=i,
            content=chunk_text,
            size_characters=len(chunk_text)
        )
        chunks.append(chunk)
    
    saved_chunks = await ChunkRepository.save_chunks_bulk(chunks)
    return saved_chunks


async def get_project_documents(project: Project) -> List[SourceDocument]:
    try:
        documents = await SourceDocumentRepository.get_by_project(project.id)
        return documents
    except Exception as e:
        print(f"❌ Error fetching documents for project '{project.name}': {str(e)}")
        return []


async def process_document_chunks(project: Project, document: SourceDocument) -> int:
    """Process a document into chunks and save to database. Returns number of chunks created."""
    # Check if chunking is already completed for this document
    is_completed = await ProcessingStateRepository.is_completed(
        stage="chunking",
        project_id=project.id,
        document_id=document.id
    )

    if is_completed:
        print(f"    ⏭️  Skipping chunking for document '{document.file_name}' (already completed)")
        return 0

    # Update status to in_progress
    await ProcessingStateRepository.update_status(
        stage="chunking",
        project_id=project.id,
        document_id=document.id,
        status="in_progress"
    )

    try:
        # Skip documents with no content
        if not document.content or len(document.content.strip()) == 0:
            await ProcessingStateRepository.update_status(
                stage="chunking",
                project_id=project.id,
                document_id=document.id,
                status="completed",
                results={"chunk_count": 0, "reason": "no_content"}
            )
            return 0

        # Create chunks from document content
        chunk_texts = create_text_chunks(document.content)

        if not chunk_texts:
            await ProcessingStateRepository.update_status(
                stage="chunking",
                project_id=project.id,
                document_id=document.id,
                status="completed",
                results={"chunk_count": 0, "reason": "no_chunks_generated"}
            )
            return 0

        # Save chunks to database
        saved_chunks = await save_chunks_to_database(document.id, chunk_texts)

        # Mark as completed
        await ProcessingStateRepository.update_status(
            stage="chunking",
            project_id=project.id,
            document_id=document.id,
            status="completed",
            results={"chunk_count": len(saved_chunks)}
        )

        return len(saved_chunks)

    except Exception as e:
        await ProcessingStateRepository.update_status(
            stage="chunking",
            project_id=project.id,
            document_id=document.id,
            status="failed",
            error_message=str(e)
        )
        print(f"    ❌ Error processing chunks for document '{document.file_name}': {str(e)}")
        return 0


async def process_project_chunks(project: Project) -> int:
    """Process all documents in a project into chunks. Returns total number of chunks processed."""
    try:
        documents = await get_project_documents(project)

        if not documents:
            print(f"    ⚠️  No documents found for project '{project.name}'")
            return 0

        # Apply DEV mode document limits
        total_documents = len(documents)
        if os.getenv('APP_MODE') == 'DEV':
            max_documents = int(os.getenv('DEV_MAX_DOCUMENTS_PER_PROJECT', '999'))
            if max_documents < total_documents:
                # Sort documents deterministically by filename for consistent selection across resumes
                documents = sorted(documents, key=lambda d: d.file_name)[:max_documents]
                print(f"    🧪 DEV MODE: Processing {len(documents)} of {total_documents} documents for '{project.name}' (limited by DEV_MAX_DOCUMENTS_PER_PROJECT={max_documents})")
                print(f"        Selected documents: {', '.join([d.file_name for d in documents])}")

        total_chunks = 0
        max_chunks_per_project = int(os.getenv('DEV_MAX_CHUNKS_PER_PROJECT', '999')) if os.getenv('APP_MODE') == 'DEV' else 999

        for doc in documents:
            # Check if we've reached the project chunk limit
            if os.getenv('APP_MODE') == 'DEV' and total_chunks >= max_chunks_per_project:
                print(f"    🧪 DEV MODE: Reached project chunk limit ({max_chunks_per_project}), skipping remaining documents")
                break

            chunk_count = await process_document_chunks(project, doc)
            total_chunks += chunk_count
            if chunk_count > 0:
                print(f"    ✅ Chunked document '{doc.file_name}': {chunk_count} chunks")

            # Log progress toward DEV limit
            if os.getenv('APP_MODE') == 'DEV' and max_chunks_per_project < 999:
                print(f"        Total chunks for project: {total_chunks}/{max_chunks_per_project}")

        return total_chunks

    except Exception as e:
        print(f"    ❌ Error processing chunks: {str(e)}")
        return 0
