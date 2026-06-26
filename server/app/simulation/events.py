import random
from dataclasses import dataclass


@dataclass
class TrafficEvent:
    id: str
    kind: str
    target_id: str | None
    started_at_tick: int
    duration_ticks: int
    payload: dict

    def is_active(self, tick: int) -> bool:
        return self.started_at_tick <= tick < self.started_at_tick + self.duration_ticks


def maybe_generate_random_event(
    tick: int,
    road_ids: list[str],
    random_events_enabled: bool,
    rng: random.Random,
) -> TrafficEvent | None:
    if not random_events_enabled:
        return None

    if tick == 0 or tick % 120 != 0:
        return None

    if not road_ids:
        return None

    kind = rng.choice(["accident", "roadwork", "traffic_boost"])
    target_id = rng.choice(road_ids)

    if kind == "accident":
        duration = rng.randint(80, 180)
        payload = {
            "severity": rng.choice(["low", "medium", "high"]),
            "speed_multiplier": 0.25,
            "manual": False,
            "radius_m": 10,
        }

    elif kind == "roadwork":
        duration = rng.randint(180, 360)
        payload = {
            "closed_lanes": 1,
            "speed_multiplier": 0.5,
            "manual": False,
        }

    else:
        duration = rng.randint(100, 220)
        payload = {"flow_multiplier": rng.choice([1.5, 2.0, 2.5])}

    return TrafficEvent(
        id=f"event:{tick}:{kind}:{target_id}",
        kind=kind,
        target_id=target_id,
        started_at_tick=tick,
        duration_ticks=duration,
        payload=payload,
    )