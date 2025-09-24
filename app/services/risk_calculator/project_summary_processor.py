from typing import List, Dict

from app.core.types import Project, RiskAssessment
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.processing_state_repository import ProcessingStateRepository
from app.core.llm_service import get_llm_service


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


async def process_project_summary_generation(project: Project) -> bool:
    """Process project summary generation by creating AI-powered summary from risk assessments."""
    is_completed = await ProcessingStateRepository.is_project_summary_completed(project.id)

    if is_completed:
        print(f"    ⏭️  Skipping project summary generation (already completed)")
        return True

    await ProcessingStateRepository.update_status(
        stage="project_summary",
        project_id=project.id,
        status="in_progress"
    )

    try:
        # Get project score to update with summary
        project_score = await ProjectScoreRepository.get_by_project(project.id)
        if not project_score:
            print(f"    ⚠️  No project score found - cannot generate summary")
            await ProcessingStateRepository.update_status(
                stage="project_summary",
                project_id=project.id,
                status="failed",
                error_message="No project score found"
            )
            return False

        # Get risk assessments for summary generation
        risk_assessments = await RiskAssessmentRepository.get_by_project(project.id)

        if not risk_assessments:
            print(f"    ⚠️  No risk assessments found - cannot generate summary")
            await ProjectScoreRepository.update_summary_by_id(
                project_score.id,
                "No risk assessments available for summary generation."
            )
            await ProcessingStateRepository.update_status(
                stage="project_summary",
                project_id=project.id,
                status="completed",
                results={"summary_generated": False, "reason": "no_risk_assessments"}
            )
            return True

        # Generate summary
        summary = await generate_project_summary(project, risk_assessments)

        # Update project score with summary
        updated_project_score = await ProjectScoreRepository.update_summary_by_id(project_score.id, summary)

        await ProcessingStateRepository.update_status(
            stage="project_summary",
            project_id=project.id,
            status="completed",
            results={
                "summary_generated": True,
                "summary_length": len(summary),
                "risk_assessments_count": len(risk_assessments)
            }
        )

        print(f"    ✅ Project summary generated and saved")
        return True

    except Exception as e:
        await ProcessingStateRepository.update_status(
            stage="project_summary",
            project_id=project.id,
            status="failed",
            error_message=str(e)
        )
        print(f"    ❌ Error processing project summary: {str(e)}")
        return False