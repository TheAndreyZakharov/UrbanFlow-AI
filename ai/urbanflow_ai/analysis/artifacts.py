from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrainingArtifactRow:
    job_id: str
    session_id: str
    signal_scope: str
    current_step: int
    current_episode: int
    current_vehicles: int
    best_reward: float | None
    latest_reward: float | None
    average_wait_time: float | None
    congestion_score: float | None
    stopped_vehicles: int | None
    checkpoint_path: str | None
    model_output_dir: str
    created_at_utc: str


def write_training_artifacts(
    model_output_dir: str | Path,
    row: TrainingArtifactRow,
    model_state: dict[str, Any] | None,
) -> None:
    output_dir = Path(model_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    row_payload = asdict(row)

    append_jsonl(output_dir / "training_history.jsonl", row_payload)
    append_csv(output_dir / "training_history.csv", row_payload)
    write_latest_summary(output_dir / "latest_summary.json", row_payload=row_payload, model_state=model_state)
    write_training_dashboard(output_dir / "training_dashboard.md", row_payload=row_payload)
    maybe_refresh_analysis_notebooks(output_dir)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "job_id",
        "session_id",
        "signal_scope",
        "current_step",
        "current_episode",
        "current_vehicles",
        "best_reward",
        "latest_reward",
        "average_wait_time",
        "congestion_score",
        "stopped_vehicles",
        "checkpoint_path",
        "model_output_dir",
        "created_at_utc",
    ]

    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow({key: payload.get(key) for key in fieldnames})


def write_latest_summary(
    path: Path,
    row_payload: dict[str, Any],
    model_state: dict[str, Any] | None,
) -> None:
    summary = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "latest_training_row": row_payload,
        "model_state": model_state or {},
        "files": {
            "history_jsonl": "training_history.jsonl",
            "history_csv": "training_history.csv",
            "dashboard_markdown": "training_dashboard.md",
            "checkpoint": row_payload.get("checkpoint_path"),
        },
    }

    write_json_atomic(path, summary)


def write_training_dashboard(path: Path, row_payload: dict[str, Any]) -> None:
    text = f"""# UrbanFlow AI Training Dashboard

This file is generated automatically by UrbanFlow AI training.

## Latest run

| Metric | Value |
|---|---:|
| Job ID | `{row_payload.get("job_id")}` |
| Session ID | `{row_payload.get("session_id")}` |
| Signal scope | `{row_payload.get("signal_scope")}` |
| Current step | {row_payload.get("current_step")} |
| Current episode | {row_payload.get("current_episode")} |
| Current vehicles | {row_payload.get("current_vehicles")} |
| Best reward | {format_value(row_payload.get("best_reward"))} |
| Latest reward | {format_value(row_payload.get("latest_reward"))} |
| Average wait time | {format_value(row_payload.get("average_wait_time"))} |
| Congestion score | {format_value(row_payload.get("congestion_score"))} |
| Stopped vehicles | {format_value(row_payload.get("stopped_vehicles"))} |
| Checkpoint | `{row_payload.get("checkpoint_path")}` |
| Updated UTC | `{row_payload.get("created_at_utc")}` |

## Generated files

- `training_history.jsonl`
- `training_history.csv`
- `latest_summary.json`
- `training_dashboard.md`
- `checkpoints/best_model.json`

## Notebook workflow

Open these notebooks after or during training:

1. `ai/notebooks/01_explore_sumo_tls.ipynb`
2. `ai/notebooks/02_reward_design.ipynb`
3. `ai/notebooks/03_train_tls_agent.ipynb`
4. `ai/notebooks/04_evaluate_tls_agent.ipynb`
"""

    path.write_text(text, encoding="utf-8")

def maybe_refresh_analysis_notebooks(output_dir: Path) -> None:
    project_root = Path(__file__).resolve().parents[3]
    generator_path = project_root / "ai" / "notebooks" / "create_analysis_notebooks.py"

    if not generator_path.exists():
        return

    stamp_path = output_dir / ".notebook_refresh_stamp"
    now = time.time()

    try:
        previous = float(stamp_path.read_text(encoding="utf-8")) if stamp_path.exists() else 0.0
    except ValueError:
        previous = 0.0

    if now - previous < 30:
        return

    stamp_path.write_text(str(now), encoding="utf-8")

    environment = os.environ.copy()
    ai_root = project_root / "ai"
    current_pythonpath = environment.get("PYTHONPATH", "")

    if current_pythonpath:
        environment["PYTHONPATH"] = f"{ai_root}{os.pathsep}{current_pythonpath}"
    else:
        environment["PYTHONPATH"] = str(ai_root)

    log_path = output_dir / "notebook_refresh.log"

    try:
        result = subprocess.run(
            [sys.executable, str(generator_path)],
            cwd=str(project_root),
            env=environment,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )

        log_path.write_text(
            "\n".join(
                [
                    f"updated_at_utc={datetime.now(timezone.utc).isoformat()}",
                    f"python={sys.executable}",
                    f"generator={generator_path}",
                    f"returncode={result.returncode}",
                    "",
                    "STDOUT:",
                    result.stdout[-12000:],
                    "",
                    "STDERR:",
                    result.stderr[-12000:],
                    "",
                ]
            ),
            encoding="utf-8",
        )
    except Exception as error:
        log_path.write_text(
            "\n".join(
                [
                    f"updated_at_utc={datetime.now(timezone.utc).isoformat()}",
                    f"python={sys.executable}",
                    f"generator={generator_path}",
                    f"error={error!r}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return

def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(path)


def format_value(value: object) -> str:
    if value is None:
        return "—"

    if isinstance(value, float):
        return f"{value:.4f}"

    return str(value)