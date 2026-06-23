import random
from dataclasses import dataclass, field

from app.schemas.editor import EditorPatchDto
from app.schemas.osm import CityMapDto
from app.schemas.simulation import (
    PedestrianStateDto,
    SimulationMode,
    SimulationStateDto,
    TrafficEventDto,
    VehicleStateDto,
)
from app.simulation.city_graph import CityGraph, build_city_graph
from app.simulation.controllers import SignalController
from app.simulation.events import TrafficEvent, maybe_generate_random_event
from app.simulation.metrics import build_intersection_load, build_metrics, build_road_load


VEHICLE_KINDS = ["car", "taxi", "bus", "truck", "emergency", "courier"]
VEHICLE_COLORS = ["blue", "white", "black", "yellow", "red", "green", "orange"]
PEDESTRIAN_COLORS = ["blue", "green", "red", "yellow", "purple", "white"]


@dataclass
class VehicleInternalState:
    id: str
    kind: str
    color: str
    route_edge_ids: list[str]
    route_index: int
    progress: float
    speed_mps: float
    wait_time: float = 0.0


@dataclass
class PedestrianInternalState:
    id: str
    color: str
    x: float
    z: float
    speed_mps: float
    wait_time: float = 0.0


@dataclass
class SimulationEngine:
    session_id: str
    city_map: CityMapDto
    mode: SimulationMode = "fixed"
    vehicles_count: int = 80
    pedestrians_count: int = 120
    random_events_enabled: bool = True
    seed: int = 42

    tick: int = 0
    throughput: int = 0
    city_graph: CityGraph = field(init=False)
    rng: random.Random = field(init=False)
    vehicles: list[VehicleInternalState] = field(default_factory=list)
    pedestrians: list[PedestrianInternalState] = field(default_factory=list)
    events: list[TrafficEvent] = field(default_factory=list)
    editor_patches: list[EditorPatchDto] = field(default_factory=list)
    signal_controller: SignalController = field(default_factory=SignalController)

    def __post_init__(self) -> None:
        self.city_graph = build_city_graph(self.city_map)
        self.rng = random.Random(self.seed)
        self._spawn_vehicles()
        self._spawn_pedestrians()

    def reset(self) -> SimulationStateDto:
        self.tick = 0
        self.throughput = 0
        self.events = []
        self.vehicles = []
        self.pedestrians = []
        self._spawn_vehicles()
        self._spawn_pedestrians()
        return self.state()

    def apply_patch(self, patch: EditorPatchDto) -> None:
        self.editor_patches.append(patch)

        if patch.kind in {"close_road", "remove_road"} and patch.target_id:
            for edge in self.city_graph.edges.values():
                if edge.road_id == patch.target_id:
                    edge.is_closed = True

        if patch.kind == "open_road" and patch.target_id:
            for edge in self.city_graph.edges.values():
                if edge.road_id == patch.target_id:
                    edge.is_closed = False

        if patch.kind in {"accident", "roadwork"}:
            self.events.append(
                TrafficEvent(
                    id=f"editor-event:{patch.id}",
                    kind=patch.kind,
                    target_id=patch.target_id,
                    started_at_tick=self.tick,
                    duration_ticks=int(patch.payload.get("duration_ticks", 240)),
                    payload=patch.payload,
                )
            )

    def set_mode(self, mode: SimulationMode) -> SimulationStateDto:
        self.mode = mode
        return self.state()

    def step(self, steps: int = 1) -> SimulationStateDto:
        for _ in range(steps):
            self.tick += 1
            self._generate_events()
            self._move_vehicles()
            self._move_pedestrians()

        return self.state()

    def state(self) -> SimulationStateDto:
        vehicle_states = self._vehicle_states()
        pedestrian_states = self._pedestrian_states()
        active_events = [event for event in self.events if event.is_active(self.tick)]
        road_load = build_road_load(self.city_map, vehicle_states)
        intersection_load = build_intersection_load(self.city_map, self.tick)
        signals = []

        for intersection in self.city_map.intersections:
            load = next(
                item for item in intersection_load if item.intersection_id == intersection.id
            )
            signals.append(
                self.signal_controller.build_signal_state(
                    tick=self.tick,
                    intersection=intersection,
                    mode=self.mode,
                    waiting_vehicles=load.waiting_vehicles,
                    waiting_pedestrians=load.waiting_pedestrians,
                )
            )

        metrics = build_metrics(
            vehicles=vehicle_states,
            pedestrians_count=len(pedestrian_states),
            active_events=len(active_events),
            throughput=self.throughput,
        )

        return SimulationStateDto(
            session_id=self.session_id,
            tick=self.tick,
            mode=self.mode,
            vehicles=vehicle_states,
            pedestrians=pedestrian_states,
            signals=signals,
            events=[
                TrafficEventDto(
                    id=event.id,
                    kind=event.kind,
                    target_id=event.target_id,
                    started_at_tick=event.started_at_tick,
                    duration_ticks=event.duration_ticks,
                    payload=event.payload,
                )
                for event in active_events
            ],
            road_load=road_load,
            intersection_load=intersection_load,
            metrics=metrics,
            editor_patches=self.editor_patches,
        )

    def _spawn_vehicles(self) -> None:
        edge_ids = list(self.city_graph.edges.keys())

        if not edge_ids:
            return

        for index in range(self.vehicles_count):
            route_length = min(len(edge_ids), self.rng.randint(1, 6))
            route_edge_ids = self.rng.sample(edge_ids, route_length)

            self.vehicles.append(
                VehicleInternalState(
                    id=f"vehicle:{index}",
                    kind=self.rng.choice(VEHICLE_KINDS),
                    color=self.rng.choice(VEHICLE_COLORS),
                    route_edge_ids=route_edge_ids,
                    route_index=0,
                    progress=self.rng.random(),
                    speed_mps=self.rng.uniform(4.0, 12.0),
                )
            )

    def _spawn_pedestrians(self) -> None:
        if not self.city_map.crossings and not self.city_map.intersections:
            return

        points = [
            (crossing.x, crossing.z)
            for crossing in self.city_map.crossings
        ] or [
            (intersection.x, intersection.z)
            for intersection in self.city_map.intersections
        ]

        for index in range(self.pedestrians_count):
            x, z = self.rng.choice(points)

            self.pedestrians.append(
                PedestrianInternalState(
                    id=f"pedestrian:{index}",
                    color=self.rng.choice(PEDESTRIAN_COLORS),
                    x=x + self.rng.uniform(-8.0, 8.0),
                    z=z + self.rng.uniform(-8.0, 8.0),
                    speed_mps=self.rng.uniform(0.8, 1.6),
                )
            )

    def _generate_events(self) -> None:
        event = maybe_generate_random_event(
            tick=self.tick,
            road_ids=[road.id for road in self.city_map.roads if road.is_driveable],
            random_events_enabled=self.random_events_enabled,
            rng=self.rng,
        )

        if event is not None:
            self.events.append(event)

    def _move_vehicles(self) -> None:
        for vehicle in self.vehicles:
            current_edge = self._current_edge(vehicle)

            if current_edge is None:
                continue

            if current_edge.is_closed:
                vehicle.speed_mps = 0.0
                vehicle.wait_time += 1.0
                continue

            speed_multiplier = self._speed_multiplier_for_road(current_edge.road_id)
            effective_speed = max(0.0, min(vehicle.speed_mps, current_edge.max_speed_mps) * speed_multiplier)

            if effective_speed < 0.5:
                vehicle.wait_time += 1.0

            vehicle.progress += effective_speed / max(current_edge.length_meters, 0.1)

            if vehicle.progress >= 1.0:
                vehicle.progress = 0.0
                vehicle.route_index += 1
                self.throughput += 1

                if vehicle.route_index >= len(vehicle.route_edge_ids):
                    vehicle.route_index = 0

    def _move_pedestrians(self) -> None:
        for pedestrian in self.pedestrians:
            pedestrian.x += self.rng.uniform(-0.5, 0.5) * pedestrian.speed_mps
            pedestrian.z += self.rng.uniform(-0.5, 0.5) * pedestrian.speed_mps

    def _vehicle_states(self) -> list[VehicleStateDto]:
        result: list[VehicleStateDto] = []

        for vehicle in self.vehicles:
            current_edge = self._current_edge(vehicle)

            if current_edge is None:
                continue

            start = current_edge.coordinates[0]
            end = current_edge.coordinates[-1]

            x = start.x + (end.x - start.x) * vehicle.progress
            z = start.z + (end.z - start.z) * vehicle.progress
            lat = start.lat + (end.lat - start.lat) * vehicle.progress
            lon = start.lon + (end.lon - start.lon) * vehicle.progress

            result.append(
                VehicleStateDto(
                    id=vehicle.id,
                    kind=vehicle.kind,
                    color=vehicle.color,
                    lat=lat,
                    lon=lon,
                    x=round(x, 3),
                    z=round(z, 3),
                    speed_mps=round(vehicle.speed_mps, 2),
                    wait_time=round(vehicle.wait_time, 2),
                    road_id=current_edge.road_id,
                    route_edge_ids=vehicle.route_edge_ids,
                    current_edge_id=current_edge.id,
                )
            )

        return result

    def _pedestrian_states(self) -> list[PedestrianStateDto]:
        return [
            PedestrianStateDto(
                id=pedestrian.id,
                color=pedestrian.color,
                lat=self.city_map.origin_lat,
                lon=self.city_map.origin_lon,
                x=round(pedestrian.x, 3),
                z=round(pedestrian.z, 3),
                speed_mps=round(pedestrian.speed_mps, 2),
                wait_time=round(pedestrian.wait_time, 2),
            )
            for pedestrian in self.pedestrians
        ]

    def _current_edge(self, vehicle: VehicleInternalState):
        if not vehicle.route_edge_ids:
            return None

        edge_id = vehicle.route_edge_ids[vehicle.route_index % len(vehicle.route_edge_ids)]
        return self.city_graph.edges.get(edge_id)

    def _speed_multiplier_for_road(self, road_id: str) -> float:
        multiplier = 1.0

        for event in self.events:
            if not event.is_active(self.tick):
                continue

            if event.target_id != road_id:
                continue

            if "speed_multiplier" in event.payload:
                multiplier *= float(event.payload["speed_multiplier"])

        return multiplier