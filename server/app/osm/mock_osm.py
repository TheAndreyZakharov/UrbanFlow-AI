from typing import Any


def get_demo_osm_json() -> dict[str, Any]:
    return {
        "version": 0.6,
        "generator": "UrbanFlow AI demo fixture",
        "elements": [
            {"type": "node", "id": 1, "lat": 55.7510, "lon": 37.6170},
            {"type": "node", "id": 2, "lat": 55.7510, "lon": 37.6180},
            {"type": "node", "id": 3, "lat": 55.7510, "lon": 37.6190},
            {"type": "node", "id": 4, "lat": 55.7505, "lon": 37.6180},
            {"type": "node", "id": 5, "lat": 55.7515, "lon": 37.6180},
            {"type": "node", "id": 6, "lat": 55.7507, "lon": 37.6175},
            {"type": "node", "id": 7, "lat": 55.7507, "lon": 37.6178},
            {"type": "node", "id": 8, "lat": 55.7510, "lon": 37.6178},
            {"type": "node", "id": 9, "lat": 55.7510, "lon": 37.6175},
            {"type": "node", "id": 10, "lat": 55.7510, "lon": 37.6180, "tags": {"highway": "traffic_signals"}},
            {"type": "node", "id": 11, "lat": 55.7510, "lon": 37.6177, "tags": {"highway": "crossing"}},
            {"type": "node", "id": 12, "lat": 55.7513, "lon": 37.6182, "tags": {"amenity": "school", "name": "Demo School"}},
            {"type": "node", "id": 13, "lat": 55.7508, "lon": 37.6184, "tags": {"public_transport": "platform", "name": "Demo Stop"}},
            {
                "type": "way",
                "id": 101,
                "nodes": [1, 2, 3],
                "tags": {
                    "highway": "primary",
                    "name": "Demo Main Street",
                    "lanes": "2",
                    "maxspeed": "50",
                },
            },
            {
                "type": "way",
                "id": 102,
                "nodes": [4, 2, 5],
                "tags": {
                    "highway": "secondary",
                    "name": "Demo Cross Street",
                    "lanes": "2",
                    "maxspeed": "40",
                },
            },
            {
                "type": "way",
                "id": 103,
                "nodes": [6, 1],
                "tags": {
                    "highway": "residential",
                    "name": "Demo Residential Road",
                    "lanes": "1",
                    "maxspeed": "30",
                },
            },
            {
                "type": "way",
                "id": 201,
                "nodes": [6, 7, 8, 9, 6],
                "tags": {"building": "yes", "building:levels": "5"},
            },
        ],
    }