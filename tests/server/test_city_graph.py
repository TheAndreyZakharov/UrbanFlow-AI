from app.osm.mock_osm import get_demo_osm_json
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import BoundingBox
from app.simulation.city_graph import build_city_graph


def test_build_city_graph_from_demo_city() -> None:
    bbox = BoundingBox(
        south=55.7500,
        west=37.6165,
        north=55.7520,
        east=37.6195,
    )

    city_map = normalize_osm_to_city_map(get_demo_osm_json(), bbox)
    city_graph = build_city_graph(city_map)

    assert len(city_graph.nodes) >= 5
    assert len(city_graph.edges) >= 4
    assert len(city_graph.road_to_edge_ids) == 3
    assert all(edge.length_meters > 0 for edge in city_graph.edges.values())
    assert all(edge.max_speed_mps > 0 for edge in city_graph.edges.values())