from fastapi import APIRouter

from app.osm.client import OverpassClient
from app.osm.mock_osm import get_demo_osm_json
from app.osm.normalizer import normalize_osm_to_city_map
from app.schemas.osm import BoundingBox, CityMapDto, OsmImportRequest

router = APIRouter()


@router.post("/import", response_model=CityMapDto)
async def import_osm_area(payload: OsmImportRequest) -> CityMapDto:
    client = OverpassClient()
    osm_json = await client.fetch_city_area(payload.bbox)
    return normalize_osm_to_city_map(osm_json, payload.bbox)


@router.get("/demo", response_model=CityMapDto)
def get_demo_city_map() -> CityMapDto:
    bbox = BoundingBox(
        south=55.7500,
        west=37.6165,
        north=55.7520,
        east=37.6195,
    )

    return normalize_osm_to_city_map(get_demo_osm_json(), bbox)