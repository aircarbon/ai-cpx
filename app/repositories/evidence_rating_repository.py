from beanie import PydanticObjectId

from app.core.models import EvidenceRating as EvidenceRatingModel
from app.core.types import EvidenceRating, LLMDimensionRating, RiskDimensionSpec, RiskType
from app.repositories.evidence_repository import EvidenceRepository


class EvidenceRatingRepository:
    @staticmethod
    async def create_from_llm_rating(
        llm_rating: LLMDimensionRating, risk_type: RiskType, dimension_spec: RiskDimensionSpec
    ) -> EvidenceRating:
        """Create an EvidenceRating from LLM dimension rating data."""
        # Get the numeric score from the dimension mapping
        score = dimension_spec.mapping.get(llm_rating.scale_value, 0.0)

        evidence_rating_model = EvidenceRatingModel(
            risk_type_id=PydanticObjectId(risk_type.id),
            risk_dimension_spec_id=PydanticObjectId(dimension_spec.id),
            scale_value=llm_rating.scale_value,
            score=score,
            higher_is_riskier=dimension_spec.higher_is_riskier,
            weight=dimension_spec.weight,
        )

        await evidence_rating_model.insert()
        return EvidenceRating.from_model(evidence_rating_model)

    @staticmethod
    async def get_by_id(rating_id: str) -> EvidenceRating | None:
        """Get evidence rating by ID."""
        model = await EvidenceRatingModel.get(PydanticObjectId(rating_id))
        return EvidenceRating.from_model(model) if model else None

    @staticmethod
    async def get_by_evidence_id(evidence_id: str) -> list[EvidenceRating]:
        """Get all evidence ratings for a specific evidence."""
        # Since evidence ratings are stored as IDs in Evidence.evidence_ratings,
        # we need to get the evidence first to get its rating IDs
        evidence = await EvidenceRepository.get_by_id(evidence_id)

        if not evidence or not evidence.evidence_ratings:
            return []

        ratings = []
        for rating_id in evidence.evidence_ratings:
            rating = await EvidenceRatingRepository.get_by_id(rating_id)
            if rating:
                ratings.append(rating)

        return ratings
