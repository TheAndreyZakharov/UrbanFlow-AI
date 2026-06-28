from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LaneObservation:
    lane_id: str
    edge_id: str
    vehicle_count: int
    halted_count: int
    mean_speed_mps: float
    max_speed_mps: float
    waiting_time_s: float
    occupancy: float
    length_m: float
    allowed_classes: tuple[str, ...]
    disallowed_classes: tuple[str, ...]

    @property
    def low_speed_score(self) -> float:
        if self.vehicle_count <= 0:
            return 0.0

        if self.max_speed_mps <= 0.1:
            return 1.0

        return max(0.0, min(1.0, 1.0 - self.mean_speed_mps / self.max_speed_mps))


@dataclass(frozen=True)
class TlsPhaseObservation:
    phase_index: int
    state: str
    green_lanes: tuple[str, ...]
    controlled_lanes: tuple[str, ...]
    queue_score: float
    vehicle_score: float
    wait_score: float
    speed_score: float
    occupancy_score: float
    emergency_score: float
    total_pressure: float


@dataclass(frozen=True)
class TlsObservation:
    tls_id: str
    current_phase_index: int
    current_phase_state: str
    program_id: str
    controlled_lanes: tuple[str, ...]
    lanes: dict[str, LaneObservation]
    phases: tuple[TlsPhaseObservation, ...]
    total_vehicle_count: int
    total_halted_count: int
    total_waiting_time_s: float
    average_speed_mps: float
    max_pressure: float
    current_pressure: float
    tick: int
    extra: dict[str, float] = field(default_factory=dict)


def collect_tls_observation(
    conn,
    tls_id: str,
    tick: int,
    max_controlled_lanes: int = 64,
) -> TlsObservation | None:
    try:
        current_phase_index = int(conn.trafficlight.getPhase(tls_id))
        current_phase_state = str(conn.trafficlight.getRedYellowGreenState(tls_id))
        program_id = str(conn.trafficlight.getProgram(tls_id))
        controlled_lanes = tuple(str(lane_id) for lane_id in conn.trafficlight.getControlledLanes(tls_id))
        logics = conn.trafficlight.getAllProgramLogics(tls_id)
    except Exception:
        return None

    if not logics or not logics[0].phases:
        return None

    controlled_lanes = controlled_lanes[:max_controlled_lanes]

    if not controlled_lanes:
        return None

    lane_observations: dict[str, LaneObservation] = {}

    for lane_id in controlled_lanes:
        if lane_id in lane_observations:
            continue

        lane_observation = collect_lane_observation(conn, lane_id)

        if lane_observation is not None:
            lane_observations[lane_id] = lane_observation

    phases: list[TlsPhaseObservation] = []

    for phase_index, phase in enumerate(logics[0].phases):
        state = str(phase.state)
        green_lanes = tuple(
            lane_id
            for index, lane_id in enumerate(controlled_lanes)
            if index < len(state) and state[index] in {"G", "g"}
        )

        phases.append(
            build_phase_observation(
                phase_index=phase_index,
                state=state,
                green_lanes=green_lanes,
                controlled_lanes=controlled_lanes,
                lane_observations=lane_observations,
            )
        )

    total_vehicle_count = sum(lane.vehicle_count for lane in lane_observations.values())
    total_halted_count = sum(lane.halted_count for lane in lane_observations.values())
    total_waiting_time_s = sum(lane.waiting_time_s for lane in lane_observations.values())

    if lane_observations:
        average_speed_mps = sum(lane.mean_speed_mps for lane in lane_observations.values()) / len(lane_observations)
    else:
        average_speed_mps = 0.0

    current_pressure = 0.0

    for phase in phases:
        if phase.phase_index == current_phase_index:
            current_pressure = phase.total_pressure
            break

    max_pressure = max((phase.total_pressure for phase in phases), default=0.0)

    return TlsObservation(
        tls_id=tls_id,
        current_phase_index=current_phase_index,
        current_phase_state=current_phase_state,
        program_id=program_id,
        controlled_lanes=controlled_lanes,
        lanes=lane_observations,
        phases=tuple(phases),
        total_vehicle_count=total_vehicle_count,
        total_halted_count=total_halted_count,
        total_waiting_time_s=total_waiting_time_s,
        average_speed_mps=average_speed_mps,
        max_pressure=max_pressure,
        current_pressure=current_pressure,
        tick=tick,
    )


def collect_lane_observation(conn, lane_id: str) -> LaneObservation | None:
    try:
        vehicle_count = int(conn.lane.getLastStepVehicleNumber(lane_id))
        halted_count = int(conn.lane.getLastStepHaltingNumber(lane_id))
        mean_speed_mps = float(conn.lane.getLastStepMeanSpeed(lane_id))
        max_speed_mps = float(conn.lane.getMaxSpeed(lane_id))
        waiting_time_s = float(conn.lane.getWaitingTime(lane_id))
        occupancy = float(conn.lane.getLastStepOccupancy(lane_id)) / 100.0
        length_m = float(conn.lane.getLength(lane_id))
        allowed = tuple(str(item) for item in conn.lane.getAllowed(lane_id))
        disallowed = tuple(str(item) for item in conn.lane.getDisallowed(lane_id))
    except Exception:
        return None

    edge_id = lane_id.rsplit("_", 1)[0] if "_" in lane_id else lane_id

    return LaneObservation(
        lane_id=lane_id,
        edge_id=edge_id,
        vehicle_count=max(0, vehicle_count),
        halted_count=max(0, halted_count),
        mean_speed_mps=max(0.0, mean_speed_mps),
        max_speed_mps=max(0.0, max_speed_mps),
        waiting_time_s=max(0.0, waiting_time_s),
        occupancy=max(0.0, min(1.0, occupancy)),
        length_m=max(0.0, length_m),
        allowed_classes=allowed,
        disallowed_classes=disallowed,
    )


def build_phase_observation(
    phase_index: int,
    state: str,
    green_lanes: tuple[str, ...],
    controlled_lanes: tuple[str, ...],
    lane_observations: dict[str, LaneObservation],
) -> TlsPhaseObservation:
    queue_score = 0.0
    vehicle_score = 0.0
    wait_score = 0.0
    speed_score = 0.0
    occupancy_score = 0.0
    emergency_score = 0.0

    for lane_id in green_lanes:
        lane = lane_observations.get(lane_id)

        if lane is None:
            continue

        queue_score += lane.halted_count
        vehicle_score += lane.vehicle_count
        wait_score += lane.waiting_time_s
        speed_score += lane.low_speed_score * max(1, lane.vehicle_count)
        occupancy_score += lane.occupancy

        if "emergency" in lane.allowed_classes:
            emergency_score += lane.vehicle_count

    total_pressure = (
        queue_score * 3.0
        + vehicle_score
        + wait_score * 0.04
        + speed_score * 0.65
        + occupancy_score * 1.6
        + emergency_score * 7.0
    )

    return TlsPhaseObservation(
        phase_index=phase_index,
        state=state,
        green_lanes=green_lanes,
        controlled_lanes=controlled_lanes,
        queue_score=queue_score,
        vehicle_score=vehicle_score,
        wait_score=wait_score,
        speed_score=speed_score,
        occupancy_score=occupancy_score,
        emergency_score=emergency_score,
        total_pressure=total_pressure,
    )


def observation_vector(observation: TlsObservation, max_phases: int = 12) -> list[float]:
    result = [
        float(observation.current_phase_index),
        float(observation.total_vehicle_count),
        float(observation.total_halted_count),
        float(observation.total_waiting_time_s),
        float(observation.average_speed_mps),
        float(observation.current_pressure),
        float(observation.max_pressure),
    ]

    phases = list(observation.phases)[:max_phases]

    for phase in phases:
        result.extend(
            [
                float(phase.phase_index),
                float(phase.queue_score),
                float(phase.vehicle_score),
                float(phase.wait_score),
                float(phase.speed_score),
                float(phase.occupancy_score),
                float(phase.total_pressure),
            ]
        )

    while len(phases) < max_phases:
        result.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        phases.append(
            TlsPhaseObservation(
                phase_index=0,
                state="",
                green_lanes=(),
                controlled_lanes=(),
                queue_score=0.0,
                vehicle_score=0.0,
                wait_score=0.0,
                speed_score=0.0,
                occupancy_score=0.0,
                emergency_score=0.0,
                total_pressure=0.0,
            )
        )

    return result