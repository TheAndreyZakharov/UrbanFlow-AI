from threading import RLock
from uuid import uuid4

from app.schemas.osm import CityMapDto
from app.schemas.simulation import SimulationMode
from app.simulation.sumo_engine import SumoSimulationEngine
from app.simulation.sumo_scenario import clean_sumo_workspace


class SimulationSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SumoSimulationEngine] = {}
        self._lock = RLock()

    def create(
        self,
        city_map: CityMapDto,
        mode: SimulationMode,
        vehicles_count: int,
        pedestrians_count: int,
        random_events_enabled: bool,
        seed: int,
        signals_on_all_intersections: bool,
    ) -> SumoSimulationEngine:
        with self._lock:
            self.clear()
            clean_sumo_workspace()

            session_id = f"session:{uuid4().hex}"

            engine = SumoSimulationEngine(
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

    def get(self, session_id: str) -> SumoSimulationEngine | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False

            engine = self._sessions[session_id]
            engine.close()

            del self._sessions[session_id]
            return True

    def clear(self) -> None:
        with self._lock:
            for engine in self._sessions.values():
                engine.close()

            self._sessions.clear()

    def list_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._sessions.keys())


session_store = SimulationSessionStore()