from typing import List, Optional

from app.core.models import RiskDimensionSpec as RiskDimensionSpecModel
from app.core.types import RiskDimensionSpec as RiskDimensionSpecType


class RiskDimensionRepository:
    
    @staticmethod
    async def get_all() -> List[RiskDimensionSpecType]:
        risk_dimensions = await RiskDimensionSpecModel.find_all().to_list()
        return [RiskDimensionSpecType.from_model(risk_dimension) for risk_dimension in risk_dimensions]
    
    @staticmethod
    async def get_by_key(key: str) -> Optional[RiskDimensionSpecType]:
        risk_dimension = await RiskDimensionSpecModel.find_one(RiskDimensionSpecModel.key == key)
        return RiskDimensionSpecType.from_model(risk_dimension) if risk_dimension else None