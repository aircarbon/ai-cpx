from fastapi import APIRouter, HTTPException
from typing import List
from app.services.api.schemas.risk_schemas import (
    ProjectSummary, RiskBreakdownItem, ProjectRiskBreakdown, RiskAssessmentDetail, EvidenceDetail
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.evidence_repository import EvidenceRepository

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/risk-calc-methodology-descr")
async def get_risk_calculation_methodology_description():
    methodology_description = (
        "AI-CPX analyzes carbon project documents and public sources using advanced AI models to calculate comprehensive risk scores. "
        "The system processes diverse project materials like Project Design Documents, monitoring reports, and validation records to identify "
        "evidence across 13 key risk categories including policy/regulatory changes, data integrity issues, financing problems, execution delays, "
        "and legal compliance risks. Each piece of evidence is evaluated on four dimensions - impact severity, likelihood certainty, timing, "
        "and reversibility - using structured rating scales. The final risk score is calculated through sophisticated weighted averaging, "
        "where different risk types and evaluation dimensions are weighted by their relative importance to project success. "
        "This produces a normalized score from 0.0 (lowest risk) to 10.0 (highest risk), providing stakeholders with a clear, "
        "data-driven assessment of each carbon project's overall risk profile."
    )
    return {"description": methodology_description}


@router.get("/projects-with-total-scores", response_model=List[ProjectSummary])
async def get_projects_with_total_scores():
    projects = await ProjectRepository.get_all()
    project_scores = await ProjectScoreRepository.get_all()
    
    score_mapping = {score.project_id: score for score in project_scores}
    
    result = []
    for project in projects:
        project_score = score_mapping.get(project.id)
        result.append(ProjectSummary(
            project_id=project.id,
            project_name=project.name,
            total_risk_score=project_score.total_score if project_score else None,
            summary=project_score.summary if project_score else None
        ))
    
    return result


@router.get("/project-risk-breakdown/{project_id}", response_model=ProjectRiskBreakdown)
async def get_project_risk_breakdown(project_id: str):
    project = await ProjectRepository.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found with ID: {project_id}")
    
    project_score = await ProjectScoreRepository.get_by_project(project_id)
    if not project_score:
        raise HTTPException(status_code=404, detail=f"No project score found for project ID: {project_id}")
    
    risk_breakdown = []
    if project_score.risk_scores:
        all_risk_types = await RiskTypeRepository.get_all()
        risk_type_mapping = {risk_type.id: risk_type for risk_type in all_risk_types}
        
        for risk_assessment_id in project_score.risk_scores:
            risk_assessment = await RiskAssessmentRepository.get_by_id(risk_assessment_id)
            
            if risk_assessment:
                risk_type_obj = risk_type_mapping.get(risk_assessment.risk_type_id)
                
                if risk_type_obj:
                    risk_breakdown.append(RiskBreakdownItem(
                        risk_assessment_id=risk_assessment.id,
                        risk_type=risk_type_obj.risk_type,
                        description=risk_type_obj.description,
                        weight=risk_type_obj.weight,
                        score=risk_assessment.score,
                        number_of_evidences=len(risk_assessment.evidence_ids)
                    ))
                else:
                    risk_breakdown.append(RiskBreakdownItem(
                        risk_assessment_id=risk_assessment.id,
                        risk_type="Unknown Risk Type",
                        description="Unknown",
                        weight=0.0,
                        score=risk_assessment.score,
                        number_of_evidences=len(risk_assessment.evidence_ids)
                    ))
    
    return ProjectRiskBreakdown(
        project_id=project_id,
        project_name=project.name,
        total_risk_score=project_score.total_score,
        risk_breakdowns=risk_breakdown
    )


@router.get("/risk-assessment/{risk_assessment_id}", response_model=RiskAssessmentDetail)
async def get_risk_assessment(risk_assessment_id: str):
    risk_assessment = await RiskAssessmentRepository.get_by_id(risk_assessment_id)
    
    if not risk_assessment:
        raise HTTPException(status_code=404, detail=f"Risk assessment not found with ID: {risk_assessment_id}")
    
    all_risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in all_risk_types}
    risk_type_obj = risk_type_mapping.get(risk_assessment.risk_type_id)
    
    all_projects = await ProjectRepository.get_all()
    project_mapping = {p.id: p for p in all_projects}
    project_obj = project_mapping.get(risk_assessment.project_id)
    
    evidences_data = await EvidenceRepository.get_by_ids(risk_assessment.evidence_ids)
    evidences = []
    for evidence in evidences_data:
        evidences.append(EvidenceDetail(
            evidence_id=evidence.id,
            claim_text=evidence.claim_text,
            chunk_id=evidence.chunk_id,
            score=evidence.score
        ))
    
    response = RiskAssessmentDetail(
        risk_assessment_id=risk_assessment.id,
        risk_name=risk_type_obj.risk_type if risk_type_obj else "Unknown Risk Type",
        risk_description=risk_type_obj.description if risk_type_obj else "Unknown",
        project_name=project_obj.name if project_obj else "Unknown Project",
        score=risk_assessment.score,
        number_of_evidences=len(evidences),
        evidences=evidences
    )
    
    return response

