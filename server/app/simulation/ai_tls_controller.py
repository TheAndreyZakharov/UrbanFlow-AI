from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


TrainingSignalScope = Literal["osm_only", "all_intersections"]

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AI_ROOT = PROJECT_ROOT / "ai"
MODELS_ROOT = PROJECT_ROOT / "data" / "models"


def ensure_ai_package_path() -> None:
    if AI_ROOT.exists() and str(AI_ROOT) not in sys.path:
        sys.path.insert(0, str(AI_ROOT))


def create_runtime_controller() -> Any:
    ensure_ai_package_path()

    from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController

    return UrbanFlowRuntimeController()


@dataclass
class UrbanFlowTlsController:
    runtime_controller: Any = field(default_factory=create_runtime_controller)
    loaded_model_path: Path | None = None

    def reset(self) -> None:
        self.runtime_controller.reset()

    def apply(self, conn, tick: int) -> None:
        self.runtime_controller.apply(conn=conn, tick=tick)

    def load_latest_saved_model(self, signal_scope: TrainingSignalScope) -> Path | None:
        model_path = latest_saved_model_path(signal_scope)

        if model_path is None:
            self.runtime_controller = create_runtime_controller()
            self.loaded_model_path = None
            return None

        ensure_ai_package_path()

        from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController

        self.runtime_controller = UrbanFlowRuntimeController.from_checkpoint(model_path)
        self.loaded_model_path = model_path
        return model_path

    def load_model(self, path: str | Path) -> Path:
        model_path = Path(path)

        if not model_path.exists():
            raise FileNotFoundError(f"UrbanFlow AI model checkpoint does not exist: {model_path}")

        ensure_ai_package_path()

        from urbanflow_ai.integration.runtime_controller import UrbanFlowRuntimeController

        self.runtime_controller = UrbanFlowRuntimeController.from_checkpoint(model_path)
        self.loaded_model_path = model_path
        return model_path

    @property
    def last_reward(self) -> float | None:
        return self.runtime_controller.last_reward

    def export_model_state(self) -> dict[str, Any]:
        payload = self.runtime_controller.checkpoint_payload()

        payload["loaded_model_path"] = str(self.loaded_model_path) if self.loaded_model_path else None

        return payload

    def save_checkpoint(self, path: str | Path) -> Path:
        return self.runtime_controller.save_checkpoint(path)


def latest_saved_model_path(signal_scope: TrainingSignalScope) -> Path | None:
    scope_dir_name = "tls_all_intersections" if signal_scope == "all_intersections" else "tls_osm_only"
    saved_dir = MODELS_ROOT / scope_dir_name / "saved"

    if not saved_dir.exists():
        return None

    candidates = [
        path
        for path in saved_dir.glob("*.json")
        if not path.name.endswith(".metadata.json")
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)