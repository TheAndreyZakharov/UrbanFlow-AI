from app.osm.mock_osm import get_demo_osm_json
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import BoundingBox


def test_normalize_demo_osm_to_city_map() -> None:
    bbox = BoundingBox(
        south=55.7500,
        west=37.6165,
        north=55.7520,
        east=37.6195,
    )

    city_map = normalize_osm_to_city_map(get_demo_osm_json(), bbox)

    assert len(city_map.roads) == 3
    assert len(city_map.buildings) == 1
    assert len(city_map.intersections) >= 1
    assert len(city_map.traffic_signals) == 1
    assert len(city_map.crossings) == 1
    assert len(city_map.infrastructure) >= 2
    assert city_map.buildings[0].height == 16.0
    assert city_map.roads[0].coordinates[0].x != 0 or city_map.roads[0].coordinates[0].z != 0