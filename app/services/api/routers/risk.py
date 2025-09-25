from fastapi import APIRouter, HTTPException
from typing import List
from app.services.api.schemas.risk_schemas import (
    ProjectSummary, RiskBreakdownItem, ProjectRiskBreakdown, TopEvidence
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.source_document_repository import SourceDocumentRepository

router = APIRouter(tags=["risk"])


@router.get("/methodology")
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


@router.get("/projects", response_model=List[ProjectSummary])
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


@router.get("/projects/{project_id}", response_model=ProjectRiskBreakdown)
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

        # Get all documents once for efficiency
        all_documents = await SourceDocumentRepository.get_all()
        document_mapping = {doc.id: doc for doc in all_documents}

        for risk_assessment_id in project_score.risk_scores:
            risk_assessment = await RiskAssessmentRepository.get_by_id(risk_assessment_id)

            if risk_assessment:
                risk_type_obj = risk_type_mapping.get(risk_assessment.risk_type_id)

                # Get top 5 evidences for this specific risk assessment
                top_evidences_for_risk = []
                if risk_assessment.evidence_ids:
                    # Get evidences for this risk assessment and sort by score
                    risk_evidences = await EvidenceRepository.get_by_ids(risk_assessment.evidence_ids)
                    sorted_evidences = sorted(risk_evidences, key=lambda e: e.score, reverse=True)[:5]

                    # Build top evidences list for this risk assessment
                    for evidence in sorted_evidences:
                        chunk = await ChunkRepository.get_by_id(evidence.chunk_id)
                        if chunk:
                            document = document_mapping.get(chunk.document_id)
                            if document:
                                # Get first 100 characters of chunk text
                                chunk_text = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content

                                top_evidences_for_risk.append(TopEvidence(
                                    claim_text=evidence.claim_text,
                                    score=evidence.score,
                                    chunk_id=evidence.chunk_id,
                                    document_name=document.file_name,
                                    document_id=document.id,
                                    document_public_url=document.document_url,
                                    chunk_text_fragment=chunk_text
                                ))

                if risk_type_obj:
                    risk_breakdown.append(RiskBreakdownItem(
                        risk_assessment_id=risk_assessment.id,
                        risk_name=risk_type_obj.name,
                        risk_description=risk_type_obj.description,
                        risk_weight=risk_type_obj.weight,
                        total_risk_score=risk_assessment.score,
                        risk_assessment_summary=risk_assessment.summary,
                        number_of_total_evidences=len(risk_assessment.evidence_ids),
                        top_evidences=top_evidences_for_risk
                    ))
                else:
                    risk_breakdown.append(RiskBreakdownItem(
                        risk_assessment_id=risk_assessment.id,
                        risk_name="Unknown Risk Type",
                        risk_description="Unknown",
                        risk_weight=0.0,
                        total_risk_score=risk_assessment.score,
                        risk_assessment_summary=risk_assessment.summary,
                        number_of_total_evidences=len(risk_assessment.evidence_ids),
                        top_evidences=top_evidences_for_risk
                    ))
    
    return ProjectRiskBreakdown(
        project_id=project_id,
        project_name=project.name,
        total_risk_score=project_score.total_score,
        summary=project_score.summary,
        risk_breakdowns=risk_breakdown
    )

