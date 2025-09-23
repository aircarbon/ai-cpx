from typing import List, Dict
import statistics

from app.core.types import Project, RiskAssessment, ProjectScore
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.core.llm_service import get_llm_service


async def calculate_total_project_score(risk_assessments: List[RiskAssessment]) -> float:
    """
    Calculate total project score from all risk assessments.
    Uses the average of all risk assessment scores for now.
    Excludes risk assessments with None scores (no evidences).
    """
    if not risk_assessments:
        return 0.0

    # Filter out None scores (risk types with no evidences)
    valid_scores = [ra.score for ra in risk_assessments if ra.score is not None]

    if not valid_scores:
        return 0.0

    scores = valid_scores
    
    # For now, use simple average. Could be enhanced with:
    # - Weighted average based on risk type importance
    # - Maximum score (worst case scenario)
    # - More sophisticated aggregation methods based on risk type categories
    return statistics.mean(scores)


async def get_top_risk_evidences_for_summary(project: Project, risk_assessments: List[RiskAssessment]) -> List[Dict]:
    """Get evidences from the top 3 highest scoring risk assessments for summary generation."""
    if not risk_assessments:
        return []
    
    # Filter out assessments with None scores and sort by score (highest first) and take top 3
    valid_assessments = [ra for ra in risk_assessments if ra.score is not None]
    sorted_assessments = sorted(valid_assessments, key=lambda ra: ra.score, reverse=True)
    top_3_assessments = sorted_assessments[:3]
    
    print(f"    📋 Getting evidences from top {len(top_3_assessments)} risk assessments for summary")
    
    # Get risk types mapping for names
    risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in risk_types}
    
    top_risk_evidences = []
    for assessment in top_3_assessments:
        # Get risk type name
        risk_type_obj = risk_type_mapping.get(assessment.risk_type_id)
        risk_type_name = risk_type_obj.risk_type if risk_type_obj else "Unknown Risk Type"
        
        # Get evidences for this risk assessment
        evidences = await EvidenceRepository.get_by_ids(assessment.evidence_ids)
        evidence_claims = [evidence.claim_text for evidence in evidences if evidence.claim_text]
        
        print(f"      • {risk_type_name}: {assessment.score:.3f} ({len(evidence_claims)} evidences)")
        
        if evidence_claims:  # Only include if there are evidences
            top_risk_evidences.append({
                "risk_type": risk_type_name,
                "score": assessment.score,
                "evidences": evidence_claims
            })
    
    return top_risk_evidences


async def generate_project_summary(project: Project, risk_assessments: List[RiskAssessment]) -> str:
    """Generate AI-powered summary based on top risk evidences."""
    print(f"    🤖 Generating AI summary for project: {project.name}")
    
    # Get top risk evidences
    top_risk_evidences = await get_top_risk_evidences_for_summary(project, risk_assessments)
    
    if not top_risk_evidences:
        print(f"    ⚠️  No evidences found for summary generation")
        return "No significant risk evidences found in the project documents."
    
    # Generate summary using LLM
    try:
        llm_service = get_llm_service()
        summary = await llm_service.generate_project_summary(top_risk_evidences, project.name)
        print(f"    ✅ Generated summary: {summary[:100]}...")
        return summary.strip()
    except Exception as e:
        print(f"    ❌ Error generating summary: {str(e)}")
        return f"Summary generation failed due to technical issues."


async def process_project_total_score(project: Project) -> Dict[str, float]:
    """Process total project score by aggregating all risk assessments."""
    # Get all risk assessments for this project
    risk_assessments = await RiskAssessmentRepository.get_by_project(project.id)

    if not risk_assessments:
        # Create project score with score 0.0 for projects with no risk assessments
        project_score = await ProjectScoreRepository.update_or_create_project_score(
            project, [], 0.0
        )
        return 0.0

    # Calculate total project score
    total_score = await calculate_total_project_score(risk_assessments)

    # Create project score in database (summary will be null initially)
    project_score = await ProjectScoreRepository.update_or_create_project_score(
        project, risk_assessments, total_score
    )

    # Generate and update summary
    summary = await generate_project_summary(project, risk_assessments)
    updated_project_score = await ProjectScoreRepository.update_summary_by_id(project_score.id, summary)

    return total_score