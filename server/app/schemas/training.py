from typing import Literal

from pydantic import BaseModel, Field


TrainingSignalScope = Literal["osm_only", "all_intersections"]
TrainingJobStatus = Literal["idle", "running", "stopping", "stopped", "failed", "completed"]
TrainingModelFormat = Literal["checkpoint", "onnx", "torchscript", "pickle"]


class TrainingCurriculumDto(BaseModel):
    start_vehicles: int = Field(default=60, ge=0, le=5000)
    max_vehicles: int = Field(default=800, ge=1, le=5000)
    vehicle_step: int = Field(default=80, ge=1, le=1000)
    steps_per_level: int = Field(default=900, ge=60, le=100000)
    pedestrians_count: int = Field(default=220, ge=0, le=10000)
    random_events_enabled: bool = True


class StartTrainingRequest(BaseModel):
    session_id: str
    signal_scope: TrainingSignalScope
    curriculum: TrainingCurriculumDto = Field(default_factory=TrainingCurriculumDto)


class SaveTrainingModelRequest(BaseModel):
    label: str = Field(default="UrbanFlow TLS model", min_length=1, max_length=120)
    notes: str = Field(default="", max_length=1000)


class ExportTrainingModelRequest(BaseModel):
    format: TrainingModelFormat = "checkpoint"


class SavedTrainingModelDto(BaseModel):
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


class TrainingJobDto(BaseModel):
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
    can_save_model: bool
    saved_model_count: int
    curriculum: TrainingCurriculumDto