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
    RailLineDto,
    RoadDto,
    SurfaceDto,
    TrafficSignalDto,
    TransitStopDto,
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
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
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
    "track",
    "cycleway",
}

def normalize_osm_to_city_map(osm_json: dict[str, Any], bbox: BoundingBox) -> CityMapDto:
    nodes, ways, relations = split_osm_elements(osm_json)
    ways_by_id = {int(way["id"]): way for way in ways if "id" in way}
    way_route_refs, way_route_types = _build_way_route_indices(relations)

    origin_lat = (bbox.south + bbox.north) / 2
    origin_lon = (bbox.west + bbox.east) / 2

    roads: list[RoadDto] = []
    buildings: list[BuildingDto] = []
    surfaces: list[SurfaceDto] = []
    rail_lines: list[RailLineDto] = []
    transit_stops: list[TransitStopDto] = []
    traffic_signals: list[TrafficSignalDto] = []
    crossings: list[CrossingDto] = []
    infrastructure: list[InfrastructureDto] = []

    for node in nodes.values():
        tags = node.get("tags", {})
        lat = node.get("lat")
        lon = node.get("lon")

        if lat is None or lon is None:
            continue

        lat = float(lat)
        lon = float(lon)

        if not _point_inside_bbox(lat, lon, bbox):
            continue

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
                    signal_type=tags.get("traffic_signals"),
                    direction=tags.get("traffic_signals:direction") or tags.get("direction"),
                    tags=_clean_tags(tags),
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
                    tags=_clean_tags(tags),
                )
            )

        transit_stop_kind = _extract_transit_stop_kind(tags)
        if transit_stop_kind is not None:
            transit_stops.append(
                TransitStopDto(
                    id=f"transit_stop:node:{node['id']}",
                    osm_id=str(node["id"]),
                    kind=transit_stop_kind,
                    name=tags.get("name"),
                    route_refs=_parse_route_refs(tags),
                    lat=lat,
                    lon=lon,
                    x=round(x, 3),
                    z=round(z, 3),
                    tags=_clean_tags(tags),
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
                    tags=_clean_tags(tags),
                )
            )

    for way in ways:
        tags = way.get("tags", {})
        raw_latlon = _element_latlon(way, nodes, ways_by_id)

        if len(raw_latlon) < 2:
            continue

        if "highway" in tags:
            clipped_parts = _clip_polyline_to_bbox(raw_latlon, bbox)

            for part_index, clipped_latlon in enumerate(clipped_parts):
                if len(clipped_latlon) < 2:
                    continue

                highway_kind = tags.get("highway", "road")
                coordinates = _coordinates_from_latlon(clipped_latlon, origin_lat, origin_lon)

                roads.append(
                    RoadDto(
                        id=f"road:way:{way['id']}:{part_index}",
                        osm_id=str(way["id"]),
                        name=tags.get("name"),
                        kind=highway_kind,
                        lanes=_parse_lanes(tags.get("lanes")),
                        lanes_forward=_parse_int(tags.get("lanes:forward")),
                        lanes_backward=_parse_int(tags.get("lanes:backward")),
                        turn_lanes=tags.get("turn:lanes"),
                        turn_lanes_forward=tags.get("turn:lanes:forward"),
                        turn_lanes_backward=tags.get("turn:lanes:backward"),
                        route_refs=way_route_refs.get(int(way["id"]), []),
                        route_types=way_route_types.get(int(way["id"]), []),
                        one_way=_parse_one_way(tags.get("oneway")),
                        max_speed_kph=_parse_speed(tags.get("maxspeed"), highway_kind),
                        surface=tags.get("surface"),
                        access=tags.get("access") or tags.get("vehicle") or tags.get("motor_vehicle"),
                        bridge=tags.get("bridge"),
                        tunnel=tags.get("tunnel"),
                        layer=_parse_int(tags.get("layer")),
                        is_driveable=_is_driveable_highway(highway_kind, tags),
                        is_walkable=_is_walkable_highway(highway_kind, tags),
                        coordinates=coordinates,
                        tags=_clean_tags(tags),
                    )
                )

        rail_kind = _extract_rail_kind(tags)
        if rail_kind is not None:
            clipped_parts = _clip_polyline_to_bbox(raw_latlon, bbox)

            for part_index, clipped_latlon in enumerate(clipped_parts):
                if len(clipped_latlon) < 2:
                    continue

                rail_lines.append(
                    RailLineDto(
                        id=f"rail:way:{way['id']}:{part_index}",
                        osm_id=str(way["id"]),
                        kind=rail_kind,
                        name=tags.get("name"),
                        is_tram=rail_kind in {"tram", "light_rail"},
                        is_service=tags.get("service") is not None,
                        route_refs=way_route_refs.get(int(way["id"]), []),
                        route_types=way_route_types.get(int(way["id"]), []),
                        bridge=tags.get("bridge"),
                        tunnel=tags.get("tunnel"),
                        layer=_parse_int(tags.get("layer")),
                        coordinates=_coordinates_from_latlon(clipped_latlon, origin_lat, origin_lon),
                        tags=_clean_tags(tags),
                    )
                )

        if _is_building(tags):
            _append_building(
                buildings=buildings,
                element_id=f"way:{way['id']}",
                osm_id=str(way["id"]),
                tags=tags,
                raw_latlon=raw_latlon,
                bbox=bbox,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        _append_surface_from_tags(
            surfaces=surfaces,
            element_id=f"way:{way['id']}",
            osm_id=str(way["id"]),
            tags=tags,
            raw_latlon=raw_latlon,
            bbox=bbox,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )

        transit_stop_kind = _extract_transit_stop_kind(tags)
        if transit_stop_kind is not None:
            center = _polygon_center(raw_latlon)

            if center is not None and _point_inside_bbox(center[0], center[1], bbox):
                x, z = latlon_to_local_meters(center[0], center[1], origin_lat, origin_lon)

                transit_stops.append(
                    TransitStopDto(
                        id=f"transit_stop:way:{way['id']}",
                        osm_id=str(way["id"]),
                        kind=transit_stop_kind,
                        name=tags.get("name"),
                        route_refs=_parse_route_refs(tags),
                        lat=center[0],
                        lon=center[1],
                        x=round(x, 3),
                        z=round(z, 3),
                        tags=_clean_tags(tags),
                    )
                )

        infrastructure_kind = _extract_infrastructure_kind(tags)
        if infrastructure_kind is not None:
            center = _polygon_center(raw_latlon)
            if center is not None and _point_inside_bbox(center[0], center[1], bbox):
                x, z = latlon_to_local_meters(center[0], center[1], origin_lat, origin_lon)
                infrastructure.append(
                    InfrastructureDto(
                        id=f"infra:way:{way['id']}",
                        osm_id=str(way["id"]),
                        kind=infrastructure_kind,
                        name=tags.get("name"),
                        lat=center[0],
                        lon=center[1],
                        x=round(x, 3),
                        z=round(z, 3),
                    )
                )

    for relation in relations:
        tags = relation.get("tags", {})
        raw_latlon = _element_latlon(relation, nodes, ways_by_id)

        if len(raw_latlon) < 2:
            continue

        if _is_building(tags):
            _append_relation_buildings(
                buildings=buildings,
                relation=relation,
                nodes=nodes,
                ways_by_id=ways_by_id,
                bbox=bbox,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        _append_surface_from_tags(
            surfaces=surfaces,
            element_id=f"relation:{relation['id']}",
            osm_id=str(relation["id"]),
            tags=tags,
            raw_latlon=raw_latlon,
            bbox=bbox,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )

        infrastructure_kind = _extract_infrastructure_kind(tags)
        if infrastructure_kind is not None:
            center = _polygon_center(raw_latlon)
            if center is not None and _point_inside_bbox(center[0], center[1], bbox):
                x, z = latlon_to_local_meters(center[0], center[1], origin_lat, origin_lon)
                infrastructure.append(
                    InfrastructureDto(
                        id=f"infra:relation:{relation['id']}",
                        osm_id=str(relation["id"]),
                        kind=infrastructure_kind,
                        name=tags.get("name"),
                        lat=center[0],
                        lon=center[1],
                        x=round(x, 3),
                        z=round(z, 3),
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
        surfaces=surfaces,
        rail_lines=rail_lines,
        transit_stops=transit_stops,
        intersections=intersections,
        traffic_signals=traffic_signals,
        crossings=crossings,
        infrastructure=infrastructure,
    )

def _build_way_route_indices(
    relations: list[dict],
) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    route_refs_by_way: dict[int, set[str]] = {}
    route_types_by_way: dict[int, set[str]] = {}

    for relation in relations:
        tags = relation.get("tags", {})
        route_type = tags.get("route") or tags.get("route_master")

        if route_type not in {
            "bus",
            "tram",
            "trolleybus",
            "share_taxi",
            "minibus",
            "coach",
            "train",
            "light_rail",
        }:
            continue

        route_ref = _route_reference(tags, route_type)

        for member in relation.get("members", []):
            if member.get("type") != "way":
                continue

            ref = member.get("ref")

            if ref is None:
                continue

            way_id = int(ref)

            route_refs_by_way.setdefault(way_id, set()).add(route_ref)
            route_types_by_way.setdefault(way_id, set()).add(route_type)

    return (
        {way_id: sorted(values) for way_id, values in route_refs_by_way.items()},
        {way_id: sorted(values) for way_id, values in route_types_by_way.items()},
    )


def _route_reference(tags: dict, route_type: str) -> str:
    for key in ["ref", "name", "from"]:
        value = tags.get(key)

        if value:
            return str(value)

    return route_type

def _append_building(
    buildings: list[BuildingDto],
    element_id: str,
    osm_id: str,
    tags: dict,
    raw_latlon: list[tuple[float, float]],
    bbox: BoundingBox,
    origin_lat: float,
    origin_lon: float,
    holes_latlon: list[list[tuple[float, float]]] | None = None,
) -> None:
    polygon = _closed_polygon(raw_latlon)
    clipped_polygon = _clip_polygon_to_bbox(polygon, bbox)

    if len(clipped_polygon) < 4:
        return

    clipped_holes: list[list[CoordinateDto]] = []

    for hole_latlon in holes_latlon or []:
        hole_polygon = _closed_polygon(hole_latlon)
        clipped_hole = _clip_polygon_to_bbox(hole_polygon, bbox)

        if len(clipped_hole) < 4:
            continue

        hole_center = _polygon_center(clipped_hole)

        if hole_center is None:
            continue

        if not _point_in_polygon_latlon(hole_center, clipped_polygon):
            continue

        clipped_holes.append(_coordinates_from_latlon(clipped_hole, origin_lat, origin_lon))

    levels = _parse_int(tags.get("building:levels"))
    height = _parse_height(tags.get("height"))

    if height is None:
        height = _parse_height(tags.get("building:height"))

    if height is None and levels is not None:
        height = levels * LEVEL_HEIGHT

    buildings.append(
        BuildingDto(
            id=f"building:{element_id}",
            osm_id=osm_id,
            height=round(height or _estimate_building_height(tags), 2),
            levels=levels,
            kind=tags.get("building") or tags.get("building:part"),
            coordinates=_coordinates_from_latlon(clipped_polygon, origin_lat, origin_lon),
            holes=clipped_holes,
            tags=_clean_tags(tags),
        )
    )

def _append_relation_buildings(
    buildings: list[BuildingDto],
    relation: dict,
    nodes: dict[int, dict],
    ways_by_id: dict[int, dict],
    bbox: BoundingBox,
    origin_lat: float,
    origin_lon: float,
) -> None:
    tags = relation.get("tags", {})
    outer_rings, inner_rings = _relation_polygon_rings(relation, nodes, ways_by_id)

    if not outer_rings:
        raw_latlon = _element_latlon(relation, nodes, ways_by_id)

        if len(raw_latlon) >= 3:
            _append_building(
                buildings=buildings,
                element_id=f"relation:{relation['id']}",
                osm_id=str(relation["id"]),
                tags=tags,
                raw_latlon=raw_latlon,
                bbox=bbox,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        return

    for outer_index, outer_ring in enumerate(outer_rings):
        holes_for_outer: list[list[tuple[float, float]]] = []

        for inner_ring in inner_rings:
            inner_center = _polygon_center(inner_ring)

            if inner_center is None:
                continue

            if _point_in_polygon_latlon(inner_center, outer_ring):
                holes_for_outer.append(inner_ring)

        _append_building(
            buildings=buildings,
            element_id=f"relation:{relation['id']}:{outer_index}",
            osm_id=str(relation["id"]),
            tags=tags,
            raw_latlon=outer_ring,
            holes_latlon=holes_for_outer,
            bbox=bbox,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
        )

def _relation_polygon_rings(
    relation: dict,
    nodes: dict[int, dict],
    ways_by_id: dict[int, dict],
) -> tuple[list[list[tuple[float, float]]], list[list[tuple[float, float]]]]:
    outer_segments: list[list[tuple[float, float]]] = []
    inner_segments: list[list[tuple[float, float]]] = []

    for member in relation.get("members", []):
        if member.get("type") != "way":
            continue

        role = str(member.get("role", "")).strip().lower()
        way = ways_by_id.get(int(member.get("ref", -1)))

        if way is None:
            continue

        coordinates = _element_latlon(way, nodes, ways_by_id)

        if len(coordinates) < 2:
            continue

        if role in {"inner", "hole"}:
            inner_segments.append(coordinates)
        else:
            outer_segments.append(coordinates)

    return _stitch_polygon_rings(outer_segments), _stitch_polygon_rings(inner_segments)

def _stitch_polygon_rings(
    segments: list[list[tuple[float, float]]],
) -> list[list[tuple[float, float]]]:
    pool = [_dedupe_adjacent_points(segment) for segment in segments if len(segment) >= 2]
    rings: list[list[tuple[float, float]]] = []

    while pool:
        current = pool.pop(0)
        changed = True

        while changed:
            changed = False

            for index, segment in enumerate(pool):
                if _same_point(current[-1], segment[0]):
                    current.extend(segment[1:])
                    pool.pop(index)
                    changed = True
                    break

                if _same_point(current[-1], segment[-1]):
                    current.extend(reversed(segment[:-1]))
                    pool.pop(index)
                    changed = True
                    break

                if _same_point(current[0], segment[-1]):
                    current = [*segment[:-1], *current]
                    pool.pop(index)
                    changed = True
                    break

                if _same_point(current[0], segment[0]):
                    current = [*reversed(segment[1:]), *current]
                    pool.pop(index)
                    changed = True
                    break

        closed = _closed_polygon(current)

        if len(closed) >= 4:
            rings.append(closed)

    return rings

def _point_in_polygon_latlon(
    point: tuple[float, float],
    polygon: list[tuple[float, float]],
) -> bool:
    lat, lon = point
    inside = False

    for index in range(len(polygon)):
        lat1, lon1 = polygon[index]
        lat2, lon2 = polygon[index - 1]

        intersects = (lat1 > lat) != (lat2 > lat)

        if not intersects:
            continue

        lon_at_lat = (lon2 - lon1) * (lat - lat1) / ((lat2 - lat1) or 0.000000000001) + lon1

        if lon < lon_at_lat:
            inside = not inside

    return inside

def _append_surface(
    surfaces: list[SurfaceDto],
    element_id: str,
    osm_id: str,
    tags: dict,
    raw_latlon: list[tuple[float, float]],
    surface_kind: str,
    bbox: BoundingBox,
    origin_lat: float,
    origin_lon: float,
) -> None:
    polygon = _closed_polygon(raw_latlon)
    clipped_polygon = _clip_polygon_to_bbox(polygon, bbox)

    if len(clipped_polygon) < 4:
        return

    surfaces.append(
        SurfaceDto(
            id=f"surface:{element_id}",
            osm_id=osm_id,
            kind=surface_kind,
            name=tags.get("name"),
            coordinates=_coordinates_from_latlon(clipped_polygon, origin_lat, origin_lon),
        )
    )

def _element_latlon(
    element: dict,
    nodes: dict[int, dict],
    ways_by_id: dict[int, dict],
) -> list[tuple[float, float]]:
    geometry = element.get("geometry")

    if isinstance(geometry, list) and geometry:
        result: list[tuple[float, float]] = []

        for point in geometry:
            lat = point.get("lat")
            lon = point.get("lon")

            if lat is None or lon is None:
                continue

            result.append((float(lat), float(lon)))

        if result:
            return result

    if element.get("type") == "way":
        return _way_latlon(element, nodes)

    if element.get("type") == "relation":
        return _relation_outer_latlon(element, nodes, ways_by_id)

    return []

def _relation_outer_latlon(
    relation: dict,
    nodes: dict[int, dict],
    ways_by_id: dict[int, dict],
) -> list[tuple[float, float]]:
    rings: list[list[tuple[float, float]]] = []

    for member in relation.get("members", []):
        if member.get("type") != "way":
            continue

        role = member.get("role", "")
        if role not in {"", "outer"}:
            continue

        way = ways_by_id.get(int(member.get("ref", -1)))
        if way is None:
            continue

        coordinates = _element_latlon(way, nodes, ways_by_id)

        if len(coordinates) >= 2:
            rings.append(coordinates)

    if not rings:
        return []

    stitched = rings.pop(0)

    while rings:
        changed = False

        for index, ring in enumerate(rings):
            if _same_point(stitched[-1], ring[0]):
                stitched.extend(ring[1:])
                rings.pop(index)
                changed = True
                break

            if _same_point(stitched[-1], ring[-1]):
                stitched.extend(reversed(ring[:-1]))
                rings.pop(index)
                changed = True
                break

            if _same_point(stitched[0], ring[-1]):
                stitched = [*ring[:-1], *stitched]
                rings.pop(index)
                changed = True
                break

            if _same_point(stitched[0], ring[0]):
                stitched = [*reversed(ring[1:]), *stitched]
                rings.pop(index)
                changed = True
                break

        if not changed:
            break

    return stitched

def _way_latlon(way: dict, nodes: dict[int, dict]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []

    for node_id in way.get("nodes", []):
        node = nodes.get(int(node_id))
        if node is None:
            continue

        lat = node.get("lat")
        lon = node.get("lon")

        if lat is None or lon is None:
            continue

        result.append((float(lat), float(lon)))

    return result

def _coordinates_from_latlon(
    points: list[tuple[float, float]],
    origin_lat: float,
    origin_lon: float,
) -> list[CoordinateDto]:
    result: list[CoordinateDto] = []

    for lat, lon in _dedupe_adjacent_points(points):
        x, z = latlon_to_local_meters(lat, lon, origin_lat, origin_lon)

        result.append(
            CoordinateDto(
                lat=round(lat, 8),
                lon=round(lon, 8),
                x=round(x, 3),
                z=round(z, 3),
            )
        )

    return result

def _dedupe_adjacent_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []

    for point in points:
        if result and _same_point(result[-1], point):
            continue
        result.append(point)

    return result

def _closed_polygon(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []

    cleaned = _dedupe_adjacent_points(points)

    if len(cleaned) < 3:
        return []

    if _same_point(cleaned[0], cleaned[-1]):
        return cleaned

    return [*cleaned, cleaned[0]]

def _point_inside_bbox(lat: float, lon: float, bbox: BoundingBox) -> bool:
    return bbox.south <= lat <= bbox.north and bbox.west <= lon <= bbox.east

def _clip_polyline_to_bbox(
    points: list[tuple[float, float]],
    bbox: BoundingBox,
) -> list[list[tuple[float, float]]]:
    parts: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []

    for index in range(1, len(points)):
        clipped = _clip_segment_to_bbox(points[index - 1], points[index], bbox)

        if clipped is None:
            if current:
                parts.append(current)
                current = []
            continue

        start, end = clipped

        if not current:
            current = [start, end]
        else:
            if _same_point(current[-1], start):
                current.append(end)
            else:
                parts.append(current)
                current = [start, end]

    if current:
        parts.append(current)

    return parts

def _clip_segment_to_bbox(
    start: tuple[float, float],
    end: tuple[float, float],
    bbox: BoundingBox,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    lat1, lon1 = start
    lat2, lon2 = end

    dx = lon2 - lon1
    dy = lat2 - lat1

    p = [-dx, dx, -dy, dy]
    q = [lon1 - bbox.west, bbox.east - lon1, lat1 - bbox.south, bbox.north - lat1]

    u1 = 0.0
    u2 = 1.0

    for pi, qi in zip(p, q, strict=True):
        if abs(pi) < 0.000000000001:
            if qi < 0:
                return None
            continue

        ratio = qi / pi

        if pi < 0:
            if ratio > u2:
                return None
            if ratio > u1:
                u1 = ratio
        else:
            if ratio < u1:
                return None
            if ratio < u2:
                u2 = ratio

    clipped_start = (lat1 + u1 * dy, lon1 + u1 * dx)
    clipped_end = (lat1 + u2 * dy, lon1 + u2 * dx)

    if _same_point(clipped_start, clipped_end):
        return None

    return clipped_start, clipped_end

def _clip_polygon_to_bbox(
    polygon: list[tuple[float, float]],
    bbox: BoundingBox,
) -> list[tuple[float, float]]:
    clipped = polygon[:]

    for edge in ["west", "east", "south", "north"]:
        clipped = _clip_polygon_edge(clipped, bbox, edge)

        if not clipped:
            return []

    clipped = _dedupe_adjacent_points(clipped)

    if clipped and not _same_point(clipped[0], clipped[-1]):
        clipped.append(clipped[0])

    return clipped

def _clip_polygon_edge(
    polygon: list[tuple[float, float]],
    bbox: BoundingBox,
    edge: str,
) -> list[tuple[float, float]]:
    if not polygon:
        return []

    result: list[tuple[float, float]] = []
    previous = polygon[-1]

    for current in polygon:
        current_inside = _inside_edge(current, bbox, edge)
        previous_inside = _inside_edge(previous, bbox, edge)

        if current_inside:
            if not previous_inside:
                result.append(_edge_intersection(previous, current, bbox, edge))
            result.append(current)
        elif previous_inside:
            result.append(_edge_intersection(previous, current, bbox, edge))

        previous = current

    return result

def _inside_edge(point: tuple[float, float], bbox: BoundingBox, edge: str) -> bool:
    lat, lon = point

    if edge == "west":
        return lon >= bbox.west
    if edge == "east":
        return lon <= bbox.east
    if edge == "south":
        return lat >= bbox.south
    if edge == "north":
        return lat <= bbox.north

    return False

def _edge_intersection(
    start: tuple[float, float],
    end: tuple[float, float],
    bbox: BoundingBox,
    edge: str,
) -> tuple[float, float]:
    lat1, lon1 = start
    lat2, lon2 = end

    if edge in {"west", "east"}:
        lon = bbox.west if edge == "west" else bbox.east

        if abs(lon2 - lon1) < 0.000000000001:
            return lat1, lon

        t = (lon - lon1) / (lon2 - lon1)
        return lat1 + t * (lat2 - lat1), lon

    lat = bbox.south if edge == "south" else bbox.north

    if abs(lat2 - lat1) < 0.000000000001:
        return lat, lon1

    t = (lat - lat1) / (lat2 - lat1)
    return lat, lon1 + t * (lon2 - lon1)

def _same_point(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) < 0.00000001 and abs(a[1] - b[1]) < 0.00000001

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
            key = f"{coordinate.lat:.6f}:{coordinate.lon:.6f}"
            point_to_roads.setdefault(key, set()).add(road.id)
            point_to_latlon[key] = (coordinate.lat, coordinate.lon)

    intersections: list[IntersectionDto] = []

    for index, (key, road_ids) in enumerate(point_to_roads.items()):
        if len(road_ids) < 2:
            continue

        lat, lon = point_to_latlon[key]
        x, z = latlon_to_local_meters(lat, lon, origin_lat, origin_lon)

        has_signal = any(
            abs(signal.lat - lat) < 0.0001 and abs(signal.lon - lon) < 0.0001
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

def _extract_surface_kind(tags: dict) -> str | None:
    if tags.get("waterway") == "riverbank":
        return "water:riverbank"

    if tags.get("natural") == "water":
        water = tags.get("water")
        return f"water:{water}" if water else "water"

    if tags.get("water") is not None:
        return f"water:{tags['water']}"

    if tags.get("landuse") == "reservoir":
        return "water:reservoir"

    if tags.get("natural") in {"bay", "sea", "strait", "lagoon", "fjord", "sound"}:
        return f"water:{tags['natural']}"

    if tags.get("place") in {"sea", "ocean"}:
        return f"water:{tags['place']}"

    if _is_linear_water(tags):
        return f"waterway:{tags['waterway']}"

    if tags.get("natural") in {"sand", "beach", "desert"}:
        return f"sand:{tags['natural']}"

    if tags.get("natural") == "shingle":
        return "shingle"

    if tags.get("landcover") in {"sand", "bare", "bare_ground"}:
        return f"sand:{tags['landcover']}"

    if tags.get("surface") == "sand" and tags.get("area") == "yes":
        return "sand:surface"

    if tags.get("leisure") == "park":
        return "park"

    if tags.get("leisure") in {"garden", "playground", "recreation_ground", "sports_centre", "pitch", "stadium"}:
        return f"leisure:{tags['leisure']}"

    if tags.get("natural") in {"wood", "scrub", "grassland", "heath", "wetland"}:
        return f"natural:{tags['natural']}"

    if tags.get("landcover") in {"grass", "trees", "wood", "forest", "meadow"}:
        return f"landcover:{tags['landcover']}"

    if tags.get("landuse") in {"grass", "meadow", "forest", "recreation_ground", "village_green", "cemetery", "farmland", "orchard"}:
        return f"landuse:{tags['landuse']}"

    if tags.get("landuse") in {"residential", "commercial", "industrial", "retail", "railway"}:
        return f"district:{tags['landuse']}"

    if tags.get("amenity") == "parking":
        return "parking"

    if tags.get("amenity") in {"school", "kindergarten", "university", "college"}:
        return "school"

    if tags.get("amenity") == "hospital":
        return "hospital"

    if tags.get("aeroway") in {"apron", "runway", "taxiway", "helipad"}:
        return f"aeroway:{tags['aeroway']}"

    if tags.get("area:highway") is not None:
        return "area_highway"

    if tags.get("highway") == "pedestrian" and tags.get("area") == "yes":
        return "area_highway:pedestrian"

    return None

def _extract_infrastructure_kind(tags: dict) -> str | None:
    for key in [
        "amenity",
        "shop",
        "office",
        "public_transport",
        "railway",
        "leisure",
        "tourism",
        "healthcare",
        "emergency",
        "historic",
        "man_made",
        "place",
    ]:
        if key in tags:
            return f"{key}:{tags[key]}"

    return None

def _is_building(tags: dict) -> bool:
    return "building" in tags or "building:part" in tags

def _polygon_center(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None

    lat = sum(point[0] for point in points) / len(points)
    lon = sum(point[1] for point in points) / len(points)
    return lat, lon

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
    default = _default_speed_for_highway(highway_kind)

    if value is None:
        return default

    value_lower = value.lower().strip()

    if value_lower in {"none", "signals", "walk", "variable"}:
        return default

    if ":" in value_lower and not any(char.isdigit() for char in value_lower):
        return default

    first_part = value_lower.replace(";", ",").split(",")[0].strip()

    cleaned = (
        first_part
        .replace("km/h", "")
        .replace("kph", "")
        .replace("mph", "")
        .strip()
    )

    number = ""

    for char in cleaned:
        if char.isdigit() or char == ".":
            number += char
        elif number:
            break

    if not number:
        return default

    try:
        parsed = float(number)
    except ValueError:
        return default

    if "mph" in first_part:
        parsed *= 1.60934

    return max(5.0, min(parsed, 140.0))


def _default_speed_for_highway(highway_kind: str) -> float:
    defaults = {
        "motorway": 100.0,
        "trunk": 80.0,
        "primary": 60.0,
        "secondary": 50.0,
        "tertiary": 40.0,
        "unclassified": 35.0,
        "residential": 30.0,
        "living_street": 20.0,
        "service": 20.0,
        "motorway_link": 60.0,
        "trunk_link": 50.0,
        "primary_link": 40.0,
        "secondary_link": 35.0,
        "tertiary_link": 30.0,
    }

    return defaults.get(highway_kind, 30.0)

def _parse_height(value: str | None) -> float | None:
    if value is None:
        return None

    cleaned = (
        value.lower()
        .replace("meters", "")
        .replace("meter", "")
        .replace("metres", "")
        .replace("metre", "")
        .replace("m", "")
        .strip()
    )

    try:
        return float(cleaned)
    except ValueError:
        return None

def _estimate_building_height(tags: dict) -> float:
    building_kind = tags.get("building") or tags.get("building:part")

    if building_kind in {"apartments", "residential", "dormitory"}:
        return 18.0
    if building_kind in {"commercial", "office", "retail"}:
        return 24.0
    if building_kind in {"industrial", "warehouse"}:
        return 10.0
    if building_kind in {"garage", "garages", "shed", "roof"}:
        return 4.0
    if building_kind in {"school", "university", "college"}:
        return 14.0
    if building_kind in {"hospital"}:
        return 22.0
    if building_kind in {"church", "cathedral", "chapel"}:
        return 28.0

    return DEFAULT_BUILDING_HEIGHT

def _append_surface_from_tags(
    surfaces: list[SurfaceDto],
    element_id: str,
    osm_id: str,
    tags: dict,
    raw_latlon: list[tuple[float, float]],
    bbox: BoundingBox,
    origin_lat: float,
    origin_lon: float,
) -> None:
    surface_kind = _extract_surface_kind(tags)

    if surface_kind is None:
        return

    if _is_linear_water(tags):
        strip = _linear_water_strip(raw_latlon, tags)

        if len(strip) >= 4:
            _append_surface(
                surfaces=surfaces,
                element_id=element_id,
                osm_id=osm_id,
                tags=tags,
                raw_latlon=strip,
                surface_kind=surface_kind,
                bbox=bbox,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
            )

        return

    if not _is_area_like(tags, raw_latlon):
        return

    _append_surface(
        surfaces=surfaces,
        element_id=element_id,
        osm_id=osm_id,
        tags=tags,
        raw_latlon=raw_latlon,
        surface_kind=surface_kind,
        bbox=bbox,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
    )

def _is_area_like(tags: dict, points: list[tuple[float, float]]) -> bool:
    if tags.get("area") == "yes":
        return True

    if len(points) >= 4 and _same_point(points[0], points[-1]):
        return True

    return False

def _is_linear_water(tags: dict) -> bool:
    waterway = tags.get("waterway")

    return waterway in {
        "river",
        "stream",
        "canal",
        "drain",
        "ditch",
        "tidal_channel",
    }

def _linear_water_strip(
    points: list[tuple[float, float]],
    tags: dict,
) -> list[tuple[float, float]]:
    if len(points) < 2:
        return []

    waterway = tags.get("waterway")
    width_m = _parse_width_meters(tags.get("width"))

    if width_m is None:
        width_m = {
            "river": 16.0,
            "canal": 8.0,
            "stream": 3.0,
            "drain": 2.0,
            "ditch": 2.0,
            "tidal_channel": 6.0,
        }.get(waterway, 3.0)

    offset_m = max(1.0, min(width_m / 2, 32.0))

    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []

    for index, point in enumerate(points):
        previous_point = points[max(0, index - 1)]
        next_point = points[min(len(points) - 1, index + 1)]

        lat, lon = point
        d_lat = next_point[0] - previous_point[0]
        d_lon = next_point[1] - previous_point[1]
        length = max((d_lat * d_lat + d_lon * d_lon) ** 0.5, 0.000000001)

        normal_lat = -d_lon / length
        normal_lon = d_lat / length

        meters_lat = 1 / 111_320
        meters_lon = 1 / (111_320 * max(0.35, abs(__import__("math").cos(__import__("math").radians(lat)))))

        left.append((lat + normal_lat * offset_m * meters_lat, lon + normal_lon * offset_m * meters_lon))
        right.append((lat - normal_lat * offset_m * meters_lat, lon - normal_lon * offset_m * meters_lon))

    ring = [*left, *reversed(right)]

    if ring and not _same_point(ring[0], ring[-1]):
        ring.append(ring[0])

    return ring

def _extract_rail_kind(tags: dict) -> str | None:
    railway = tags.get("railway")

    if railway in {"subway"}:
        return None

    if railway in {"rail", "tram", "light_rail"}:
        return railway

    if railway in {"construction", "proposed"}:
        value = tags.get("construction") or tags.get("proposed") or tags.get("railway:construction") or tags.get("railway:proposed")

        if value in {"rail", "tram", "light_rail"}:
            return value

    if railway in {"disused", "abandoned"}:
        value = tags.get("disused:railway") or tags.get("abandoned:railway")

        if value in {"rail", "tram", "light_rail"}:
            return value

        return "rail"

    return None

def _extract_transit_stop_kind(tags: dict) -> str | None:
    if tags.get("railway") == "subway":
        return None

    if tags.get("highway") == "bus_stop":
        return "bus_stop"

    if tags.get("railway") == "tram_stop":
        return "tram_stop"

    if tags.get("railway") == "halt":
        return "rail_halt"

    if tags.get("railway") == "station":
        return "rail_station"

    if tags.get("railway") in {"platform", "platform_edge", "platform_section"}:
        return "rail_platform"

    if tags.get("public_transport") == "platform":
        return "platform"

    if tags.get("public_transport") == "stop_position":
        return "stop_position"

    if tags.get("public_transport") == "station":
        return "station"

    return None

def _parse_route_refs(tags: dict) -> list[str]:
    refs = []

    for key in ["ref", "route_ref", "local_ref"]:
        value = tags.get(key)

        if value:
            refs.extend(part.strip() for part in value.replace(";", ",").split(",") if part.strip())

    return sorted(set(refs))

def _is_driveable_highway(highway_kind: str, tags: dict) -> bool:
    if highway_kind not in DRIVEABLE_HIGHWAYS:
        return False

    if tags.get("access") in {"no", "private"}:
        return False

    if tags.get("motor_vehicle") in {"no", "private"}:
        return False

    if tags.get("vehicle") in {"no", "private"}:
        return False

    return True

def _is_walkable_highway(highway_kind: str, tags: dict) -> bool:
    if highway_kind in WALKABLE_HIGHWAYS:
        return True

    if tags.get("sidewalk") not in {None, "no", "none"}:
        return True

    if tags.get("foot") in {"yes", "designated", "permissive"}:
        return True

    return False

def _parse_width_meters(value: str | None) -> float | None:
    if value is None:
        return None

    cleaned = value.lower().replace(",", ".")
    number = ""

    for char in cleaned:
        if char.isdigit() or char == ".":
            number += char
        elif number:
            break

    if not number:
        return None

    try:
        parsed = float(number)
    except ValueError:
        return None

    if parsed <= 0:
        return None

    return parsed

def _clean_tags(tags: dict) -> dict[str, str]:
    result: dict[str, str] = {}

    for key, value in tags.items():
        if value is None:
            continue

        result[str(key)] = str(value)

    return result