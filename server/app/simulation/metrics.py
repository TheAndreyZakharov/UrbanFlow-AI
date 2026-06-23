from app.schemas.simulation import SimulationMetricsDto, VehicleStateDto


def calculate_congestion_score(vehicles: list[VehicleStateDto]) -> float:
    if not vehicles:
        return 0.0

    slow_vehicles = [vehicle for vehicle in vehicles if vehicle.speed < 2.0]
    return round(len(slow_vehicles) / len(vehicles), 3)


def build_metrics(
    vehicles: list[VehicleStateDto],
    pedestrians_count: int,
) -> SimulationMetricsDto:
    average_speed = 0.0

    if vehicles:
        average_speed = sum(vehicle.speed for vehicle in vehicles) / len(vehicles)

    return SimulationMetricsDto(
        average_vehicle_wait_time=0.0,
        average_pedestrian_wait_time=0.0,
        average_speed=round(average_speed, 2),
        active_vehicles=len(vehicles),
        active_pedestrians=pedestrians_count,
        congestion_score=calculate_congestion_score(vehicles),
    )