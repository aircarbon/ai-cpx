from typing import List

from app.core.types import Project, SourceDocument, Chunk
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.chunk_repository import ChunkRepository

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
    # Skip documents with no content
    if not document.content or len(document.content.strip()) == 0:
        return 0

    # Create chunks from document content
    chunk_texts = create_text_chunks(document.content)

    if not chunk_texts:
        return 0

    # Save chunks to database
    saved_chunks = await save_chunks_to_database(document.id, chunk_texts)
    return len(saved_chunks)


async def process_project_chunks(project: Project) -> int:
    """Process all documents in a project into chunks. Returns total number of chunks processed."""
    try:
        documents = await get_project_documents(project)

        if not documents:
            return 0

        total_chunks = 0
        for doc in documents:
            chunk_count = await process_document_chunks(project, doc)
            total_chunks += chunk_count

        return total_chunks

    except Exception as e:
        print(f"    ❌ Error processing chunks: {str(e)}")
        return 0
