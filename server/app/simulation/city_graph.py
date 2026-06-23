from dataclasses import dataclass

from app.schemas.osm import CityMapDto, CoordinateDto
from app.utils.geo import distance_meters


@dataclass
class GraphNode:
    id: str
    lat: float
    lon: float
    x: float
    z: float
    connected_edge_ids: list[str]


@dataclass
class GraphEdge:
    id: str
    road_id: str
    from_node_id: str
    to_node_id: str
    length_meters: float
    max_speed_mps: float
    coordinates: list[CoordinateDto]
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

        road_to_edge_ids[road.id] = []

        for index, coordinate in enumerate(road.coordinates):
            node_id = coordinate_node_id(coordinate)

            if node_id not in nodes:
                nodes[node_id] = GraphNode(
                    id=node_id,
                    lat=coordinate.lat,
                    lon=coordinate.lon,
                    x=coordinate.x,
                    z=coordinate.z,
                    connected_edge_ids=[],
                )

            if index == 0:
                continue

            previous_coordinate = road.coordinates[index - 1]
            previous_node_id = coordinate_node_id(previous_coordinate)

            edge_id = f"edge:{road.id}:{index - 1}-{index}"
            length = distance_meters(
                previous_coordinate.lat,
                previous_coordinate.lon,
                coordinate.lat,
                coordinate.lon,
            )

            edge = GraphEdge(
                id=edge_id,
                road_id=road.id,
                from_node_id=previous_node_id,
                to_node_id=node_id,
                length_meters=round(max(length, 0.1), 2),
                max_speed_mps=round(road.max_speed_kph / 3.6, 2),
                coordinates=[previous_coordinate, coordinate],
            )

            edges[edge_id] = edge
            road_to_edge_ids[road.id].append(edge_id)
            nodes[previous_node_id].connected_edge_ids.append(edge_id)
            nodes[node_id].connected_edge_ids.append(edge_id)

    return CityGraph(
        nodes=nodes,
        edges=edges,
        road_to_edge_ids=road_to_edge_ids,
    )


def coordinate_node_id(coordinate: CoordinateDto) -> str:
    return f"node:{coordinate.lat:.7f}:{coordinate.lon:.7f}"