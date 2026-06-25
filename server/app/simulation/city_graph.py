from dataclasses import dataclass
from math import atan2

from app.schemas.osm import CityMapDto, CoordinateDto
from app.utils.geo import distance_meters


@dataclass
class GraphNode:
    id: str
    lat: float
    lon: float
    x: float
    z: float
    outgoing_edge_ids: list[str]
    incoming_edge_ids: list[str]


@dataclass
class GraphEdge:
    id: str
    road_id: str
    from_node_id: str
    to_node_id: str
    length_meters: float
    max_speed_mps: float
    lanes: int
    heading_rad: float
    coordinates: list[CoordinateDto]
    bridge: str | None
    tunnel: str | None
    layer: int | None
    start_elevation_m: float
    end_elevation_m: float
    elevation_m: float
    is_closed: bool = False


@dataclass
class CityGraph:
    nodes: dict[str, GraphNode]
    edges: dict[str, GraphEdge]
    road_to_edge_ids: dict[str, list[str]]


def build_city_graph(city_map: CityMapDto) -> CityGraph:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    road_to_edge_ids: dict[str, list[str]] = {}

    for road in city_map.roads:
        if not road.is_driveable:
            continue

        road_to_edge_ids.setdefault(road.id, [])

        for index, coordinate in enumerate(road.coordinates):
            node_id = coordinate_node_id(coordinate)

            if node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    lat=coordinate.lat,
                    lon=coordinate.lon,
                    x=coordinate.x,
                    z=coordinate.z,
                    outgoing_edge_ids=[],
                    incoming_edge_ids=[],
                )

            if index == 0:
                continue

            previous_coordinate = road.coordinates[index - 1]
            previous_node_id = coordinate_node_id(previous_coordinate)

            _add_edge(
                edge_id=f"edge:{road.id}:{index - 1}-{index}:fwd",
                road_id=road.id,
                from_node_id=previous_node_id,
                to_node_id=node_id,
                start=previous_coordinate,
                end=coordinate,
                max_speed_mps=round(road.max_speed_kph / 3.6, 2),
                lanes=road.lanes,
                bridge=road.bridge,
                tunnel=road.tunnel,
                layer=road.layer,
                start_elevation_m=feature_elevation_at_fraction(
                    bridge=road.bridge,
                    tunnel=road.tunnel,
                    layer=road.layer,
                    fraction=(index - 1) / max(1, len(road.coordinates) - 1),
                ),
                end_elevation_m=feature_elevation_at_fraction(
                    bridge=road.bridge,
                    tunnel=road.tunnel,
                    layer=road.layer,
                    fraction=index / max(1, len(road.coordinates) - 1),
                ),
                nodes=nodes,
                edges=edges,
                road_to_edge_ids=road_to_edge_ids,
            )

            if not road.one_way:
                _add_edge(
                    edge_id=f"edge:{road.id}:{index}-{index - 1}:rev",
                    road_id=road.id,
                    from_node_id=node_id,
                    to_node_id=previous_node_id,
                    start=coordinate,
                    end=previous_coordinate,
                    max_speed_mps=round(road.max_speed_kph / 3.6, 2),
                    lanes=road.lanes,
                    bridge=road.bridge,
                    tunnel=road.tunnel,
                    layer=road.layer,
                    start_elevation_m=feature_elevation_at_fraction(
                        bridge=road.bridge,
                        tunnel=road.tunnel,
                        layer=road.layer,
                        fraction=index / max(1, len(road.coordinates) - 1),
                    ),
                    end_elevation_m=feature_elevation_at_fraction(
                        bridge=road.bridge,
                        tunnel=road.tunnel,
                        layer=road.layer,
                        fraction=(index - 1) / max(1, len(road.coordinates) - 1),
                    ),
                    nodes=nodes,
                    edges=edges,
                    road_to_edge_ids=road_to_edge_ids,
                )

    return CityGraph(
        nodes=nodes,
        edges=edges,
        road_to_edge_ids=road_to_edge_ids,
    )


def _add_edge(
    edge_id: str,
    road_id: str,
    from_node_id: str,
    to_node_id: str,
    start: CoordinateDto,
    end: CoordinateDto,
    max_speed_mps: float,
    lanes: int,
    bridge: str | None,
    tunnel: str | None,
    layer: int | None,
    start_elevation_m: float,
    end_elevation_m: float,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    road_to_edge_ids: dict[str, list[str]],
) -> None:
    length = distance_meters(start.lat, start.lon, end.lat, end.lon)

    if length < 1.0:
        return

    heading = atan2(end.z - start.z, end.x - start.x)

    edge = GraphEdge(
        id=edge_id,
        road_id=road_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        length_meters=round(length, 2),
        max_speed_mps=max(2.0, max_speed_mps),
        lanes=max(1, lanes),
        heading_rad=heading,
        coordinates=[start, end],
        bridge=bridge,
        tunnel=tunnel,
        layer=layer,
        start_elevation_m=round(start_elevation_m, 3),
        end_elevation_m=round(end_elevation_m, 3),
        elevation_m=round((start_elevation_m + end_elevation_m) / 2, 3),
    )

    edges[edge_id] = edge
    road_to_edge_ids.setdefault(road_id, []).append(edge_id)
    nodes[from_node_id].outgoing_edge_ids.append(edge_id)
    nodes[to_node_id].incoming_edge_ids.append(edge_id)


def coordinate_node_id(coordinate: CoordinateDto) -> str:
    return f"node:{coordinate.lat:.7f}:{coordinate.lon:.7f}"


def feature_elevation_at_fraction(
    bridge: str | None,
    tunnel: str | None,
    layer: int | None,
    fraction: float,
) -> float:
    target = feature_target_elevation_m(bridge=bridge, tunnel=tunnel, layer=layer)

    if target == 0:
        return 0.0

    ramp = ramp_profile(fraction)

    return target * ramp


def feature_target_elevation_m(
    bridge: str | None,
    tunnel: str | None,
    layer: int | None,
) -> float:
    normalized_bridge = _normalize_osm_bool_text(bridge)
    normalized_tunnel = _normalize_osm_bool_text(tunnel)
    safe_layer = layer or 0

    if normalized_tunnel:
        return -min(3, max(1, abs(safe_layer) or 1)) * 3.4

    if normalized_bridge or safe_layer > 0:
        return max(1, safe_layer) * 7.0

    if safe_layer < 0:
        return -min(3, abs(safe_layer)) * 3.4

    return 0.0


def ramp_profile(fraction: float) -> float:
    fraction = max(0.0, min(1.0, fraction))
    ramp_size = 0.22

    if fraction <= ramp_size:
        return smoothstep(fraction / ramp_size)

    if fraction >= 1.0 - ramp_size:
        return smoothstep((1.0 - fraction) / ramp_size)

    return 1.0


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def _normalize_osm_bool_text(value: str | None) -> bool:
    if value is None:
        return False

    normalized = value.strip().lower()

    if not normalized:
        return False

    return normalized not in {"no", "false", "0"}