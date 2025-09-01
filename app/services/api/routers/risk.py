from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.evidence_rating_repository import EvidenceRatingRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.source_document_repository import SourceDocumentRepository
# Removed direct model imports - using repositories instead

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/projects-with-total-scores", response_model=List[Dict[str, Any]])
async def get_projects_with_total_scores():
    """Get all projects with their total risk scores"""
    # Get all projects and project scores
    projects = await ProjectRepository.get_all()
    project_scores = await ProjectScoreRepository.get_all()
    
    # Create a mapping of project_id to project_score
    score_mapping = {score.project_id: score for score in project_scores}
    
    # Build the response with project info and total score
    result = []
    for project in projects:
        project_score = score_mapping.get(project.id)
        result.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_risk_score": project_score.total_score if project_score else None
        })
    
    return result


@router.get("/project-risk-breakdown/{project_id}", response_model=List[Dict[str, Any]])
async def get_project_risk_breakdown(project_id: str):
    """Get detailed risk breakdown for a specific project"""
    # Get all project scores and find the matching one (same approach as projects-with-total-scores)
    all_project_scores = await ProjectScoreRepository.get_all()
    project_score = None
    
    for ps in all_project_scores:
        if ps.project_id == project_id:
            project_score = ps
            break
    
    if not project_score:
        raise HTTPException(status_code=404, detail=f"No project score found for project ID: {project_id}")
    
    if not project_score.risk_scores:
        return []  # Return empty list if no risk assessments
    
    # Get all risk types to create a mapping
    all_risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {risk_type.id: risk_type for risk_type in all_risk_types}
    
    # Fetch the RiskAssessment records using the IDs from project_score.risk_scores
    risk_breakdown = []
    for risk_assessment_id in project_score.risk_scores:
        # Use repository instead of direct model access
        risk_assessment = await RiskAssessmentRepository.get_by_id(risk_assessment_id)
        
        if risk_assessment:
            # Get the risk type details
            risk_type_obj = risk_type_mapping.get(risk_assessment.risk_type_id)
            
            if risk_type_obj:
                risk_breakdown.append({
                    "id": risk_assessment.id,
                    "risk_type": risk_type_obj.risk_type,
                    "description": risk_type_obj.description,
                    "weight": risk_type_obj.weight,
                    "score": risk_assessment.score,
                    "number_of_evidences": len(risk_assessment.evidence_ids)
                })
            else:
                # Fallback for unknown risk types
                risk_breakdown.append({
                    "id": risk_assessment.id,
                    "risk_type": "Unknown Risk Type",
                    "description": "Unknown",
                    "weight": 0.0,
                    "score": risk_assessment.score,
                    "number_of_evidences": len(risk_assessment.evidence_ids)
                })
    
    return risk_breakdown


@router.get("/risk-assessment/{risk_assessment_id}", response_model=Dict[str, Any])
async def get_risk_assessment(risk_assessment_id: str):
    """Get detailed information about a specific risk assessment including evidences"""
    # Use repository instead of direct model access
    risk_assessment = await RiskAssessmentRepository.get_by_id(risk_assessment_id)
    
    if not risk_assessment:
        raise HTTPException(status_code=404, detail=f"Risk assessment not found with ID: {risk_assessment_id}")
    
    # Get risk type details
    all_risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in all_risk_types}
    risk_type_obj = risk_type_mapping.get(risk_assessment.risk_type_id)
    
    # Get project details
    all_projects = await ProjectRepository.get_all()
    project_mapping = {p.id: p for p in all_projects}
    project_obj = project_mapping.get(risk_assessment.project_id)
    
    # Get evidence details using repository
    evidences_data = await EvidenceRepository.get_by_ids(risk_assessment.evidence_ids)
    evidences = []
    for evidence in evidences_data:
        evidences.append({
            "id": evidence.id,
            "claim_text": evidence.claim_text,
            "chunk_id": evidence.chunk_id,
            "score": evidence.score
        })
    
    # Build the response
    response = {
        "id": risk_assessment.id,
        "risk_name": risk_type_obj.risk_type if risk_type_obj else "Unknown Risk Type",
        "risk_description": risk_type_obj.description if risk_type_obj else "Unknown",
        "project_name": project_obj.name if project_obj else "Unknown Project",
        "score": risk_assessment.score,
        "number_of_evidences": len(evidences),
        "evidences": evidences
    }
    
    return response


@router.get("/evidence-rating-breakdown/{evidence_id}", response_model=Dict[str, Any])
async def get_evidence_rating_breakdown(evidence_id: str):
    """Get detailed rating breakdown for a specific evidence"""
    # Use repository instead of direct model access
    evidence = await EvidenceRepository.get_by_id(evidence_id)
    
    if not evidence:
        raise HTTPException(status_code=404, detail=f"Evidence not found with ID: {evidence_id}")
    
    # Get all risk types and risk dimension specs for mapping
    all_risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in all_risk_types}
    
    all_dimension_specs = await RiskDimensionRepository.get_all()
    dimension_spec_mapping = {ds.id: ds for ds in all_dimension_specs}
    
    # Get risk type information (should be same for all ratings)
    risk_type_name = None
    risk_type_description = None
    
    # Get chunk, document and project information for additional fields
    chunk = await ChunkRepository.get_by_id(evidence.chunk_id)
    project_name = "Unknown Project"
    
    if chunk:
        # Get all documents to find the one that contains this chunk
        all_documents = await SourceDocumentRepository.get_all()
        document = None
        for doc in all_documents:
            if doc.id == chunk.document_id:
                document = doc
                break
        
        if document:
            # Get all projects to find the project name
            all_projects = await ProjectRepository.get_all()
            for project in all_projects:
                if project.id == document.project_id:
                    project_name = project.name
                    break
    
    # Get all evidence ratings for this evidence using repository
    evidence_ratings = await EvidenceRatingRepository.get_by_evidence_id(evidence_id)
    
    rating_breakdown = []
    for evidence_rating in evidence_ratings:
        # Get risk type and dimension spec details
        risk_type_obj = risk_type_mapping.get(evidence_rating.risk_type_id)
        dimension_spec_obj = dimension_spec_mapping.get(evidence_rating.risk_dimension_spec_id)
        
        # Set risk type info from the first rating (they're all the same)
        if risk_type_name is None and risk_type_obj:
            risk_type_name = risk_type_obj.risk_type
            risk_type_description = risk_type_obj.description
        
        rating_breakdown.append({
            "id": evidence_rating.id,
            "risk_dimension_name": dimension_spec_obj.label if dimension_spec_obj else "Unknown Dimension",
            "scale_value": evidence_rating.scale_value,
            "score": evidence_rating.score,
            "higher_is_riskier": evidence_rating.higher_is_riskier,
            "weight": evidence_rating.weight
        })
    
    # Build the response with risk type at the top level
    response = {
        "evidence_id": evidence_id,
        "chunk_id": evidence.chunk_id,
        "claim_text": evidence.claim_text,
        "project_name": project_name,
        "risk_type_name": risk_type_name or "Unknown Risk Type",
        "risk_type_description": risk_type_description or "Unknown",
        "ratings": rating_breakdown
    }
    
    return response


@router.get("/get-chunk/{chunk_id}", response_model=Dict[str, Any])
async def get_chunk(chunk_id: str):
    """Get chunk details with project and document name mapping"""
    # Use repository instead of direct model access
    chunk = await ChunkRepository.get_by_id(chunk_id)
    
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk not found with ID: {chunk_id}")
    
    # Get all source documents and projects for mapping
    all_projects = await ProjectRepository.get_all()
    project_mapping = {p.id: p for p in all_projects}
    
    # Get the document details using repository
    all_documents = await SourceDocumentRepository.get_all()
    document = None
    for doc in all_documents:
        if doc.id == chunk.document_id:
            document = doc
            break
    
    if not document:
        raise HTTPException(status_code=500, detail="Failed to fetch linked document")
    
    # Get the project name
    project_obj = project_mapping.get(document.project_id)
    
    # Build the response
    response = {
        "chunk_id": chunk_id,
        "project_name": project_obj.name if project_obj else "Unknown Project",
        "document_name": document.file_name,
        "chunk_index": chunk.chunk_index,
        "content": chunk.content
    }
    
    return response