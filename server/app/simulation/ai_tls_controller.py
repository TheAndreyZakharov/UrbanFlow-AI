from dataclasses import dataclass, field


@dataclass
class TlsRuntimeState:
    last_switch_tick: int = 0
    last_phase: int = 0


@dataclass
class UrbanFlowTlsController:
    min_green_ticks: int = 12
    max_green_ticks: int = 45
    queue_switch_threshold: int = 4
    state_by_tls_id: dict[str, TlsRuntimeState] = field(default_factory=dict)

    def reset(self) -> None:
        self.state_by_tls_id = {}

    def apply(self, conn, tick: int) -> None:
        try:
            tls_ids = list(conn.trafficlight.getIDList())
        except Exception:
            return

        for tls_id in tls_ids:
            self._apply_tls(conn=conn, tick=tick, tls_id=tls_id)

    def _apply_tls(self, conn, tick: int, tls_id: str) -> None:
        try:
            current_phase = int(conn.trafficlight.getPhase(tls_id))
            logics = conn.trafficlight.getAllProgramLogics(tls_id)
            controlled_lanes = list(conn.trafficlight.getControlledLanes(tls_id))
        except Exception:
            return

        if not logics or not logics[0].phases:
            return

        phases = logics[0].phases
        phase_count = len(phases)

        if phase_count <= 1:
            return

        runtime_state = self.state_by_tls_id.setdefault(
            tls_id,
            TlsRuntimeState(last_switch_tick=tick, last_phase=current_phase),
        )

        ticks_since_switch = tick - runtime_state.last_switch_tick

        if ticks_since_switch < self.min_green_ticks:
            return

        current_score = self._phase_pressure_score(
            conn=conn,
            state=phases[current_phase].state,
            controlled_lanes=controlled_lanes,
        )

        best_phase = current_phase
        best_score = current_score

        for phase_index, phase in enumerate(phases):
            if phase_index == current_phase:
                continue

            if not self._phase_has_green(phase.state):
                continue

            score = self._phase_pressure_score(
                conn=conn,
                state=phase.state,
                controlled_lanes=controlled_lanes,
            )

            if score > best_score:
                best_score = score
                best_phase = phase_index

        should_switch_by_pressure = best_phase != current_phase and best_score >= current_score + self.queue_switch_threshold
        should_switch_by_timeout = ticks_since_switch >= self.max_green_ticks and best_phase != current_phase

        if not should_switch_by_pressure and not should_switch_by_timeout:
            return

        try:
            conn.trafficlight.setPhase(tls_id, best_phase)
            conn.trafficlight.setPhaseDuration(tls_id, self.min_green_ticks)
            runtime_state.last_switch_tick = tick
            runtime_state.last_phase = best_phase
        except Exception:
            return

    def _phase_pressure_score(self, conn, state: str, controlled_lanes: list[str]) -> int:
        score = 0

        for index, signal_char in enumerate(state):
            if index >= len(controlled_lanes):
                continue

            if signal_char not in {"G", "g"}:
                continue

            lane_id = controlled_lanes[index]

            try:
                halted = int(conn.lane.getLastStepHaltingNumber(lane_id))
                vehicles = int(conn.lane.getLastStepVehicleNumber(lane_id))
            except Exception:
                continue

            score += halted * 3 + vehicles

        return score

    def _phase_has_green(self, state: str) -> bool:
        return "G" in state or "g" in state