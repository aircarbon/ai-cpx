from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.core.models import ProjectRisk, RiskScore

router = APIRouter(
    prefix="/project-risks",
    tags=["project-risks"]
)

@router.get("/")
async def get_project_risks():
    """Get all project risks from the database"""
    try:
        # Query all project risks from the database
        project_risks = await ProjectRisk.find_all().to_list()
        
        # Format the response with only the requested fields
        formatted_risks = []
        
        for risk in project_risks:
            # Extract risk values from the risks list
            risk_values = []
            for risk_score in risk.risks:
                risk_values.append({
                    "risk_type": risk_score.risk_type.name,
                    "description": risk_score.risk_type.description,
                    "score": risk_score.score,
                    "weight": risk_score.risk_type.weight
                })
            
            formatted_risk = {
                "project_name": risk.project_name,
                "risk_values": risk_values,
                "average_risk": risk.average_risk,
                "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None
            }
            formatted_risks.append(formatted_risk)
        
        return {
            "count": len(formatted_risks),
            "data": formatted_risks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving project risks: {str(e)}")

@router.get("/{project_name}")
async def get_project_risk_by_name(project_name: str):
    """Get project risks for a specific project"""
    try:
        # Query project risks for a specific project
        project_risks = await ProjectRisk.find(ProjectRisk.project_name == project_name).to_list()
        
        if not project_risks:
            raise HTTPException(status_code=404, detail=f"No risks found for project: {project_name}")
        
        # Format the response with only the requested fields
        formatted_risks = []
        
        for risk in project_risks:
            # Extract risk values from the risks list
            risk_values = []
            for risk_score in risk.risks:
                risk_values.append({
                    "risk_type": risk_score.risk_type.name,
                    "description": risk_score.risk_type.description,
                    "score": risk_score.score,
                    "weight": risk_score.risk_type.weight
                })
            
            formatted_risk = {
                "project_name": risk.project_name,
                "risk_values": risk_values,
                "average_risk": risk.average_risk,
                "calculated_at": risk.calculated_at.isoformat() if risk.calculated_at else None
            }
            formatted_risks.append(formatted_risk)
        
        return {
            "count": len(formatted_risks),
            "data": formatted_risks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving project risks: {str(e)}") 