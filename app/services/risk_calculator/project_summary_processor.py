import os
from typing import List, Dict

from app.core.types import Project, RiskAssessment, ProjectScore
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.project_score_repository import ProjectScoreRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.processing_state_repository import ProcessingStateRepository
from app.core.llm_service import get_llm_service


async def get_risk_assessment_data_for_summary(project_score: ProjectScore, risk_assessments: List[RiskAssessment]) -> Dict:
    """Get risk assessment scores and summaries for project summary generation."""
    if not risk_assessments:
        return {}

    # Get risk types mapping for names
    risk_types = await RiskTypeRepository.get_all()
    risk_type_mapping = {rt.id: rt for rt in risk_types}

    risk_data = []
    total_assessments = 0
    assessments_with_scores = 0
    assessments_with_summaries = 0

    for assessment in risk_assessments:
        # Get risk type name
        risk_type_obj = risk_type_mapping.get(assessment.risk_type_id)
        risk_type_name = risk_type_obj.name if risk_type_obj else "Unknown Risk Type"

        total_assessments += 1

        # Include assessment if it has a score (even if summary is None)
        if assessment.score is not None:
            assessments_with_scores += 1

            risk_entry = {
                "risk_type": risk_type_name,
                "score": assessment.score,
                "summary": assessment.summary or "No detailed risk assessment summary available."
            }

            if assessment.summary:
                assessments_with_summaries += 1

            risk_data.append(risk_entry)
            print(f"      • {risk_type_name}: {assessment.score:.3f} ({'with' if assessment.summary else 'without'} summary)")

    # Sort by score descending for better prompt organization
    risk_data.sort(key=lambda x: x["score"], reverse=True)

    print(f"    📋 Prepared {len(risk_data)} risk assessments for summary ({assessments_with_scores}/{total_assessments} with scores, {assessments_with_summaries} with summaries)")

    return {
        "project_total_score": project_score.total_score,
        "risk_assessments": risk_data,
        "assessment_count": len(risk_data)
    }


async def generate_project_summary(project: Project, project_score: ProjectScore, risk_assessments: List[RiskAssessment]) -> str:
    """Generate AI-powered project summary based on risk assessment scores and summaries."""
    print(f"    🤖 Generating AI summary for project: {project.name}")

    # Get risk assessment data for summary
    risk_data = await get_risk_assessment_data_for_summary(project_score, risk_assessments)

    if not risk_data or risk_data["assessment_count"] == 0:
        print(f"    ⚠️  No risk assessments with scores found for summary generation")
        return "No risk assessment data available for project summary generation."

    # Build the detailed prompt for LLM
    risk_sections = []
    for risk_info in risk_data["risk_assessments"]:
        risk_section = f"""**{risk_info['risk_type']}** (Score: {risk_info['score']:.2f})
Risk Assessment Summary: {risk_info['summary']}"""
        risk_sections.append(risk_section)

    all_risk_info = "\n\n".join(risk_sections)

    prompt = f"""You are a carbon project risk analyst. You will be provided with the final project score, individual risk type scores, and detailed summaries for each risk type assessment.

Project: {project.name}
Final Project Score: {risk_data['project_total_score']:.2f}

Individual Risk Type Assessments:
{all_risk_info}

Your job is to create a comprehensive project summary (2-3 sentences) that explains why the final project score is {risk_data['project_total_score']:.2f} based on the individual risk type scores and their detailed assessment summaries.

Instructions:
- Focus on the most significant risk factors that drive the overall project score
- Synthesize insights from the individual risk assessment summaries
- Explain how the different risk types contribute to the final score
- Use clear, professional language suitable for stakeholders and decision-makers
- Be specific about the key risk drivers rather than providing generic statements
- Connect the individual risk scores and their explanations to the overall project assessment

Project Summary:"""

    # Generate summary using LLM
    try:
        llm_service = get_llm_service()
        summary = await llm_service.query(
            prompt,
            session_id=f"project_summary_{project.name}"
        )
        print(f"    ✅ Generated summary: {summary[:100]}...")
        return summary.strip()
    except Exception as e:
        print(f"    ❌ Error generating summary: {str(e)}")
        return f"Project summary generation failed due to technical issues."


async def process_project_summary_generation(project: Project) -> bool:
    """Process project summary generation by creating AI-powered summary from risk assessments."""
    is_completed = await ProcessingStateRepository.is_project_summary_completed(project.id)

    if is_completed:
        print(f"    ⏭️  Skipping project summary generation (already completed)")
        return True

    # Check DEV mode skip option
    if os.getenv('APP_MODE') == 'DEV' and os.getenv('DEV_SKIP_PROJECT_SUMMARIES', 'false').lower() == 'true':
        print(f"    🧪 DEV MODE: Skipping project summary generation (DEV_SKIP_PROJECT_SUMMARIES=true)")
        await ProcessingStateRepository.update_status(
            stage="project_summary",
            project_id=project.id,
            status="completed",
            results={"skipped_dev_mode": True, "reason": "DEV_SKIP_PROJECT_SUMMARIES"}
        )
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
        summary = await generate_project_summary(project, project_score, risk_assessments)

        # Update project score with summary
        updated_project_score = await ProjectScoreRepository.update_summary_by_id(project_score.id, summary)

        # Count risk assessments with scores (used for summary generation)
        assessments_with_scores = len([ra for ra in risk_assessments if ra.score is not None])
        assessments_with_summaries = len([ra for ra in risk_assessments if ra.score is not None and ra.summary is not None])

        if updated_project_score:
            print(f"    ✅ Project summary updated successfully")
        else:
            print(f"    ⚠️  Project summary generated but update may have failed")

        await ProcessingStateRepository.update_status(
            stage="project_summary",
            project_id=project.id,
            status="completed",
            results={
                "summary_generated": True,
                "summary_length": len(summary),
                "total_risk_assessments": len(risk_assessments),
                "risk_assessments_with_scores": assessments_with_scores,
                "risk_assessments_with_summaries": assessments_with_summaries,
                "risk_assessments_used_for_summary": assessments_with_scores
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