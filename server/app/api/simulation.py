from fastapi import APIRouter

from app.schemas.simulation import SimulationStateDto
from app.simulation.engine import SimulationEngine

router = APIRouter()

engine = SimulationEngine()


@router.post("/step", response_model=SimulationStateDto)
def step_simulation() -> SimulationStateDto:
    return engine.step()