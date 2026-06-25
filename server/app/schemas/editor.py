from typing import Literal

from pydantic import BaseModel


EditorPatchKind = Literal[
    "close_road",
    "open_road",
    "remove_road",
    "add_road",
    "add_crossing",
    "remove_crossing",
    "add_signal",
    "remove_signal",
    "accident",
    "roadwork",
    "traffic_boost",
    "attraction_point",
    "clear_event",
]


class EditorPatchDto(BaseModel):
    id: str
    kind: EditorPatchKind
    target_id: str | None = None
    payload: dict = {}


class ApplyEditorPatchRequest(BaseModel):
    session_id: str
    patch: EditorPatchDto


class ApplyEditorPatchResponse(BaseModel):
    session_id: str
    applied_patch: EditorPatchDto
    total_patches: int