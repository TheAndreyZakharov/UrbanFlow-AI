from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from urbanflow_ai.env.observations import TlsObservation
from urbanflow_ai.utils.metrics import NetworkMetrics, collect_network_metrics

if TYPE_CHECKING:
    from urbanflow_ai.integration.runtime_controller import RuntimeStepResult, UrbanFlowRuntimeController

def create_runtime_controller() -> "UrbanFlowRuntimeController":
    from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController

    return UrbanFlowRuntimeController()
@dataclass
class SumoTlsEnvStep:
    tick: int
    observations: list[TlsObservation]
    reward: float
    done: bool
    metrics: NetworkMetrics
    result: "RuntimeStepResult"


@dataclass
class SumoTlsEnv:
    conn: object
    controller: "UrbanFlowRuntimeController" = field(default_factory=create_runtime_controller)
    max_ticks: int = 3600
    tick: int = 0

    def reset(self) -> list[TlsObservation]:
        self.tick = 0
        self.controller.reset()

        try:
            self.conn.simulationStep()
        except Exception:
            return []

        result = self.controller.apply(self.conn, self.tick)
        return result.observations

    def step(self) -> SumoTlsEnvStep:
        self.tick += 1

        result = self.controller.apply(self.conn, self.tick)

        try:
            self.conn.simulationStep()
        except Exception as error:
            raise RuntimeError(f"SUMO simulation step failed during AI env step: {error!r}") from error

        metrics = collect_network_metrics(self.conn)
        done = self.tick >= self.max_ticks

        return SumoTlsEnvStep(
            tick=self.tick,
            observations=result.observations,
            reward=result.reward.reward,
            done=done,
            metrics=metrics,
            result=result,
        )