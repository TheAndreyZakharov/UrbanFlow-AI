import httpx

from app.core.config import settings
from app.schemas.osm import BoundingBox


class OverpassClient:
    def __init__(self, api_url: str = settings.overpass_api_url) -> None:
        self.api_url = api_url

    async def fetch_city_area(self, bbox: BoundingBox) -> dict:
        query = self._build_query(bbox)

        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(self.api_url, data={"data": query})
            response.raise_for_status()
            return response.json()

    def _build_query(self, bbox: BoundingBox) -> str:
        bbox_string = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"

        return f"""
        [out:json][timeout:90];
        (
          way["highway"]({bbox_string});
          way["building"]({bbox_string});
          node["highway"="traffic_signals"]({bbox_string});
          node["highway"="crossing"]({bbox_string});
          node["public_transport"]({bbox_string});
          node["amenity"]({bbox_string});
          node["shop"]({bbox_string});
          node["railway"="station"]({bbox_string});
          node["railway"="subway_entrance"]({bbox_string});
          node["leisure"="park"]({bbox_string});
        );
        out body;
        >;
        out skel qt;
        """