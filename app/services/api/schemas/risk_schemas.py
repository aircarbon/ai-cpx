from pydantic import BaseModel, Field


# Base schemas
class ProjectSummary(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: float | None = Field(None, description="Total aggregated risk score for the project")
    summary: str | None = Field(None, description="Optional summary text describing the project's risk assessment")


class TopEvidence(BaseModel):
    title: str | None = Field(None, description="Short 2-4 word title for the evidence")
    evidence_description: str = Field(..., description="Description of what evidence of risk was found")
    score: float = Field(..., description="Calculated evidence score", ge=0.0, le=1.0)
    chunk_id: str = Field(..., description="ID of the chunk this evidence was extracted from")
    document_name: str = Field(..., description="Name of the source document")
    document_id: str = Field(..., description="ID of the source document")
    document_public_url: str | None = Field(None, description="Public URL to access the document")
    chunk_text_fragment: str = Field(..., description="First 100 characters of the chunk text ending with '...'")


class RiskBreakdownItem(BaseModel):
    risk_assessment_id: str = Field(..., description="Unique identifier for the risk assessment")
    risk_name: str = Field(..., description="Name of the risk type")
    risk_description: str = Field(..., description="Detailed description of the risk type")
    risk_weight: float = Field(..., description="Weight of this risk type in overall scoring", ge=0.0)
    total_risk_score: float | None = Field(
        None, description="Calculated risk score (null if no evidences)", ge=0.0, le=1.0
    )
    risk_assessment_summary: str | None = Field(
        None, description="AI-generated summary explaining the risk assessment score"
    )
    number_of_total_evidences: int = Field(..., description="Number of evidences supporting this risk assessment", ge=0)


class ProjectRiskBreakdown(BaseModel):
    project_id: str = Field(..., description="Unique identifier for the project")
    project_name: str = Field(..., description="Name of the project")
    total_risk_score: float | None = Field(None, description="Total aggregated risk score for the project")
    summary: str | None = Field(None, description="AI-generated summary of the project's risk assessment")
    risk_breakdowns: list[RiskBreakdownItem] = Field(
        ..., description="List of individual risk assessments for this project"
    )
