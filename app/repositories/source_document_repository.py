from typing import Optional, List
from beanie import PydanticObjectId

from app.core.models import SourceDocument as SourceDocumentModel, Project as ProjectModel
from app.core.types import SourceDocument as SourceDocumentType


class SourceDocumentRepository:
    
    @staticmethod
    async def get_all() -> List[SourceDocumentType]:
        documents = await SourceDocumentModel.find_all().to_list()
        return [SourceDocumentType.from_model(document) for document in documents]
    
    @staticmethod
    async def get_by_project(project_id: str) -> List[SourceDocumentType]:
        try:
            documents = await SourceDocumentModel.find(SourceDocumentModel.project_id.id == PydanticObjectId(project_id)).to_list()
            return [SourceDocumentType.from_model(document) for document in documents]
        except Exception as e:
            print(f"❌ Error fetching documents for project {project_id}: {str(e)}")
            return []
    
    @staticmethod
    async def is_existing(file_name: str) -> bool:
        existing_document = await SourceDocumentModel.find_one(SourceDocumentModel.file_name == file_name)
        return existing_document is not None
    
    @staticmethod
    async def add_or_get_existing(document_data: SourceDocumentType) -> SourceDocumentType:
        existing_document = await SourceDocumentModel.find_one(SourceDocumentModel.file_name == document_data.file_name)
        
        if existing_document:
            return SourceDocumentType.from_model(existing_document)
        
        new_document_model = document_data.to_model()
        await new_document_model.save()
        
        return SourceDocumentType.from_model(new_document_model)