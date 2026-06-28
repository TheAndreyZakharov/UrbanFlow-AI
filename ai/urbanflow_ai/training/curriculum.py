from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurriculumLevel:
    index: int
    vehicles: int
    pedestrians: int
    steps: int
    random_events_enabled: bool


@dataclass(frozen=True)
class TrafficCurriculum:
    start_vehicles: int = 60
    max_vehicles: int = 800
    vehicle_step: int = 80
    pedestrians_count: int = 220
    steps_per_level: int = 900
    random_events_enabled: bool = True

    def levels(self) -> list[CurriculumLevel]:
        result: list[CurriculumLevel] = []
        vehicles = self.start_vehicles
        index = 0

        while vehicles <= self.max_vehicles:
            result.append(
                CurriculumLevel(
                    index=index,
                    vehicles=vehicles,
                    pedestrians=self.pedestrians_count,
                    steps=self.steps_per_level,
                    random_events_enabled=self.random_events_enabled,
                )
            )

            vehicles += self.vehicle_step
            index += 1

        if not result or result[-1].vehicles != self.max_vehicles:
            result.append(
                CurriculumLevel(
                    index=index,
                    vehicles=self.max_vehicles,
                    pedestrians=self.pedestrians_count,
                    steps=self.steps_per_level,
                    random_events_enabled=self.random_events_enabled,
                )
            )

        return result