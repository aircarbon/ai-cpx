from fastapi import APIRouter
from typing import List, Dict, Any
from app.repositories.project_repository import ProjectRepository
from app.repositories.project_score_repository import ProjectScoreRepository

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/projects-with-total-scores", response_model=List[Dict[str, Any]])
async def get_projects_with_total_scores():
    """Get all projects with their total risk scores"""
    # Get all projects and project scores
    projects = await ProjectRepository.get_all()
    project_scores = await ProjectScoreRepository.get_all()
    
    # Create a mapping of project_id to project_score
    score_mapping = {score.project_id: score for score in project_scores}
    
    # Build the response with project info and total score
    result = []
    for project in projects:
        project_score = score_mapping.get(project.id)
        result.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_risk_score": project_score.total_score if project_score else None
        })
    
    return result