from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from urbanflow_ai.config import PolicyWeights, RuntimeControllerConfig
from urbanflow_ai.env.observations import TlsObservation, TlsPhaseObservation


ActionKind = Literal["hold", "switch_to_phase"]


@dataclass(frozen=True)
class TlsAction:
    tls_id: str
    kind: ActionKind
    target_phase_index: int
    reason: str
    score: float


@dataclass
class TlsActionRuntime:
    last_switch_tick: int = 0
    last_action_tick: int = 0
    last_phase_index: int = 0
    switches: int = 0


def choose_tls_action(
    observation: TlsObservation,
    runtime: TlsActionRuntime,
    config: RuntimeControllerConfig,
    weights: PolicyWeights,
) -> TlsAction:
    ticks_since_action = observation.tick - runtime.last_action_tick
    ticks_since_switch = observation.tick - runtime.last_switch_tick

    if ticks_since_action < config.action_interval_ticks:
        return TlsAction(
            tls_id=observation.tls_id,
            kind="hold",
            target_phase_index=observation.current_phase_index,
            reason="action_interval",
            score=observation.current_pressure,
        )

    if ticks_since_switch < config.min_green_ticks:
        return TlsAction(
            tls_id=observation.tls_id,
            kind="hold",
            target_phase_index=observation.current_phase_index,
            reason="min_green",
            score=observation.current_pressure,
        )

    candidate = best_green_phase(observation=observation, weights=weights)

    if candidate is None:
        return TlsAction(
            tls_id=observation.tls_id,
            kind="hold",
            target_phase_index=observation.current_phase_index,
            reason="no_green_candidate",
            score=observation.current_pressure,
        )

    current_pressure = observation.current_pressure
    candidate_pressure = phase_pressure(candidate, weights)

    should_switch_by_pressure = (
        candidate.phase_index != observation.current_phase_index
        and candidate_pressure >= current_pressure + config.switch_margin
    )
    should_switch_by_timeout = (
        candidate.phase_index != observation.current_phase_index
        and ticks_since_switch >= config.max_green_ticks
        and candidate_pressure > 0.0
    )

    if should_switch_by_pressure:
        return TlsAction(
            tls_id=observation.tls_id,
            kind="switch_to_phase",
            target_phase_index=candidate.phase_index,
            reason="pressure",
            score=candidate_pressure,
        )

    if should_switch_by_timeout:
        return TlsAction(
            tls_id=observation.tls_id,
            kind="switch_to_phase",
            target_phase_index=candidate.phase_index,
            reason="max_green_timeout",
            score=candidate_pressure,
        )

    return TlsAction(
        tls_id=observation.tls_id,
        kind="hold",
        target_phase_index=observation.current_phase_index,
        reason="current_phase_ok",
        score=current_pressure,
    )


def apply_tls_action(
    conn,
    action: TlsAction,
    runtime: TlsActionRuntime,
    tick: int,
    min_green_ticks: int,
) -> bool:
    runtime.last_action_tick = tick

    if action.kind == "hold":
        return False

    try:
        current_phase = int(conn.trafficlight.getPhase(action.tls_id))
    except Exception:
        return False

    if current_phase == action.target_phase_index:
        return False

    try:
        conn.trafficlight.setPhase(action.tls_id, action.target_phase_index)
        conn.trafficlight.setPhaseDuration(action.tls_id, min_green_ticks)
    except Exception:
        return False

    runtime.last_switch_tick = tick
    runtime.last_phase_index = action.target_phase_index
    runtime.switches += 1

    return True


def best_green_phase(
    observation: TlsObservation,
    weights: PolicyWeights,
) -> TlsPhaseObservation | None:
    candidates = [
        phase
        for phase in observation.phases
        if phase_has_green(phase.state)
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda phase: phase_pressure(phase, weights))


def phase_pressure(phase: TlsPhaseObservation, weights: PolicyWeights) -> float:
    return (
        phase.queue_score * weights.halted
        + phase.vehicle_score * weights.vehicles
        + phase.wait_score * weights.waiting_time
        + phase.occupancy_score * weights.occupancy
        + phase.speed_score * weights.low_speed
        + phase.emergency_score * weights.emergency
    )


def phase_has_green(state: str) -> bool:
    return "G" in state or "g" in state