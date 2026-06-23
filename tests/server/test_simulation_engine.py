from app.osm.mock_osm import get_demo_osm_json
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.editor import EditorPatchDto
from app.schemas.osm import BoundingBox
from app.simulation.engine import SimulationEngine


def _city_map():
    bbox = BoundingBox(
        south=55.7500,
        west=37.6165,
        north=55.7520,
        east=37.6195,
    )

    return normalize_osm_to_city_map(get_demo_osm_json(), bbox)


def test_simulation_engine_builds_state() -> None:
    engine = SimulationEngine(
        session_id="session:test",
        city_map=_city_map(),
        vehicles_count=10,
        pedestrians_count=15,
        seed=1,
    )

    state = engine.state()

    assert state.session_id == "session:test"
    assert state.tick == 0
    assert len(state.vehicles) == 10
    assert len(state.pedestrians) == 15
    assert len(state.signals) >= 1
    assert state.metrics.active_vehicles == 10


def test_simulation_engine_steps_forward() -> None:
    engine = SimulationEngine(
        session_id="session:test",
        city_map=_city_map(),
        vehicles_count=10,
        pedestrians_count=15,
        seed=1,
    )

    state = engine.step(steps=5)

    assert state.tick == 5
    assert state.metrics.active_vehicles == 10


def test_simulation_engine_applies_close_road_patch() -> None:
    city_map = _city_map()
    engine = SimulationEngine(
        session_id="session:test",
        city_map=city_map,
        vehicles_count=10,
        pedestrians_count=15,
        seed=1,
    )

    road_id = city_map.roads[0].id

    engine.apply_patch(
        EditorPatchDto(
            id="patch:1",
            kind="close_road",
            target_id=road_id,
            payload={},
        )
    )

    closed_edges = [
        edge for edge in engine.city_graph.edges.values()
        if edge.road_id == road_id and edge.is_closed
    ]

    assert len(closed_edges) > 0