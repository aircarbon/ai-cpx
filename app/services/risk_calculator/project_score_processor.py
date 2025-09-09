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
    """
    if not risk_assessments:
        return 0.0
    
    scores = [ra.score for ra in risk_assessments]
    
    # For now, use simple average. Could be enhanced with:
    # - Weighted average based on risk type importance
    # - Maximum score (worst case scenario)
    # - More sophisticated aggregation methods based on risk type categories
    return statistics.mean(scores)


async def get_top_risk_evidences_for_summary(project: Project, risk_assessments: List[RiskAssessment]) -> List[Dict]:
    """Get evidences from the top 3 highest scoring risk assessments for summary generation."""
    if not risk_assessments:
        return []
    
    # Sort risk assessments by score (highest first) and take top 3
    sorted_assessments = sorted(risk_assessments, key=lambda ra: ra.score, reverse=True)
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
    """
    Process total project score by aggregating all risk assessments.
    Implementation is decoupled: first save score with summary=null, then generate and update summary.
    """
    print(f"📊 Processing total project score for: {project.name}")
    
    # Get all risk assessments for this project
    risk_assessments = await RiskAssessmentRepository.get_by_project(project.id)
    print(f"    📊 Found {len(risk_assessments)} risk assessments")
    
    if not risk_assessments:
        print(f"    📄 No risk assessments found for {project.name}")
        # Create project score with score 0.0 for projects with no risk assessments
        project_score = await ProjectScoreRepository.update_or_create_project_score(
            project, [], 0.0
        )
        return {"total_score": 0.0}
    
    print(f"    📈 Found {len(risk_assessments)} risk assessments")
    
    # Calculate total project score
    total_score = await calculate_total_project_score(risk_assessments)
    print(f"    📊 Calculated total project score: {total_score:.3f}")
    
    # STEP 1: Create or update project score in database (summary will be null initially)
    try:
        project_score = await ProjectScoreRepository.update_or_create_project_score(
            project, risk_assessments, total_score
        )
        print(f"    ✅ Saved project score with summary=null (ID: {str(project_score.id)[:8]}...)")
        
        # Display risk assessment breakdown
        print(f"    📋 Risk Assessment Breakdown:")
        for ra in risk_assessments:
            print(f"      • Risk Assessment {str(ra.id)[:8]}: {ra.score:.3f}")
        
    except Exception as e:
        print(f"    ❌ Error saving project score: {str(e)}")
        return {"total_score": 0.0}
    
    # STEP 2: Generate and update summary (decoupled from score calculation)
    print(f"\n    🔄 STEP 2: Generating project summary...")
    try:
        summary = await generate_project_summary(project, risk_assessments)
        
        # Update the summary directly on the project score we just created/updated
        updated_project_score = await ProjectScoreRepository.update_summary_by_id(project_score.id, summary)
        if updated_project_score:
            print(f"    ✅ Updated project score with summary")
        else:
            print(f"    ❌ Failed to update summary")
            
    except Exception as e:
        print(f"    ❌ Error generating/updating summary: {str(e)}")
        print(f"    ℹ️  Project score saved successfully, but summary generation failed")
    
    return {"total_score": total_score}