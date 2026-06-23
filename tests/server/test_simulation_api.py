from fastapi.testclient import TestClient

from app.main import app


def test_create_demo_simulation_and_step() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/simulation/create-demo",
        json={
            "mode": "fixed",
            "vehicles_count": 10,
            "pedestrians_count": 20,
            "random_events_enabled": True,
            "seed": 123,
        },
    )

    assert create_response.status_code == 200

    payload = create_response.json()
    session_id = payload["session_id"]

    assert session_id.startswith("session:")
    assert payload["state"]["metrics"]["active_vehicles"] == 10

    step_response = client.post(
        f"/simulation/{session_id}/step",
        json={"steps": 10},
    )

    assert step_response.status_code == 200
    assert step_response.json()["tick"] == 10


def test_set_simulation_mode() -> None:
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

    session_id = create_response.json()["session_id"]

    mode_response = client.post(f"/simulation/{session_id}/mode/rule_based")

    assert mode_response.status_code == 200
    assert mode_response.json()["mode"] == "rule_based"