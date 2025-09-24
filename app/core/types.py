from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING, List
from dataclasses import dataclass, field
from beanie import PydanticObjectId

if TYPE_CHECKING:
    from app.core.models import Project as ProjectModel, SourceDocument as SourceDocumentModel, Chunk as ChunkModel, RiskType as RiskTypeModel
else:
    from app.core.models import Project as ProjectModel, SourceDocument as SourceDocumentModel, Chunk as ChunkModel, RiskType as RiskTypeModel


@dataclass
class Project:
    name: str
    folder_path: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    @classmethod
    def from_model(cls, model: 'ProjectModel') -> 'Project':
        return cls(
            name=model.name,
            folder_path=model.folder_path,
            created_at=model.created_at,
            updated_at=model.updated_at,
            id=str(model.id)
        )
    
    def to_model(self) -> 'ProjectModel':
        return ProjectModel(
            name=self.name,
            folder_path=self.folder_path,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


@dataclass
class Chunk:
    document_id: str
    chunk_index: int
    content: str
    size_characters: int
    page_from: Optional[int] = None
    page_to: Optional[int] = None
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.size_characters == 0:
            self.size_characters = len(self.content)
    
    @classmethod
    def from_model(cls, model: 'ChunkModel') -> 'Chunk':
        # Extract ObjectId from DBRef for Link fields
        document_id_str = str(model.document_id.to_ref().id) if hasattr(model.document_id, 'to_ref') else str(model.document_id)
        
        return cls(
            document_id=document_id_str,
            chunk_index=model.chunk_index,
            content=model.content,
            size_characters=model.size_characters,
            page_from=model.page_from,
            page_to=model.page_to,
            previous_chunk_id=str(model.previous_chunk_id) if model.previous_chunk_id else None,
            next_chunk_id=str(model.next_chunk_id) if model.next_chunk_id else None,
            created_at=model.created_at,
            id=str(model.id)
        )
    
    def to_model(self) -> 'ChunkModel':
        return ChunkModel(
            document_id=PydanticObjectId(self.document_id),
            chunk_index=self.chunk_index,
            content=self.content,
            size_characters=self.size_characters,
            page_from=self.page_from,
            page_to=self.page_to,
            previous_chunk_id=PydanticObjectId(self.previous_chunk_id) if self.previous_chunk_id else None,
            next_chunk_id=PydanticObjectId(self.next_chunk_id) if self.next_chunk_id else None,
            created_at=self.created_at
        )


@dataclass
class RiskType:
    risk_type: str
    description: str
    weight: float
    id: Optional[str] = None
    
    @classmethod
    def from_model(cls, model: 'RiskTypeModel') -> 'RiskType':
        return cls(
            risk_type=model.risk_type,
            description=model.description,
            weight=model.weight,
            id=str(model.id)
        )
    
    def to_model(self) -> 'RiskTypeModel':
        return RiskTypeModel(
            risk_type=self.risk_type,
            description=self.description,
            weight=self.weight
        )


@dataclass
class SourceDocument:
    project_id: str
    file_name: str
    source_type: str
    source_path: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    document_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_processed_successfully(self) -> bool:
        return self.success and self.error is None
    
    @property
    def has_content(self) -> bool:
        return bool(self.content and self.content.strip())
    
    @classmethod
    def from_model(cls, model: 'SourceDocumentModel') -> 'SourceDocument':
        # Extract ObjectId from DBRef for Link fields
        project_id_str = str(model.project_id.to_ref().id) if hasattr(model.project_id, 'to_ref') else str(model.project_id)

        return cls(
            project_id=project_id_str,
            file_name=model.file_name,
            source_type=model.source_type,
            source_path=model.source_path,
            title=model.title,
            content=model.content,
            success=model.success,
            error=model.error,
            file_size=model.file_size,
            page_count=model.page_count,
            document_url=model.document_url,
            metadata=model.metadata,
            created_at=model.created_at,
            id=str(model.id)
        )
    
    def to_model(self) -> 'SourceDocumentModel':
        return SourceDocumentModel(
            project_id=PydanticObjectId(self.project_id),
            file_name=self.file_name,
            source_type=self.source_type,
            source_path=self.source_path,
            title=self.title,
            content=self.content,
            success=self.success,
            error=self.error,
            file_size=self.file_size,
            page_count=self.page_count,
            document_url=self.document_url,
            metadata=self.metadata,
            created_at=self.created_at
        )


@dataclass
class LLMDimensionRating:
    """Rating for a specific dimension of an evidence, as returned by LLM"""
    dimension_key: str  # Key from RiskDimensionSpec
    scale_value: str    # Value from the dimension's scale (e.g., 'mild', 'moderate', 'severe')
    reasoning: str      # LLM's explanation for this rating
    confidence: float   # LLM's confidence in this rating (0.0 to 1.0)


@dataclass
class LLMEvidence:
    """Individual evidence found by LLM in a text chunk"""
    claim_text: str                              # Summary of the evidence claim
    supporting_text: str                         # Actual text snippet from chunk that supports this evidence
    dimension_ratings: List[LLMDimensionRating]  # Ratings for each required dimension
    confidence: float                            # Overall confidence in this evidence (0.0 to 1.0)


@dataclass
class LLMRiskAnalysisResponse:
    """Complete response from LLM for analyzing a chunk for a specific risk type"""
    risk_type: str                    # The risk type that was being analyzed
    evidences: List[LLMEvidence]      # List of evidences found in the chunk
    chunk_summary: str                # Brief summary of what the chunk contains
    no_evidence_reasoning: str        # If no evidences found, explanation why
    
    @property
    def has_evidences(self) -> bool:
        return len(self.evidences) > 0
    
    @property
    def evidence_count(self) -> int:
        return len(self.evidences)
    
    @property
    def average_confidence(self) -> float:
        if not self.evidences:
            return 0.0
        return sum(evidence.confidence for evidence in self.evidences) / len(self.evidences)


@dataclass 
class RiskDimensionSpec:
    """Risk dimension specification type for business logic"""
    key: str
    label: str
    description: str
    rationale: str
    guidance: str
    higher_is_riskier: bool
    scale: List[str]
    mapping: Dict[str, float]
    weight: float
    id: Optional[str] = None
    
    @classmethod
    def from_model(cls, model) -> 'RiskDimensionSpec':
        return cls(
            key=model.key,
            label=model.label,
            description=model.description,
            rationale=model.rationale,
            guidance=model.guidance,
            higher_is_riskier=model.higher_is_riskier,
            scale=model.scale,
            mapping=model.mapping,
            weight=model.weight,
            id=str(model.id)
        )


@dataclass
class EvidenceRating:
    """Evidence rating for a specific risk dimension"""
    risk_type_id: str
    risk_dimension_spec_id: str
    scale_value: str
    score: float
    higher_is_riskier: bool
    weight: float
    id: Optional[str] = None
    
    @classmethod
    def from_model(cls, model) -> 'EvidenceRating':
        # Extract ObjectId from DBRef for Link fields
        risk_type_id_str = str(model.risk_type_id.to_ref().id) if hasattr(model.risk_type_id, 'to_ref') else str(model.risk_type_id)
        risk_dimension_spec_id_str = str(model.risk_dimension_spec_id.to_ref().id) if hasattr(model.risk_dimension_spec_id, 'to_ref') else str(model.risk_dimension_spec_id)
        
        return cls(
            risk_type_id=risk_type_id_str,
            risk_dimension_spec_id=risk_dimension_spec_id_str,
            scale_value=model.scale_value,
            score=model.score,
            higher_is_riskier=model.higher_is_riskier,
            weight=model.weight,
            id=str(model.id)
        )


@dataclass
class Evidence:
    """Evidence found for a specific risk type in a chunk"""
    risk_type_id: str
    claim_text: str
    chunk_id: str
    evidence_ratings: List[str]  # List of EvidenceRating IDs
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @classmethod
    def from_model(cls, model) -> 'Evidence':
        # Extract ObjectId from DBRef for Link fields
        risk_type_id_str = str(model.risk_type_id.to_ref().id) if hasattr(model.risk_type_id, 'to_ref') else str(model.risk_type_id)
        chunk_id_str = str(model.chunk_id.to_ref().id) if hasattr(model.chunk_id, 'to_ref') else str(model.chunk_id)
        evidence_ratings_str = [str(rating_id.to_ref().id if hasattr(rating_id, 'to_ref') else rating_id) for rating_id in model.evidence_ratings]
        
        return cls(
            risk_type_id=risk_type_id_str,
            claim_text=model.claim_text,
            chunk_id=chunk_id_str,
            evidence_ratings=evidence_ratings_str,
            score=model.score,
            metadata=model.metadata,
            created_at=model.created_at,
            id=str(model.id)
        )


@dataclass
class RiskAssessment:
    """Risk assessment aggregating evidences for a specific risk type and project"""
    project_id: str
    risk_type_id: str
    evidence_ids: List[str]  # List of Evidence IDs
    score: Optional[float]
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @classmethod
    def from_model(cls, model) -> 'RiskAssessment':
        # Extract ObjectId from DBRef for Link fields
        project_id_str = str(model.project_id.to_ref().id) if hasattr(model.project_id, 'to_ref') else str(model.project_id)
        risk_type_id_str = str(model.risk_type_id.to_ref().id) if hasattr(model.risk_type_id, 'to_ref') else str(model.risk_type_id)
        evidence_ids_str = [str(evidence_id.to_ref().id if hasattr(evidence_id, 'to_ref') else evidence_id) for evidence_id in model.evidence_ids]

        return cls(
            project_id=project_id_str,
            risk_type_id=risk_type_id_str,
            evidence_ids=evidence_ids_str,
            score=model.score,
            summary=model.summary,
            created_at=model.created_at,
            id=str(model.id)
        )


@dataclass
class ProjectScore:
    """Total project score aggregating all risk assessments for a project"""
    project_id: str
    risk_scores: List[str]  # List of RiskAssessment IDs
    total_score: float
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @classmethod
    def from_model(cls, model) -> 'ProjectScore':
        # Extract ObjectId from DBRef
        project_id_str = str(model.project_id.to_ref().id) if hasattr(model.project_id, 'to_ref') else str(model.project_id)
        risk_scores_str = [str(risk_id.to_ref().id if hasattr(risk_id, 'to_ref') else risk_id) for risk_id in model.risk_scores]
        
        return cls(
            project_id=project_id_str,
            risk_scores=risk_scores_str,
            total_score=model.total_score,
            summary=model.summary,
            created_at=model.created_at,
            id=str(model.id)
        )


@dataclass
class ProcessingState:
    """Processing state for tracking intermediate results and enabling resume capability"""
    stage: str                              # "chunking", "evidence_extraction", "risk_assessment", "project_scoring"
    project_id: str                         # Always present
    status: str                             # "pending", "in_progress", "completed", "failed"

    # Optional references (depend on stage)
    document_id: Optional[str] = None       # For chunking stage
    chunk_id: Optional[str] = None          # For evidence_extraction stage
    risk_type_id: Optional[str] = None      # For evidence_extraction, risk_assessment stages

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0

    # Results and metadata
    results: Dict[str, Any] = field(default_factory=dict)
    processing_version: str = "1.0"
    id: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @classmethod
    def from_model(cls, model) -> 'ProcessingState':
        # Extract ObjectId from DBRef for Link fields
        project_id_str = str(model.project_id.to_ref().id) if hasattr(model.project_id, 'to_ref') else str(model.project_id)
        document_id_str = str(model.document_id.to_ref().id) if model.document_id and hasattr(model.document_id, 'to_ref') else (str(model.document_id) if model.document_id else None)
        chunk_id_str = str(model.chunk_id.to_ref().id) if model.chunk_id and hasattr(model.chunk_id, 'to_ref') else (str(model.chunk_id) if model.chunk_id else None)
        risk_type_id_str = str(model.risk_type_id.to_ref().id) if model.risk_type_id and hasattr(model.risk_type_id, 'to_ref') else (str(model.risk_type_id) if model.risk_type_id else None)

        return cls(
            stage=model.stage,
            project_id=project_id_str,
            document_id=document_id_str,
            chunk_id=chunk_id_str,
            risk_type_id=risk_type_id_str,
            status=model.status,
            started_at=model.started_at,
            completed_at=model.completed_at,
            error_message=model.error_message,
            retry_count=model.retry_count,
            results=model.results,
            processing_version=model.processing_version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            id=str(model.id)
        )
