from app.core.models import RiskType as RiskTypeModel
from app.core.types import RiskType as RiskTypeType


class RiskTypeRepository:
    @staticmethod
    async def get_all() -> list[RiskTypeType]:
        risk_types = await RiskTypeModel.find_all().to_list()
        return [RiskTypeType.from_model(risk_type) for risk_type in risk_types]
