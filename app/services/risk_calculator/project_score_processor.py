from typing import List

from app.core.types import Project, RiskAssessment
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.processing_state_repository import ProcessingStateRepository
from app.repositories.risk_type_repository import RiskTypeRepository


async def calculate_total_project_score(risk_assessments: List[RiskAssessment]) -> float:
    """
    Calculate total project score from all risk assessments using weighted average.
    Uses risk type weights from the database to calculate weighted average.
    Excludes risk assessments with None scores (no evidences).
    """
    if not risk_assessments:
        return 0.0

    # Get risk types with weights from database
    risk_types = await RiskTypeRepository.get_all()
    risk_type_weights = {rt.id: rt.weight for rt in risk_types}

    # Collect valid assessments with their weights
    weighted_scores = []
    total_weight = 0.0

    for ra in risk_assessments:
        if ra.score is not None:
            weight = risk_type_weights.get(ra.risk_type_id, 1.0)  # Default weight of 1.0 if not found
            weighted_scores.append(ra.score * weight)
            total_weight += weight

    if not weighted_scores or total_weight == 0.0:
        return 0.0

    # Calculate weighted average
    weighted_sum = sum(weighted_scores)
    weighted_average = weighted_sum / total_weight

    return weighted_average



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