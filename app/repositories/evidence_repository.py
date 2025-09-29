from typing import List, Optional

from app.core.models import Evidence as EvidenceModel, EvidenceRating as EvidenceRatingModel
from app.core.types import RiskType, Chunk, LLMEvidence, Evidence, EvidenceRating
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from beanie import PydanticObjectId
from beanie.operators import In


class EvidenceRepository:
    
    @staticmethod
    async def create_from_llm_evidence(llm_evidence: LLMEvidence, risk_type: RiskType, chunk: Chunk, evidence_ratings: List[EvidenceRating]) -> Evidence:
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
        
        evidence_model = EvidenceModel(
            risk_type_id=PydanticObjectId(risk_type.id),
            title=llm_evidence.title,
            claim_text=llm_evidence.claim_text,
            chunk_id=PydanticObjectId(chunk.id),
            evidence_ratings=[rating.id for rating in evidence_ratings],
            score=overall_score,
            metadata={
                "supporting_text": llm_evidence.supporting_text,
                "llm_confidence": llm_evidence.confidence
            }
        )
        
        await evidence_model.insert()
        
        return Evidence.from_model(evidence_model)
    
    @staticmethod
    async def get_by_id(evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID."""
        model = await EvidenceModel.get(PydanticObjectId(evidence_id), fetch_links=True)
        return Evidence.from_model(model) if model else None
    
    @staticmethod
    async def get_by_project_and_risk_type(project_id: str, risk_type_id: str) -> List[Evidence]:
        """Get all evidences for a specific project and risk type by querying through chunks."""
        
        # Get all documents for the project
        documents = await SourceDocumentRepository.get_by_project(project_id)
        if not documents:
            return []
        
        # Get all chunks for these documents
        all_chunk_ids = []
        for document in documents:
            chunks = await ChunkRepository.get_chunks_by_document(document.id)
            all_chunk_ids.extend([chunk.id for chunk in chunks])

        if not all_chunk_ids:
            return []

        # Due to Beanie Link field complexity, query all evidences and filter in memory
        # This is less efficient but more reliable for Link field matching
        all_evidences = await EvidenceModel.find(fetch_links=True).to_list()

        # Filter evidences that match our project's chunks and risk type
        filtered_evidences = []
        chunk_id_set = set(str(chunk_id) for chunk_id in all_chunk_ids)

        for evidence in all_evidences:
            # Check if evidence has resolved chunk_id and risk_type_id
            if evidence.chunk_id and evidence.risk_type_id:
                # Since we use fetch_links=True, Link fields are resolved to document objects
                evidence_chunk_id = str(evidence.chunk_id.id)
                evidence_risk_type_id = str(evidence.risk_type_id.id)

                # Check if this evidence belongs to our project and risk type
                if evidence_chunk_id in chunk_id_set and evidence_risk_type_id == risk_type_id:
                    filtered_evidences.append(evidence)
        
        return [Evidence.from_model(model) for model in filtered_evidences]
    
    @staticmethod
    async def get_by_ids(evidence_ids: List[str]) -> List[Evidence]:
        """Get multiple evidences by their IDs."""
        if not evidence_ids:
            return []
        
        evidences = []
        for evidence_id in evidence_ids:
            evidence = await EvidenceRepository.get_by_id(evidence_id)
            if evidence:
                evidences.append(evidence)
        
        return evidences