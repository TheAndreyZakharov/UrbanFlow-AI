from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    south: float = Field(..., ge=-90, le=90)
    west: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)


class OsmImportRequest(BaseModel):
    bbox: BoundingBox


class RoadDto(BaseModel):
    id: str
    name: str | None = None
    kind: str
    coordinates: list[list[float]]


class BuildingDto(BaseModel):
    id: str
    height: float
    levels: int | None = None
    coordinates: list[list[float]]


class IntersectionDto(BaseModel):
    id: str
    lat: float
    lon: float
    connected_road_ids: list[str]


class CityMapDto(BaseModel):
    bbox: BoundingBox
    roads: list[RoadDto]
    buildings: list[BuildingDto]
    intersections: list[IntersectionDto]