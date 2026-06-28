import httpx

from app.core.config import settings
from app.schemas.osm import BoundingBox


class OverpassClient:
    def __init__(self, api_url: str = settings.overpass_api_url) -> None:
        self.api_urls = _unique_urls(
            [
                api_url,
                "https://overpass-api.de/api/interpreter",
                "https://lz4.overpass-api.de/api/interpreter",
                "https://overpass.kumi.systems/api/interpreter",
                "https://overpass.openstreetmap.ru/api/interpreter",
                "https://overpass.nchc.org.tw/api/interpreter",
                "https://overpass.private.coffee/api/interpreter",
                "https://overpass.osm.ch/api/interpreter",
            ]
        )

    async def fetch_city_area(self, bbox: BoundingBox) -> dict:
        query = self._build_query(bbox)
        attempts: list[str] = []

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json",
            "User-Agent": "UrbanFlow-AI/0.1 local-development",
        }

        timeout = httpx.Timeout(connect=25.0, read=180.0, write=25.0, pool=25.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, trust_env=True) as client:
            for index, api_url in enumerate(self.api_urls, start=1):
                try:
                    response = await client.post(
                        api_url,
                        data={"data": query},
                        headers=headers,
                    )

                    if response.status_code in {429, 500, 502, 503, 504}:
                        attempts.append(
                            f"{index}. {api_url} -> temporary HTTP {response.status_code}: {response.text[:260]}"
                        )
                        continue

                    response.raise_for_status()

                    payload = response.json()
                    elements_count = len(payload.get("elements", []))

                    if elements_count == 0:
                        attempts.append(f"{index}. {api_url} -> empty elements response")
                        continue

                    return payload

                except httpx.HTTPStatusError as error:
                    attempts.append(
                        f"{index}. {api_url} -> HTTP {error.response.status_code}: {error.response.text[:260]}"
                    )

                except httpx.RequestError as error:
                    attempts.append(f"{index}. {api_url} -> connection error: {error!r}")

                except ValueError as error:
                    attempts.append(f"{index}. {api_url} -> invalid JSON: {error!r}")

        raise RuntimeError("All Overpass endpoints failed or returned empty data. " + " | ".join(attempts))

    def _build_query(self, bbox: BoundingBox) -> str:
        bbox_string = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"

        return f"""
[out:json][timeout:180];
(
  nwr["highway"]({bbox_string});
  node["highway"="crossing"]({bbox_string});
  way["footway"="crossing"]({bbox_string});
  node["highway"="traffic_signals"]({bbox_string});
  nwr["traffic_signals"]({bbox_string});
  nwr["traffic_signals:direction"]({bbox_string});
  nwr["traffic_calming"]({bbox_string});
  nwr["kerb"]({bbox_string});
  nwr["barrier"]({bbox_string});

  nwr["area:highway"]({bbox_string});
  relation["type"="multipolygon"]["area:highway"]({bbox_string});
  relation["type"="multipolygon"]["highway"="pedestrian"]({bbox_string});
  way["highway"="pedestrian"]["area"="yes"]({bbox_string});

  nwr["railway"]({bbox_string});
  nwr["railway"~"^(rail|tram|light_rail|platform|platform_edge|platform_section|halt|tram_stop|station|buffer_stop)$"]({bbox_string});

  nwr["public_transport"~"^(platform|stop_position|station)$"]({bbox_string});
  relation["type"="public_transport"]["public_transport"="stop_area"]({bbox_string});
  node["highway"="bus_stop"]({bbox_string});
  way["highway"="bus_stop"]({bbox_string});

  relation["type"="route"]["route"~"^(bus|tram|trolleybus|share_taxi|minibus|coach|train|light_rail)$"]({bbox_string});
  relation["type"="route_master"]["route_master"~"^(bus|tram|trolleybus|share_taxi|minibus|coach|train|light_rail)$"]({bbox_string});
  
  nwr["waterway"]({bbox_string});
  nwr["water"]({bbox_string});
  nwr["natural"="water"]({bbox_string});
  nwr["natural"~"^(bay|beach|sand|shingle|wetland|wood|scrub|grassland|heath|bare_rock)$"]({bbox_string});
  relation["type"="multipolygon"]["waterway"="riverbank"]({bbox_string});

  nwr["landuse"]({bbox_string});
  nwr["landcover"]({bbox_string});
  nwr["leisure"]({bbox_string});
  nwr["military"]({bbox_string});

  nwr["building"]({bbox_string});
  nwr["building:part"]({bbox_string});
  relation["type"="building"]({bbox_string});

  nwr["amenity"]({bbox_string});
  nwr["shop"]({bbox_string});
  nwr["office"]({bbox_string});
  nwr["craft"]({bbox_string});
  nwr["tourism"]({bbox_string});
  nwr["sport"]({bbox_string});
  nwr["healthcare"]({bbox_string});
  nwr["emergency"]({bbox_string});
  nwr["historic"]({bbox_string});
  nwr["information"]({bbox_string});
  nwr["man_made"]({bbox_string});
  nwr["power"]({bbox_string});
  nwr["aeroway"]({bbox_string});
  nwr["place"]({bbox_string});
);
(._; >>;);
out body geom;
""".strip()


def _unique_urls(urls: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for url in urls:
        normalized = url.strip().rstrip("/")

        if not normalized:
            continue

        if normalized not in seen:
            result.append(normalized)
            seen.add(normalized)

    return result