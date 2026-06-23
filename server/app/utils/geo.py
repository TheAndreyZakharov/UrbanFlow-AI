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
    z = (lat - origin_lat) * EARTH_METERS_PER_DEGREE_LAT
    return x, z


def local_meters_to_latlon(
    x: float,
    z: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    lat = origin_lat + z / EARTH_METERS_PER_DEGREE_LAT
    lon = origin_lon + x / meters_per_degree_lon(origin_lat)
    return lat, lon


def distance_meters(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> float:
    origin_lat = (lat_a + lat_b) / 2
    x1, z1 = latlon_to_local_meters(lat_a, lon_a, origin_lat, lon_a)
    x2, z2 = latlon_to_local_meters(lat_b, lon_b, origin_lat, lon_a)
    return sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)


def polyline_length_meters(coordinates: list[tuple[float, float]]) -> float:
    if len(coordinates) < 2:
        return 0.0

    total = 0.0

    for index in range(1, len(coordinates)):
        lat_a, lon_a = coordinates[index - 1]
        lat_b, lon_b = coordinates[index]
        total += distance_meters(lat_a, lon_a, lat_b, lon_b)

    return total