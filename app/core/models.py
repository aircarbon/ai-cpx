from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from beanie import Document, Link, PydanticObjectId
from pydantic import Field

# Carbon project, a separate folder in the S3 bucket
class Project(Document):
    name: str = Field(..., description="Name of the project", unique=True)
    folder_path: str = Field(..., description="Path to the project folder")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the project was created")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the project was last updated")
    
    class Settings:
        name = "projects"
        indexes = [
            "name",
            "folder_path",
            "created_at",
            "updated_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Individual parsed file from S3 file
class SourceDocument(Document):
    project_id: Link[Project] = Field(..., description="Reference to the project this document belongs to")

    file_name: str = Field(..., description="Name of the file")
    source_type: str = Field(..., description="Type of source (file, url, etc.)")
    source_path: str = Field(..., description="Source path or URL of the document")

    title: str = Field(..., description="Title of the document")
    content: str = Field(..., description="Extracted text content from the document")

    success: bool = Field(..., description="Whether processing was successful")
    error: Optional[str] = Field(None, description="Error message if processing failed")

    file_size: Optional[int] = Field(None, description="Size of the file in bytes")
    page_count: Optional[int] = Field(None, description="Number of pages in the document")
    document_url: Optional[str] = Field(None, description="Public URL to access the document")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional document metadata")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the document was created")
    
    class Settings:
        name = "documents"
        indexes = [
            "project_id",
            "file_name",
            "source_type",
            "success",
            "created_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Chunk of text from the parsed document
class Chunk(Document):
    document_id: Link[SourceDocument] = Field(..., description="Reference to the document this chunk belongs to")
    
    chunk_index: int = Field(..., description="Index of this chunk within the document")
    page_from: Optional[int] = Field(None, description="Starting page number for this chunk")
    page_to: Optional[int] = Field(None, description="Ending page number for this chunk")
    content: str = Field(..., description="Text content of this chunk")
    size_characters: int = Field(..., description="Size of the chunk in characters")
    
    previous_chunk_id: Optional[PydanticObjectId] = Field(None, description="ID of the previous chunk")
    next_chunk_id: Optional[PydanticObjectId] = Field(None, description="ID of the next chunk")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the chunk was created")
    
    class Settings:
        name = "chunks"
        indexes = [
            "document_id",
            "chunk_index",
            "page_from",
            "page_to",
            "previous_chunk_id",
            "next_chunk_id",
            "created_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Risk type, taken from config, LLM will have to find evidences for each risk type in each chunk
class RiskType(Document):
    risk_type: str = Field(..., description="Unique risk type identifier/name", unique=True)
    description: str = Field(..., description="Description of the risk type")
    weight: float = Field(..., description="Weight factor for this risk type in calculations")
    
    class Settings:
        name = "risk_types"
        indexes = [
            "risk_type",
            "weight"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Instead of scoring a risk directly, we score each dimension of the risk and then calculate the 
# overall score as a weighted average of the dimension scores. RiskDimensionSpec is a config file
# that defines the dimensions and their scale, and will be used by the LLM for scoring.
class RiskDimensionSpec(Document):
    key: str = Field(..., description="Unique key identifier for the dimension", unique=True)
    label: str = Field(..., description="Human-readable label for the dimension")
    description: str = Field(..., description="Description of what this dimension measures")
    rationale: str = Field(..., description="Rationale for why this dimension is important")
    guidance: str = Field(..., description="Guidance on how to assess this dimension")
    
    higher_is_riskier: bool = Field(..., description="Whether higher values indicate higher risk")
    
    scale: List[str] = Field(..., description="Ordered list of scale values from lowest to highest")
    mapping: Dict[str, float] = Field(..., description="Mapping from scale values to numeric scores")
    
    weight: float = Field(..., description="Weight factor for this dimension in calculations")
    
    class Settings:
        name = "risk_dimensions"
        indexes = [
            "key",
            "weight",
            "higher_is_riskier"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Evidence rating for a specific dimension of a specific risk type.
# For example, how severe is the impact of the political risk on the project from X claim?
class EvidenceRating(Document):
    risk_type_id: Link[RiskType] = Field(..., description="Reference to the risk type")
    risk_dimension_spec_id: Link[RiskDimensionSpec] = Field(..., description="Reference to the risk dimension specification")
    scale_value: str = Field(..., description="String value from the scale (e.g., 'mild', 'moderate', 'severe')")
    score: float = Field(..., description="Numeric score for this assessment")
    higher_is_riskier: bool = Field(..., description="Whether higher values indicate higher risk")
    weight: float = Field(..., description="Weight factor for this assessment")
    
    class Settings:
        name = "evidence_ratings"
        indexes = [
            "risk_type_id",
            "risk_dimension_spec_id",
            "scale_value",
            "higher_is_riskier",
            "weight"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Evidence is found by an LLM from a chunk of text for a specific risk type,
# and contains a list of evidence ratings for different dimensions, from which
# the final score of the evidence is calculated as a weighted average.
class Evidence(Document):
    risk_type_id: Link[RiskType] = Field(..., description="Reference to the risk type")
    claim_text: str = Field(..., description="Summary of an evidence")
    chunk_id: Link[Chunk] = Field(..., description="Reference to the chunk")
    
    evidence_ratings: List[Link[EvidenceRating]] = Field(default_factory=list, description="List of evidence ratings for different dimensions (one for each dimension with the assigned score)")
    score: float = Field(..., description="Overall score for this evidence (calculated as a weighted avergae of all evidence assessments)")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for the evidence")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the evidence was created")
    
    class Settings:
        name = "evidences"
        indexes = [
            "risk_type_id",
            "chunk_id",
            "score",
            "created_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Risk assessment aggregates different evidences and their scores for a specific risk type
class RiskAssessment(Document):
    project_id: Link[Project] = Field(..., description="Reference to the project this assessment belongs to")
    risk_type_id: Link[RiskType] = Field(..., description="Reference to the risk type")
    evidence_ids: List[Link[Evidence]] = Field(default_factory=list, description="Array of links to Evidence objects (each risk type can have multiple evidences)")
    score: Optional[float] = Field(None, description="Risk assessment score for this risk type (null if no evidences)")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the assessment was created")
    
    class Settings:
        name = "risk_assessments"
        indexes = [
            "project_id",
            "risk_type_id",
            "score",
            "created_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Project score is a weighted average of all risk scores for a project
class ProjectScore(Document):
    project_id: Link[Project] = Field(..., description="Reference to the project this score belongs to")
    risk_scores: List[Link[RiskAssessment]] = Field(default_factory=list, description="Array of links to RiskAssessment objects, one for each type of risk")
    total_score: float = Field(..., description="Total calculated score for the project (as weighted average of all risk scores)")
    summary: Optional[str] = Field(None, description="Optional summary text describing the project's risk assessment")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the project score was created")
    
    class Settings:
        name = "project_scores"
        indexes = [
            "project_id",
            "total_score",
            "created_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Model for tracking processing coverage of chunks and evidence counts.
class CoverageLedger(Document):
    project_id: Link[Project] = Field(..., description="Reference to the project")
    document_id: Link[SourceDocument] = Field(..., description="Reference to the source document")
    chunk_id: Link[Chunk] = Field(..., description="Reference to the chunk")
    processed: bool = Field(..., description="Whether this chunk has been processed")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the chunk was processed")
    evidence_counts: Dict[str, int] = Field(default_factory=dict, description="Count of evidences found by risk type (e.g., {'PoliticalRegulatory':2,...})")
    
    class Settings:
        name = "coverage_ledger"
        indexes = [
            "project_id",
            "document_id", 
            "chunk_id",
            "processed",
            "processed_at"
        ]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }