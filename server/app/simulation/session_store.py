from uuid import uuid4

from app.schemas.osm import CityMapDto
from app.schemas.simulation import SimulationMode
from app.simulation.engine import SimulationEngine


class SimulationSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SimulationEngine] = {}

    def create(
        self,
        city_map: CityMapDto,
        mode: SimulationMode,
        vehicles_count: int,
        pedestrians_count: int,
        random_events_enabled: bool,
        seed: int,
        signals_on_all_intersections: bool,
    ) -> SimulationEngine:
        session_id = f"session:{uuid4().hex}"

        engine = SimulationEngine(
            session_id=session_id,
            city_map=city_map,
            mode=mode,
            vehicles_count=vehicles_count,
            pedestrians_count=pedestrians_count,
            random_events_enabled=random_events_enabled,
            seed=seed,
            signals_on_all_intersections=signals_on_all_intersections,
        )

        self._sessions[session_id] = engine
        return engine

    def get(self, session_id: str) -> SimulationEngine | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False

        del self._sessions[session_id]
        return True

    def list_ids(self) -> list[str]:
        return sorted(self._sessions.keys())


session_store = SimulationSessionStore()