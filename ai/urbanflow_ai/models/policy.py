from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from urbanflow_ai.config import PolicyWeights, RewardWeights, RuntimeControllerConfig, UrbanFlowModelConfig
from urbanflow_ai.env.actions import TlsAction, TlsActionRuntime, choose_tls_action
from urbanflow_ai.env.observations import TlsObservation


@dataclass
class UrbanFlowTlsPolicy:
    config: UrbanFlowModelConfig = field(default_factory=UrbanFlowModelConfig)
    training_steps: int = 0
    best_reward: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def choose_action(
        self,
        observation: TlsObservation,
        runtime: TlsActionRuntime,
    ) -> TlsAction:
        return choose_tls_action(
            observation=observation,
            runtime=runtime,
            config=self.config.runtime,
            weights=self.config.policy,
        )

    def update_score(self, reward: float) -> bool:
        self.training_steps += 1

        if self.best_reward is None or reward > self.best_reward:
            self.best_reward = reward
            return True

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_type": "UrbanFlowTlsPolicy",
            "model_version": self.config.runtime.model_version,
            "training_steps": self.training_steps,
            "best_reward": self.best_reward,
            "config": self.config.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "UrbanFlowTlsPolicy":
        config_payload = payload.get("config", {})

        runtime_payload = config_payload.get("runtime", {})
        policy_payload = config_payload.get("policy", {})
        reward_payload = config_payload.get("reward", {})

        config = UrbanFlowModelConfig(
            runtime=RuntimeControllerConfig(**runtime_payload),
            policy=PolicyWeights(**policy_payload),
            reward=RewardWeights(**reward_payload),
        )

        policy = cls(
            config=config,
            training_steps=int(payload.get("training_steps", 0)),
            best_reward=payload.get("best_reward"),
            metadata=dict(payload.get("metadata", {})),
        )

        return policy

    def save_json(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return output_path

    @classmethod
    def load_json(cls, path: str | Path) -> "UrbanFlowTlsPolicy":
        input_path = Path(path)
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        return cls.from_dict(payload)


def default_policy() -> UrbanFlowTlsPolicy:
    return UrbanFlowTlsPolicy()