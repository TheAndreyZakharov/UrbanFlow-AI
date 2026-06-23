from app.schemas.simulation import (
    PedestrianStateDto,
    SimulationStateDto,
    TrafficSignalStateDto,
    VehicleStateDto,
)
from app.simulation.metrics import build_metrics


class SimulationEngine:
    def __init__(self) -> None:
        self.tick = 0

    def step(self) -> SimulationStateDto:
        self.tick += 1

        vehicles = [
            VehicleStateDto(
                id="vehicle-1",
                kind="car",
                lat=55.751244 + self.tick * 0.00001,
                lon=37.618423,
                speed=8.0,
                road_id="demo-road-1",
            )
        ]

        pedestrians = [
            PedestrianStateDto(
                id="pedestrian-1",
                lat=55.751244,
                lon=37.618423 + self.tick * 0.000005,
                speed=1.2,
            )
        ]

        signals = [
            TrafficSignalStateDto(
                id="signal-1",
                intersection_id="intersection-1",
                phase="green_north_south",
                time_left=max(0.0, 30.0 - self.tick),
            )
        ]

        metrics = build_metrics(
            vehicles=vehicles,
            pedestrians_count=len(pedestrians),
        )

        return SimulationStateDto(
            tick=self.tick,
            vehicles=vehicles,
            pedestrians=pedestrians,
            signals=signals,
            metrics=metrics,
        )