from fastapi import APIRouter, HTTPException

from app.schemas.editor import ApplyEditorPatchRequest, ApplyEditorPatchResponse
from app.simulation.session_store import session_store

router = APIRouter()


@router.post("/apply", response_model=ApplyEditorPatchResponse)
def apply_editor_patch(payload: ApplyEditorPatchRequest) -> ApplyEditorPatchResponse:
    engine = session_store.get(payload.session_id)

    if engine is None:
        raise HTTPException(status_code=404, detail="simulation session not found")

    try:
        engine.apply_patch(payload.patch)
    except Exception as error:
        raise HTTPException(status_code=409, detail=f"editor patch failed: {error}") from error

    return ApplyEditorPatchResponse(
        session_id=payload.session_id,
        applied_patch=payload.patch,
        total_patches=len(engine.editor_patches),
    )