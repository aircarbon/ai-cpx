from typing import List, Dict
import statistics

from app.core.types import Project, RiskType, Evidence
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.repositories.risk_type_repository import RiskTypeRepository


async def calculate_risk_assessment_score(evidences: List[Evidence]) -> float:
    """
    Calculate risk assessment score from multiple evidences.
    Uses the average of all evidence scores for now.
    """
    if not evidences:
        return 0.0
    
    scores = [evidence.score for evidence in evidences]
    
    # For now, use simple average. Could be enhanced with:
    # - Weighted average based on evidence confidence
    # - Maximum score (worst case scenario)
    # - More sophisticated aggregation methods
    return statistics.mean(scores)


async def process_project_risk_assessments(project: Project) -> Dict[str, float]:
    """
    Process all risk assessments for a project by aggregating evidences.
    """
    print(f"\n📊 Processing risk assessments for project: {project.name}")
    
    # Get all risk types
    risk_types = await RiskTypeRepository.get_all()
    if not risk_types:
        print("⚠️  No risk types found")
        return {}
    
    print(f"🎯 Processing {len(risk_types)} risk types")
    
    risk_assessment_scores = {}
    processed_count = 0
    
    for risk_type in risk_types:
        print(f"  🔍 Processing risk type: {risk_type.risk_type}")
        
        # Check if risk assessment already exists for this risk type
        has_existing = await RiskAssessmentRepository.has_risk_assessment_for_type(project.id, risk_type.id)
        if has_existing:
            existing_assessment = await RiskAssessmentRepository.get_by_project_and_risk_type(project.id, risk_type.id)
            print(f"    ✅ Risk assessment already exists: {existing_assessment.score:.3f}")
            risk_assessment_scores[risk_type.risk_type] = existing_assessment.score
            processed_count += 1
            continue
        
        # Get all evidences for this project and risk type
        evidences = await EvidenceRepository.get_by_project_and_risk_type(project.id, risk_type.id)
        
        if not evidences:
            print(f"    📄 No evidences found for {risk_type.risk_type}")
            # Create risk assessment with score 0.0 for risk types with no evidence
            await RiskAssessmentRepository.update_or_create_risk_assessment(
                project, risk_type, [], 0.0
            )
            risk_assessment_scores[risk_type.risk_type] = 0.0
            continue
        
        print(f"    📈 Found {len(evidences)} evidences")
        
        # Calculate risk assessment score
        risk_score = await calculate_risk_assessment_score(evidences)
        print(f"    📊 Calculated risk score: {risk_score:.3f}")
        
        # Create or update risk assessment in database
        try:
            risk_assessment = await RiskAssessmentRepository.update_or_create_risk_assessment(
                project, risk_type, evidences, risk_score
            )
            print(f"    ✅ Saved risk assessment (ID: {str(risk_assessment.id)[:8]}...)")
            risk_assessment_scores[risk_type.risk_type] = risk_score
            processed_count += 1
            
        except Exception as e:
            print(f"    ❌ Error saving risk assessment for {risk_type.risk_type}: {str(e)}")
            risk_assessment_scores[risk_type.risk_type] = 0.0
    
    print(f"✅ Processed {processed_count} risk assessments for project '{project.name}'")
    return risk_assessment_scores


async def get_project_evidence_summary(project: Project) -> Dict[str, int]:
    """
    Get a summary of evidence counts by risk type for a project.
    """
    print(f"📋 Getting evidence summary for project: {project.name}")
    
    # Get all risk types
    risk_types = await RiskTypeRepository.get_all()
    evidence_summary = {}
    
    total_evidences = 0
    for risk_type in risk_types:
        evidences = await EvidenceRepository.get_by_project_and_risk_type(project.id, risk_type.id)
        evidence_count = len(evidences)
        evidence_summary[risk_type.risk_type] = evidence_count
        total_evidences += evidence_count
    
    print(f"📊 Total evidences found: {total_evidences}")
    for risk_type_name, count in evidence_summary.items():
        if count > 0:
            print(f"  • {risk_type_name}: {count} evidences")
    
    return evidence_summary