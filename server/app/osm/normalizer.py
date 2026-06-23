from typing import Any

from app.osm.parser import split_osm_elements
from app.schemas.osm import (
    BoundingBox,
    BuildingDto,
    CityMapDto,
    CoordinateDto,
    CrossingDto,
    InfrastructureDto,
    IntersectionDto,
    RoadDto,
    TrafficSignalDto,
)
from app.utils.geo import latlon_to_local_meters


DEFAULT_BUILDING_HEIGHT = 12.0
LEVEL_HEIGHT = 3.2

DRIVEABLE_HIGHWAYS = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "service",
    "living_street",
}

WALKABLE_HIGHWAYS = {
    "footway",
    "path",
    "pedestrian",
    "steps",
    "residential",
    "living_street",
    "service",
    "crossing",
}


def normalize_osm_to_city_map(osm_json: dict[str, Any], bbox: BoundingBox) -> CityMapDto:
    nodes, ways, _relations = split_osm_elements(osm_json)

    origin_lat = (bbox.south + bbox.north) / 2
    origin_lon = (bbox.west + bbox.east) / 2

    roads: list[RoadDto] = []
    buildings: list[BuildingDto] = []
    traffic_signals: list[TrafficSignalDto] = []
    crossings: list[CrossingDto] = []
    infrastructure: list[InfrastructureDto] = []

    for node in nodes.values():
        tags = node.get("tags", {})
        lat = float(node["lat"])
        lon = float(node["lon"])
        x, z = latlon_to_local_meters(lat, lon, origin_lat, origin_lon)

        if tags.get("highway") == "traffic_signals":
            traffic_signals.append(
                TrafficSignalDto(
                    id=f"signal:{node['id']}",
                    osm_id=str(node["id"]),
                    lat=lat,
                    lon=lon,
                    x=round(x, 3),
                    z=round(z, 3),
                )
            )

        if tags.get("highway") == "crossing":
            crossings.append(
                CrossingDto(
                    id=f"crossing:{node['id']}",
                    osm_id=str(node["id"]),
                    lat=lat,
                    lon=lon,
                    x=round(x, 3),
                    z=round(z, 3),
                )
            )

        infrastructure_kind = _extract_infrastructure_kind(tags)
        if infrastructure_kind is not None:
            infrastructure.append(
                InfrastructureDto(
                    id=f"infra:{node['id']}",
                    osm_id=str(node["id"]),
                    kind=infrastructure_kind,
                    name=tags.get("name"),
                    lat=lat,
                    lon=lon,
                    x=round(x, 3),
                    z=round(z, 3),
                )
            )

    for way in ways:
        tags = way.get("tags", {})
        coordinates = _way_coordinates(way, nodes, origin_lat, origin_lon)

        if len(coordinates) < 2:
            continue

        if "highway" in tags:
            highway_kind = tags.get("highway", "road")

            roads.append(
                RoadDto(
                    id=f"road:{way['id']}",
                    osm_id=str(way["id"]),
                    name=tags.get("name"),
                    kind=highway_kind,
                    lanes=_parse_lanes(tags.get("lanes")),
                    one_way=_parse_one_way(tags.get("oneway")),
                    max_speed_kph=_parse_speed(tags.get("maxspeed"), highway_kind),
                    is_driveable=highway_kind in DRIVEABLE_HIGHWAYS,
                    is_walkable=highway_kind in WALKABLE_HIGHWAYS,
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
                    id=f"building:{way['id']}",
                    osm_id=str(way["id"]),
                    height=round(height or DEFAULT_BUILDING_HEIGHT, 2),
                    levels=levels,
                    kind=tags.get("building"),
                    coordinates=coordinates,
                )
            )

    intersections = _detect_intersections(
        roads=roads,
        traffic_signals=traffic_signals,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )

    return CityMapDto(
        bbox=bbox,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        roads=roads,
        buildings=buildings,
        intersections=intersections,
        traffic_signals=traffic_signals,
        crossings=crossings,
        infrastructure=infrastructure,
    )


def _way_coordinates(
    way: dict,
    nodes: dict[int, dict],
    origin_lat: float,
    origin_lon: float,
) -> list[CoordinateDto]:
    result: list[CoordinateDto] = []

    for node_id in way.get("nodes", []):
        node = nodes.get(int(node_id))
        if node is None:
            continue

        lat = float(node["lat"])
        lon = float(node["lon"])
        x, z = latlon_to_local_meters(lat, lon, origin_lat, origin_lon)

        result.append(
            CoordinateDto(
                lat=lat,
                lon=lon,
                x=round(x, 3),
                z=round(z, 3),
            )
        )

    return result


def _detect_intersections(
    roads: list[RoadDto],
    traffic_signals: list[TrafficSignalDto],
    origin_lat: float,
    origin_lon: float,
) -> list[IntersectionDto]:
    point_to_roads: dict[str, set[str]] = {}
    point_to_latlon: dict[str, tuple[float, float]] = {}

    for road in roads:
        if not road.is_driveable:
            continue

        for coordinate in road.coordinates:
            key = f"{coordinate.lat:.7f}:{coordinate.lon:.7f}"
            point_to_roads.setdefault(key, set()).add(road.id)
            point_to_latlon[key] = (coordinate.lat, coordinate.lon)

    intersections: list[IntersectionDto] = []

    for index, (key, road_ids) in enumerate(point_to_roads.items()):
        if len(road_ids) < 2:
            continue

        lat, lon = point_to_latlon[key]
        x, z = latlon_to_local_meters(lat, lon, origin_lat, origin_lon)

        has_signal = any(
            abs(signal.lat - lat) < 0.00008 and abs(signal.lon - lon) < 0.00008
            for signal in traffic_signals
        )

        intersections.append(
            IntersectionDto(
                id=f"intersection:{index}",
                lat=lat,
                lon=lon,
                x=round(x, 3),
                z=round(z, 3),
                connected_road_ids=sorted(road_ids),
                has_signal=has_signal,
            )
        )

    return intersections


def _extract_infrastructure_kind(tags: dict) -> str | None:
    for key in ["amenity", "shop", "public_transport", "railway", "leisure"]:
        if key in tags:
            return f"{key}:{tags[key]}"
    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None

    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_lanes(value: str | None) -> int:
    parsed = _parse_int(value)
    if parsed is None:
        return 1
    return max(1, min(parsed, 8))


def _parse_one_way(value: str | None) -> bool:
    if value is None:
        return False

    return value.lower() in {"yes", "true", "1"}


def _parse_speed(value: str | None, highway_kind: str) -> float:
    if value is None:
        defaults = {
            "motorway": 100.0,
            "trunk": 80.0,
            "primary": 60.0,
            "secondary": 50.0,
            "tertiary": 40.0,
            "residential": 30.0,
            "living_street": 20.0,
            "service": 20.0,
        }
        return defaults.get(highway_kind, 30.0)

    cleaned = (
        value.lower()
        .replace("km/h", "")
        .replace("kph", "")
        .replace("mph", "")
        .strip()
    )

    try:
        return float(cleaned)
    except ValueError:
        return 30.0


def _parse_height(value: str | None) -> float | None:
    if value is None:
        return None

    cleaned = value.lower().replace("meters", "").replace("meter", "").replace("m", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None