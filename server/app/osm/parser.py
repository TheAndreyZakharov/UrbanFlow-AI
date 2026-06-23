from typing import Any


def split_osm_elements(osm_json: dict[str, Any]) -> tuple[dict[int, dict], list[dict]]:
    nodes: dict[int, dict] = {}
    ways: list[dict] = []

    for element in osm_json.get("elements", []):
        if element.get("type") == "node":
            nodes[int(element["id"])] = element
        elif element.get("type") == "way":
            ways.append(element)

    return nodes, ways