from typing import List, Optional

from app.core.models import RiskAssessment as RiskAssessmentModel, Evidence as EvidenceModel
from app.core.types import Project, RiskType, Evidence, RiskAssessment
from beanie import PydanticObjectId


class RiskAssessmentRepository:
    
    @staticmethod
    async def create_risk_assessment(project: Project, risk_type: RiskType, evidences: List[Evidence], score: float) -> RiskAssessment:
        """Create a new risk assessment from evidences."""
        risk_assessment_model = RiskAssessmentModel(
            project_id=PydanticObjectId(project.id),
            risk_type_id=PydanticObjectId(risk_type.id),
            evidence_ids=[evidence.id for evidence in evidences],
            score=score
        )
        
        await risk_assessment_model.insert()
        return RiskAssessment.from_model(risk_assessment_model)
    
    @staticmethod
    async def get_by_project_and_risk_type(project_id: str, risk_type_id: str) -> Optional[RiskAssessment]:
        """Get existing risk assessment for a project and risk type."""
        model = await RiskAssessmentModel.find_one(
            RiskAssessmentModel.project_id == PydanticObjectId(project_id),
            RiskAssessmentModel.risk_type_id == PydanticObjectId(risk_type_id)
        )
        return RiskAssessment.from_model(model) if model else None
    
    @staticmethod
    async def get_by_project(project_id: str) -> List[RiskAssessment]:
        """Get all risk assessments for a project."""
        models = await RiskAssessmentModel.find(
            RiskAssessmentModel.project_id == PydanticObjectId(project_id)
        ).to_list()
        return [RiskAssessment.from_model(model) for model in models]
    
    @staticmethod
    async def update_or_create_risk_assessment(project: Project, risk_type: RiskType, evidences: List[Evidence], score: float) -> RiskAssessment:
        """Update existing risk assessment or create new one."""
        existing_model = await RiskAssessmentModel.find_one(
            RiskAssessmentModel.project_id == PydanticObjectId(project.id),
            RiskAssessmentModel.risk_type_id == PydanticObjectId(risk_type.id)
        )
        
        if existing_model:
            # Update existing assessment
            existing_model.evidence_ids = [evidence.id for evidence in evidences]
            existing_model.score = score
            await existing_model.save()
            return RiskAssessment.from_model(existing_model)
        else:
            # Create new assessment
            return await RiskAssessmentRepository.create_risk_assessment(project, risk_type, evidences, score)
    
    @staticmethod
    async def project_has_risk_assessments(project_id: str) -> bool:
        """Check if a project has any risk assessments."""
        count = await RiskAssessmentModel.find(
            RiskAssessmentModel.project_id == PydanticObjectId(project_id)
        ).count()
        return count > 0
    
    @staticmethod
    async def has_risk_assessment_for_type(project_id: str, risk_type_id: str) -> bool:
        """Check if a specific risk assessment exists for a project and risk type."""
        existing = await RiskAssessmentModel.find_one(
            RiskAssessmentModel.project_id == PydanticObjectId(project_id),
            RiskAssessmentModel.risk_type_id == PydanticObjectId(risk_type_id)
        )
        return existing is not None