from dataclasses import dataclass


@dataclass
class Road:
    id: str
    kind: str
    coordinates: list[list[float]]
    is_closed: bool = False


@dataclass
class Building:
    id: str
    height: float
    coordinates: list[list[float]]


@dataclass
class Intersection:
    id: str
    lat: float
    lon: float
    connected_road_ids: list[str]


@dataclass
class City:
    roads: list[Road]
    buildings: list[Building]
    intersections: list[Intersection]