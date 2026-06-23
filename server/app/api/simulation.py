from fastapi import APIRouter, HTTPException

from app.osm.mock_osm import get_demo_osm_json
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import BoundingBox
from app.schemas.simulation import (
    CreateDemoSimulationRequest,
    CreateSimulationRequest,
    SimulationSessionDto,
    SimulationStateDto,
    StepSimulationRequest,
)
from app.simulation.session_store import session_store

router = APIRouter()


@router.post("/create", response_model=SimulationSessionDto)
def create_simulation(payload: CreateSimulationRequest) -> SimulationSessionDto:
    engine = session_store.create(
        city_map=payload.city_map,
        mode=payload.mode,
        vehicles_count=payload.vehicles_count,
        pedestrians_count=payload.pedestrians_count,
        random_events_enabled=payload.random_events_enabled,
        seed=payload.seed,
    )

    return SimulationSessionDto(
        session_id=engine.session_id,
        city_map=engine.city_map,
        state=engine.state(),
    )


@router.post("/create-demo", response_model=SimulationSessionDto)
def create_demo_simulation(payload: CreateDemoSimulationRequest) -> SimulationSessionDto:
    bbox = BoundingBox(
        south=55.7500,
        west=37.6165,
        north=55.7520,
        east=37.6195,
    )
    city_map = normalize_osm_to_city_map(get_demo_osm_json(), bbox)

    engine = session_store.create(
        city_map=city_map,
        mode=payload.mode,
        vehicles_count=payload.vehicles_count,
        pedestrians_count=payload.pedestrians_count,
        random_events_enabled=payload.random_events_enabled,
        seed=payload.seed,
    )

    return SimulationSessionDto(
        session_id=engine.session_id,
        city_map=engine.city_map,
        state=engine.state(),
    )


@router.get("/{session_id}/state", response_model=SimulationStateDto)
def get_simulation_state(session_id: str) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)
    return engine.state()


@router.post("/{session_id}/step", response_model=SimulationStateDto)
def step_simulation(session_id: str, payload: StepSimulationRequest) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)
    return engine.step(payload.steps)


@router.post("/{session_id}/reset", response_model=SimulationStateDto)
def reset_simulation(session_id: str) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)
    return engine.reset()


@router.post("/{session_id}/mode/{mode}", response_model=SimulationStateDto)
def set_simulation_mode(session_id: str, mode: str) -> SimulationStateDto:
    if mode not in {"fixed", "rule_based", "ai"}:
        raise HTTPException(status_code=400, detail="mode must be fixed, rule_based or ai")

    engine = _get_engine_or_404(session_id)
    return engine.set_mode(mode)  # type: ignore[arg-type]


@router.delete("/{session_id}")
def delete_simulation(session_id: str) -> dict[str, bool]:
    deleted = session_store.delete(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="simulation session not found")

    return {"deleted": True}


@router.get("")
def list_simulations() -> dict[str, list[str]]:
    return {"sessions": session_store.list_ids()}


def _get_engine_or_404(session_id: str):
    engine = session_store.get(session_id)

    if engine is None:
        raise HTTPException(status_code=404, detail="simulation session not found")

    return engine