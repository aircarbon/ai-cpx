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
        return cls(
            document_id=str(model.document_id),
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
        return cls(
            project_id=str(model.project_id),
            file_name=model.file_name,
            source_type=model.source_type,
            source_path=model.source_path,
            title=model.title,
            content=model.content,
            success=model.success,
            error=model.error,
            file_size=model.file_size,
            page_count=model.page_count,
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
