from typing import List, Optional

from app.core.types import Project, RiskType, Evidence
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.processing_state_repository import ProcessingStateRepository
from app.core.llm_service import get_llm_service


async def generate_risk_assessment_summary(project: Project, risk_type: RiskType) -> Optional[str]:
    """Generate a summary for a risk assessment based on top evidence."""

    # Get the risk assessment to check if it exists and has a score
    risk_assessment = await RiskAssessmentRepository.get_by_project_and_risk_type(project.id, risk_type.id)
    if not risk_assessment or risk_assessment.score is None:
        return None

    # Get top 10 evidences with highest scores for this project and risk type
    evidences = await EvidenceRepository.get_by_project_and_risk_type(project.id, risk_type.id)
    if not evidences:
        return None

    # Sort by score descending and take top 10
    top_evidences = sorted(evidences, key=lambda e: e.score, reverse=True)[:10]

    if not top_evidences:
        return None

    # Build evidence text for prompt
    evidence_texts = []
    for i, evidence in enumerate(top_evidences, 1):
        evidence_texts.append(f"{i}. {evidence.claim_text} (Score: {evidence.score:.2f})")

    evidence_list = "\n".join(evidence_texts)

    # Create detailed prompt for LLM
    prompt = f"""You are a carbon project risk analyst. You will be provided with the top {len(top_evidences)} evidences for the "{risk_type.risk_type}" risk type.

Risk Type: {risk_type.risk_type}
Risk Description: {risk_type.description}
Total Risk Assessment Score: {risk_assessment.score:.2f}

Top Evidences (ranked by risk score):
{evidence_list}

Your job is to create a short summary (2-3 sentences) explaining why the total risk assessment score is {risk_assessment.score:.2f} based on these evidences.

Instructions:
- Focus on the most significant evidence findings that drive the risk score
- Explain the key factors that contribute to this risk level
- Use clear, professional language suitable for risk assessment reports
- Be specific about the evidence rather than generic
- Connect the individual evidence scores to the overall assessment

Summary:"""

    # Get LLM service and generate summary
    llm_service = get_llm_service()
    try:
        summary = await llm_service.query(
            prompt,
            session_id=f"risk_summary_{project.name}_{risk_type.risk_type}"
        )
        return summary.strip()
    except Exception as e:
        print(f"❌ Error generating risk assessment summary: {str(e)}")
        return None


async def process_project_risk_assessment_summaries(project: Project, risk_types: List[RiskType]) -> int:
    """Process risk assessment summary generation for all risk types in a project."""
    if not risk_types:
        return 0

    processed_count = 0
    skipped_count = 0

    for risk_type in risk_types:
        # Check if risk assessment summary is already completed for this project + risk type
        is_completed = await ProcessingStateRepository.is_completed(
            stage="risk_assessment_summary",
            project_id=project.id,
            risk_type_id=risk_type.id
        )

        if is_completed:
            print(f"    ⏭️  Skipping risk assessment summary for '{risk_type.risk_type}' (already completed)")
            skipped_count += 1
            continue

        # Update status to in_progress
        await ProcessingStateRepository.update_status(
            stage="risk_assessment_summary",
            project_id=project.id,
            risk_type_id=risk_type.id,
            status="in_progress"
        )

        try:
            # Generate summary
            summary = await generate_risk_assessment_summary(project, risk_type)

            if summary:
                # Update risk assessment with summary
                success = await RiskAssessmentRepository.update_summary(
                    project.id, risk_type.id, summary
                )

                if success:
                    processed_count += 1
                    # Mark as completed
                    await ProcessingStateRepository.update_status(
                        stage="risk_assessment_summary",
                        project_id=project.id,
                        risk_type_id=risk_type.id,
                        status="completed",
                        results={"summary_generated": True, "summary_length": len(summary)}
                    )
                    print(f"    ✅ Generated summary for '{risk_type.risk_type}' ({len(summary)} chars)")
                else:
                    await ProcessingStateRepository.update_status(
                        stage="risk_assessment_summary",
                        project_id=project.id,
                        risk_type_id=risk_type.id,
                        status="failed",
                        error_message="Failed to update risk assessment with summary"
                    )
                    print(f"    ❌ Failed to update risk assessment with summary for '{risk_type.risk_type}'")
            else:
                # Mark as completed with no summary (no evidences or risk assessment)
                await ProcessingStateRepository.update_status(
                    stage="risk_assessment_summary",
                    project_id=project.id,
                    risk_type_id=risk_type.id,
                    status="completed",
                    results={"summary_generated": False, "reason": "no_evidences_or_risk_assessment"}
                )
                print(f"    ⏭️  No summary needed for '{risk_type.risk_type}' (no evidences or risk assessment)")

        except Exception as e:
            await ProcessingStateRepository.update_status(
                stage="risk_assessment_summary",
                project_id=project.id,
                risk_type_id=risk_type.id,
                status="failed",
                error_message=str(e)
            )
            print(f"    ❌ Error processing risk assessment summary for '{risk_type.risk_type}': {str(e)}")

    print(f"✅ Processed {processed_count} risk assessment summaries, skipped {skipped_count} for project '{project.name}'")
    return processed_count