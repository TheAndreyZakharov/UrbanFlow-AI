from math import cos, radians, sqrt


EARTH_METERS_PER_DEGREE_LAT = 111_320.0


def meters_per_degree_lon(latitude: float) -> float:
    return EARTH_METERS_PER_DEGREE_LAT * cos(radians(latitude))


def latlon_to_local_meters(
    lat: float,
    lon: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    x = (lon - origin_lon) * meters_per_degree_lon(origin_lat)
    y = (lat - origin_lat) * EARTH_METERS_PER_DEGREE_LAT
    return x, y


def local_meters_to_latlon(
    x: float,
    y: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    lat = origin_lat + y / EARTH_METERS_PER_DEGREE_LAT
    lon = origin_lon + x / meters_per_degree_lon(origin_lat)
    return lat, lon


def distance_meters(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> float:
    origin_lat = (lat_a + lat_b) / 2
    x1, y1 = latlon_to_local_meters(lat_a, lon_a, origin_lat, lon_a)
    x2, y2 = latlon_to_local_meters(lat_b, lon_b, origin_lat, lon_a)
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)