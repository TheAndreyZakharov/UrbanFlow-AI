from dataclasses import dataclass

from app.schemas.osm import IntersectionDto
from app.schemas.simulation import SimulationMode, TrafficSignalStateDto


@dataclass
class SignalDecision:
    phase: str
    time_left: float
    reason: str


class SignalController:
    def decide(
        self,
        tick: int,
        intersection: IntersectionDto,
        mode: SimulationMode,
        waiting_vehicles: int,
        waiting_pedestrians: int,
    ) -> SignalDecision:
        if mode == "ai":
            return self._ai_placeholder_decision(
                tick=tick,
                waiting_vehicles=waiting_vehicles,
                waiting_pedestrians=waiting_pedestrians,
            )

        if mode == "rule_based":
            return self._rule_based_decision(
                tick=tick,
                waiting_vehicles=waiting_vehicles,
                waiting_pedestrians=waiting_pedestrians,
            )

        return self._fixed_decision(tick=tick)

    def build_signal_state(
        self,
        tick: int,
        intersection: IntersectionDto,
        mode: SimulationMode,
        waiting_vehicles: int,
        waiting_pedestrians: int,
    ) -> TrafficSignalStateDto:
        decision = self.decide(
            tick=tick,
            intersection=intersection,
            mode=mode,
            waiting_vehicles=waiting_vehicles,
            waiting_pedestrians=waiting_pedestrians,
        )

        return TrafficSignalStateDto(
            id=f"signal:{intersection.id}",
            intersection_id=intersection.id,
            phase=decision.phase,
            time_left=decision.time_left,
            controlled_road_ids=intersection.connected_road_ids,
        )

    def _fixed_decision(self, tick: int) -> SignalDecision:
        phase_index = (tick // 40) % 2
        phase_tick = tick % 40
        phase = "green_north_south" if phase_index == 0 else "green_east_west"

        return SignalDecision(
            phase=phase,
            time_left=float(40 - phase_tick),
            reason="fixed timing",
        )

    def _rule_based_decision(
        self,
        tick: int,
        waiting_vehicles: int,
        waiting_pedestrians: int,
    ) -> SignalDecision:
        if waiting_pedestrians > 8 and tick % 20 < 10:
            return SignalDecision(
                phase="pedestrian_crossing",
                time_left=10.0 - float(tick % 10),
                reason="pedestrian pressure",
            )

        if waiting_vehicles > 12:
            return SignalDecision(
                phase="green_high_pressure",
                time_left=25.0 - float(tick % 25),
                reason="vehicle queue pressure",
            )

        return self._fixed_decision(tick)

    def _ai_placeholder_decision(
        self,
        tick: int,
        waiting_vehicles: int,
        waiting_pedestrians: int,
    ) -> SignalDecision:
        if waiting_pedestrians > 10:
            phase = "ai_pedestrian_priority"
        elif waiting_vehicles > 15:
            phase = "ai_vehicle_pressure_release"
        else:
            phase = "ai_balanced_flow"

        return SignalDecision(
            phase=phase,
            time_left=20.0 - float(tick % 20),
            reason="AI controller placeholder until trained model is connected",
        )