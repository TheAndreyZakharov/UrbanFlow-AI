from typing import Any

from app.osm.parser import split_osm_elements
from app.schemas.osm import BoundingBox, BuildingDto, CityMapDto, IntersectionDto, RoadDto


DEFAULT_BUILDING_HEIGHT = 12.0
LEVEL_HEIGHT = 3.2


def normalize_osm_to_city_map(osm_json: dict[str, Any], bbox: BoundingBox) -> CityMapDto:
    nodes, ways = split_osm_elements(osm_json)

    roads: list[RoadDto] = []
    buildings: list[BuildingDto] = []

    for way in ways:
        tags = way.get("tags", {})
        coordinates = _way_coordinates(way, nodes)

        if len(coordinates) < 2:
            continue

        if "highway" in tags:
            roads.append(
                RoadDto(
                    id=str(way["id"]),
                    name=tags.get("name"),
                    kind=tags.get("highway", "road"),
                    coordinates=coordinates,
                )
            )

        if "building" in tags:
            levels = _parse_int(tags.get("building:levels"))
            height = _parse_height(tags.get("height"))

            if height is None and levels is not None:
                height = levels * LEVEL_HEIGHT

            buildings.append(
                BuildingDto(
                    id=str(way["id"]),
                    height=height or DEFAULT_BUILDING_HEIGHT,
                    levels=levels,
                    coordinates=coordinates,
                )
            )

    intersections = _detect_basic_intersections(roads)

    return CityMapDto(
        bbox=bbox,
        roads=roads,
        buildings=buildings,
        intersections=intersections,
    )


def _way_coordinates(way: dict, nodes: dict[int, dict]) -> list[list[float]]:
    result: list[list[float]] = []

    for node_id in way.get("nodes", []):
        node = nodes.get(int(node_id))
        if node is None:
            continue

        result.append([float(node["lat"]), float(node["lon"])])

    return result


def _detect_basic_intersections(roads: list[RoadDto]) -> list[IntersectionDto]:
    point_to_roads: dict[str, set[str]] = {}

    for road in roads:
        for lat, lon in road.coordinates:
            key = f"{lat:.7f}:{lon:.7f}"
            point_to_roads.setdefault(key, set()).add(road.id)

    intersections: list[IntersectionDto] = []

    for index, (key, road_ids) in enumerate(point_to_roads.items()):
        if len(road_ids) < 2:
            continue

        lat_text, lon_text = key.split(":")

        intersections.append(
            IntersectionDto(
                id=f"intersection-{index}",
                lat=float(lat_text),
                lon=float(lon_text),
                connected_road_ids=sorted(road_ids),
            )
        )

    return intersections


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except ValueError:
        return None


def _parse_height(value: str | None) -> float | None:
    if value is None:
        return None

    cleaned = value.lower().replace("meters", "").replace("meter", "").replace("m", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None