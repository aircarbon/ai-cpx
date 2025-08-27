from fastapi import APIRouter
from typing import List
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.core.types import RiskType, RiskDimensionSpec

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/risk-types", response_model=List[RiskType])
async def get_risk_types():
    """Get all risk types with name, description, and weight"""
    return await RiskTypeRepository.get_all()


@router.get("/dimension-specs", response_model=List[RiskDimensionSpec])
async def get_dimension_specs():
    """Get all risk dimension specifications"""
    return await RiskDimensionRepository.get_all()