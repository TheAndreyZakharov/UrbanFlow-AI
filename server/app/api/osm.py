from fastapi import APIRouter

from app.osm.client import OverpassClient
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import CityMapDto, OsmImportRequest

router = APIRouter()


@router.post("/import", response_model=CityMapDto)
async def import_osm_area(payload: OsmImportRequest) -> CityMapDto:
    client = OverpassClient()
    osm_json = await client.fetch_city_area(payload.bbox)
    return normalize_osm_to_city_map(osm_json, payload.bbox)