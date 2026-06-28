from __future__ import annotations

import json
import pickle
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4

from app.schemas.training import (
    ExportTrainingModelRequest,
    SaveTrainingModelRequest,
    SavedTrainingModelDto,
    StartTrainingRequest,
    TrainingCurriculumDto,
    TrainingJobDto,
    TrainingJobStatus,
    TrainingModelFormat,
    TrainingSignalScope,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"


@dataclass
class TrainingJob:
    id: str
    session_id: str
    status: TrainingJobStatus
    signal_scope: TrainingSignalScope
    current_episode: int
    current_step: int
    current_vehicles: int
    best_reward: float | None
    latest_reward: float | None
    average_wait_time: float | None
    congestion_score: float | None
    stopped_vehicles: int | None
    message: str
    model_output_dir: str
    checkpoint_path: str | None
    curriculum: TrainingCurriculumDto


@dataclass
class SavedTrainingModel:
    id: str
    job_id: str
    session_id: str
    signal_scope: TrainingSignalScope
    label: str
    notes: str
    path: str
    format: TrainingModelFormat
    created_at_tick: int
    best_reward: float | None
    average_wait_time: float | None
    congestion_score: float | None
    stopped_vehicles: int | None


class TrainingJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, TrainingJob] = {}
        self._models: dict[str, SavedTrainingModel] = {}
        self._active_job_id_by_session_id: dict[str, str] = {}
        self._lock = RLock()

    def start(self, payload: StartTrainingRequest) -> TrainingJobDto:
        with self._lock:
            existing_job_id = self._active_job_id_by_session_id.get(payload.session_id)

            if existing_job_id is not None:
                existing_job = self._jobs.get(existing_job_id)

                if existing_job is not None and existing_job.status == "running":
                    existing_job.status = "stopped"
                    existing_job.message = "Training job replaced by a new run."

            job_id = f"training:{uuid4().hex}"
            model_output_dir = str(self._training_run_output_dir(payload.signal_scope, job_id))

            Path(model_output_dir).mkdir(parents=True, exist_ok=True)
            Path(model_output_dir, "checkpoints").mkdir(parents=True, exist_ok=True)
            Path(model_output_dir, "snapshots").mkdir(parents=True, exist_ok=True)

            self._scope_saved_dir(payload.signal_scope).mkdir(parents=True, exist_ok=True)
            self._scope_exports_dir(payload.signal_scope).mkdir(parents=True, exist_ok=True)

            job = TrainingJob(
                id=job_id,
                session_id=payload.session_id,
                status="running",
                signal_scope=payload.signal_scope,
                current_episode=0,
                current_step=0,
                current_vehicles=payload.curriculum.start_vehicles,
                best_reward=None,
                latest_reward=None,
                average_wait_time=None,
                congestion_score=None,
                stopped_vehicles=None,
                message="UrbanFlow AI runtime controller is collecting SUMO traffic-light training metrics.",
                model_output_dir=model_output_dir,
                checkpoint_path=None,
                curriculum=payload.curriculum,
            )

            self._jobs[job_id] = job
            self._active_job_id_by_session_id[payload.session_id] = job_id

            self._write_job_metadata(job)

            return self._to_dto(job)

    def stop(self, job_id: str) -> TrainingJobDto | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                return None

            if job.status == "running":
                job.status = "stopped"
                job.message = "Training job stopped."

            if self._active_job_id_by_session_id.get(job.session_id) == job.id:
                self._active_job_id_by_session_id.pop(job.session_id, None)

            self._write_job_metadata(job)

            return self._to_dto(job)

    def get(self, job_id: str) -> TrainingJobDto | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                return None

            return self._to_dto(job)

    def get_for_session(self, session_id: str) -> TrainingJobDto | None:
        with self._lock:
            job_id = self._active_job_id_by_session_id.get(session_id)

            if job_id is None:
                return None

            job = self._jobs.get(job_id)

            if job is None:
                return None

            return self._to_dto(job)

    def list_jobs(self) -> list[TrainingJobDto]:
        with self._lock:
            return [self._to_dto(job) for job in self._jobs.values()]

    def record_runtime_metrics(
        self,
        session_id: str,
        current_step: int,
        current_vehicles: int,
        latest_reward: float | None,
        average_wait_time: float | None,
        congestion_score: float | None,
        stopped_vehicles: int | None,
        model_state: dict | None,
    ) -> TrainingJobDto | None:
        with self._lock:
            job_id = self._active_job_id_by_session_id.get(session_id)

            if job_id is None:
                return None

            job = self._jobs.get(job_id)

            if job is None or job.status != "running":
                return None

            job.current_step = max(job.current_step, int(current_step))
            job.current_episode = job.current_step // max(1, job.curriculum.steps_per_level)
            job.current_vehicles = int(current_vehicles)
            job.latest_reward = latest_reward
            job.average_wait_time = average_wait_time
            job.congestion_score = congestion_score
            job.stopped_vehicles = stopped_vehicles

            improved = False

            if latest_reward is not None:
                if job.best_reward is None or latest_reward > job.best_reward:
                    job.best_reward = latest_reward
                    improved = True

            should_write_checkpoint = (
                model_state is not None
                and (
                    improved
                    or job.checkpoint_path is None
                    or job.current_step % 120 == 0
                )
            )

            should_write_analysis_snapshot = (
                model_state is not None
                and (
                    should_write_checkpoint
                    or job.current_step % 10 == 0
                )
            )

            if should_write_checkpoint:
                checkpoint_dir = Path(job.model_output_dir) / "checkpoints"
                snapshot_dir = Path(job.model_output_dir) / "snapshots"
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                snapshot_dir.mkdir(parents=True, exist_ok=True)

                best_checkpoint_path = checkpoint_dir / "best_model.json"
                step_checkpoint_path = snapshot_dir / f"checkpoint_step_{job.current_step:08d}.json"

                checkpoint_payload = {
                    **model_state,
                    "job_id": job.id,
                    "session_id": job.session_id,
                    "signal_scope": job.signal_scope,
                    "current_step": job.current_step,
                    "current_episode": job.current_episode,
                    "current_vehicles": job.current_vehicles,
                    "best_reward": job.best_reward,
                    "latest_reward": job.latest_reward,
                    "average_wait_time": job.average_wait_time,
                    "congestion_score": job.congestion_score,
                    "stopped_vehicles": job.stopped_vehicles,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                }

                write_json_atomic(best_checkpoint_path, checkpoint_payload)
                write_json_atomic(step_checkpoint_path, checkpoint_payload)

                job.checkpoint_path = str(best_checkpoint_path)

            if should_write_analysis_snapshot:
                self._write_analysis_artifacts(job=job, model_state=model_state)

            if job.checkpoint_path:
                job.message = "Training metrics live. Checkpoint is available for saving."

            self._write_job_metadata(job)

            return self._to_dto(job)

    def _write_analysis_artifacts(self, job: TrainingJob, model_state: dict | None) -> None:
        try:
            ensure_ai_package_path()

            from urbanflow_ai.analysis.artifacts import TrainingArtifactRow, write_training_artifacts

            write_training_artifacts(
                model_output_dir=job.model_output_dir,
                row=TrainingArtifactRow(
                    job_id=job.id,
                    session_id=job.session_id,
                    signal_scope=job.signal_scope,
                    current_step=job.current_step,
                    current_episode=job.current_episode,
                    current_vehicles=job.current_vehicles,
                    best_reward=job.best_reward,
                    latest_reward=job.latest_reward,
                    average_wait_time=job.average_wait_time,
                    congestion_score=job.congestion_score,
                    stopped_vehicles=job.stopped_vehicles,
                    checkpoint_path=job.checkpoint_path,
                    model_output_dir=job.model_output_dir,
                    created_at_utc=datetime.now(timezone.utc).isoformat(),
                ),
                model_state=model_state,
            )
        except Exception:
            return

    def save_model(self, job_id: str, payload: SaveTrainingModelRequest) -> SavedTrainingModelDto | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                return None

            if not job.checkpoint_path:
                raise RuntimeError("No trained checkpoint exists yet. Run visual AI training until checkpoint_path is created.")

            checkpoint_path = Path(job.checkpoint_path)

            if not checkpoint_path.exists():
                raise RuntimeError(f"Checkpoint file does not exist: {checkpoint_path}")

            model_id = f"model:{uuid4().hex}"
            model_dir = self._scope_saved_dir(job.signal_scope)
            model_dir.mkdir(parents=True, exist_ok=True)

            base_name = (
                f"{safe_file_name(model_id)}_"
                f"{safe_file_name(job.id)}_"
                f"step_{job.current_step:08d}"
            )

            artifact_path = model_dir / f"{base_name}.json"
            metadata_path = model_dir / f"{base_name}.metadata.json"

            shutil.copyfile(checkpoint_path, artifact_path)

            saved = SavedTrainingModel(
                id=model_id,
                job_id=job.id,
                session_id=job.session_id,
                signal_scope=job.signal_scope,
                label=payload.label,
                notes=payload.notes,
                path=str(artifact_path),
                format="checkpoint",
                created_at_tick=job.current_step,
                best_reward=job.best_reward,
                average_wait_time=job.average_wait_time,
                congestion_score=job.congestion_score,
                stopped_vehicles=job.stopped_vehicles,
            )

            write_json_atomic(metadata_path, asdict(saved))

            self._models[model_id] = saved
            self._write_job_metadata(job)

            return self._model_to_dto(saved)

    def export_model(self, job_id: str, payload: ExportTrainingModelRequest) -> SavedTrainingModelDto | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                return None

            if not job.checkpoint_path:
                raise RuntimeError("No trained checkpoint exists yet. Export is available after training writes checkpoint_path.")

            checkpoint_path = Path(job.checkpoint_path)

            if not checkpoint_path.exists():
                raise RuntimeError(f"Checkpoint file does not exist: {checkpoint_path}")

            if payload.format not in {"checkpoint", "pickle"}:
                raise RuntimeError(
                    f"Export format '{payload.format}' is not available yet. "
                    "Current UrbanFlow policy is a JSON checkpoint policy, not a Torch neural network."
                )

            model_id = f"export:{uuid4().hex}"
            export_dir = self._scope_exports_dir(job.signal_scope)
            export_dir.mkdir(parents=True, exist_ok=True)

            base_name = (
                f"{safe_file_name(model_id)}_"
                f"{safe_file_name(job.id)}_"
                f"step_{job.current_step:08d}"
            )

            if payload.format == "checkpoint":
                artifact_path = export_dir / f"{base_name}.json"
                shutil.copyfile(checkpoint_path, artifact_path)
            else:
                artifact_path = export_dir / f"{base_name}.pkl"
                checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                artifact_path.write_bytes(pickle.dumps(checkpoint_payload))

            metadata_path = export_dir / f"{base_name}.metadata.json"

            saved = SavedTrainingModel(
                id=model_id,
                job_id=job.id,
                session_id=job.session_id,
                signal_scope=job.signal_scope,
                label=f"Export {payload.format}",
                notes="Exported UrbanFlow traffic-light controller artifact.",
                path=str(artifact_path),
                format=payload.format,
                created_at_tick=job.current_step,
                best_reward=job.best_reward,
                average_wait_time=job.average_wait_time,
                congestion_score=job.congestion_score,
                stopped_vehicles=job.stopped_vehicles,
            )

            write_json_atomic(metadata_path, asdict(saved))

            self._models[model_id] = saved

            return self._model_to_dto(saved)

    def list_models(self) -> list[SavedTrainingModelDto]:
        with self._lock:
            self._load_models_from_disk()
            return [
                self._model_to_dto(model)
                for model in sorted(
                    self._models.values(),
                    key=lambda item: (item.created_at_tick, item.id),
                    reverse=True,
                )
            ]

    def delete_model(self, model_id: str) -> bool:
        with self._lock:
            model = self._models.pop(model_id, None)

            if model is None:
                self._load_models_from_disk()
                model = self._models.pop(model_id, None)

            if model is None:
                return False

            artifact_path = Path(model.path)

            candidate_paths = {
                artifact_path,
                artifact_path.with_suffix(".metadata.json"),
                artifact_path.with_name(f"{artifact_path.stem}.metadata.json"),
                artifact_path.with_name(f"{safe_file_name(model.id)}.metadata.json"),
            }

            for candidate in candidate_paths:
                if candidate.exists():
                    candidate.unlink()

            return True

    def _load_models_from_disk(self) -> None:
        for metadata_path in MODELS_DIR.glob("**/*.metadata.json"):
            try:
                payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                model = SavedTrainingModel(**payload)
            except Exception:
                continue

            self._models[model.id] = model

    def _write_job_metadata(self, job: TrainingJob) -> None:
        job_dir = Path(job.model_output_dir)
        job_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "id": job.id,
            "session_id": job.session_id,
            "status": job.status,
            "signal_scope": job.signal_scope,
            "current_episode": job.current_episode,
            "current_step": job.current_step,
            "current_vehicles": job.current_vehicles,
            "best_reward": job.best_reward,
            "latest_reward": job.latest_reward,
            "average_wait_time": job.average_wait_time,
            "congestion_score": job.congestion_score,
            "stopped_vehicles": job.stopped_vehicles,
            "message": job.message,
            "model_output_dir": job.model_output_dir,
            "checkpoint_path": job.checkpoint_path,
            "curriculum": job.curriculum.model_dump() if hasattr(job.curriculum, "model_dump") else dict(job.curriculum),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        write_json_atomic(job_dir / "job.json", payload)

    def _scope_dir(self, signal_scope: TrainingSignalScope) -> Path:
        if signal_scope == "all_intersections":
            return MODELS_DIR / "tls_all_intersections"

        return MODELS_DIR / "tls_osm_only"

    def _training_run_output_dir(self, signal_scope: TrainingSignalScope, job_id: str) -> Path:
        return self._scope_dir(signal_scope) / "runs" / safe_file_name(job_id)

    def _scope_saved_dir(self, signal_scope: TrainingSignalScope) -> Path:
        return self._scope_dir(signal_scope) / "saved"

    def _scope_exports_dir(self, signal_scope: TrainingSignalScope) -> Path:
        return self._scope_dir(signal_scope) / "exports"

    def _to_dto(self, job: TrainingJob) -> TrainingJobDto:
        self._load_models_from_disk()

        saved_model_count = len(
            [
                model
                for model in self._models.values()
                if model.job_id == job.id
            ]
        )

        return TrainingJobDto(
            id=job.id,
            session_id=job.session_id,
            status=job.status,
            signal_scope=job.signal_scope,
            current_episode=job.current_episode,
            current_step=job.current_step,
            current_vehicles=job.current_vehicles,
            best_reward=job.best_reward,
            latest_reward=job.latest_reward,
            average_wait_time=job.average_wait_time,
            congestion_score=job.congestion_score,
            stopped_vehicles=job.stopped_vehicles,
            message=job.message,
            model_output_dir=job.model_output_dir,
            checkpoint_path=job.checkpoint_path,
            can_save_model=bool(job.checkpoint_path),
            saved_model_count=saved_model_count,
            curriculum=job.curriculum,
        )

    def _model_to_dto(self, model: SavedTrainingModel) -> SavedTrainingModelDto:
        return SavedTrainingModelDto(
            id=model.id,
            job_id=model.job_id,
            session_id=model.session_id,
            signal_scope=model.signal_scope,
            label=model.label,
            notes=model.notes,
            path=model.path,
            format=model.format,
            created_at_tick=model.created_at_tick,
            best_reward=model.best_reward,
            average_wait_time=model.average_wait_time,
            congestion_score=model.congestion_score,
            stopped_vehicles=model.stopped_vehicles,
        )


def safe_file_name(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    cleaned = cleaned.strip("_")
    return cleaned or "artifact"


def ensure_ai_package_path() -> None:
    ai_path = PROJECT_ROOT / "ai"

    if ai_path.exists() and str(ai_path) not in sys.path:
        sys.path.insert(0, str(ai_path))


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(path)


training_job_store = TrainingJobStore()