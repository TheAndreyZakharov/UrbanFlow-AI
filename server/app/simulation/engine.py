import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

from app.schemas.editor import EditorPatchDto
from app.schemas.osm import CityMapDto, CoordinateDto
from app.schemas.simulation import (
    PedestrianStateDto,
    SimulationMode,
    SimulationStateDto,
    TrafficEventDto,
    VehicleStateDto,
)
from app.simulation.city_graph import CityGraph, GraphEdge, build_city_graph
from app.simulation.controllers import SignalController
from app.simulation.events import TrafficEvent, maybe_generate_random_event
from app.simulation.metrics import build_intersection_load, build_metrics, build_road_load


VEHICLE_KINDS = ["car", "taxi", "bus", "truck", "emergency", "courier"]
VEHICLE_COLORS = ["#38bdf8", "#e5e7eb", "#111827", "#facc15", "#ef4444", "#22c55e", "#f97316"]
PEDESTRIAN_COLORS = ["#38bdf8", "#22c55e", "#ef4444", "#facc15", "#a855f7", "#f8fafc"]


@dataclass
class VehicleInternalState:
    id: str
    kind: str
    color: str
    route_edge_ids: list[str]
    route_index: int
    progress: float
    desired_speed_mps: float
    current_speed_mps: float
    lane_index: int
    wait_time: float = 0.0


@dataclass
class PedestrianInternalState:
    id: str
    color: str
    path: list[CoordinateDto]
    path_index: int
    progress: float
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
    signals_on_all_intersections: bool = False

    tick: int = 0
    throughput: int = 0
    city_graph: CityGraph = field(init=False)
    rng: random.Random = field(init=False)
    vehicles: list[VehicleInternalState] = field(default_factory=list)
    pedestrians: list[PedestrianInternalState] = field(default_factory=list)
    events: list[TrafficEvent] = field(default_factory=list)
    editor_patches: list[EditorPatchDto] = field(default_factory=list)
    closed_road_ids: set[str] = field(default_factory=set)
    forced_open_road_ids: set[str] = field(default_factory=set)
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
        self.rng = random.Random(self.seed)
        self._spawn_vehicles()
        self._spawn_pedestrians()
        return self.state()

    def apply_patch(self, patch: EditorPatchDto) -> None:
        self.editor_patches.append(patch)

        if patch.kind == "clear_event":
            if patch.target_id:
                self.events = [event for event in self.events if event.id != patch.target_id]
            return

        if patch.kind in {"close_road", "remove_road"} and patch.target_id:
            self.closed_road_ids.add(patch.target_id)
            self.forced_open_road_ids.discard(patch.target_id)

            for edge in self.city_graph.edges.values():
                if edge.road_id == patch.target_id:
                    edge.is_closed = True

            return

        if patch.kind == "open_road" and patch.target_id:
            self.closed_road_ids.discard(patch.target_id)
            self.forced_open_road_ids.add(patch.target_id)

            self.events = [
                event
                for event in self.events
                if event.target_id != patch.target_id or event.kind not in {"accident", "roadwork"}
            ]

            for edge in self.city_graph.edges.values():
                if edge.road_id == patch.target_id:
                    edge.is_closed = False

            return

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

    def update_settings(
        self,
        vehicles_count: int,
        pedestrians_count: int,
        signals_on_all_intersections: bool,
    ) -> SimulationStateDto:
        self.vehicles_count = vehicles_count
        self.pedestrians_count = pedestrians_count
        self.signals_on_all_intersections = signals_on_all_intersections

        self.vehicles = []
        self.pedestrians = []

        self._spawn_vehicles()
        self._spawn_pedestrians()

        return self.state()
    
    def step(self, steps: int = 1) -> SimulationStateDto:
        for _ in range(steps):
            self.tick += 1
            self._generate_events()
            self._move_pedestrians()
            self._move_vehicles()

        return self.state()

    def state(self) -> SimulationStateDto:
        vehicle_states = self._vehicle_states()
        pedestrian_states = self._pedestrian_states()
        active_events = [event for event in self.events if event.is_active(self.tick)]
        road_load = build_road_load(self.city_map, vehicle_states)
        intersection_load = build_intersection_load(self.city_map, vehicle_states, pedestrian_states)
        signals = []

        for intersection in self.city_map.intersections:
            if not self.signals_on_all_intersections and not intersection.has_signal:
                continue

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
            pedestrians=pedestrian_states,
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
            closed_road_ids=sorted(self.closed_road_ids),
            forced_open_road_ids=sorted(self.forced_open_road_ids),
        )

    def _spawn_vehicles(self) -> None:
        usable_edges = [
            edge for edge in self.city_graph.edges.values()
            if not edge.is_closed and edge.length_meters > 8
        ]

        if not usable_edges:
            return

        usable_edges.sort(key=lambda edge: edge.id)

        for index in range(self.vehicles_count):
            start_edge = usable_edges[index % len(usable_edges)]
            route = self._build_vehicle_route(start_edge.id, max_edges=self.rng.randint(5, 18))

            if not route:
                continue

            kind = self.rng.choice(VEHICLE_KINDS)
            desired_speed = self._vehicle_desired_speed(kind, start_edge)

            lane_count = max(1, start_edge.lanes)
            progress_slot = (index // len(usable_edges)) % 12
            progress = (progress_slot + 0.5) / 12

            self.vehicles.append(
                VehicleInternalState(
                    id=f"vehicle:{index}",
                    kind=kind,
                    color=self.rng.choice(VEHICLE_COLORS),
                    route_edge_ids=route,
                    route_index=0,
                    progress=progress,
                    desired_speed_mps=desired_speed,
                    current_speed_mps=0.0,
                    lane_index=index % lane_count,
                )
            )

    def _spawn_pedestrians(self) -> None:
        pedestrian_paths = self._pedestrian_paths()

        if not pedestrian_paths:
            return

        for index in range(self.pedestrians_count):
            path = pedestrian_paths[index % len(pedestrian_paths)][:]

            if len(path) < 2:
                continue

            if self.rng.random() < 0.5:
                path.reverse()

            progress_slot = (index // len(pedestrian_paths)) % 10
            progress = (progress_slot + 0.5) / 10

            self.pedestrians.append(
                PedestrianInternalState(
                    id=f"pedestrian:{index}",
                    color=self.rng.choice(PEDESTRIAN_COLORS),
                    path=path,
                    path_index=0,
                    progress=progress,
                    speed_mps=self.rng.uniform(0.8, 1.55),
                )
            )

    def _pedestrian_paths(self) -> list[list[CoordinateDto]]:
        paths: list[list[CoordinateDto]] = []

        for road in self.city_map.roads:
            if not road.is_walkable:
                continue

            if road.is_driveable:
                continue

            if len(road.coordinates) >= 2:
                paths.append(road.coordinates)

        for surface in self.city_map.surfaces:
            if not self._is_walkable_surface(surface.kind):
                continue

            if len(surface.coordinates) >= 2:
                paths.append(surface.coordinates)

        return paths

    def _is_walkable_surface(self, kind: str) -> bool:
        if "water" in kind:
            return False

        return any(
            token in kind
            for token in [
                "park",
                "garden",
                "playground",
                "recreation_ground",
                "grass",
                "meadow",
                "forest",
                "wood",
                "village_green",
                "cemetery",
                "school",
                "hospital",
            ]
        )

    def _build_vehicle_route(self, start_edge_id: str, max_edges: int) -> list[str]:
        route = [start_edge_id]
        current_edge = self.city_graph.edges[start_edge_id]

        for _ in range(max_edges - 1):
            to_node = self.city_graph.nodes.get(current_edge.to_node_id)

            if to_node is None:
                break

            candidates = [
                edge_id for edge_id in to_node.outgoing_edge_ids
                if edge_id in self.city_graph.edges and not self.city_graph.edges[edge_id].is_closed
            ]

            if not candidates:
                break

            current_edge = self.city_graph.edges[self.rng.choice(candidates)]
            route.append(current_edge.id)

        return route

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
        vehicles_by_edge: dict[str, list[VehicleInternalState]] = defaultdict(list)

        for vehicle in self.vehicles:
            current_edge = self._current_edge(vehicle)
            if current_edge is not None:
                vehicles_by_edge[current_edge.id].append(vehicle)

        for edge_id, edge_vehicles in vehicles_by_edge.items():
            edge = self.city_graph.edges[edge_id]
            edge_vehicles.sort(key=lambda vehicle: vehicle.progress, reverse=True)

            previous_vehicle: VehicleInternalState | None = None

            for vehicle in edge_vehicles:
                if edge.is_closed:
                    vehicle.current_speed_mps = 0.0
                    vehicle.wait_time += 1.0
                    previous_vehicle = vehicle
                    continue

                desired_speed = min(vehicle.desired_speed_mps, edge.max_speed_mps)
                desired_speed *= self._speed_multiplier_for_vehicle(edge.road_id, vehicle.progress)

                desired_speed = self._apply_pedestrian_collision_speed(edge, vehicle, desired_speed)

                if previous_vehicle is not None:
                    safe_gap_m = self._vehicle_length(previous_vehicle.kind) + self._vehicle_length(vehicle.kind) + 3.5
                    safe_gap_progress = safe_gap_m / max(edge.length_meters, 1.0)
                    allowed_progress = previous_vehicle.progress - safe_gap_progress

                    if vehicle.progress >= allowed_progress:
                        desired_speed = 0.0
                        vehicle.progress = max(0.0, allowed_progress - 0.001)

                acceleration = 1.4
                braking = 3.2

                if desired_speed > vehicle.current_speed_mps:
                    vehicle.current_speed_mps = min(desired_speed, vehicle.current_speed_mps + acceleration)
                else:
                    vehicle.current_speed_mps = max(desired_speed, vehicle.current_speed_mps - braking)

                if vehicle.current_speed_mps < 0.45:
                    vehicle.wait_time += 1.0

                vehicle.progress += vehicle.current_speed_mps / max(edge.length_meters, 1.0)

                while vehicle.progress >= 1.0:
                    vehicle.progress -= 1.0
                    vehicle.route_index += 1
                    self.throughput += 1

                    if vehicle.route_index >= len(vehicle.route_edge_ids):
                        new_route = self._build_vehicle_route(edge.id, max_edges=self.rng.randint(5, 18))
                        vehicle.route_edge_ids = new_route or vehicle.route_edge_ids
                        vehicle.route_index = 0
                        break

                previous_vehicle = vehicle

    def _apply_pedestrian_collision_speed(
        self,
        edge: GraphEdge,
        vehicle: VehicleInternalState,
        desired_speed: float,
    ) -> float:
        start = edge.coordinates[0]
        end = edge.coordinates[-1]
        vehicle_x = start.x + (end.x - start.x) * vehicle.progress
        vehicle_z = start.z + (end.z - start.z) * vehicle.progress

        ahead_distance = max(8.0, desired_speed * 1.2)

        for pedestrian in self._pedestrian_states():
            dx = pedestrian.x - vehicle_x
            dz = pedestrian.z - vehicle_z
            distance = math.hypot(dx, dz)

            if distance > ahead_distance:
                continue

            forward_x = math.cos(edge.heading_rad)
            forward_z = math.sin(edge.heading_rad)
            lateral_x = -forward_z
            lateral_z = forward_x

            forward_distance = dx * forward_x + dz * forward_z
            lateral_distance = abs(dx * lateral_x + dz * lateral_z)

            if 0 <= forward_distance <= ahead_distance and lateral_distance < 3.2:
                return 0.0

        return desired_speed

    def _move_pedestrians(self) -> None:
        for pedestrian in self.pedestrians:
            if len(pedestrian.path) < 2:
                pedestrian.wait_time += 1.0
                continue

            start = pedestrian.path[pedestrian.path_index]
            end = pedestrian.path[(pedestrian.path_index + 1) % len(pedestrian.path)]
            segment_length = math.hypot(end.x - start.x, end.z - start.z)

            if segment_length < 0.5:
                pedestrian.path_index = (pedestrian.path_index + 1) % (len(pedestrian.path) - 1)
                pedestrian.progress = 0.0
                continue

            pedestrian.progress += pedestrian.speed_mps / segment_length

            if pedestrian.progress >= 1.0:
                pedestrian.progress = 0.0
                pedestrian.path_index += 1

                if pedestrian.path_index >= len(pedestrian.path) - 1:
                    pedestrian.path.reverse()
                    pedestrian.path_index = 0

    def _vehicle_states(self) -> list[VehicleStateDto]:
        result: list[VehicleStateDto] = []

        for vehicle in self.vehicles:
            current_edge = self._current_edge(vehicle)

            if current_edge is None:
                continue

            start = current_edge.coordinates[0]
            end = current_edge.coordinates[-1]

            lane_offset = self._lane_offset(vehicle, current_edge)
            lateral_x = -math.sin(current_edge.heading_rad)
            lateral_z = math.cos(current_edge.heading_rad)

            base_x = start.x + (end.x - start.x) * vehicle.progress
            base_z = start.z + (end.z - start.z) * vehicle.progress

            x = base_x + lateral_x * lane_offset
            z = base_z + lateral_z * lane_offset
            lat = start.lat + (end.lat - start.lat) * vehicle.progress
            lon = start.lon + (end.lon - start.lon) * vehicle.progress

            result.append(
                VehicleStateDto(
                    id=vehicle.id,
                    kind=vehicle.kind,
                    color=vehicle.color,
                    lat=round(lat, 8),
                    lon=round(lon, 8),
                    x=round(x, 3),
                    z=round(z, 3),
                    elevation_m=round(
                        current_edge.start_elevation_m
                        + (current_edge.end_elevation_m - current_edge.start_elevation_m) * vehicle.progress,
                        3,
                    ),
                    speed_mps=round(vehicle.current_speed_mps, 2),
                    wait_time=round(vehicle.wait_time, 2),
                    road_id=current_edge.road_id,
                    route_edge_ids=vehicle.route_edge_ids,
                    current_edge_id=current_edge.id,
                    heading_rad=round(current_edge.heading_rad, 5),
                    lane_offset_m=round(lane_offset, 3),
                    length_m=self._vehicle_length(vehicle.kind),
                    width_m=self._vehicle_width(vehicle.kind),
                )
            )

        return result

    def _pedestrian_states(self) -> list[PedestrianStateDto]:
        result: list[PedestrianStateDto] = []

        for pedestrian in self.pedestrians:
            if len(pedestrian.path) < 2:
                continue

            start = pedestrian.path[pedestrian.path_index]
            end = pedestrian.path[(pedestrian.path_index + 1) % len(pedestrian.path)]
            x = start.x + (end.x - start.x) * pedestrian.progress
            z = start.z + (end.z - start.z) * pedestrian.progress
            lat = start.lat + (end.lat - start.lat) * pedestrian.progress
            lon = start.lon + (end.lon - start.lon) * pedestrian.progress
            heading = math.atan2(end.z - start.z, end.x - start.x)

            result.append(
                PedestrianStateDto(
                    id=pedestrian.id,
                    color=pedestrian.color,
                    lat=round(lat, 8),
                    lon=round(lon, 8),
                    x=round(x, 3),
                    z=round(z, 3),
                    speed_mps=round(pedestrian.speed_mps, 2),
                    wait_time=round(pedestrian.wait_time, 2),
                    heading_rad=round(heading, 5),
                )
            )

        return result

    def _current_edge(self, vehicle: VehicleInternalState) -> GraphEdge | None:
        if not vehicle.route_edge_ids:
            return None

        edge_id = vehicle.route_edge_ids[vehicle.route_index % len(vehicle.route_edge_ids)]
        return self.city_graph.edges.get(edge_id)

    def _speed_multiplier_for_vehicle(self, road_id: str, vehicle_progress: float) -> float:
        multiplier = 1.0

        for event in self.events:
            if not event.is_active(self.tick):
                continue

            if event.target_id != road_id:
                continue

            if "speed_multiplier" not in event.payload:
                continue

            if event.kind == "accident":
                event_progress = float(event.payload.get("progress", 0.5))
                radius_m = float(event.payload.get("radius_m", 35))
                radius_progress = max(0.03, min(0.4, radius_m / 100))

                if abs(vehicle_progress - event_progress) > radius_progress:
                    continue

            multiplier *= float(event.payload["speed_multiplier"])

        return max(0.0, multiplier)

    def _lane_offset(self, vehicle: VehicleInternalState, edge: GraphEdge) -> float:
        lane_width = 3.2
        lanes = max(1, edge.lanes)
        lane_index = min(vehicle.lane_index, lanes - 1)
        return (lane_index - (lanes - 1) / 2) * lane_width

    def _vehicle_desired_speed(self, kind: str, edge: GraphEdge) -> float:
        multiplier = {
            "car": 0.92,
            "taxi": 0.98,
            "bus": 0.72,
            "truck": 0.68,
            "emergency": 1.12,
            "courier": 1.02,
        }.get(kind, 0.9)

        return max(2.0, edge.max_speed_mps * multiplier * self.rng.uniform(0.82, 1.08))

    def _vehicle_length(self, kind: str) -> float:
        return {
            "bus": 10.5,
            "truck": 8.5,
            "emergency": 5.0,
            "courier": 4.4,
            "taxi": 4.2,
            "car": 4.2,
        }.get(kind, 4.2)

    def _vehicle_width(self, kind: str) -> float:
        return {
            "bus": 2.5,
            "truck": 2.5,
            "emergency": 2.1,
            "courier": 1.9,
            "taxi": 1.8,
            "car": 1.8,
        }.get(kind, 1.8)