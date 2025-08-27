from typing import List, Optional

from app.core.models import ProjectScore as ProjectScoreModel
from app.core.types import Project, ProjectScore, RiskAssessment
from beanie import PydanticObjectId


class ProjectScoreRepository:
    
    @staticmethod
    async def create_project_score(project: Project, risk_assessments: List[RiskAssessment], total_score: float) -> ProjectScore:
        """Create a new project score from risk assessments."""
        project_score_model = ProjectScoreModel(
            project_id=PydanticObjectId(project.id),
            risk_scores=[PydanticObjectId(ra.id) for ra in risk_assessments],
            total_score=total_score
        )
        
        await project_score_model.insert()
        return ProjectScore.from_model(project_score_model)
    
    @staticmethod
    async def get_by_project(project_id: str) -> Optional[ProjectScore]:
        """Get existing project score for a project."""
        model = await ProjectScoreModel.find_one(
            ProjectScoreModel.project_id == PydanticObjectId(project_id)
        )
        return ProjectScore.from_model(model) if model else None
    
    @staticmethod
    async def get_all() -> List[ProjectScore]:
        """Get all project scores."""
        models = await ProjectScoreModel.find().to_list()
        return [ProjectScore.from_model(model) for model in models]
    
    @staticmethod
    async def update_or_create_project_score(project: Project, risk_assessments: List[RiskAssessment], total_score: float) -> ProjectScore:
        """Update existing project score or create new one."""
        existing_model = await ProjectScoreModel.find_one(
            ProjectScoreModel.project_id == PydanticObjectId(project.id)
        )
        
        if existing_model:
            # Update existing project score
            existing_model.risk_scores = [PydanticObjectId(ra.id) for ra in risk_assessments]
            existing_model.total_score = total_score
            await existing_model.save()
            return ProjectScore.from_model(existing_model)
        else:
            # Create new project score
            return await ProjectScoreRepository.create_project_score(project, risk_assessments, total_score)
    
    @staticmethod
    async def project_has_score(project_id: str) -> bool:
        """Check if a project has a project score."""
        existing = await ProjectScoreModel.find_one(
            ProjectScoreModel.project_id == PydanticObjectId(project_id)
        )
        return existing is not None
    
    @staticmethod
    async def delete_by_project(project_id: str) -> bool:
        """Delete project score for a specific project."""
        result = await ProjectScoreModel.find(
            ProjectScoreModel.project_id == PydanticObjectId(project_id)
        ).delete()
        return result.deleted_count > 0