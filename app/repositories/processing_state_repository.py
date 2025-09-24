from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.models import ProcessingState as ProcessingStateModel
from app.core.types import ProcessingState
from beanie import PydanticObjectId


class ProcessingStateRepository:
    """Repository for managing processing state records"""

    @staticmethod
    async def update_status(
        stage: str,
        project_id: str,
        status: str,
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        risk_type_id: Optional[str] = None,
        error_message: Optional[str] = None,
        results: Optional[Dict[str, Any]] = None
    ) -> Optional[ProcessingState]:
        """Update status of an existing processing state record"""

        # Build query
        query = {
            "stage": stage,
            "project_id": PydanticObjectId(project_id)
        }

        if document_id:
            query["document_id"] = PydanticObjectId(document_id)
        if chunk_id:
            query["chunk_id"] = PydanticObjectId(chunk_id)
        if risk_type_id:
            query["risk_type_id"] = PydanticObjectId(risk_type_id)

        # Build update
        update_data = {
            "status": status,
            "updated_at": datetime.now()
        }

        if status == "in_progress":
            update_data["started_at"] = datetime.now()
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = datetime.now()

        if error_message:
            update_data["error_message"] = error_message

        if results:
            update_data["results"] = results

        # Find and update or create if not exists
        model = await ProcessingStateModel.find_one(query)
        if model:
            # Update existing
            for key, value in update_data.items():
                setattr(model, key, value)
            await model.save()
        else:
            # Create new record
            model = ProcessingStateModel(
                stage=stage,
                project_id=PydanticObjectId(project_id),
                document_id=PydanticObjectId(document_id) if document_id else None,
                chunk_id=PydanticObjectId(chunk_id) if chunk_id else None,
                risk_type_id=PydanticObjectId(risk_type_id) if risk_type_id else None,
                **update_data
            )
            await model.insert()

        return ProcessingState.from_model(model)

    @staticmethod
    async def is_completed(
        stage: str,
        project_id: str,
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        risk_type_id: Optional[str] = None
    ) -> bool:
        """Check if a specific processing state is completed"""

        query = {
            "stage": stage,
            "project_id": PydanticObjectId(project_id),
            "status": "completed"
        }

        if document_id:
            query["document_id"] = PydanticObjectId(document_id)
        if chunk_id:
            query["chunk_id"] = PydanticObjectId(chunk_id)
        if risk_type_id:
            query["risk_type_id"] = PydanticObjectId(risk_type_id)

        count = await ProcessingStateModel.find(query).count()
        return count > 0

    @staticmethod
    async def is_project_scoring_completed(project_id: str) -> bool:
        """Check if project scoring is completed for a project"""

        return await ProcessingStateRepository.is_completed(
            stage="project_scoring",
            project_id=project_id
        )