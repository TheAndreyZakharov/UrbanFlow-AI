from fastapi import APIRouter, HTTPException

from app.schemas.training import (
    ExportTrainingModelRequest,
    SaveTrainingModelRequest,
    SavedTrainingModelDto,
    StartTrainingRequest,
    TrainingJobDto,
)
from app.simulation.session_store import session_store
from app.simulation.training_jobs import training_job_store

router = APIRouter()


@router.post("/start", response_model=TrainingJobDto)
def start_training(payload: StartTrainingRequest) -> TrainingJobDto:
    engine = session_store.get(payload.session_id)

    if engine is None:
        raise HTTPException(status_code=404, detail="simulation session not found")

    should_enable_all_intersections = payload.signal_scope == "all_intersections"

    if engine.signals_on_all_intersections != should_enable_all_intersections:
        try:
            engine.update_settings(
                vehicles_count=payload.curriculum.start_vehicles,
                pedestrians_count=payload.curriculum.pedestrians_count,
                signals_on_all_intersections=should_enable_all_intersections,
            )
        except Exception as error:
            raise HTTPException(status_code=409, detail=f"training scenario rebuild failed: {error}") from error
    else:
        try:
            engine.update_settings(
                vehicles_count=payload.curriculum.start_vehicles,
                pedestrians_count=payload.curriculum.pedestrians_count,
                signals_on_all_intersections=engine.signals_on_all_intersections,
            )
        except Exception as error:
            raise HTTPException(status_code=409, detail=f"training settings failed: {error}") from error

    try:
        engine.set_mode("ai")
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"AI traffic light mode failed: {error}") from error

    return training_job_store.start(payload)


@router.post("/{job_id}/stop", response_model=TrainingJobDto)
def stop_training(job_id: str) -> TrainingJobDto:
    job = training_job_store.stop(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="training job not found")

    return job


@router.post("/{job_id}/save-model", response_model=SavedTrainingModelDto)
def save_training_model(job_id: str, payload: SaveTrainingModelRequest) -> SavedTrainingModelDto:
    try:
        model = training_job_store.save_model(job_id, payload)
    except Exception as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if model is None:
        raise HTTPException(status_code=404, detail="training job not found")

    return model


@router.post("/{job_id}/export-model", response_model=SavedTrainingModelDto)
def export_training_model(job_id: str, payload: ExportTrainingModelRequest) -> SavedTrainingModelDto:
    try:
        model = training_job_store.export_model(job_id, payload)
    except Exception as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if model is None:
        raise HTTPException(status_code=404, detail="training job not found")

    return model


@router.get("/{job_id}", response_model=TrainingJobDto)
def get_training_job(job_id: str) -> TrainingJobDto:
    job = training_job_store.get(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="training job not found")

    return job


@router.get("/session/{session_id}", response_model=TrainingJobDto | None)
def get_training_job_for_session(session_id: str) -> TrainingJobDto | None:
    return training_job_store.get_for_session(session_id)


@router.get("", response_model=list[TrainingJobDto])
def list_training_jobs() -> list[TrainingJobDto]:
    return training_job_store.list_jobs()


@router.get("/models/list", response_model=list[SavedTrainingModelDto])
def list_training_models() -> list[SavedTrainingModelDto]:
    return training_job_store.list_models()


@router.delete("/models/{model_id}")
def delete_training_model(model_id: str) -> dict[str, bool]:
    deleted = training_job_store.delete_model(model_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="training model not found")

    return {"deleted": True}