from typing import List, Optional

from app.core.models import Evidence as EvidenceModel, EvidenceRating as EvidenceRatingModel
from app.core.types import RiskType, Chunk, LLMEvidence
from beanie import PydanticObjectId


class EvidenceRepository:
    
    @staticmethod
    async def create_from_llm_evidence(llm_evidence: LLMEvidence, risk_type: RiskType, chunk: Chunk, evidence_ratings: List[EvidenceRatingModel]) -> EvidenceModel:
        """Create an Evidence from LLM evidence data and associated ratings."""
        
        # Calculate overall score as weighted average of evidence ratings
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for rating in evidence_ratings:
            # Adjust score based on whether higher is riskier
            adjusted_score = rating.score if rating.higher_is_riskier else (1.0 - rating.score)
            total_weighted_score += adjusted_score * rating.weight
            total_weight += rating.weight
        
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0.0
        
        evidence = EvidenceModel(
            risk_type_id=PydanticObjectId(risk_type.id),
            claim_text=llm_evidence.claim_text,
            chunk_id=PydanticObjectId(chunk.id),
            evidence_ratings=[rating.id for rating in evidence_ratings],
            score=overall_score,
            metadata={
                "supporting_text": llm_evidence.supporting_text,
                "llm_confidence": llm_evidence.confidence
            }
        )
        
        await evidence.insert()
        return evidence
    
    @staticmethod
    async def get_by_id(evidence_id: str) -> Optional[EvidenceModel]:
        """Get evidence by ID."""
        return await EvidenceModel.get(PydanticObjectId(evidence_id))
    
    @staticmethod
    async def get_by_chunk_and_risk_type(chunk_id: str, risk_type_id: str) -> List[EvidenceModel]:
        """Get all evidences for a specific chunk and risk type."""
        return await EvidenceModel.find(
            EvidenceModel.chunk_id == PydanticObjectId(chunk_id),
            EvidenceModel.risk_type_id == PydanticObjectId(risk_type_id)
        ).to_list()
    
    @staticmethod
    async def get_by_chunk(chunk_id: str) -> List[EvidenceModel]:
        """Get all evidences for a specific chunk (any risk type)."""
        return await EvidenceModel.find(
            EvidenceModel.chunk_id == PydanticObjectId(chunk_id)
        ).to_list()