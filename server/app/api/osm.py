from fastapi import APIRouter, HTTPException

from app.osm.client import OverpassClient
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import CityMapDto, OsmImportRequest

router = APIRouter()


@router.post("/import", response_model=CityMapDto)
async def import_osm_area(payload: OsmImportRequest) -> CityMapDto:
    client = OverpassClient()

    try:
        osm_json = await client.fetch_city_area(payload.bbox)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"OSM import failed: {error}",
        ) from error

    city_map = normalize_osm_to_city_map(osm_json, payload.bbox)

    if not city_map.roads and not city_map.buildings and not city_map.surfaces:
        elements_count = len(osm_json.get("elements", []))
        raise HTTPException(
            status_code=422,
            detail=(
                "Selected area was loaded from OSM, but no usable roads, buildings or surfaces were parsed. "
                f"Raw OSM elements: {elements_count}. "
                "This usually means OSM geometry was missing or unsupported. Try increasing area size or send this error with server logs."
            ),
        )

    return city_map