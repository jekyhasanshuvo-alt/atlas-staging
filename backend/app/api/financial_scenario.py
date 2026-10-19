from typing import Annotated

from fastapi import APIRouter, Depends

from app.schemas.financial_scenario import ScenarioInput, ScenarioResult
from app.services.financial_scenario import calculate
from app.services.security import verified

router = APIRouter(prefix="/api/v1/me/financial-scenarios", tags=["request-only scenarios"])


@router.post("/calculate", response_model=ScenarioResult)
def calculate_scenario(data: ScenarioInput, user: Annotated[object, Depends(verified)]):
    return calculate(data)
