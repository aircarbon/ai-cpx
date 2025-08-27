from typing import List, Dict
import statistics

from app.core.types import Project, RiskAssessment, ProjectScore
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository


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


async def process_project_total_score(project: Project) -> Dict[str, float]:
    """
    Process total project score by aggregating all risk assessments.
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
    
    # Create or update project score in database
    try:
        project_score = await ProjectScoreRepository.update_or_create_project_score(
            project, risk_assessments, total_score
        )
        print(f"    ✅ Saved project score (ID: {str(project_score.id)[:8]}...)")
        
        # Display risk assessment breakdown
        print(f"    📋 Risk Assessment Breakdown:")
        for ra in risk_assessments:
            print(f"      • Risk Assessment {str(ra.id)[:8]}: {ra.score:.3f}")
        
        return {"total_score": total_score}
        
    except Exception as e:
        print(f"    ❌ Error saving project score: {str(e)}")
        return {"total_score": 0.0}