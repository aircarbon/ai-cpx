from beanie import PydanticObjectId

from app.core.models import Chunk as ChunkModel
from app.core.types import Chunk as ChunkType
from app.repositories.source_document_repository import SourceDocumentRepository


class ChunkRepository:
    @staticmethod
    async def save_chunk(chunk_data: ChunkType) -> ChunkType:
        chunk_model = chunk_data.to_model()
        await chunk_model.save()
        return ChunkType.from_model(chunk_model)

    @staticmethod
    async def save_chunks_bulk(chunks_data: list[ChunkType]) -> list[ChunkType]:
        if not chunks_data:
            return []

        chunk_models = [chunk_data.to_model() for chunk_data in chunks_data]

        await ChunkModel.insert_many(chunk_models)

        # Return the original chunk data with updated IDs
        # Note: MongoDB insert_many doesn't return the inserted documents with IDs in Beanie
        # So we return the original data - the IDs will be set when needed
        return chunks_data

    @staticmethod
    async def get_chunks_by_document(document_id: str) -> list[ChunkType]:
        try:
            # For Link references, query using the .id property
            chunks = await ChunkModel.find(ChunkModel.document_id.id == PydanticObjectId(document_id)).to_list()
            return [ChunkType.from_model(chunk) for chunk in chunks]
        except Exception as e:
            print(f"❌ Error fetching chunks for document {document_id}: {str(e)}")
            return []

    @staticmethod
    async def project_has_chunks(project_id: str) -> bool:
        """Check if a project has any chunks by checking its documents."""
        # Get all documents for the project
        documents = await SourceDocumentRepository.get_by_project(project_id)
        if not documents:
            return False

        # Check if any document has chunks
        for document in documents:
            chunk_count = await ChunkModel.find(ChunkModel.document_id.id == PydanticObjectId(document.id)).count()
            if chunk_count > 0:
                return True

        return False

    @staticmethod
    async def get_by_id(chunk_id: str) -> ChunkType | None:
        model = await ChunkModel.get(PydanticObjectId(chunk_id), fetch_links=True)
        return ChunkType.from_model(model) if model else None
