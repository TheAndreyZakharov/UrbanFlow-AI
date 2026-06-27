from __future__ import annotations

import json
from dataclasses import asdict, dataclass
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
            model_output_dir = self._model_output_dir(payload.signal_scope)

            Path(model_output_dir).mkdir(parents=True, exist_ok=True)

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
                message=(
                    "Training job is ready for this zone. "
                    "A model can be saved after the RL trainer writes a checkpoint."
                ),
                model_output_dir=model_output_dir,
                checkpoint_path=None,
                curriculum=payload.curriculum,
            )

            self._jobs[job_id] = job
            self._active_job_id_by_session_id[payload.session_id] = job_id

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

    def save_model(self, job_id: str, payload: SaveTrainingModelRequest) -> SavedTrainingModelDto | None:
        with self._lock:
            job = self._jobs.get(job_id)

            if job is None:
                return None

            if not job.checkpoint_path:
                raise RuntimeError("No trained checkpoint exists yet. Run the RL trainer until it writes checkpoint_path.")

            checkpoint_path = Path(job.checkpoint_path)

            if not checkpoint_path.exists():
                raise RuntimeError(f"Checkpoint file does not exist: {checkpoint_path}")

            model_id = f"model:{uuid4().hex}"
            model_dir = Path(job.model_output_dir) / "saved"
            model_dir.mkdir(parents=True, exist_ok=True)

            metadata_path = model_dir / f"{safe_file_name(model_id)}.json"

            saved = SavedTrainingModel(
                id=model_id,
                job_id=job.id,
                session_id=job.session_id,
                signal_scope=job.signal_scope,
                label=payload.label,
                notes=payload.notes,
                path=str(checkpoint_path),
                format="checkpoint",
                created_at_tick=job.current_step,
                best_reward=job.best_reward,
                average_wait_time=job.average_wait_time,
                congestion_score=job.congestion_score,
                stopped_vehicles=job.stopped_vehicles,
            )

            metadata_path.write_text(json.dumps(asdict(saved), indent=2), encoding="utf-8")
            self._models[model_id] = saved

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

            if payload.format != "checkpoint":
                raise RuntimeError(
                    f"Export format '{payload.format}' is not available until the real model exporter is connected."
                )

            model_id = f"export:{uuid4().hex}"
            saved = SavedTrainingModel(
                id=model_id,
                job_id=job.id,
                session_id=job.session_id,
                signal_scope=job.signal_scope,
                label=f"Export {payload.format}",
                notes="Exported model artifact.",
                path=str(checkpoint_path),
                format=payload.format,
                created_at_tick=job.current_step,
                best_reward=job.best_reward,
                average_wait_time=job.average_wait_time,
                congestion_score=job.congestion_score,
                stopped_vehicles=job.stopped_vehicles,
            )

            self._models[model_id] = saved

            return self._model_to_dto(saved)

    def list_models(self) -> list[SavedTrainingModelDto]:
        with self._lock:
            return [self._model_to_dto(model) for model in self._models.values()]

    def delete_model(self, model_id: str) -> bool:
        with self._lock:
            return self._models.pop(model_id, None) is not None

    def _model_output_dir(self, signal_scope: TrainingSignalScope) -> str:
        if signal_scope == "all_intersections":
            return "data/models/tls_all_intersections"

        return "data/models/tls_osm_only"

    def _to_dto(self, job: TrainingJob) -> TrainingJobDto:
        saved_model_count = len([model for model in self._models.values() if model.job_id == job.id])

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
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


training_job_store = TrainingJobStore()