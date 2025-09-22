from pydantic import BaseModel, Field
from typing import List, Optional


# Base schemas
class ProjectSummary(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: Optional[float] = Field(None, description="Total aggregated risk score for the project")
    summary: Optional[str] = Field(None, description="Optional summary text describing the project's risk assessment")


class EvidenceDetail(BaseModel):
    evidence_id: str = Field(..., description="Unique identifier for the evidence")
    claim_text: str = Field(..., description="The main claim or finding text")
    chunk_id: str = Field(..., description="ID of the chunk this evidence was extracted from")
    score: float = Field(..., description="Calculated evidence score", ge=0.0, le=1.0)


class RiskBreakdownItem(BaseModel):
    risk_assessment_id: str = Field(..., description="Unique identifier for the risk assessment")
    risk_type: str = Field(..., description="Name of the risk type")
    description: str = Field(..., description="Detailed description of the risk type")
    weight: float = Field(..., description="Weight of this risk type in overall scoring", ge=0.0)
    score: Optional[float] = Field(None, description="Calculated risk score (null if no evidences)", ge=0.0, le=1.0)
    number_of_evidences: int = Field(..., description="Number of evidences supporting this risk assessment", ge=0)


class ProjectRiskBreakdown(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: Optional[float] = Field(None, description="Total aggregated risk score for the project")
    risk_breakdowns: List[RiskBreakdownItem] = Field(..., description="List of individual risk assessments for this project")


class RatingDetail(BaseModel):
    evidence_rating_id: str = Field(..., description="Unique identifier for the evidence rating")
    risk_dimension_name: str = Field(..., description="Name of the risk dimension")
    scale_value: str = Field(..., description="Selected scale value for this dimension")
    score: float = Field(..., description="Numerical score for this rating", ge=0.0, le=1.0)
    higher_is_riskier: bool = Field(..., description="Whether higher values indicate higher risk")
    weight: float = Field(..., description="Weight of this dimension", ge=0.0)


class RiskAssessmentDetail(BaseModel):
    risk_assessment_id: str = Field(..., description="Unique identifier for the risk assessment")
    risk_name: str = Field(..., description="Name of the risk type")
    risk_description: str = Field(..., description="Detailed description of the risk")
    project_name: str = Field(..., description="Name of the project this assessment belongs to")
    score: Optional[float] = Field(None, description="Overall risk assessment score (null if no evidences)", ge=0.0, le=1.0)
    number_of_evidences: int = Field(..., description="Total number of evidences", ge=0)
    evidences: List[EvidenceDetail] = Field(..., description="List of evidences supporting this assessment")


class EvidenceRatingBreakdown(BaseModel):
    evidence_id: str = Field(..., description="Unique identifier for the evidence")
    chunk_id: str = Field(..., description="ID of the chunk this evidence was extracted from")
    claim_text: str = Field(..., description="The main claim or finding text")
    project_name: str = Field(..., description="Name of the project")
    risk_type_name: str = Field(..., description="Name of the associated risk type")
    risk_type_description: str = Field(..., description="Description of the risk type")
    ratings: List[RatingDetail] = Field(..., description="Detailed breakdown of dimension ratings")


class ChunkDetail(BaseModel):
    chunk_id: str = Field(..., description="Unique identifier for the chunk")
    project_name: str = Field(..., description="Name of the project this chunk belongs to")
    document_name: str = Field(..., description="Name of the source document")
    document_url: Optional[str] = Field(None, description="Public URL to access the document")
    chunk_index: int = Field(..., description="Index of this chunk within the document", ge=0)
    content: str = Field(..., description="Text content of the chunk")
