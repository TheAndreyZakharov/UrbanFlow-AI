from fastapi import APIRouter, HTTPException

from app.schemas.simulation import (
    CreateSimulationRequest,
    SimulationSessionDto,
    SimulationStateDto,
    StepSimulationRequest,
    UpdateSimulationSettingsRequest,
)
from app.simulation.session_store import session_store

router = APIRouter()


@router.post("/create", response_model=SimulationSessionDto)
def create_simulation(payload: CreateSimulationRequest) -> SimulationSessionDto:
    try:
        engine = session_store.create(
            city_map=payload.city_map,
            mode=payload.mode,
            vehicles_count=payload.vehicles_count,
            pedestrians_count=payload.pedestrians_count,
            random_events_enabled=payload.random_events_enabled,
            seed=payload.seed,
            signals_on_all_intersections=payload.signals_on_all_intersections,
        )
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"simulation create failed: {error}") from error

    return SimulationSessionDto(
        session_id=engine.session_id,
        city_map=engine.city_map,
        state=engine.state(),
    )


@router.get("/{session_id}/state", response_model=SimulationStateDto)
def get_simulation_state(session_id: str) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)
    return engine.state()


@router.patch("/{session_id}/settings", response_model=SimulationStateDto)
def update_simulation_settings(
    session_id: str,
    payload: UpdateSimulationSettingsRequest,
) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)

    try:
        return engine.update_settings(
            vehicles_count=payload.vehicles_count,
            pedestrians_count=payload.pedestrians_count,
            signals_on_all_intersections=payload.signals_on_all_intersections,
        )
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"simulation settings failed: {error}") from error


@router.post("/{session_id}/step", response_model=SimulationStateDto)
def step_simulation(session_id: str, payload: StepSimulationRequest) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)

    try:
        return engine.step(payload.steps)
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"simulation step failed: {error}") from error


@router.post("/{session_id}/traffic-light-override/{override}", response_model=SimulationStateDto)
def set_traffic_light_override(session_id: str, override: str) -> SimulationStateDto:
    if override not in {"sumo", "red", "yellow", "green"}:
        raise HTTPException(status_code=400, detail="override must be sumo, red, yellow or green")

    engine = _get_engine_or_404(session_id)
    return engine.set_traffic_light_override(override)  # type: ignore[arg-type]


@router.post("/{session_id}/reset", response_model=SimulationStateDto)
def reset_simulation(session_id: str) -> SimulationStateDto:
    engine = _get_engine_or_404(session_id)

    try:
        return engine.reset()
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"simulation reset failed: {error}") from error


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