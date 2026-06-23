from fastapi.testclient import TestClient

from app.main import app


def test_apply_editor_patch() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/simulation/create-demo",
        json={
            "mode": "fixed",
            "vehicles_count": 5,
            "pedestrians_count": 5,
            "random_events_enabled": False,
            "seed": 123,
        },
    )

    session = create_response.json()
    session_id = session["session_id"]
    road_id = session["city_map"]["roads"][0]["id"]

    patch_response = client.post(
        "/editor/apply",
        json={
            "session_id": session_id,
            "patch": {
                "id": "patch:close-road",
                "kind": "close_road",
                "target_id": road_id,
                "payload": {},
            },
        },
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["total_patches"] == 1

    state_response = client.get(f"/simulation/{session_id}/state")

    assert state_response.status_code == 200
    assert len(state_response.json()["editor_patches"]) == 1