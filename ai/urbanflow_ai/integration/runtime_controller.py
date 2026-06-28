from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from urbanflow_ai.config import RuntimeControllerConfig
from urbanflow_ai.env.actions import TlsAction, TlsActionRuntime, apply_tls_action
from urbanflow_ai.env.observations import TlsObservation, collect_tls_observation
from urbanflow_ai.env.rewards import RewardBreakdown, network_reward
from urbanflow_ai.models.policy import UrbanFlowTlsPolicy, default_policy
from urbanflow_ai.utils.metrics import NetworkMetrics, collect_network_metrics


@dataclass
class RuntimeStepResult:
    tick: int
    observations: list[TlsObservation]
    actions: list[TlsAction]
    switched_count: int
    reward: RewardBreakdown
    network_metrics: NetworkMetrics


@dataclass
class UrbanFlowRuntimeController:
    policy: UrbanFlowTlsPolicy = field(default_factory=default_policy)
    config: RuntimeControllerConfig = field(default_factory=RuntimeControllerConfig)
    runtime_by_tls_id: dict[str, TlsActionRuntime] = field(default_factory=dict)
    last_result: RuntimeStepResult | None = None

    def reset(self) -> None:
        self.runtime_by_tls_id = {}
        self.last_result = None

    @classmethod
    def from_checkpoint(cls, path: str | Path) -> "UrbanFlowRuntimeController":
        policy = UrbanFlowTlsPolicy.load_json(path)
        return cls(policy=policy, config=policy.config.runtime)

    def apply(self, conn, tick: int) -> RuntimeStepResult:
        observations = self._collect_observations(conn=conn, tick=tick)
        actions: list[TlsAction] = []
        switched_count = 0

        for observation in observations:
            runtime = self.runtime_by_tls_id.setdefault(
                observation.tls_id,
                TlsActionRuntime(
                    last_switch_tick=tick,
                    last_action_tick=0,
                    last_phase_index=observation.current_phase_index,
                ),
            )

            action = self.policy.choose_action(observation=observation, runtime=runtime)
            switched = apply_tls_action(
                conn=conn,
                action=action,
                runtime=runtime,
                tick=tick,
                min_green_ticks=self.config.min_green_ticks,
            )

            if switched:
                switched_count += 1

            actions.append(action)

        reward = network_reward(
            observations=observations,
            switches=switched_count,
            weights=self.policy.config.reward,
        )
        network_metrics = collect_network_metrics(conn)

        self.policy.update_score(reward.reward)

        self.last_result = RuntimeStepResult(
            tick=tick,
            observations=observations,
            actions=actions,
            switched_count=switched_count,
            reward=reward,
            network_metrics=network_metrics,
        )

        return self.last_result

    def _collect_observations(self, conn, tick: int) -> list[TlsObservation]:
        try:
            tls_ids = list(conn.trafficlight.getIDList())
        except Exception:
            return []

        result: list[TlsObservation] = []

        for tls_id in tls_ids:
            observation = collect_tls_observation(
                conn=conn,
                tls_id=str(tls_id),
                tick=tick,
                max_controlled_lanes=self.config.max_controlled_lanes_per_tls,
            )

            if observation is not None:
                result.append(observation)

        return result

    @property
    def last_reward(self) -> float | None:
        if self.last_result is None:
            return None

        return self.last_result.reward.reward

    @property
    def last_network_metrics(self) -> NetworkMetrics | None:
        if self.last_result is None:
            return None

        return self.last_result.network_metrics

    def checkpoint_payload(self) -> dict[str, Any]:
        payload = self.policy.to_dict()

        payload["runtime"] = {
            "controlled_tls": len(self.runtime_by_tls_id),
            "last_reward": self.last_reward,
            "last_tick": self.last_result.tick if self.last_result else 0,
            "last_switches": self.last_result.switched_count if self.last_result else 0,
        }

        return payload

    def save_checkpoint(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy.metadata["last_runtime"] = {
            "last_reward": self.last_reward,
            "controlled_tls": len(self.runtime_by_tls_id),
        }
        return self.policy.save_json(output_path)