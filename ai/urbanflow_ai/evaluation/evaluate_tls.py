from __future__ import annotations

from dataclasses import dataclass

from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController
from urbanflow_ai.utils.metrics import NetworkMetrics, collect_network_metrics


@dataclass(frozen=True)
class EvaluationResult:
    mode: str
    ticks: int
    average_speed_mps: float
    average_waiting_time_s: float
    congestion_score: float
    halted_count: int
    vehicle_count: int


def evaluate_runtime_controller(
    conn,
    ticks: int,
    controller: UrbanFlowRuntimeController | None = None,
    mode: str = "urbanflow_ai",
) -> EvaluationResult:
    runtime_controller = controller or UrbanFlowRuntimeController()
    snapshots: list[NetworkMetrics] = []

    for tick in range(ticks):
        runtime_controller.apply(conn, tick=tick)

        try:
            conn.simulationStep()
        except Exception as error:
            raise RuntimeError(f"SUMO failed during evaluation: {error!r}") from error

        snapshots.append(collect_network_metrics(conn))

    if not snapshots:
        return EvaluationResult(
            mode=mode,
            ticks=0,
            average_speed_mps=0.0,
            average_waiting_time_s=0.0,
            congestion_score=0.0,
            halted_count=0,
            vehicle_count=0,
        )  

    return EvaluationResult(
        mode=mode,
        ticks=ticks,
        average_speed_mps=sum(item.average_speed_mps for item in snapshots) / len(snapshots),
        average_waiting_time_s=sum(item.average_waiting_time_s for item in snapshots) / len(snapshots),
        congestion_score=sum(item.congestion_score for item in snapshots) / len(snapshots),
        halted_count=int(sum(item.halted_count for item in snapshots) / len(snapshots)),
        vehicle_count=int(sum(item.vehicle_count for item in snapshots) / len(snapshots)),
    )