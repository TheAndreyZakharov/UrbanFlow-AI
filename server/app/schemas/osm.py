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
    lanes_forward: int | None = None
    lanes_backward: int | None = None
    turn_lanes: str | None = None
    turn_lanes_forward: str | None = None
    turn_lanes_backward: str | None = None
    route_refs: list[str] = Field(default_factory=list)
    route_types: list[str] = Field(default_factory=list)
    one_way: bool
    max_speed_kph: float
    surface: str | None = None
    access: str | None = None
    bridge: str | None = None
    tunnel: str | None = None
    layer: int | None = None
    is_driveable: bool
    is_walkable: bool
    coordinates: list[CoordinateDto]
    tags: dict[str, str] = Field(default_factory=dict)

class BuildingDto(BaseModel):
    id: str
    osm_id: str
    height: float
    levels: int | None = None
    kind: str | None = None
    coordinates: list[CoordinateDto]
    holes: list[list[CoordinateDto]] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)

class SurfaceDto(BaseModel):
    id: str
    osm_id: str
    kind: str
    name: str | None = None
    coordinates: list[CoordinateDto]
    tags: dict[str, str] = Field(default_factory=dict)

class RailLineDto(BaseModel):
    id: str
    osm_id: str
    kind: str
    name: str | None = None
    is_tram: bool = False
    is_service: bool = False
    route_refs: list[str] = Field(default_factory=list)
    route_types: list[str] = Field(default_factory=list)
    bridge: str | None = None
    tunnel: str | None = None
    layer: int | None = None
    coordinates: list[CoordinateDto]
    tags: dict[str, str] = Field(default_factory=dict)

class TransitStopDto(BaseModel):
    id: str
    osm_id: str
    kind: str
    name: str | None = None
    route_refs: list[str] = Field(default_factory=list)
    lat: float
    lon: float
    x: float
    z: float
    tags: dict[str, str] = Field(default_factory=dict)

class TrafficSignalDto(BaseModel):
    id: str
    osm_id: str
    lat: float
    lon: float
    x: float
    z: float
    signal_type: str | None = None
    direction: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)

class CrossingDto(BaseModel):
    id: str
    osm_id: str
    lat: float
    lon: float
    x: float
    z: float
    tags: dict[str, str] = Field(default_factory=dict)

class InfrastructureDto(BaseModel):
    id: str
    osm_id: str
    kind: str
    name: str | None = None
    lat: float
    lon: float
    x: float
    z: float
    tags: dict[str, str] = Field(default_factory=dict)

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
    surfaces: list[SurfaceDto] = []
    rail_lines: list[RailLineDto] = []
    transit_stops: list[TransitStopDto] = []
    intersections: list[IntersectionDto]
    traffic_signals: list[TrafficSignalDto]
    crossings: list[CrossingDto]
    infrastructure: list[InfrastructureDto]