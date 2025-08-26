from typing import Optional, List
from beanie import PydanticObjectId

from app.core.models import Chunk as ChunkModel
from app.core.types import Chunk as ChunkType


class ChunkRepository:
    
    @staticmethod
    async def save_chunk(chunk_data: ChunkType) -> ChunkType:
        chunk_model = chunk_data.to_model()
        await chunk_model.save()
        return ChunkType.from_model(chunk_model)
    
    @staticmethod
    async def save_chunks_bulk(chunks_data: List[ChunkType]) -> List[ChunkType]:
        if not chunks_data:
            return []
        
        chunk_models = [chunk_data.to_model() for chunk_data in chunks_data]
        
        await ChunkModel.insert_many(chunk_models)
        
        # Return the original chunk data with updated IDs
        # Note: MongoDB insert_many doesn't return the inserted documents with IDs in Beanie
        # So we return the original data - the IDs will be set when needed
        return chunks_data
    
    @staticmethod
    async def get_chunks_by_document(document_id: str) -> List[ChunkType]:
        try:
            # For Link references, query using the .id property
            chunks = await ChunkModel.find(ChunkModel.document_id.id == PydanticObjectId(document_id)).to_list()
            return [ChunkType.from_model(chunk) for chunk in chunks]
        except Exception as e:
            print(f"❌ Error fetching chunks for document {document_id}: {str(e)}")
            return []
    