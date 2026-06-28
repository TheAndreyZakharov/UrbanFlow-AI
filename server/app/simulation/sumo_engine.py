import asyncio
import math
import os
import random
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal

from app.schemas.editor import EditorPatchDto
from app.schemas.osm import CityMapDto, CoordinateDto
from app.schemas.simulation import (
    PedestrianStateDto,
    SimulationMode,
    SimulationStateDto,
    TrafficEventDto,
    TrafficSignalStateDto,
    VehicleStateDto,
)
from app.simulation.controllers import SignalController
from app.simulation.events import TrafficEvent, maybe_generate_random_event
from app.simulation.ai_tls_controller import UrbanFlowTlsController
from app.simulation.metrics import build_intersection_load, build_metrics, build_road_load
from app.simulation.sumo_scenario import build_sumo_scenario, ensure_sumo_python_tools, sumo_environment


TrafficLightOverride = Literal["sumo", "red", "yellow", "green"]

VEHICLE_COLORS = ["#38bdf8", "#e5e7eb", "#111827", "#facc15", "#ef4444", "#22c55e", "#f97316"]
PEDESTRIAN_COLORS = ["#38bdf8", "#22c55e", "#ef4444", "#facc15", "#a855f7", "#f8fafc"]

@dataclass
class PublicTransportStop:
    id: str
    kind: str
    edge_id: str
    lane_id: str
    position: float


@dataclass
class PublicTransportLine:
    id: str
    kind: Literal["bus", "tram"]
    label: str
    route_edges: list[str]
    stops: list[PublicTransportStop]
    period_ticks: int = 180
    last_depart_tick: int = -999999

@dataclass
class SumoSimulationEngine:
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
    events: list[TrafficEvent] = field(default_factory=list)
    editor_patches: list[EditorPatchDto] = field(default_factory=list)
    closed_road_ids: set[str] = field(default_factory=set)
    forced_open_road_ids: set[str] = field(default_factory=set)
    signal_controller: SignalController = field(default_factory=SignalController)
    urbanflow_tls_controller: UrbanFlowTlsController = field(default_factory=UrbanFlowTlsController)

    _rng: random.Random = field(init=False)
    _sumo_config_path: Path = field(init=False)
    _traci: object = field(init=False)
    _conn: object = field(init=False)
    _started: bool = field(default=False, init=False)
    _sumo_failed_reason: str | None = field(default=None, init=False)
    _vehicle_spawn_index: int = field(default=0, init=False)
    _person_spawn_index: int = field(default=0, init=False)
    _vehicle_route_ids: list[str] = field(default_factory=list, init=False)
    _sumo_location: dict[str, tuple[float, float, float, float]] | None = field(default=None, init=False)
    _scene_bounds: tuple[float, float, float, float] = field(init=False)
    _visible_sumo_edges: set[str] = field(default_factory=set, init=False)
    _vehicle_edge_weights: list[tuple[str, float]] = field(default_factory=list, init=False)
    _pedestrian_edges: list[str] = field(default_factory=list, init=False)
    _traffic_light_override: TrafficLightOverride = field(default="sumo", init=False)
    _traffic_light_program_ids: dict[str, str] = field(default_factory=dict, init=False)
    _traffic_light_override_active: bool = field(default=False, init=False)
    _public_transport_lines: list[PublicTransportLine] = field(default_factory=list, init=False)
    _public_transport_spawn_index: int = field(default=0, init=False)
    _closed_sumo_edges_by_road_id: dict[str, set[str]] = field(default_factory=dict, init=False)
    _lane_original_speeds: dict[str, float] = field(default_factory=dict, init=False)
    _event_lanes_applied: dict[str, set[str]] = field(default_factory=dict, init=False)
    _vehicle_stuck_ticks: dict[str, int] = field(default_factory=dict, init=False)
    _vehicle_speed_limited_by_event: set[str] = field(default_factory=set, init=False)
    _dynamic_route_edges_by_route_id: dict[str, list[str]] = field(default_factory=dict, init=False)
    _managed_vehicle_ids: set[str] = field(default_factory=set, init=False)
    _managed_vehicle_route_edges: dict[str, list[str]] = field(default_factory=dict, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._scene_bounds = self._build_scene_bounds()
        self._sumo_config_path = asyncio.run(
            build_sumo_scenario(
                city_map=self.city_map,
                session_id=self.session_id,
                vehicles_count=self.vehicles_count,
                pedestrians_count=self.pedestrians_count,
                signals_on_all_intersections=self.signals_on_all_intersections,
            )
        )
        self._start_sumo()

    def reset(self) -> SimulationStateDto:
        with self._lock:
            next_sumo_config_path = asyncio.run(
                build_sumo_scenario(
                    city_map=self.city_map,
                    session_id=self.session_id,
                    vehicles_count=self.vehicles_count,
                    pedestrians_count=self.pedestrians_count,
                    signals_on_all_intersections=self.signals_on_all_intersections,
                )
            )

            self._close_unlocked()
            self.tick = 0
            self.throughput = 0
            self.events = []
            self.editor_patches = []
            self.closed_road_ids = set()
            self.forced_open_road_ids = set()
            self._rng = random.Random(self.seed)
            self._vehicle_spawn_index = 0
            self._person_spawn_index = 0
            self._vehicle_route_ids = []
            self._visible_sumo_edges = set()
            self._vehicle_edge_weights = []
            self._traffic_light_program_ids = {}
            self._traffic_light_override_active = False
            self._traffic_light_override = "sumo"
            self.urbanflow_tls_controller.reset()
            self._public_transport_lines = []
            self._public_transport_spawn_index = 0
            self._closed_sumo_edges_by_road_id = {}
            self._lane_original_speeds = {}
            self._event_lanes_applied = {}
            self._vehicle_stuck_ticks = {}
            self._vehicle_speed_limited_by_event = set()
            self._dynamic_route_edges_by_route_id = {}
            self._managed_vehicle_ids = set()
            self._managed_vehicle_route_edges = {}
            self._scene_bounds = self._build_scene_bounds()
            self._sumo_config_path = next_sumo_config_path
            self._start_sumo()

            if self.mode == "ai":
                self._load_latest_ai_model_unlocked()
                self.urbanflow_tls_controller.reset()

            return self._state_unlocked()

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        if not self._started:
            return

        try:
            self._conn.close()
        except Exception:
            pass

        self._started = False

    def apply_patch(self, patch: EditorPatchDto) -> None:
        with self._lock:
            self.editor_patches.append(patch)

            if patch.kind == "clear_event":
                if patch.target_id:
                    self.events = [event for event in self.events if event.id != patch.target_id]
                    self._restore_event_lane_speeds(patch.target_id)
                    self._refresh_runtime_event_effects()
                return

            if patch.kind in {"close_road", "remove_road"} and patch.target_id:
                self.closed_road_ids.add(patch.target_id)
                self.forced_open_road_ids.discard(patch.target_id)
                self.events = [
                    event
                    for event in self.events
                    if event.target_id != patch.target_id or event.kind not in {"roadwork"}
                ]
                self._close_matching_sumo_edges(patch.target_id)
                self._vehicle_edge_weights = self._build_vehicle_edge_weights()
                return

            if patch.kind == "open_road" and patch.target_id:
                self.closed_road_ids.discard(patch.target_id)
                self.forced_open_road_ids.add(patch.target_id)
                self._open_matching_sumo_edges(patch.target_id)
                self._vehicle_edge_weights = self._build_vehicle_edge_weights()
                self._reroute_vehicles_affected_by_road(patch.target_id)
                return

            if patch.kind in {"accident", "roadwork"}:
                event = TrafficEvent(
                    id=f"editor-event:{patch.id}",
                    kind=patch.kind,
                    target_id=patch.target_id,
                    started_at_tick=self.tick,
                    duration_ticks=int(patch.payload.get("duration_ticks", 240)),
                    payload=patch.payload,
                )

                self.events.append(event)
                self._apply_event_to_sumo(event)

    def set_mode(self, mode: SimulationMode) -> SimulationStateDto:
        with self._lock:
            self.mode = mode
            self._traffic_light_override = "sumo"
            self._restore_sumo_traffic_lights()

            if mode == "ai":
                self._load_latest_ai_model_unlocked()
                self.urbanflow_tls_controller.reset()

            return self._state_unlocked()

    def set_traffic_light_override(self, override: TrafficLightOverride) -> SimulationStateDto:
        with self._lock:
            self._traffic_light_override = override

            if override == "sumo":
                self._restore_sumo_traffic_lights()
            else:
                self._set_all_traffic_lights_to_color(override)

            return self._state_unlocked()

    def update_settings(
        self,
        vehicles_count: int,
        pedestrians_count: int,
        signals_on_all_intersections: bool,
    ) -> SimulationStateDto:
        with self._lock:
            previous_vehicles_count = self.vehicles_count
            previous_pedestrians_count = self.pedestrians_count
            previous_signals_on_all_intersections = self.signals_on_all_intersections

            traffic_lights_changed = previous_signals_on_all_intersections != signals_on_all_intersections

            self.vehicles_count = vehicles_count
            self.pedestrians_count = pedestrians_count
            self.signals_on_all_intersections = signals_on_all_intersections

            if traffic_lights_changed:
                try:
                    return self.reset()
                except Exception:
                    self.vehicles_count = previous_vehicles_count
                    self.pedestrians_count = previous_pedestrians_count
                    self.signals_on_all_intersections = previous_signals_on_all_intersections
                    raise

            self._ensure_visible_vehicles()
            self._spawn_public_transport(force=False)

            return self._state_unlocked()

    def step(self, steps: int = 1) -> SimulationStateDto:
        with self._lock:
            self._require_sumo_started()

            for _ in range(steps):
                self._remove_invalid_managed_vehicles()
                self._ensure_visible_vehicles()

                self.tick += 1
                self._generate_events()
                self._refresh_runtime_event_effects()
                self._apply_traffic_light_mode()
                self._spawn_public_transport(force=False)

                self._remove_invalid_managed_vehicles()

                try:
                    self._conn.simulationStep()
                except Exception as error:
                    self._started = False
                    self._sumo_failed_reason = repr(error)
                    raise RuntimeError(f"SUMO simulation step failed: {error!r}") from error

                self._apply_traffic_light_override_after_step()
                self._remove_invalid_managed_vehicles()
                self._ensure_visible_vehicles()

            return self._state_unlocked()

    def state(self) -> SimulationStateDto:
        with self._lock:
            self._require_sumo_started()
            return self._state_unlocked()

    def _state_unlocked(self) -> SimulationStateDto:
        self._require_sumo_started()

        vehicle_states = self._vehicle_states()
        pedestrian_states = self._pedestrian_states()
        active_events = [event for event in self.events if event.is_active(self.tick)]
        road_load = build_road_load(self.city_map, vehicle_states)
        intersection_load = build_intersection_load(self.city_map, vehicle_states, pedestrian_states)
        signals = self._traffic_signal_states(intersection_load)
        metrics = build_metrics(
            vehicles=vehicle_states,
            pedestrians=pedestrian_states,
            active_events=len(active_events),
            throughput=self.throughput,
        )

        self._record_ai_training_metrics(metrics)

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

    def _load_latest_ai_model_unlocked(self) -> None:
        signal_scope = "all_intersections" if self.signals_on_all_intersections else "osm_only"

        try:
            loaded_model_path = self.urbanflow_tls_controller.load_latest_saved_model(signal_scope)

            if loaded_model_path is not None:
                print(f"UrbanFlow AI loaded saved model: {loaded_model_path}")
            else:
                print(f"UrbanFlow AI saved model not found for scope={signal_scope}; using default runtime policy.")
        except Exception as error:
            print(f"UrbanFlow AI model load failed: {error!r}; using default runtime policy.")

    def _record_ai_training_metrics(self, metrics) -> None:
        if self.mode != "ai":
            return

        try:
            from app.simulation.training_jobs import training_job_store

            training_job_store.record_runtime_metrics(
                session_id=self.session_id,
                current_step=self.tick,
                current_vehicles=self.vehicles_count,
                latest_reward=self.urbanflow_tls_controller.last_reward,
                average_wait_time=float(metrics.average_vehicle_wait_time),
                congestion_score=float(metrics.congestion_score),
                stopped_vehicles=int(metrics.stopped_vehicles),
                model_state=self.urbanflow_tls_controller.export_model_state(),
            )
        except Exception:
            return

    def _require_sumo_started(self) -> None:
        if self._started:
            return

        raise RuntimeError(f"SUMO is not running. Reason: {self._sumo_failed_reason or 'unknown'}")

    def _start_sumo(self) -> None:
        ensure_sumo_python_tools()

        for key, value in sumo_environment().items():
            if key in {"SUMO_HOME", "PYTHONPATH", "PROJ_LIB"}:
                os.environ[key] = value

        import traci
        import sumolib

        self._traci = traci

        sumo_binary = sumolib.checkBinary("sumo")
        command = [
            sumo_binary,
            "-c",
            str(self._sumo_config_path),
            "--start",
            "--quit-on-end",
            "false",
            "--step-length",
            "1",
            "--no-warnings",
            "true",
            "--ignore-route-errors",
            "true",
        ]

        try:
            traci.start(command, label=self.session_id)
            self._conn = traci.getConnection(self.session_id)
            self._started = True
            self._sumo_failed_reason = None
            self._sumo_location = self._load_sumo_location()
            self._visible_sumo_edges = self._build_visible_sumo_edges()
            self._vehicle_edge_weights = self._build_vehicle_edge_weights()
            self._cache_traffic_light_programs()
            self._cache_spawn_sources()
            self._cache_public_transport_lines()
            self._ensure_visible_vehicles()
            self._spawn_public_transport(force=False)
        except Exception as error:
            self._started = False
            self._sumo_failed_reason = repr(error)
            raise

    def _vehicle_states(self) -> list[VehicleStateDto]:
        result: list[VehicleStateDto] = []

        for vehicle_id in self._conn.vehicle.getIDList():
            state = self._vehicle_state_from_id(vehicle_id)

            if state is not None:
                result.append(state)

        normal = [vehicle for vehicle in result if not self._is_public_transport_vehicle(vehicle.id, vehicle.kind)]
        public_transport = [vehicle for vehicle in result if self._is_public_transport_vehicle(vehicle.id, vehicle.kind)]

        return normal[: self.vehicles_count] + public_transport

    def _vehicle_state_from_id(self, vehicle_id: str) -> VehicleStateDto | None:
        try:
            x, y = self._conn.vehicle.getPosition(vehicle_id)
            angle = self._conn.vehicle.getAngle(vehicle_id)
            speed = self._conn.vehicle.getSpeed(vehicle_id)
            road_id = self._conn.vehicle.getRoadID(vehicle_id)
            lane_id = self._conn.vehicle.getLaneID(vehicle_id)
            lane_index = self._lane_index_from_lane_id(lane_id)
            vehicle_type = self._conn.vehicle.getTypeID(vehicle_id)
            vehicle_class = self._conn.vehicle.getVehicleClass(vehicle_id)
            length = self._conn.vehicle.getLength(vehicle_id)
            width = self._conn.vehicle.getWidth(vehicle_id)
        except Exception:
            return None

        if not road_id or road_id.startswith(":"):
            return None

        lat, lon, city_x, city_z = self._sumo_position_to_city_coordinates(x, y)

        if not self._point_inside_scene(city_x, city_z):
            return None

        frontend_kind = self._frontend_vehicle_kind(vehicle_id, vehicle_type, vehicle_class)

        return VehicleStateDto(
            id=vehicle_id,
            kind=frontend_kind,
            color=VEHICLE_COLORS[stable_index(vehicle_id, len(VEHICLE_COLORS))],
            lat=round(lat, 8),
            lon=round(lon, 8),
            x=round(city_x, 3),
            z=round(city_z, 3),
            elevation_m=0.0,
            speed_mps=round(speed, 2),
            wait_time=0.0 if speed > 0.5 else 1.0,
            road_id=self._city_road_id_from_sumo_edge(road_id),
            route_edge_ids=[],
            current_edge_id=road_id,
            heading_rad=round(math.radians(90 - angle), 5),
            lane_offset_m=round(lane_index * 3.2, 3),
            length_m=round(length, 2),
            width_m=round(width, 2),
        )

    def _pedestrian_states(self) -> list[PedestrianStateDto]:
        result: list[PedestrianStateDto] = []

        for person_id in self._conn.person.getIDList():
            try:
                x, y = self._conn.person.getPosition(person_id)
                angle = self._conn.person.getAngle(person_id)
                speed = self._conn.person.getSpeed(person_id)
            except Exception:
                continue

            lat, lon, city_x, city_z = self._sumo_position_to_city_coordinates(x, y)

            if not self._point_inside_scene(city_x, city_z):
                continue

            result.append(
                PedestrianStateDto(
                    id=person_id,
                    color=PEDESTRIAN_COLORS[stable_index(person_id, len(PEDESTRIAN_COLORS))],
                    lat=round(lat, 8),
                    lon=round(lon, 8),
                    x=round(city_x, 3),
                    z=round(city_z, 3),
                    speed_mps=round(speed, 2),
                    wait_time=0.0 if speed > 0.2 else 1.0,
                    heading_rad=round(math.radians(90 - angle), 5),
                )
            )

        return result[: self.pedestrians_count]

    def _traffic_signal_states(self, intersection_load) -> list[TrafficSignalStateDto]:
        result: list[TrafficSignalStateDto] = []

        try:
            tls_ids = list(self._conn.trafficlight.getIDList())
        except Exception:
            tls_ids = []

        if not tls_ids:
            return result

        target_intersections = self.city_map.intersections

        if not self.signals_on_all_intersections:
            target_intersections = [
                intersection
                for intersection in self.city_map.intersections
                if intersection.has_signal
            ]

        for index, intersection in enumerate(target_intersections):
            tls_id = tls_ids[index % len(tls_ids)]

            try:
                phase = self._conn.trafficlight.getPhase(tls_id)
                next_switch = self._conn.trafficlight.getNextSwitch(tls_id)
                state = self._conn.trafficlight.getRedYellowGreenState(tls_id)
            except Exception:
                continue

            result.append(
                TrafficSignalStateDto(
                    id=f"sumo-signal:{tls_id}:{intersection.id}",
                    intersection_id=intersection.id,
                    phase=sumo_signal_phase_name(state=state, phase=phase),
                    time_left=max(0.0, round(next_switch - self.tick, 2)),
                    controlled_road_ids=intersection.connected_road_ids,
                )
            )

        return result

    def _apply_traffic_light_mode(self) -> None:
        if self._traffic_light_override != "sumo":
            self._set_all_traffic_lights_to_color(self._traffic_light_override)
            return

        if self._traffic_light_override_active:
            self._restore_sumo_traffic_lights()

        if self.mode == "rule_based":
            return

        if self.mode == "ai":
            self.urbanflow_tls_controller.apply(self._conn, self.tick)
            return

        try:
            tls_ids = list(self._conn.trafficlight.getIDList())
        except Exception:
            return

        if not tls_ids:
            return

        minute_index = self.tick // 60

        for index, tls_id in enumerate(tls_ids):
            try:
                logics = self._conn.trafficlight.getAllProgramLogics(tls_id)
            except Exception:
                continue

            if not logics:
                continue

            phase_count = len(logics[0].phases)

            if phase_count <= 0:
                continue

            if phase_count == 1:
                target_phase = 0
            else:
                first_phase = 0
                opposite_phase = max(1, phase_count // 2)
                target_phase = first_phase if (minute_index + index) % 2 == 0 else opposite_phase

            try:
                self._conn.trafficlight.setPhase(tls_id, target_phase)
            except Exception:
                continue

    def _apply_traffic_light_override_after_step(self) -> None:
        if self._traffic_light_override == "sumo":
            return

        self._set_all_traffic_lights_to_color(self._traffic_light_override)

    def _cache_traffic_light_programs(self) -> None:
        self._traffic_light_program_ids = {}

        try:
            tls_ids = list(self._conn.trafficlight.getIDList())
        except Exception:
            return

        for tls_id in tls_ids:
            try:
                self._traffic_light_program_ids[tls_id] = self._conn.trafficlight.getProgram(tls_id)
            except Exception:
                continue

    def _set_all_traffic_lights_to_color(self, color: Literal["red", "yellow", "green"]) -> None:
        try:
            tls_ids = list(self._conn.trafficlight.getIDList())
        except Exception:
            return

        for tls_id in tls_ids:
            try:
                current_state = self._conn.trafficlight.getRedYellowGreenState(tls_id)
            except Exception:
                continue

            if not current_state:
                continue

            if color == "red":
                forced_state = "".join("r" if char.lower() in {"r", "g", "y", "u", "s"} else char for char in current_state)
            elif color == "yellow":
                forced_state = "".join("y" if char.lower() in {"r", "g", "y", "u", "s"} else char for char in current_state)
            else:
                forced_state = "".join("G" if char.lower() in {"r", "g", "y", "u", "s"} else char for char in current_state)

            try:
                self._conn.trafficlight.setRedYellowGreenState(tls_id, forced_state)
                self._conn.trafficlight.setPhaseDuration(tls_id, 999999)
                self._traffic_light_override_active = True
            except Exception:
                continue

    def _restore_sumo_traffic_lights(self) -> None:
        try:
            tls_ids = list(self._conn.trafficlight.getIDList())
        except Exception:
            return

        for tls_id in tls_ids:
            program_id = self._traffic_light_program_ids.get(tls_id)

            if program_id is None:
                continue

            try:
                self._conn.trafficlight.setProgram(tls_id, program_id)
            except Exception:
                continue

        self._traffic_light_override_active = False

    def _cache_spawn_sources(self) -> None:
        self._vehicle_route_ids = self._available_vehicle_route_ids()

    def _cache_public_transport_lines(self) -> None:
        self._public_transport_lines = []

        bus_lines = self._build_public_transport_lines_for_kind("bus")
        tram_lines = self._build_public_transport_lines_for_kind("tram")

        self._public_transport_lines = bus_lines + tram_lines

        covered_bus_stop_ids = {
            stop.id
            for line in self._public_transport_lines
            if line.kind == "bus"
            for stop in line.stops
        }
        covered_tram_stop_ids = {
            stop.id
            for line in self._public_transport_lines
            if line.kind == "tram"
            for stop in line.stops
        }

        bus_stops = [
            stop
            for stop in self._public_transport_stops_for_kind("bus")
            if stop.id not in covered_bus_stop_ids
        ]
        tram_stops = [
            stop
            for stop in self._public_transport_stops_for_kind("tram")
            if stop.id not in covered_tram_stop_ids
        ]

        self._public_transport_lines.extend(
            self._build_stop_arrival_lines(kind="bus", stops=bus_stops)
        )
        self._public_transport_lines.extend(
            self._build_stop_arrival_lines(kind="tram", stops=tram_stops)
        )

        for index, line in enumerate(self._public_transport_lines):
            line.period_ticks = 180
            line.last_depart_tick = -(index % line.period_ticks)

        print(
            f"UrbanFlow SUMO public transport: "
            f"{len([line for line in self._public_transport_lines if line.kind == 'bus'])} bus lines, "
            f"{len([line for line in self._public_transport_lines if line.kind == 'tram'])} tram lines"
        )

    def _build_public_transport_lines_for_kind(self, kind: Literal["bus", "tram"]) -> list[PublicTransportLine]:
        grouped_osm_ids: dict[str, list[str]] = {}

        if kind == "bus":
            allowed_types = {"bus", "trolleybus", "share_taxi", "minibus", "coach"}
            features = self.city_map.roads
        else:
            allowed_types = {"tram", "light_rail"}
            features = self.city_map.rail_lines

        for feature in features:
            route_types = set(self._text_list(getattr(feature, "route_types", [])))
            feature_kind = str(getattr(feature, "kind", "")).lower()

            if kind == "bus":
                if not route_types.intersection(allowed_types):
                    continue
            else:
                if not route_types.intersection(allowed_types) and feature_kind not in allowed_types:
                    continue

            osm_id = str(getattr(feature, "osm_id", "") or "")
            if not osm_id:
                continue

            refs = self._text_list(getattr(feature, "route_refs", []))

            if not refs:
                refs = [f"{kind}:local"]

            for ref in refs:
                key = f"{kind}:{ref}"
                grouped_osm_ids.setdefault(key, [])

                if osm_id not in grouped_osm_ids[key]:
                    grouped_osm_ids[key].append(osm_id)

        result: list[PublicTransportLine] = []
        stops = self._public_transport_stops_for_kind(kind)

        for key, osm_ids in grouped_osm_ids.items():
            candidate_edges = self._sumo_edges_for_osm_sequence(osm_ids, kind)

            if len(candidate_edges) < 1:
                continue

            route_edges = self._stitched_public_transport_route(
                candidate_edges=candidate_edges,
                kind=kind,
            )

            if len(route_edges) < 1:
                continue

            if not self._public_transport_route_is_departable(route_edges, kind):
                continue

            route_id = f"pt_route_{safe_runtime_id(key)}_{len(result)}"

            try:
                self._conn.route.add(route_id, route_edges)
            except Exception:
                continue

            route_edge_set = set(route_edges)
            line_stops = [
                stop
                for stop in stops
                if stop.edge_id in route_edge_set
            ]

            result.append(
                PublicTransportLine(
                    id=route_id,
                    kind=kind,
                    label=key,
                    route_edges=route_edges,
                    stops=line_stops,
                    period_ticks=180,
                )
            )

            reverse_route_edges = self._reverse_public_transport_route(route_edges, kind)

            if len(reverse_route_edges) >= 2 and self._public_transport_route_is_departable(reverse_route_edges, kind):
                reverse_route_id = f"{route_id}_reverse"

                try:
                    self._conn.route.add(reverse_route_id, reverse_route_edges)
                    reverse_route_edge_set = set(reverse_route_edges)
                    reverse_stops = [
                        stop
                        for stop in reversed(line_stops)
                        if stop.edge_id in reverse_route_edge_set
                    ]

                    result.append(
                        PublicTransportLine(
                            id=reverse_route_id,
                            kind=kind,
                            label=f"{key}:reverse",
                            route_edges=reverse_route_edges,
                            stops=reverse_stops,
                            period_ticks=180,
                        )
                    )
                except Exception:
                    pass

        return result

    def _build_stop_arrival_lines(
        self,
        kind: Literal["bus", "tram"],
        stops: list[PublicTransportStop],
    ) -> list[PublicTransportLine]:
        result: list[PublicTransportLine] = []

        for stop in stops:
            route_edges = self._route_that_reaches_stop(stop=stop, kind=kind)

            if not route_edges:
                continue

            if not self._public_transport_route_is_departable(route_edges, kind):
                continue

            route_id = (
                f"pt_stop_route_{kind}_"
                f"{safe_runtime_id(stop.id)}_"
                f"{len(result)}"
            )

            try:
                self._conn.route.add(route_id, route_edges)
            except Exception:
                continue

            result.append(
                PublicTransportLine(
                    id=route_id,
                    kind=kind,
                    label=f"{kind}:stop:{stop.id}",
                    route_edges=route_edges,
                    stops=[stop],
                    period_ticks=180,
                )
            )

        return result

    def _route_that_reaches_stop(
        self,
        stop: PublicTransportStop,
        kind: Literal["bus", "tram"],
    ) -> list[str]:
        vtype = "bus" if kind == "bus" else "tram"

        if kind == "tram":
            candidate_edges = self._edge_candidates_from_map_border(kind="tram", target_edge=stop.edge_id)
        else:
            candidate_edges = self._edge_candidates_from_map_border(kind="bus", target_edge=stop.edge_id)

        if stop.edge_id not in candidate_edges:
            candidate_edges.append(stop.edge_id)

        for start_edge in candidate_edges[:220]:
            if start_edge == stop.edge_id:
                continue

            try:
                route = self._conn.simulation.findRoute(start_edge, stop.edge_id, vType=vtype)
                route_edges = self._clean_route_edges(list(route.edges))
            except Exception:
                continue

            if len(route_edges) < 2:
                continue

            if stop.edge_id not in route_edges:
                continue

            if kind == "tram" and not self._route_looks_like_rail(route_edges):
                continue

            return route_edges

        if kind == "tram" and not self._edge_allows_tram(stop.edge_id):
            return []

        if kind == "bus" and not self._edge_allows_bus(stop.edge_id):
            return []

        return [stop.edge_id]

    def _public_transport_candidate_edges(self, kind: Literal["bus", "tram"]) -> list[str]:
        result: list[str] = []

        for edge_id in sorted(self._visible_sumo_edges):
            if edge_id.startswith(":"):
                continue

            if kind == "tram":
                if self._edge_allows_tram(edge_id) or self._edge_looks_like_rail(edge_id):
                    result.append(edge_id)
            else:
                if self._edge_allows_bus(edge_id):
                    result.append(edge_id)

        if kind == "tram" and not result:
            for edge_id in sorted(self._visible_sumo_edges):
                if edge_id.startswith(":"):
                    continue

                if self._edge_looks_like_rail(edge_id):
                    result.append(edge_id)

        return result

    def _edge_candidates_from_map_border(
        self,
        kind: Literal["bus", "tram"],
        target_edge: str,
    ) -> list[str]:
        candidates = self._public_transport_candidate_edges(kind)

        if not candidates:
            return []

        target_center = self._edge_city_center(target_edge)

        min_x, max_x, min_z, max_z = self._scene_bounds

        scored: list[tuple[float, str]] = []

        for edge_id in candidates:
            if edge_id == target_edge:
                continue

            center = self._edge_city_center(edge_id)

            if center is None:
                continue

            edge_x, edge_z = center

            border_score = min(
                abs(edge_x - min_x),
                abs(edge_x - max_x),
                abs(edge_z - min_z),
                abs(edge_z - max_z),
            )

            if target_center is None:
                distance_score = 0.0
            else:
                target_x, target_z = target_center
                distance_score = math.hypot(edge_x - target_x, edge_z - target_z)

            score = border_score - distance_score * 0.35

            scored.append((score, edge_id))

        scored.sort(key=lambda item: item[0])

        border_edges = [edge_id for _score, edge_id in scored[:120]]
        self._rng.shuffle(border_edges)

        return border_edges

    def _edge_city_center(self, edge_id: str) -> tuple[float, float] | None:
        points = self._sumo_edge_city_points(edge_id)

        if not points:
            return None

        xs = [point[2] for point in points]
        zs = [point[3] for point in points]

        return sum(xs) / len(xs), sum(zs) / len(zs)

    def _best_sumo_edge_for_city_polyline(
        self,
        coordinates: list[CoordinateDto],
        kind: Literal["bus", "tram"],
    ) -> str | None:
        if not coordinates:
            return None

        candidate_edges = self._public_transport_candidate_edges(kind)

        if not candidate_edges:
            return None

        target_points = coordinates[:: max(1, len(coordinates) // 6)]

        best_edge_id = None
        best_distance = 999999999.0

        for edge_id in candidate_edges:
            edge_points = self._sumo_edge_city_points(edge_id)

            if not edge_points:
                continue

            for target in target_points:
                for _lat, _lon, x, z in edge_points:
                    distance = ((target.x - x) ** 2 + (target.z - z) ** 2) ** 0.5

                    if distance < best_distance:
                        best_distance = distance
                        best_edge_id = edge_id

        if best_edge_id is None:
            return None

        if best_distance > 90:
            return None

        return best_edge_id

    def _sumo_edge_city_points(self, edge_id: str) -> list[tuple[float, float, float, float]]:
        result: list[tuple[float, float, float, float]] = []

        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return result

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                shape = self._conn.lane.getShape(lane_id)
            except Exception:
                continue

            for x, y in shape:
                result.append(self._sumo_position_to_city_coordinates(x, y))

            if result:
                return result

        return result

    def _first_lane_id(self, edge_id: str) -> str | None:
        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return None

        if lane_count <= 0:
            return None

        return f"{edge_id}_0"

    def _edge_looks_like_rail(self, edge_id: str) -> bool:
        text = edge_id.lower()

        if "rail" in text or "tram" in text:
            return True

        city_rail = self._city_rail_from_sumo_edge(edge_id)

        if city_rail is not None:
            return True

        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return False

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                allowed = set(self._conn.lane.getAllowed(lane_id))
            except Exception:
                allowed = set()

            if {"tram", "rail", "rail_urban"} & allowed:
                return True

            for param_key in ["origId", "origid", "osm:id", "osmId"]:
                try:
                    value = self._conn.lane.getParameter(lane_id, param_key)
                except Exception:
                    continue

                if self._osm_value_matches_city_rail(value):
                    return True

        return False

    def _osm_value_matches_city_rail(self, value: str) -> bool:
        tokens = set(re.findall(r"\d+", value))

        if not tokens:
            return False

        for rail in self.city_map.rail_lines:
            if not rail.is_tram:
                continue

            if rail.osm_id in tokens:
                return True

        return False

    def _city_rail_from_sumo_edge(self, edge_id: str):
        tokens = self._osm_tokens_from_sumo_edge(edge_id)

        for rail in self.city_map.rail_lines:
            if not rail.is_tram:
                continue

            if rail.osm_id in tokens:
                return rail

        return None

    def _stitched_public_transport_route(
        self,
        candidate_edges: list[str],
        kind: Literal["bus", "tram"],
    ) -> list[str]:
        cleaned_candidates = self._clean_route_edges(candidate_edges)

        if not cleaned_candidates:
            return []

        if len(cleaned_candidates) == 1:
            return cleaned_candidates

        vtype = "bus" if kind == "bus" else "tram"
        stitched: list[str] = []

        current_edge = cleaned_candidates[0]
        stitched.append(current_edge)

        for next_edge in cleaned_candidates[1:]:
            if next_edge == current_edge:
                continue

            try:
                route = self._conn.simulation.findRoute(current_edge, next_edge, vType=vtype)
                route_edges = self._clean_route_edges(list(route.edges))
            except Exception:
                continue

            if len(route_edges) < 1:
                continue

            if kind == "tram" and not self._route_looks_like_rail(route_edges):
                continue

            for edge_id in route_edges:
                if not stitched or stitched[-1] != edge_id:
                    stitched.append(edge_id)

            current_edge = stitched[-1]

        if kind == "tram" and not self._route_looks_like_rail(stitched):
            return []

        return stitched

    def _reverse_public_transport_route(
        self,
        route_edges: list[str],
        kind: Literal["bus", "tram"],
    ) -> list[str]:
        if len(route_edges) < 2:
            return []

        vtype = "bus" if kind == "bus" else "tram"
        reversed_targets = list(reversed(route_edges))
        stitched: list[str] = []

        current_edge = reversed_targets[0]
        stitched.append(current_edge)

        for next_edge in reversed_targets[1:]:
            if next_edge == current_edge:
                continue

            try:
                route = self._conn.simulation.findRoute(current_edge, next_edge, vType=vtype)
                route_edges_part = self._clean_route_edges(list(route.edges))
            except Exception:
                continue

            if len(route_edges_part) < 1:
                continue

            if kind == "tram" and not self._route_looks_like_rail(route_edges_part):
                continue

            for edge_id in route_edges_part:
                if not stitched or stitched[-1] != edge_id:
                    stitched.append(edge_id)

            current_edge = stitched[-1]

        if kind == "tram" and not self._route_looks_like_rail(stitched):
            return []

        return stitched

    def _clean_route_edges(self, route_edges: list[str]) -> list[str]:
        result: list[str] = []

        for edge_id in route_edges:
            if not edge_id:
                continue

            if edge_id.startswith(":"):
                continue

            if result and result[-1] == edge_id:
                continue

            result.append(edge_id)

        return result

    def _public_transport_route_is_departable(
        self,
        route_edges: list[str],
        kind: Literal["bus", "tram"],
    ) -> bool:
        if not route_edges:
            return False

        first_edge = route_edges[0]

        if self._sumo_edge_is_closed(first_edge):
            return False

        if kind == "bus":
            return self._edge_allows_bus(first_edge)

        return self._edge_allows_tram(first_edge)

    def _spawn_public_transport(self, force: bool) -> None:
        if not self._public_transport_lines:
            return

        for line in self._public_transport_lines:
            if not force and self.tick - line.last_depart_tick < line.period_ticks:
                continue

            line.last_depart_tick = self.tick

            if not self._public_transport_route_is_departable(line.route_edges, line.kind):
                continue

            vehicle_id = (
                f"pt_{line.kind}_{safe_runtime_id(line.label)}_"
                f"{self.session_id.replace(':', '_')}_{self.tick}_{self._public_transport_spawn_index}"
            )
            self._public_transport_spawn_index += 1

            try:
                self._conn.vehicle.add(
                    vehID=vehicle_id,
                    routeID=line.id,
                    typeID="bus" if line.kind == "bus" else "tram",
                    depart="now",
                    departLane="best",
                    departSpeed="max",
                )
            except Exception:
                continue

            for stop in line.stops:
                try:
                    if stop.kind == "busstop":
                        self._conn.vehicle.setBusStop(vehicle_id, stop.id, duration=14.0)
                    else:
                        if stop.id.startswith("virtual_tram_stop_"):
                            continue

                        lane_index = self._lane_index_from_lane_id(stop.lane_id)
                        self._conn.vehicle.setStop(
                            vehicle_id,
                            stop.edge_id,
                            pos=max(0.0, stop.position),
                            laneIndex=lane_index,
                            duration=14.0,
                        )
                except Exception:
                    continue

    def _public_transport_stops_for_kind(self, kind: Literal["bus", "tram"]) -> list[PublicTransportStop]:
        result: list[PublicTransportStop] = []

        if kind == "bus":
            result.extend(self._traci_stops_from_domain("busstop", expected_kind="busstop"))
            return result

        result.extend(self._traci_stops_from_domain("trainstop", expected_kind="trainstop"))

        existing_edge_ids = {stop.edge_id for stop in result}

        for stop in self._traci_stops_from_domain("busstop", expected_kind="busstop"):
            if stop.edge_id in existing_edge_ids:
                continue

            if self._edge_allows_tram(stop.edge_id) or self._edge_looks_like_rail(stop.edge_id):
                result.append(stop)
                existing_edge_ids.add(stop.edge_id)

        for rail in self.city_map.rail_lines:
            if not rail.is_tram:
                continue

            edge_id = self._best_sumo_edge_for_city_polyline(
                coordinates=rail.coordinates,
                kind="tram",
            )

            if edge_id is None:
                continue

            if edge_id in existing_edge_ids:
                continue

            lane_id = self._first_lane_id(edge_id)

            if lane_id is None:
                continue

            result.append(
                PublicTransportStop(
                    id=f"virtual_tram_stop_{safe_runtime_id(rail.id)}",
                    kind="trainstop",
                    edge_id=edge_id,
                    lane_id=lane_id,
                    position=max(4.0, self._edge_length(edge_id) * 0.5),
                )
            )
            existing_edge_ids.add(edge_id)

        return result

    def _traci_stops_from_domain(self, domain_name: str, expected_kind: str) -> list[PublicTransportStop]:
        result: list[PublicTransportStop] = []
        domain = getattr(self._conn, domain_name, None)

        if domain is None:
            return result

        try:
            stop_ids = list(domain.getIDList())
        except Exception:
            return result

        for stop_id in stop_ids:
            try:
                lane_id = str(domain.getLaneID(stop_id))
                position = float(domain.getStartPos(stop_id))
            except Exception:
                continue

            edge_id = lane_id.rsplit("_", 1)[0]

            if edge_id not in self._visible_sumo_edges:
                continue

            result.append(
                PublicTransportStop(
                    id=stop_id,
                    kind=expected_kind,
                    edge_id=edge_id,
                    lane_id=lane_id,
                    position=position,
                )
            )

        return result

    def _sumo_edges_for_osm_sequence(self, osm_ids: list[str], kind: Literal["bus", "tram"]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        osm_set = set(osm_ids)

        for edge_id in self._conn.edge.getIDList():
            if edge_id.startswith(":"):
                continue

            if edge_id not in self._visible_sumo_edges:
                continue

            edge_tokens = self._osm_tokens_from_sumo_edge(edge_id)

            if not edge_tokens.intersection(osm_set):
                continue

            if kind == "tram" and not self._edge_allows_tram(edge_id):
                continue

            if kind == "bus" and not self._edge_allows_bus(edge_id):
                continue

            if edge_id in seen:
                continue

            seen.add(edge_id)
            result.append(edge_id)

        ordered: list[str] = []

        for osm_id in osm_ids:
            for edge_id in result:
                if edge_id in ordered:
                    continue

                if osm_id in self._osm_tokens_from_sumo_edge(edge_id):
                    ordered.append(edge_id)

        return ordered

    def _route_looks_like_rail(self, route_edges: list[str]) -> bool:
        if not route_edges:
            return False

        rail_like_count = sum(1 for edge_id in route_edges if self._edge_allows_tram(edge_id) or self._edge_looks_like_rail(edge_id))
        return rail_like_count >= max(1, len(route_edges) // 2)

    def _edge_allows_bus(self, edge_id: str) -> bool:
        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return False

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                allowed = set(self._conn.lane.getAllowed(lane_id))
                disallowed = set(self._conn.lane.getDisallowed(lane_id))
            except Exception:
                continue

            if "bus" in disallowed:
                continue

            if not allowed:
                return True

            if {"bus", "public_transport"} & allowed:
                return True

        return False

    def _edge_allows_tram(self, edge_id: str) -> bool:
        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return False

        if self._edge_looks_like_rail(edge_id):
            return True

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                allowed = set(self._conn.lane.getAllowed(lane_id))
                disallowed = set(self._conn.lane.getDisallowed(lane_id))
            except Exception:
                continue

            if "tram" in disallowed or "rail_urban" in disallowed:
                continue

            if {"tram", "rail_urban", "rail"} & allowed:
                return True

        return False

    def _osm_tokens_from_sumo_edge(self, edge_id: str) -> set[str]:
        result = set(re.findall(r"\d+", edge_id))

        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return result

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            for param_key in ["origId", "origid", "osm:id", "osmId"]:
                try:
                    value = self._conn.lane.getParameter(lane_id, param_key)
                except Exception:
                    continue

                result.update(re.findall(r"\d+", value))

        return result

    def _text_list(self, value: object) -> list[str]:
        if value is None:
            return []

        if isinstance(value, str):
            items = [value]
        elif isinstance(value, (list, tuple, set)):
            items = [str(item) for item in value]
        else:
            items = [str(value)]

        return [
            item.strip().lower()
            for item in items
            if item is not None and item.strip()
        ]

    def _ensure_visible_vehicles(self) -> None:
        if self.vehicles_count <= 0:
            return

        self._remove_invalid_managed_vehicles()

        visible_normal_vehicle_count = self._visible_normal_vehicle_count()
        missing_count = max(0, self.vehicles_count - visible_normal_vehicle_count)

        if missing_count <= 0:
            return

        spawn_limit = min(missing_count, max(150, self.vehicles_count))

        for _ in range(spawn_limit):
            route_id = self._dynamic_vehicle_route_id()

            if route_id is None:
                break

            route_edges = self._dynamic_route_edges_by_route_id.get(route_id, [])

            if not route_edges:
                continue

            if any(self._sumo_edge_is_closed(edge_id) for edge_id in route_edges):
                continue

            if not self._sumo_edge_has_departable_vehicle_lane(route_edges[0]):
                continue

            vehicle_id = f"sumo_car_{self.session_id.replace(':', '_')}_{self.tick}_{self._vehicle_spawn_index}"
            self._vehicle_spawn_index += 1

            try:
                self._conn.vehicle.add(
                    vehID=vehicle_id,
                    routeID=route_id,
                    typeID="car",
                    depart="now",
                    departLane="best",
                    departSpeed="max",
                )
            except Exception:
                continue

            self._managed_vehicle_ids.add(vehicle_id)
            self._managed_vehicle_route_edges[vehicle_id] = route_edges

    def _visible_normal_vehicle_count(self) -> int:
        count = 0

        for vehicle_id in self._conn.vehicle.getIDList():
            try:
                vehicle_type = self._conn.vehicle.getTypeID(vehicle_id)
            except Exception:
                vehicle_type = ""

            if self._is_public_transport_vehicle(vehicle_id, vehicle_type):
                continue

            if self._vehicle_state_from_id(vehicle_id) is not None:
                count += 1

        return count

    def _dynamic_vehicle_route_id(self) -> str | None:
        if not self._vehicle_edge_weights:
            self._vehicle_edge_weights = self._build_vehicle_edge_weights()

        if len(self._vehicle_edge_weights) < 2:
            return None

        edge_ids = [item[0] for item in self._vehicle_edge_weights]
        weights = [item[1] for item in self._vehicle_edge_weights]

        for _ in range(80):
            start_edge = self._rng.choices(edge_ids, weights=weights, k=1)[0]
            end_edge = self._rng.choices(edge_ids, weights=weights, k=1)[0]

            if start_edge == end_edge:
                continue

            if self._sumo_edge_is_closed(start_edge) or self._sumo_edge_is_closed(end_edge):
                continue

            if not self._sumo_edge_has_departable_vehicle_lane(start_edge):
                continue

            try:
                route = self._conn.simulation.findRoute(start_edge, end_edge, vType="car")
                route_edges = list(route.edges)
            except Exception:
                continue

            if len(route_edges) < 2:
                continue

            if any(edge_id.startswith(":") for edge_id in route_edges):
                continue

            if any(self._sumo_edge_is_closed(edge_id) for edge_id in route_edges):
                continue

            if not self._sumo_edge_has_departable_vehicle_lane(route_edges[0]):
                continue

            route_id = f"sumo_dynamic_route_{self.session_id.replace(':', '_')}_{self.tick}_{self._vehicle_spawn_index}_{self._rng.randrange(1_000_000)}"

            try:
                self._conn.route.add(route_id, route_edges)
                self._dynamic_route_edges_by_route_id[route_id] = route_edges
                return route_id
            except Exception:
                continue

        return None

    def _available_vehicle_route_ids(self) -> list[str]:
        result: list[str] = []

        for route_id in self._conn.route.getIDList():
            route_text = route_id.lower()

            if route_text.startswith("pt_") or "bus" in route_text or "tram" in route_text or "rail" in route_text:
                continue

            try:
                edges = list(self._conn.route.getEdges(route_id))
            except Exception:
                continue

            if len(edges) < 2:
                continue

            if any(edge_id.startswith(":") for edge_id in edges):
                continue

            visible_edges = [edge_id for edge_id in edges if edge_id in self._visible_sumo_edges]

            if len(visible_edges) < 2:
                continue

            result.append(route_id)

        return result

    def _ensure_visible_pedestrians(self) -> None:
        return

    def _spawn_sumo_pedestrian(self) -> None:
        return

    def _edge_length(self, edge_id: str) -> float:
        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return 20.0

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                return float(self._conn.lane.getLength(lane_id))
            except Exception:
                continue

        return 20.0

    def _build_visible_sumo_edges(self) -> set[str]:
        result: set[str] = set()

        for edge_id in self._conn.edge.getIDList():
            if edge_id.startswith(":"):
                continue

            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            if lane_count <= 0:
                continue

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    shape = self._conn.lane.getShape(lane_id)
                except Exception:
                    continue

                for x, y in shape:
                    _lat, _lon, city_x, city_z = self._sumo_position_to_city_coordinates(x, y)

                    if self._point_inside_scene(city_x, city_z):
                        result.add(edge_id)
                        break

                if edge_id in result:
                    break

        return result

    def _build_vehicle_edge_weights(self) -> list[tuple[str, float]]:
        result: list[tuple[str, float]] = []

        for edge_id in sorted(self._visible_sumo_edges):
            if edge_id.startswith(":"):
                continue

            if self._sumo_edge_is_closed(edge_id):
                continue

            if not self._sumo_edge_has_departable_vehicle_lane(edge_id):
                continue

            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            if lane_count <= 0:
                continue

            vehicle_lane_found = False
            max_speed = 8.0

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    allowed = set(self._conn.lane.getAllowed(lane_id))
                    disallowed = set(self._conn.lane.getDisallowed(lane_id))
                    max_speed = max(max_speed, float(self._conn.lane.getMaxSpeed(lane_id)))
                except Exception:
                    continue

                if self._lane_allows_vehicle(allowed, disallowed):
                    vehicle_lane_found = True

            if not vehicle_lane_found:
                continue

            city_road = self._city_road_from_sumo_edge(edge_id)
            kind = city_road.kind if city_road is not None else ""
            weight = self._vehicle_edge_weight(kind=kind, lane_count=lane_count, max_speed=max_speed)

            if weight > 0:
                result.append((edge_id, weight))

        return result

    def _vehicle_edge_weight(self, kind: str, lane_count: int, max_speed: float) -> float:
        kind_multiplier = {
            "motorway": 10.0,
            "trunk": 9.0,
            "primary": 7.5,
            "secondary": 6.2,
            "tertiary": 5.0,
            "unclassified": 3.8,
            "residential": 3.2,
            "living_street": 0.9,
            "service": 0.65,
            "track": 0.0,
            "path": 0.0,
            "footway": 0.0,
            "pedestrian": 0.0,
            "cycleway": 0.0,
            "steps": 0.0,
        }.get(kind, 3.0)

        if kind_multiplier <= 0:
            return 0.0

        lane_factor = 1.0 + max(0, lane_count - 1) * 0.55
        speed_factor = max(0.55, min(1.35, max_speed / 13.9))

        return max(0.1, kind_multiplier * lane_factor * speed_factor)

    def _build_pedestrian_edges(self) -> list[str]:
        result: list[str] = []

        for edge_id in sorted(self._visible_sumo_edges):
            if edge_id.startswith(":"):
                continue

            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    allowed = set(self._conn.lane.getAllowed(lane_id))
                    disallowed = set(self._conn.lane.getDisallowed(lane_id))
                except Exception:
                    continue

                if self._lane_allows_pedestrian(allowed, disallowed):
                    result.append(edge_id)
                    break

        return result
    
    def _sumo_edge_has_departable_vehicle_lane(self, edge_id: str) -> bool:
        if not edge_id or edge_id.startswith(":"):
            return False

        try:
            lane_count = self._conn.edge.getLaneNumber(edge_id)
        except Exception:
            return False

        for lane_index in range(lane_count):
            lane_id = f"{edge_id}_{lane_index}"

            try:
                allowed = set(self._conn.lane.getAllowed(lane_id))
                disallowed = set(self._conn.lane.getDisallowed(lane_id))
            except Exception:
                continue

            if self._lane_allows_vehicle(allowed, disallowed):
                return True

        return False
    
    def _sumo_edge_is_closed(self, edge_id: str) -> bool:
        city_road_id = self._city_road_id_from_sumo_edge(edge_id)

        if city_road_id in self.closed_road_ids:
            return True

        for closed_edges in self._closed_sumo_edges_by_road_id.values():
            if edge_id in closed_edges:
                return True

        return False
    
    def _lane_allows_vehicle(self, allowed: set[str], disallowed: set[str]) -> bool:
        if "passenger" in disallowed:
            return False

        if not allowed:
            return True

        return bool({"passenger", "taxi", "bus", "truck", "emergency"} & allowed)

    def _lane_allows_pedestrian(self, allowed: set[str], disallowed: set[str]) -> bool:
        if "pedestrian" in disallowed:
            return False

        if not allowed:
            return False

        return "pedestrian" in allowed

    def _refresh_runtime_event_effects(self) -> None:
        active_events = [event for event in self.events if event.is_active(self.tick)]
        active_event_ids = {event.id for event in active_events}

        expired_event_ids = [
            event_id
            for event_id in self._event_lanes_applied
            if event_id not in active_event_ids
        ]

        for event_id in expired_event_ids:
            self._restore_event_lane_speeds(event_id)

        for vehicle_id in list(self._vehicle_speed_limited_by_event):
            try:
                self._conn.vehicle.setSpeed(vehicle_id, -1)
            except Exception:
                pass

        self._vehicle_speed_limited_by_event = set()

        for event in active_events:
            self._apply_event_to_sumo(event)

        self._apply_accident_vehicle_speed_limits(active_events)

    def _apply_event_to_sumo(self, event: TrafficEvent) -> None:
        if event.kind == "roadwork":
            self._apply_roadwork_to_sumo(event)

    def _apply_roadwork_to_sumo(self, event: TrafficEvent) -> None:
        if not event.target_id:
            return

        if event.id in self._event_lanes_applied:
            return

        multiplier = self._float_payload(event.payload, "speed_multiplier", 0.5)
        multiplier = max(0.1, min(1.0, multiplier))

        edge_ids = self._sumo_edges_for_city_road(event.target_id)
        changed_lanes: set[str] = set()

        for edge_id in edge_ids:
            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    original_speed = float(self._conn.lane.getMaxSpeed(lane_id))
                except Exception:
                    continue

                if lane_id not in self._lane_original_speeds:
                    self._lane_original_speeds[lane_id] = original_speed

                try:
                    self._conn.lane.setMaxSpeed(lane_id, max(1.4, original_speed * multiplier))
                    changed_lanes.add(lane_id)
                except Exception:
                    continue

        if changed_lanes:
            self._event_lanes_applied[event.id] = changed_lanes
            self._reroute_vehicles_affected_by_road(event.target_id)

    def _restore_event_lane_speeds(self, event_id: str) -> None:
        lane_ids = self._event_lanes_applied.pop(event_id, set())

        for lane_id in lane_ids:
            original_speed = self._lane_original_speeds.get(lane_id)

            if original_speed is None:
                continue

            try:
                self._conn.lane.setMaxSpeed(lane_id, original_speed)
            except Exception:
                continue

    def _apply_accident_vehicle_speed_limits(self, active_events: list[TrafficEvent]) -> None:
        accident_events = [
            event
            for event in active_events
            if event.kind == "accident" and event.target_id
        ]

        if not accident_events:
            return

        for vehicle_id in self._conn.vehicle.getIDList():
            try:
                road_id = self._conn.vehicle.getRoadID(vehicle_id)
                x, y = self._conn.vehicle.getPosition(vehicle_id)
            except Exception:
                continue

            if not road_id or road_id.startswith(":"):
                continue

            lat, lon, city_x, city_z = self._sumo_position_to_city_coordinates(x, y)

            for event in accident_events:
                if not event.target_id:
                    continue

                if self._city_road_id_from_sumo_edge(road_id) != event.target_id:
                    continue

                event_x = self._float_payload(event.payload, "x", None)
                event_z = self._float_payload(event.payload, "z", None)
                radius_m = self._float_payload(event.payload, "radius_m", 10.0)

                if event_x is None or event_z is None:
                    event_point = self._event_point_for_road(event)

                    if event_point is None:
                        continue

                    event_x, event_z = event_point

                distance = math.hypot(city_x - event_x, city_z - event_z)

                if distance > radius_m:
                    continue

                try:
                    self._conn.vehicle.setSpeed(vehicle_id, 2.78)
                    self._vehicle_speed_limited_by_event.add(vehicle_id)
                except Exception:
                    pass

                break

    def _event_point_for_road(self, event: TrafficEvent) -> tuple[float, float] | None:
        if not event.target_id:
            return None

        road = next((item for item in self.city_map.roads if item.id == event.target_id), None)

        if road is None or len(road.coordinates) < 2:
            return None

        progress = self._float_payload(event.payload, "progress", 0.5)
        progress = max(0.0, min(1.0, progress))

        segment_index = min(
            len(road.coordinates) - 2,
            max(0, int(progress * (len(road.coordinates) - 1))),
        )

        segment_progress = progress * (len(road.coordinates) - 1) - segment_index
        start = road.coordinates[segment_index]
        end = road.coordinates[segment_index + 1]

        return (
            start.x + (end.x - start.x) * segment_progress,
            start.z + (end.z - start.z) * segment_progress,
        )

    def _rescue_stuck_vehicles(self) -> None:
        for vehicle_id in self._conn.vehicle.getIDList():
            try:
                speed = float(self._conn.vehicle.getSpeed(vehicle_id))
                road_id = self._conn.vehicle.getRoadID(vehicle_id)
            except Exception:
                continue

            if not road_id or road_id.startswith(":"):
                self._vehicle_stuck_ticks.pop(vehicle_id, None)
                continue

            if self._vehicle_waiting_at_red_light(vehicle_id):
                self._vehicle_stuck_ticks.pop(vehicle_id, None)
                continue

            if self._vehicle_near_active_event(vehicle_id):
                self._vehicle_stuck_ticks.pop(vehicle_id, None)
                continue

            if speed > 0.25:
                self._vehicle_stuck_ticks.pop(vehicle_id, None)
                continue

            stuck_ticks = self._vehicle_stuck_ticks.get(vehicle_id, 0) + 1
            self._vehicle_stuck_ticks[vehicle_id] = stuck_ticks

            if stuck_ticks < 25:
                continue

            try:
                self._conn.vehicle.setSpeed(vehicle_id, -1)
            except Exception:
                pass

            rescued = self._assign_fresh_route_from_current_edge(vehicle_id, road_id)

            if not rescued:
                try:
                    self._conn.vehicle.rerouteTraveltime(vehicle_id)
                except Exception:
                    pass

            self._vehicle_stuck_ticks[vehicle_id] = 0

    def _vehicle_waiting_at_red_light(self, vehicle_id: str) -> bool:
        try:
            next_tls = self._conn.vehicle.getNextTLS(vehicle_id)
        except Exception:
            return False

        if not next_tls:
            return False

        for item in next_tls:
            try:
                state = str(item[3]).lower()
                distance = float(item[2])
            except Exception:
                continue

            if distance <= 18 and ("r" in state or "y" in state):
                return True

        return False

    def _vehicle_near_active_event(self, vehicle_id: str) -> bool:
        try:
            road_id = self._conn.vehicle.getRoadID(vehicle_id)
            x, y = self._conn.vehicle.getPosition(vehicle_id)
        except Exception:
            return False

        if not road_id or road_id.startswith(":"):
            return False

        _lat, _lon, city_x, city_z = self._sumo_position_to_city_coordinates(x, y)
        city_road_id = self._city_road_id_from_sumo_edge(road_id)

        for event in self.events:
            if not event.is_active(self.tick):
                continue

            if event.kind not in {"accident", "roadwork"}:
                continue

            if event.target_id != city_road_id:
                continue

            if event.kind == "roadwork":
                return True

            event_point = self._event_point_for_road(event)

            if event_point is None:
                return True

            radius_m = self._float_payload(event.payload, "radius_m", 10.0)
            event_x, event_z = event_point

            if math.hypot(city_x - event_x, city_z - event_z) <= radius_m + 8:
                return True

        return False

    def _assign_fresh_route_from_current_edge(self, vehicle_id: str, current_edge: str) -> bool:
        if current_edge.startswith(":"):
            return False

        if self._sumo_edge_is_closed(current_edge):
            return False

        if not self._vehicle_edge_weights:
            self._vehicle_edge_weights = self._build_vehicle_edge_weights()

        if len(self._vehicle_edge_weights) < 2:
            return False

        edge_ids = [item[0] for item in self._vehicle_edge_weights]
        weights = [item[1] for item in self._vehicle_edge_weights]

        for _ in range(40):
            target_edge = self._rng.choices(edge_ids, weights=weights, k=1)[0]

            if target_edge == current_edge:
                continue

            if self._sumo_edge_is_closed(target_edge):
                continue

            try:
                route = self._conn.simulation.findRoute(current_edge, target_edge, vType="car")
                route_edges = list(route.edges)
            except Exception:
                continue

            if len(route_edges) < 2:
                continue

            if any(edge_id.startswith(":") for edge_id in route_edges):
                continue

            if any(self._sumo_edge_is_closed(edge_id) for edge_id in route_edges):
                continue

            try:
                self._conn.vehicle.setRoute(vehicle_id, route_edges)
                return True
            except Exception:
                continue

        return False
    
    def _reroute_vehicles_affected_by_road(self, road_id: str) -> None:
        affected_edges = self._sumo_edges_for_city_road(road_id)

        if not affected_edges:
            return

        for vehicle_id in self._conn.vehicle.getIDList():
            try:
                route_edges = list(self._conn.vehicle.getRoute(vehicle_id))
                current_edge = self._conn.vehicle.getRoadID(vehicle_id)
            except Exception:
                continue

            if not any(edge_id in affected_edges for edge_id in route_edges):
                continue

            if current_edge in affected_edges:
                try:
                    self._conn.vehicle.setSpeed(vehicle_id, -1)
                except Exception:
                    pass

                continue

            try:
                self._conn.vehicle.rerouteTraveltime(vehicle_id)
            except Exception:
                pass

    def _sumo_edges_for_city_road(self, road_id: str) -> set[str]:
        result: set[str] = set()

        for edge_id in self._conn.edge.getIDList():
            if edge_id.startswith(":"):
                continue

            city_road_id = self._city_road_id_from_sumo_edge(edge_id)

            if city_road_id == road_id:
                result.add(edge_id)
                continue

            if road_id in edge_id:
                result.add(edge_id)

        return result

    def _float_payload(self, payload: dict, key: str, default):
        value = payload.get(key, default)

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
        
    def _generate_events(self) -> None:
        event = maybe_generate_random_event(
            tick=self.tick,
            road_ids=[road.id for road in self.city_map.roads if road.is_driveable],
            random_events_enabled=self.random_events_enabled,
            rng=self._rng,
        )

        if event is not None:
            self.events.append(event)

    def _remove_vehicle_from_sumo_and_cache(self, vehicle_id: str, known_vehicle_ids: set[str] | None = None) -> None:
        if known_vehicle_ids is None:
            try:
                known_vehicle_ids = set(self._conn.vehicle.getIDList())
            except Exception:
                known_vehicle_ids = set()

        if vehicle_id in known_vehicle_ids:
            try:
                self._conn.vehicle.remove(vehicle_id)
            except Exception:
                pass

        self._managed_vehicle_ids.discard(vehicle_id)
        self._managed_vehicle_route_edges.pop(vehicle_id, None)
        self._vehicle_stuck_ticks.pop(vehicle_id, None)
        self._vehicle_speed_limited_by_event.discard(vehicle_id)

    def _remove_invalid_managed_vehicles(self) -> None:
        try:
            known_vehicle_ids = set(self._conn.vehicle.getIDList())
        except Exception:
            known_vehicle_ids = set()

        for vehicle_id in list(self._managed_vehicle_ids):
            if vehicle_id not in known_vehicle_ids:
                self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)
                continue

            route_edges = self._managed_vehicle_route_edges.get(vehicle_id, [])

            if route_edges and any(self._sumo_edge_is_closed(edge_id) for edge_id in route_edges):
                self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)
                continue

            try:
                current_edge = self._conn.vehicle.getRoadID(vehicle_id)
            except Exception:
                self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)
                continue

            if current_edge and self._sumo_edge_is_closed(current_edge):
                self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)

    def _remove_vehicles_using_edges(self, edge_ids: set[str]) -> None:
        if not edge_ids:
            return

        try:
            known_vehicle_ids = set(self._conn.vehicle.getIDList())
        except Exception:
            known_vehicle_ids = set()

        self._managed_vehicle_ids.intersection_update(known_vehicle_ids)

        candidate_vehicle_ids: set[str] = set(known_vehicle_ids)

        for vehicle_id in list(candidate_vehicle_ids):
            route_edges = self._managed_vehicle_route_edges.get(vehicle_id, [])

            try:
                current_edge = self._conn.vehicle.getRoadID(vehicle_id)
            except Exception:
                self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)
                continue

            if not route_edges:
                try:
                    route_edges = list(self._conn.vehicle.getRoute(vehicle_id))
                except Exception:
                    route_edges = []

            should_remove = False

            if current_edge in edge_ids:
                should_remove = True

            if route_edges and route_edges[0] in edge_ids:
                should_remove = True

            if any(edge_id in edge_ids for edge_id in route_edges):
                should_remove = True

            if not should_remove:
                continue

            self._remove_vehicle_from_sumo_and_cache(vehicle_id, known_vehicle_ids)

    def _close_matching_sumo_edges(self, road_id: str) -> None:
        if not self._started:
            return

        edge_ids = self._sumo_edges_for_city_road(road_id)
        self._closed_sumo_edges_by_road_id[road_id] = edge_ids

        self._remove_vehicles_using_edges(edge_ids)

        blocked_classes = [
            "passenger",
            "taxi",
            "bus",
            "truck",
            "emergency",
            "delivery",
        ]

        for edge_id in edge_ids:
            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    self._conn.lane.setDisallowed(lane_id, blocked_classes)
                except Exception:
                    pass

        self._remove_vehicles_using_edges(edge_ids)
        self._dynamic_route_edges_by_route_id = {
            route_id: route_edges
            for route_id, route_edges in self._dynamic_route_edges_by_route_id.items()
            if not any(edge_id in edge_ids for edge_id in route_edges)
        }

    def _open_matching_sumo_edges(self, road_id: str) -> None:
        if not self._started:
            return

        edge_ids = self._closed_sumo_edges_by_road_id.pop(road_id, set())

        if not edge_ids:
            edge_ids = self._sumo_edges_for_city_road(road_id)

        for edge_id in edge_ids:
            try:
                lane_count = self._conn.edge.getLaneNumber(edge_id)
            except Exception:
                continue

            for lane_index in range(lane_count):
                lane_id = f"{edge_id}_{lane_index}"

                try:
                    self._conn.lane.setDisallowed(lane_id, [])
                except Exception:
                    pass

    def _city_road_from_sumo_edge(self, edge_id: str):
        osm_id = edge_id.split("#")[0].split("-")[0].replace("way_", "").replace(":", "")

        for road in self.city_map.roads:
            if road.osm_id == osm_id or road.id in edge_id:
                return road

        return None

    def _city_road_id_from_sumo_edge(self, edge_id: str) -> str:
        road = self._city_road_from_sumo_edge(edge_id)

        if road is not None:
            return road.id

        return edge_id

    def _sumo_position_to_city_coordinates(self, x: float, y: float) -> tuple[float, float, float, float]:
        try:
            lon, lat = self._conn.simulation.convertGeo(x, y, fromGeo=False)
        except Exception:
            lon_lat = self._sumo_xy_to_lon_lat(x, y)

            if lon_lat is not None:
                lon, lat = lon_lat
            else:
                lon = self.city_map.origin_lon
                lat = self.city_map.origin_lat

        city_x = (lon - self.city_map.origin_lon) * max(
            1.0,
            111_320 * math.cos(math.radians(self.city_map.origin_lat)),
        )
        city_z = (lat - self.city_map.origin_lat) * 111_320

        return lat, lon, city_x, city_z

    def _load_sumo_location(self) -> dict[str, tuple[float, float, float, float]] | None:
        net_path = self._sumo_config_path.with_name("map.net.xml")

        if not net_path.exists():
            return None

        try:
            root = ET.parse(net_path).getroot()
        except ET.ParseError:
            return None

        location = root.find("location")

        if location is None:
            return None

        conv_boundary = parse_sumo_boundary(location.get("convBoundary"))
        orig_boundary = parse_sumo_boundary(location.get("origBoundary"))

        if conv_boundary is None or orig_boundary is None:
            return None

        return {
            "conv": conv_boundary,
            "orig": orig_boundary,
        }

    def _sumo_xy_to_lon_lat(self, x: float, y: float) -> tuple[float, float] | None:
        if self._sumo_location is None:
            return None

        conv = self._sumo_location.get("conv")
        orig = self._sumo_location.get("orig")

        if conv is None or orig is None:
            return None

        conv_min_x, conv_min_y, conv_max_x, conv_max_y = conv
        orig_min_lon, orig_min_lat, orig_max_lon, orig_max_lat = orig

        conv_width = conv_max_x - conv_min_x
        conv_height = conv_max_y - conv_min_y

        if abs(conv_width) <= 0.000001 or abs(conv_height) <= 0.000001:
            return None

        lon_fraction = (x - conv_min_x) / conv_width
        lat_fraction = (y - conv_min_y) / conv_height

        lon = orig_min_lon + (orig_max_lon - orig_min_lon) * lon_fraction
        lat = orig_min_lat + (orig_max_lat - orig_min_lat) * lat_fraction

        return lon, lat

    def _build_scene_bounds(self) -> tuple[float, float, float, float]:
        points: list[CoordinateDto] = []

        for road in self.city_map.roads:
            points.extend(road.coordinates)

        for rail in self.city_map.rail_lines:
            points.extend(rail.coordinates)

        for crossing in self.city_map.crossings:
            points.append(
                CoordinateDto(
                    lat=crossing.lat,
                    lon=crossing.lon,
                    x=crossing.x,
                    z=crossing.z,
                )
            )

        if not points:
            return -1000.0, 1000.0, -1000.0, 1000.0

        min_x = min(point.x for point in points)
        max_x = max(point.x for point in points)
        min_z = min(point.z for point in points)
        max_z = max(point.z for point in points)

        padding = max(120.0, min(450.0, max(max_x - min_x, max_z - min_z) * 0.18))

        return (
            min_x - padding,
            max_x + padding,
            min_z - padding,
            max_z + padding,
        )

    def _point_inside_scene(self, x: float, z: float) -> bool:
        min_x, max_x, min_z, max_z = self._scene_bounds
        return min_x <= x <= max_x and min_z <= z <= max_z

    def _is_public_transport_vehicle(self, vehicle_id: str, vehicle_type: str) -> bool:
        text = f"{vehicle_id} {vehicle_type}".lower()

        return (
            text.startswith("pt_")
            or "pt_" in text
            or "bus" in text
            or "tram" in text
            or "trolleybus" in text
            or "minibus" in text
            or "coach" in text
            or "light_rail" in text
            or "train" in text
            or "rail" in text
        )

    def _lane_index_from_lane_id(self, lane_id: str) -> int:
        if "_" not in lane_id:
            return 0

        try:
            return int(lane_id.rsplit("_", 1)[1])
        except ValueError:
            return 0

    def _frontend_vehicle_kind(self, vehicle_id: str, vehicle_type: str, vehicle_class: str) -> str:
        text = f"{vehicle_id} {vehicle_type} {vehicle_class}".lower()

        if "tram" in text or "light_rail" in text or "rail_urban" in text:
            return "tram"

        if "train" in text or "rail" in text:
            return "tram"

        if "bus" in text or "trolleybus" in text or "coach" in text or "minibus" in text:
            return "bus"

        if "truck" in text or "lorry" in text:
            return "truck"

        if "emergency" in text:
            return "emergency"

        if "taxi" in text:
            return "taxi"

        return "car"


def sumo_signal_phase_name(state: str, phase: int) -> str:
    lowered = state.lower()

    if "g" in lowered:
        return f"green:sumo_phase_{phase}:{state}"

    if "y" in lowered:
        return f"yellow:sumo_phase_{phase}:{state}"

    if "r" in lowered:
        return f"red:sumo_phase_{phase}:{state}"

    return f"unknown:sumo_phase_{phase}:{state}"


def parse_sumo_boundary(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None

    parts = value.split(",")

    if len(parts) != 4:
        return None

    try:
        return (
            float(parts[0]),
            float(parts[1]),
            float(parts[2]),
            float(parts[3]),
        )
    except ValueError:
        return None


def stable_index(value: str, length: int) -> int:
    result = 0

    for char in value:
        result = (result * 31 + ord(char)) & 0xFFFFFFFF

    return result % max(1, length)

def safe_runtime_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    cleaned = cleaned.strip("_")

    if not cleaned:
        return "line"

    return cleaned[:80]