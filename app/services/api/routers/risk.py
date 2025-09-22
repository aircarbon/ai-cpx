from fastapi import APIRouter, HTTPException
from typing import List
from app.services.api.schemas.risk_schemas import (
    ProjectSummary, RiskBreakdownItem, ProjectRiskBreakdown, RiskAssessmentDetail, EvidenceDetail,
    EvidenceRatingBreakdown, RatingDetail, ChunkDetail
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.evidence_rating_repository import EvidenceRatingRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.source_document_repository import SourceDocumentRepository

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


@router.get("/evidence-rating-breakdown/{evidence_id}", response_model=EvidenceRatingBreakdown)
async def get_evidence_rating_breakdown(evidence_id: str):
    evidence = await EvidenceRepository.get_by_id(evidence_id)
    
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence not found with ID: {evidence_id}")
    
    all_risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in all_risk_types}
    
    all_dimension_specs = await RiskDimensionRepository.get_all()
    dimension_spec_mapping = {ds.id: ds for ds in all_dimension_specs}
    
    risk_type_name = None
    risk_type_description = None
    
    chunk = await ChunkRepository.get_by_id(evidence.chunk_id)
    project_name = "Unknown Project"
    
    if chunk:
        all_documents = await SourceDocumentRepository.get_all()
        document = None
        for doc in all_documents:
            if doc.id == chunk.document_id:
                document = doc
                break
        
        if document:
            all_projects = await ProjectRepository.get_all()
            for project in all_projects:
                if project.id == document.project_id:
                    project_name = project.name
                    break
    
    evidence_ratings = await EvidenceRatingRepository.get_by_evidence_id(evidence_id)
    
    rating_breakdown = []
    for evidence_rating in evidence_ratings:
        risk_type_obj = risk_type_mapping.get(evidence_rating.risk_type_id)
        dimension_spec_obj = dimension_spec_mapping.get(evidence_rating.risk_dimension_spec_id)
        
        if risk_type_name is None and risk_type_obj:
            risk_type_name = risk_type_obj.risk_type
            risk_type_description = risk_type_obj.description
        
        rating_breakdown.append(RatingDetail(
            evidence_rating_id=evidence_rating.id,
            risk_dimension_name=dimension_spec_obj.label if dimension_spec_obj else "Unknown Dimension",
            scale_value=evidence_rating.scale_value,
            score=evidence_rating.score,
            higher_is_riskier=evidence_rating.higher_is_riskier,
            weight=evidence_rating.weight
        ))
    
    response = EvidenceRatingBreakdown(
        evidence_id=evidence_id,
        chunk_id=evidence.chunk_id,
        claim_text=evidence.claim_text,
        project_name=project_name,
        risk_type_name=risk_type_name or "Unknown Risk Type",
        risk_type_description=risk_type_description or "Unknown",
        ratings=rating_breakdown
    )
    
    return response


@router.get("/get-chunk/{chunk_id}", response_model=ChunkDetail)
async def get_chunk(chunk_id: str):
    chunk = await ChunkRepository.get_by_id(chunk_id)
    
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk not found with ID: {chunk_id}")
    
    all_projects = await ProjectRepository.get_all()
    project_mapping = {p.id: p for p in all_projects}
    
    all_documents = await SourceDocumentRepository.get_all()
    document = None
    for doc in all_documents:
        if doc.id == chunk.document_id:
            document = doc
            break
    
    if not document:
        raise HTTPException(status_code=500, detail="Failed to fetch linked document")
    
    project_obj = project_mapping.get(document.project_id)
    
    response = ChunkDetail(
        chunk_id=chunk_id,
        project_name=project_obj.name if project_obj else "Unknown Project",
        document_name=document.file_name,
        document_url=document.document_url,
        chunk_index=chunk.chunk_index,
        content=chunk.content
    )
    
    return response