from fastapi import APIRouter

from app.core.types import RiskDimensionSpec, RiskType
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.repositories.risk_type_repository import RiskTypeRepository

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/risk-types", response_model=list[RiskType])
async def get_risk_types():
    return await RiskTypeRepository.get_all()


@router.get("/dimension-specs", response_model=list[RiskDimensionSpec])
async def get_dimension_specs():
    return await RiskDimensionRepository.get_all()
