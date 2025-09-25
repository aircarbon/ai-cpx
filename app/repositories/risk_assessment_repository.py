from typing import List, Optional

from app.core.models import RiskAssessment as RiskAssessmentModel, Evidence as EvidenceModel, Project as ProjectModel, RiskType as RiskTypeModel
from app.core.types import Project, RiskType, Evidence, RiskAssessment
from beanie import PydanticObjectId


class RiskAssessmentRepository:
    
    @staticmethod
    async def create_risk_assessment(project: Project, risk_type: RiskType, evidences: List[Evidence], score: Optional[float]) -> RiskAssessment:
        """Create a new risk assessment from evidences."""
        # Get the actual model objects to create Links
        project_model = await ProjectModel.get(PydanticObjectId(project.id))
        risk_type_model = await RiskTypeModel.get(PydanticObjectId(risk_type.id))
        evidence_models = []
        for evidence in evidences:
            evidence_model = await EvidenceModel.get(PydanticObjectId(evidence.id))
            evidence_models.append(evidence_model)
        
        risk_assessment_model = RiskAssessmentModel(
            project_id=project_model,
            risk_type_id=risk_type_model,
            evidence_ids=evidence_models,
            score=score
        )
        
        await risk_assessment_model.insert()
        return RiskAssessment.from_model(risk_assessment_model)
    
    @staticmethod
    async def get_by_project_and_risk_type(project_id: str, risk_type_id: str) -> Optional[RiskAssessment]:
        """Get existing risk assessment for a project and risk type."""
        # Use the same filtering approach as get_by_project for consistency
        all_models = await RiskAssessmentModel.find_all(fetch_links=True).to_list()

        for model in all_models:
            # Check if the project_id and risk_type_id Links match
            if (model.project_id and model.risk_type_id and
                hasattr(model.project_id, 'id') and hasattr(model.risk_type_id, 'id') and
                str(model.project_id.id) == project_id and
                str(model.risk_type_id.id) == risk_type_id):
                return RiskAssessment.from_model(model)

        return None
    
    @staticmethod
    async def get_by_project(project_id: str) -> List[RiskAssessment]:
        """Get all risk assessments for a project."""
        # Get all risk assessments and filter by project_id
        all_models = await RiskAssessmentModel.find_all(fetch_links=True).to_list()
        
        matching_models = []
        for model in all_models:
            # Check if the project_id Link references the correct project
            if hasattr(model.project_id, 'id') and str(model.project_id.id) == project_id:
                matching_models.append(model)
        
        return [RiskAssessment.from_model(model) for model in matching_models]
    
    @staticmethod
    async def update_or_create_risk_assessment(project: Project, risk_type: RiskType, evidences: List[Evidence], score: Optional[float]) -> RiskAssessment:
        """Update existing risk assessment or create new one."""
        project_model = await ProjectModel.get(PydanticObjectId(project.id))
        risk_type_model = await RiskTypeModel.get(PydanticObjectId(risk_type.id))
        
        existing_model = await RiskAssessmentModel.find_one(
            RiskAssessmentModel.project_id == project_model,
            RiskAssessmentModel.risk_type_id == risk_type_model,
            fetch_links=True
        )
        
        if existing_model:
            # Update existing assessment
            evidence_models = []
            for evidence in evidences:
                evidence_model = await EvidenceModel.get(PydanticObjectId(evidence.id))
                evidence_models.append(evidence_model)
            existing_model.evidence_ids = evidence_models
            existing_model.score = score
            await existing_model.save()
            return RiskAssessment.from_model(existing_model)
        else:
            # Create new assessment
            return await RiskAssessmentRepository.create_risk_assessment(project, risk_type, evidences, score)
    
    @staticmethod
    async def project_has_risk_assessments(project_id: str) -> bool:
        """Check if a project has any risk assessments."""
        # Use the same approach as get_by_project for consistency
        all_models = await RiskAssessmentModel.find_all(fetch_links=True).to_list()
        
        count = 0
        for model in all_models:
            # Check if the project_id Link references the correct project
            if hasattr(model.project_id, 'id') and str(model.project_id.id) == project_id:
                count += 1
        
        return count > 0
    
    @staticmethod
    async def has_risk_assessment_for_type(project_id: str, risk_type_id: str) -> bool:
        """Check if a specific risk assessment exists for a project and risk type."""
        project_model = await ProjectModel.get(PydanticObjectId(project_id))
        risk_type_model = await RiskTypeModel.get(PydanticObjectId(risk_type_id))
        existing = await RiskAssessmentModel.find_one(
            RiskAssessmentModel.project_id == project_model,
            RiskAssessmentModel.risk_type_id == risk_type_model,
            fetch_links=True
        )
        return existing is not None
    
    @staticmethod
    async def get_by_id(risk_assessment_id: str) -> Optional[RiskAssessment]:
        """Get risk assessment by ID."""
        model = await RiskAssessmentModel.get(PydanticObjectId(risk_assessment_id), fetch_links=True)
        return RiskAssessment.from_model(model) if model else None

    @staticmethod
    async def update_summary(project_id: str, risk_type_id: str, summary: str) -> bool:
        """Update the summary field of a risk assessment."""
        # Use the same filtering approach as get_by_project_and_risk_type for consistency
        all_models = await RiskAssessmentModel.find_all(fetch_links=True).to_list()

        for model in all_models:
            # Check if the project_id and risk_type_id Links match
            if (model.project_id and model.risk_type_id and
                hasattr(model.project_id, 'id') and hasattr(model.risk_type_id, 'id') and
                str(model.project_id.id) == project_id and
                str(model.risk_type_id.id) == risk_type_id):
                model.summary = summary
                await model.save()
                return True

        return False