from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.editor import EditorPatchDto
from app.schemas.osm import CityMapDto


SimulationMode = Literal["fixed", "rule_based", "ai"]


class CreateSimulationRequest(BaseModel):
    city_map: CityMapDto
    mode: SimulationMode = "fixed"
    vehicles_count: int = Field(default=80, ge=0, le=5000)
    pedestrians_count: int = Field(default=120, ge=0, le=10000)
    random_events_enabled: bool = True
    seed: int = 42
    signals_on_all_intersections: bool = False


class UpdateSimulationSettingsRequest(BaseModel):
    vehicles_count: int = Field(default=80, ge=0, le=5000)
    pedestrians_count: int = Field(default=120, ge=0, le=10000)
    signals_on_all_intersections: bool = False


class StepSimulationRequest(BaseModel):
    steps: int = Field(default=1, ge=1, le=300)


class VehicleStateDto(BaseModel):
    id: str
    kind: str
    color: str
    lat: float
    lon: float
    x: float
    z: float
    elevation_m: float
    speed_mps: float
    wait_time: float
    road_id: str
    route_edge_ids: list[str]
    current_edge_id: str | None
    heading_rad: float
    lane_offset_m: float
    length_m: float
    width_m: float


class PedestrianStateDto(BaseModel):
    id: str
    color: str
    lat: float
    lon: float
    x: float
    z: float
    speed_mps: float
    wait_time: float
    heading_rad: float


class TrafficSignalStateDto(BaseModel):
    id: str
    intersection_id: str
    phase: str
    time_left: float
    controlled_road_ids: list[str]


class TrafficEventDto(BaseModel):
    id: str
    kind: str
    target_id: str | None
    started_at_tick: int
    duration_ticks: int
    payload: dict


class RoadLoadDto(BaseModel):
    road_id: str
    vehicle_count: int
    average_speed_mps: float
    congestion_score: float


class IntersectionLoadDto(BaseModel):
    intersection_id: str
    waiting_vehicles: int
    waiting_pedestrians: int
    congestion_score: float


class SimulationMetricsDto(BaseModel):
    average_vehicle_wait_time: float
    average_pedestrian_wait_time: float
    average_speed_mps: float
    active_vehicles: int
    active_pedestrians: int
    congestion_score: float
    stopped_vehicles: int
    active_events: int
    throughput: int


class SimulationStateDto(BaseModel):
    session_id: str
    tick: int
    mode: SimulationMode
    vehicles: list[VehicleStateDto]
    pedestrians: list[PedestrianStateDto]
    signals: list[TrafficSignalStateDto]
    events: list[TrafficEventDto]
    road_load: list[RoadLoadDto]
    intersection_load: list[IntersectionLoadDto]
    metrics: SimulationMetricsDto
    editor_patches: list[EditorPatchDto]
    closed_road_ids: list[str]
    forced_open_road_ids: list[str]


class SimulationSessionDto(BaseModel):
    session_id: str
    city_map: CityMapDto
    state: SimulationStateDto