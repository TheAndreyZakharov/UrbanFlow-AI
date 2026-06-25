from collections import defaultdict
from math import hypot

from app.schemas.osm import CityMapDto
from app.schemas.simulation import (
    IntersectionLoadDto,
    PedestrianStateDto,
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
            capacity = max(1, road.lanes * max(1, len(road.coordinates) - 1) * 6)
            density = min(1.0, len(road_vehicles) / capacity)
            congestion = max(slow_count / len(road_vehicles), density)
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


def build_intersection_load(
    city_map: CityMapDto,
    vehicles: list[VehicleStateDto],
    pedestrians: list[PedestrianStateDto],
) -> list[IntersectionLoadDto]:
    result: list[IntersectionLoadDto] = []

    for intersection in city_map.intersections:
        waiting_vehicles = 0
        waiting_pedestrians = 0

        for vehicle in vehicles:
            if vehicle.speed_mps > 1.5:
                continue
            if hypot(vehicle.x - intersection.x, vehicle.z - intersection.z) <= 35:
                waiting_vehicles += 1

        for pedestrian in pedestrians:
            if hypot(pedestrian.x - intersection.x, pedestrian.z - intersection.z) <= 22:
                waiting_pedestrians += 1

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
    pedestrians: list[PedestrianStateDto],
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

    if pedestrians:
        average_pedestrian_wait_time = sum(pedestrian.wait_time for pedestrian in pedestrians) / len(pedestrians)
    else:
        average_pedestrian_wait_time = 0.0

    return SimulationMetricsDto(
        average_vehicle_wait_time=round(average_vehicle_wait_time, 2),
        average_pedestrian_wait_time=round(average_pedestrian_wait_time, 2),
        average_speed_mps=round(average_speed, 2),
        active_vehicles=len(vehicles),
        active_pedestrians=len(pedestrians),
        congestion_score=round(congestion_score, 3),
        stopped_vehicles=stopped_vehicles,
        active_events=active_events,
        throughput=throughput,
    )