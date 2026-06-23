from app.utils.geo import distance_meters, latlon_to_local_meters, local_meters_to_latlon


def test_latlon_local_roundtrip() -> None:
    lat = 55.751244
    lon = 37.618423

    x, y = latlon_to_local_meters(lat, lon, lat, lon)
    next_lat, next_lon = local_meters_to_latlon(x, y, lat, lon)

    assert abs(next_lat - lat) < 0.000001
    assert abs(next_lon - lon) < 0.000001


def test_distance_meters() -> None:
    distance = distance_meters(55.751244, 37.618423, 55.752244, 37.618423)

    assert 100 <= distance <= 120