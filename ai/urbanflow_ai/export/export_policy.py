from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Literal

from urbanflow_ai.models.policy import UrbanFlowTlsPolicy


ExportFormat = Literal["checkpoint", "pickle"]


def export_policy(
    checkpoint_path: str | Path,
    output_path: str | Path,
    export_format: ExportFormat,
) -> Path:
    checkpoint = Path(checkpoint_path)

    if not checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint does not exist: {checkpoint}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    policy = UrbanFlowTlsPolicy.load_json(checkpoint)

    if export_format == "checkpoint":
        output.write_text(json.dumps(policy.to_dict(), indent=2), encoding="utf-8")
        return output

    if export_format == "pickle":
        output.write_bytes(pickle.dumps(policy.to_dict()))
        return output

    raise ValueError(f"Unsupported export format: {export_format}")