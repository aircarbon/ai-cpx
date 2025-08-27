from typing import List, Optional

from app.core.models import EvidenceRating as EvidenceRatingModel, RiskType as RiskTypeModel, RiskDimensionSpec as RiskDimensionSpecModel
from app.core.types import RiskType, RiskDimensionSpec, LLMDimensionRating
from beanie import PydanticObjectId


class EvidenceRatingRepository:
    
    @staticmethod
    async def create_from_llm_rating(llm_rating: LLMDimensionRating, risk_type: RiskType, dimension_spec: RiskDimensionSpec) -> EvidenceRatingModel:
        """Create an EvidenceRating from LLM dimension rating data."""
        # Get the numeric score from the dimension mapping
        score = dimension_spec.mapping.get(llm_rating.scale_value, 0.0)
        
        evidence_rating = EvidenceRatingModel(
            risk_type_id=PydanticObjectId(risk_type.id),
            risk_dimension_spec_id=PydanticObjectId(dimension_spec.id),
            scale_value=llm_rating.scale_value,
            score=score,
            higher_is_riskier=dimension_spec.higher_is_riskier,
            weight=dimension_spec.weight
        )
        
        await evidence_rating.insert()
        return evidence_rating
    
    @staticmethod
    async def get_by_id(rating_id: str) -> Optional[EvidenceRatingModel]:
        """Get evidence rating by ID."""
        return await EvidenceRatingModel.get(PydanticObjectId(rating_id))