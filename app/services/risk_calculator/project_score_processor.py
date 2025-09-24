from typing import List
import statistics

from app.core.types import Project, RiskAssessment, ProjectScore
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.processing_state_repository import ProcessingStateRepository


async def calculate_total_project_score(risk_assessments: List[RiskAssessment]) -> float:
    """
    Calculate total project score from all risk assessments.
    Uses the average of all risk assessment scores for now.
    Excludes risk assessments with None scores (no evidences).
    """
    if not risk_assessments:
        return 0.0

    valid_scores = [ra.score for ra in risk_assessments if ra.score is not None]

    if not valid_scores:
        return 0.0

    scores = valid_scores
    
    # For now, use simple average. Could be enhanced with:
    # - Weighted average based on risk type importance
    # - Maximum score (worst case scenario)
    # - More sophisticated aggregation methods based on risk type categories
    return statistics.mean(scores)



async def process_project_total_score(project: Project) -> float:
    """Process total project score by aggregating all risk assessments."""
    is_completed = await ProcessingStateRepository.is_project_scoring_completed(project.id)

    if is_completed:
        print(f"    ⏭️  Skipping project scoring (already completed)")
        project_score = await ProjectScoreRepository.get_by_project(project.id)
        return project_score.total_score if project_score else 0.0

    await ProcessingStateRepository.update_status(
        stage="project_scoring",
        project_id=project.id,
        status="in_progress"
    )

    try:
        risk_assessments = await RiskAssessmentRepository.get_by_project(project.id)

        if not risk_assessments:
            project_score = await ProjectScoreRepository.update_or_create_project_score(
                project, [], 0.0
            )

            await ProcessingStateRepository.update_status(
                stage="project_scoring",
                project_id=project.id,
                status="completed",
                results={"total_score": 0.0, "risk_assessment_count": 0}
            )
            return 0.0

        total_score = await calculate_total_project_score(risk_assessments)

        project_score = await ProjectScoreRepository.update_or_create_project_score(
            project, risk_assessments, total_score
        )

        await ProcessingStateRepository.update_status(
            stage="project_scoring",
            project_id=project.id,
            status="completed",
            results={"total_score": total_score, "risk_assessment_count": len(risk_assessments)}
        )

        return total_score

    except Exception as e:
        await ProcessingStateRepository.update_status(
            stage="project_scoring",
            project_id=project.id,
            status="failed",
            error_message=str(e)
        )
        print(f"    ❌ Error processing project score: {str(e)}")
        return 0.0