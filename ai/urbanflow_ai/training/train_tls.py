from __future__ import annotations

import argparse
from pathlib import Path

from urbanflow_ai.config import model_output_dir_for_scope
from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController
from urbanflow_ai.models.policy import UrbanFlowTlsPolicy
from urbanflow_ai.training.curriculum import TrafficCurriculum


def create_initial_checkpoint(signal_scope: str, output_dir: str | None = None) -> Path:
    if signal_scope not in {"osm_only", "all_intersections"}:
        raise ValueError("signal_scope must be 'osm_only' or 'all_intersections'")

    model_dir = Path(output_dir) if output_dir else model_output_dir_for_scope(signal_scope)  # type: ignore[arg-type]
    checkpoint_path = model_dir / "checkpoints" / "initial_policy.json"

    policy = UrbanFlowTlsPolicy()
    policy.metadata["signal_scope"] = signal_scope
    policy.metadata["training_mode"] = "runtime_pressure_policy"
    policy.metadata["description"] = (
        "UrbanFlow TLS policy checkpoint. "
        "The policy controls real SUMO traffic lights through TraCI using queue, speed, waiting-time and occupancy pressure."
    )

    policy.save_json(checkpoint_path)
    return checkpoint_path


def train_with_connection(
    conn,
    signal_scope: str,
    curriculum: TrafficCurriculum,
    output_dir: str | None = None,
) -> Path:
    if signal_scope not in {"osm_only", "all_intersections"}:
        raise ValueError("signal_scope must be 'osm_only' or 'all_intersections'")

    model_dir = Path(output_dir) if output_dir else model_output_dir_for_scope(signal_scope)  # type: ignore[arg-type]
    checkpoint_path = model_dir / "checkpoints" / "best_model.json"

    controller = UrbanFlowRuntimeController()
    best_reward: float | None = None

    for level in curriculum.levels():
        for _step in range(level.steps):
            result = controller.apply(conn, tick=_step)

            try:
                conn.simulationStep()
            except Exception as error:
                raise RuntimeError(f"SUMO failed during training: {error!r}") from error

            reward = result.reward.reward

            if best_reward is None or reward > best_reward:
                best_reward = reward
                controller.save_checkpoint(checkpoint_path)

    if not checkpoint_path.exists():
        controller.save_checkpoint(checkpoint_path)

    return checkpoint_path


def main() -> None:
    parser = argparse.ArgumentParser(description="UrbanFlow AI traffic-light policy tools")
    parser.add_argument("--signal-scope", choices=["osm_only", "all_intersections"], default="osm_only")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--create-initial-checkpoint", action="store_true")
    args = parser.parse_args()

    if args.create_initial_checkpoint:
        checkpoint_path = create_initial_checkpoint(
            signal_scope=args.signal_scope,
            output_dir=args.output_dir,
        )
        print(checkpoint_path)
        return

    raise SystemExit(
        "This trainer needs a live TraCI SUMO connection. "
        "Use server visual training for runtime control, or call train_with_connection(conn, ...) from an integration script."
    )


if __name__ == "__main__":
    main()