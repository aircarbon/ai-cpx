from typing import List, Dict, Optional
import statistics

from app.core.types import Project, RiskType, Evidence
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.processing_state_repository import ProcessingStateRepository


async def calculate_risk_assessment_score(evidences: List[Evidence]) -> Optional[float]:
    """
    Calculate risk assessment score from multiple evidences.
    Uses the average of all evidence scores for now.
    Returns None if no evidences provided.
    """
    if not evidences:
        return None
    
    scores = [evidence.score for evidence in evidences]
    
    # For now, use simple average. Could be enhanced with:
    # - Weighted average based on evidence confidence
    # - Maximum score (worst case scenario)
    # - More sophisticated aggregation methods
    return statistics.mean(scores)


async def process_project_risk_assessments(project: Project, risk_types: List[RiskType]) -> Dict[str, Optional[float]]:
    """Process all risk assessments for a project by aggregating evidences."""
    if not risk_types:
        return {}

    risk_assessment_scores = {}
    processed_count = 0
    skipped_count = 0

    for risk_type in risk_types:
        # Check if risk assessment is already completed for this project + risk type
        is_completed = await ProcessingStateRepository.is_completed(
            stage="risk_assessment",
            project_id=project.id,
            risk_type_id=risk_type.id
        )

        if is_completed:
            print(f"    ⏭️  Skipping risk assessment for '{risk_type.risk_type}' (already completed)")
            skipped_count += 1
            continue

        # Update status to in_progress
        await ProcessingStateRepository.update_status(
            stage="risk_assessment",
            project_id=project.id,
            risk_type_id=risk_type.id,
            status="in_progress"
        )

        try:
            # Get all evidences for this project and risk type
            evidences = await EvidenceRepository.get_by_project_and_risk_type(project.id, risk_type.id)

            if not evidences:
                # Create risk assessment with score None for risk types with no evidence
                await RiskAssessmentRepository.update_or_create_risk_assessment(
                    project, risk_type, [], None
                )
                risk_assessment_scores[risk_type.risk_type] = None

                # Mark as completed with no evidences
                await ProcessingStateRepository.update_status(
                    stage="risk_assessment",
                    project_id=project.id,
                    risk_type_id=risk_type.id,
                    status="completed",
                    results={"evidence_count": 0, "score": None}
                )
                continue

            # Calculate risk assessment score
            risk_score = await calculate_risk_assessment_score(evidences)

            # Create risk assessment in database
            await RiskAssessmentRepository.update_or_create_risk_assessment(
                project, risk_type, evidences, risk_score
            )
            risk_assessment_scores[risk_type.risk_type] = risk_score
            processed_count += 1

            # Mark as completed
            await ProcessingStateRepository.update_status(
                stage="risk_assessment",
                project_id=project.id,
                risk_type_id=risk_type.id,
                status="completed",
                results={"evidence_count": len(evidences), "score": risk_score}
            )

        except Exception as e:
            await ProcessingStateRepository.update_status(
                stage="risk_assessment",
                project_id=project.id,
                risk_type_id=risk_type.id,
                status="failed",
                error_message=str(e)
            )
            print(f"    ❌ Error processing risk assessment for '{risk_type.risk_type}': {str(e)}")

    print(f"✅ Processed {processed_count} risk assessments, skipped {skipped_count} for project '{project.name}'")
    return risk_assessment_scores