from typing import Any


def split_osm_elements(osm_json: dict[str, Any]) -> tuple[dict[int, dict], list[dict], list[dict]]:
    nodes: dict[int, dict] = {}
    ways: list[dict] = []
    relations: list[dict] = []

    for element in osm_json.get("elements", []):
        element_type = element.get("type")

        if element_type == "node" and "id" in element:
            nodes[int(element["id"])] = element

        elif element_type == "way":
            ways.append(element)

        elif element_type == "relation":
            relations.append(element)

    return nodes, ways, relations