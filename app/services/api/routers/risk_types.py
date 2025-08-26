from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.core.models import RiskTypes

router = APIRouter(
    prefix="/risk-types",
    tags=["risk-types"]
)

@router.get("/latest")
async def get_latest_risk_types():
    """Get the most recently calculated risk types"""
    try:
        # Query the most recent risk types by sorting by created_at descending
        latest_risk_types = await RiskTypes.find_all().sort("-created_at").limit(1).to_list()
        
        if not latest_risk_types:
            return {
                "version": None,
                "created_at": None,
                "data": [],
                "metadata": {}
            }
        
        risk_types_doc = latest_risk_types[0]
        
        # Format the response
        formatted_risk_types = []
        for risk_type in risk_types_doc.risk_types:
            formatted_risk_types.append({
                "name": risk_type.name,
                "description": risk_type.description,
                "weight": risk_type.weight
            })
        
        return {
            "version": risk_types_doc.version,
            "created_at": risk_types_doc.created_at.isoformat(),
            "data": formatted_risk_types,
            "metadata": risk_types_doc.metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest risk types: {str(e)}")

@router.get("/")
async def get_all_risk_types():
    """Get all risk type definitions from the database"""
    try:
        # Query all risk types from the database, sorted by created_at descending
        all_risk_types = await RiskTypes.find_all().sort("-created_at").to_list()
        
        # Format the response
        formatted_response = []
        
        for risk_types_doc in all_risk_types:
            formatted_risk_types = []
            for risk_type in risk_types_doc.risk_types:
                formatted_risk_types.append({
                    "name": risk_type.name,
                    "description": risk_type.description,
                    "weight": risk_type.weight
                })
            
            formatted_response.append({
                "version": risk_types_doc.version,
                "created_at": risk_types_doc.created_at.isoformat(),
                "risk_types_count": len(formatted_risk_types),
                "risk_types": formatted_risk_types,
                "metadata": risk_types_doc.metadata
            })
        
        return {
            "total_versions": len(formatted_response),
            "data": formatted_response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving all risk types: {str(e)}")
