from collections import defaultdict

from app.schemas.osm import CityMapDto
from app.schemas.simulation import (
    IntersectionLoadDto,
    RoadLoadDto,
    SimulationMetricsDto,
    VehicleStateDto,
)


def build_road_load(city_map: CityMapDto, vehicles: list[VehicleStateDto]) -> list[RoadLoadDto]:
    vehicles_by_road: dict[str, list[VehicleStateDto]] = defaultdict(list)

    for vehicle in vehicles:
        vehicles_by_road[vehicle.road_id].append(vehicle)

    result: list[RoadLoadDto] = []

    for road in city_map.roads:
        road_vehicles = vehicles_by_road.get(road.id, [])

        if road_vehicles:
            average_speed = sum(vehicle.speed_mps for vehicle in road_vehicles) / len(road_vehicles)
            slow_count = len([vehicle for vehicle in road_vehicles if vehicle.speed_mps < 2.0])
            congestion = slow_count / len(road_vehicles)
        else:
            average_speed = 0.0
            congestion = 0.0

        result.append(
            RoadLoadDto(
                road_id=road.id,
                vehicle_count=len(road_vehicles),
                average_speed_mps=round(average_speed, 2),
                congestion_score=round(congestion, 3),
            )
        )

    return result


def build_intersection_load(city_map: CityMapDto, tick: int) -> list[IntersectionLoadDto]:
    result: list[IntersectionLoadDto] = []

    for index, intersection in enumerate(city_map.intersections):
        waiting_vehicles = (tick + index * 3) % 18
        waiting_pedestrians = (tick + index * 5) % 12
        congestion = min(1.0, waiting_vehicles / 18)

        result.append(
            IntersectionLoadDto(
                intersection_id=intersection.id,
                waiting_vehicles=waiting_vehicles,
                waiting_pedestrians=waiting_pedestrians,
                congestion_score=round(congestion, 3),
            )
        )

    return result


def build_metrics(
    vehicles: list[VehicleStateDto],
    pedestrians_count: int,
    active_events: int,
    throughput: int,
) -> SimulationMetricsDto:
    if vehicles:
        average_speed = sum(vehicle.speed_mps for vehicle in vehicles) / len(vehicles)
        average_vehicle_wait_time = sum(vehicle.wait_time for vehicle in vehicles) / len(vehicles)
        stopped_vehicles = len([vehicle for vehicle in vehicles if vehicle.speed_mps < 0.5])
        congestion_score = stopped_vehicles / len(vehicles)
    else:
        average_speed = 0.0
        average_vehicle_wait_time = 0.0
        stopped_vehicles = 0
        congestion_score = 0.0

    return SimulationMetricsDto(
        average_vehicle_wait_time=round(average_vehicle_wait_time, 2),
        average_pedestrian_wait_time=0.0,
        average_speed_mps=round(average_speed, 2),
        active_vehicles=len(vehicles),
        active_pedestrians=pedestrians_count,
        congestion_score=round(congestion_score, 3),
        stopped_vehicles=stopped_vehicles,
        active_events=active_events,
        throughput=throughput,
    )