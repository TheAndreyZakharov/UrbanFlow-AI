from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    south: float = Field(..., ge=-90, le=90)
    west: float = Field(..., ge=-180, le=180)
    north: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)

    @model_validator(mode="after")
    def validate_bbox(self) -> "BoundingBox":
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        if self.west >= self.east:
            raise ValueError("west must be less than east")
        return self


class OsmImportRequest(BaseModel):
    bbox: BoundingBox


class CoordinateDto(BaseModel):
    lat: float
    lon: float
    x: float
    z: float


class RoadDto(BaseModel):
    id: str
    osm_id: str
    name: str | None = None
    kind: str
    lanes: int
    one_way: bool
    max_speed_kph: float
    is_driveable: bool
    is_walkable: bool
    coordinates: list[CoordinateDto]


class BuildingDto(BaseModel):
    id: str
    osm_id: str
    height: float
    levels: int | None = None
    kind: str | None = None
    coordinates: list[CoordinateDto]


class TrafficSignalDto(BaseModel):
    id: str
    osm_id: str
    lat: float
    lon: float
    x: float
    z: float


class CrossingDto(BaseModel):
    id: str
    osm_id: str
    lat: float
    lon: float
    x: float
    z: float


class InfrastructureDto(BaseModel):
    id: str
    osm_id: str
    kind: str
    name: str | None = None
    lat: float
    lon: float
    x: float
    z: float


class IntersectionDto(BaseModel):
    id: str
    lat: float
    lon: float
    x: float
    z: float
    connected_road_ids: list[str]
    has_signal: bool


class CityMapDto(BaseModel):
    bbox: BoundingBox
    origin_lat: float
    origin_lon: float
    roads: list[RoadDto]
    buildings: list[BuildingDto]
    intersections: list[IntersectionDto]
    traffic_signals: list[TrafficSignalDto]
    crossings: list[CrossingDto]
    infrastructure: list[InfrastructureDto]