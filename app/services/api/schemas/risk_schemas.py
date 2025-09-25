from pydantic import BaseModel, Field
from typing import List, Optional


# Base schemas
class ProjectSummary(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: Optional[float] = Field(None, description="Total aggregated risk score for the project")
    summary: Optional[str] = Field(None, description="Optional summary text describing the project's risk assessment")


class RiskBreakdownItem(BaseModel):
    risk_assessment_id: str = Field(..., description="Unique identifier for the risk assessment")
    risk_name: str = Field(..., description="Name of the risk type")
    risk_description: str = Field(..., description="Detailed description of the risk type")
    risk_weight: float = Field(..., description="Weight of this risk type in overall scoring", ge=0.0)
    total_risk_score: Optional[float] = Field(None, description="Calculated risk score (null if no evidences)", ge=0.0, le=1.0)
    risk_assessment_summary: Optional[str] = Field(None, description="AI-generated summary explaining the risk assessment score")
    number_of_total_evidences: int = Field(..., description="Number of evidences supporting this risk assessment", ge=0)


class ProjectRiskBreakdown(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: Optional[float] = Field(None, description="Total aggregated risk score for the project")
    summary: Optional[str] = Field(None, description="AI-generated summary of the project's risk assessment")
    risk_breakdowns: List[RiskBreakdownItem] = Field(..., description="List of individual risk assessments for this project")
