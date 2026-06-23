from pydantic import BaseModel


class VehicleStateDto(BaseModel):
    id: str
    kind: str
    lat: float
    lon: float
    speed: float
    road_id: str


class PedestrianStateDto(BaseModel):
    id: str
    lat: float
    lon: float
    speed: float


class TrafficSignalStateDto(BaseModel):
    id: str
    intersection_id: str
    phase: str
    time_left: float


class SimulationMetricsDto(BaseModel):
    average_vehicle_wait_time: float
    average_pedestrian_wait_time: float
    average_speed: float
    active_vehicles: int
    active_pedestrians: int
    congestion_score: float


class SimulationStateDto(BaseModel):
    tick: int
    vehicles: list[VehicleStateDto]
    pedestrians: list[PedestrianStateDto]
    signals: list[TrafficSignalStateDto]
    metrics: SimulationMetricsDto