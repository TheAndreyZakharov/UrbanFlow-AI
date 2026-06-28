from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkMetrics:
    vehicle_count: int
    halted_count: int
    average_speed_mps: float
    total_waiting_time_s: float
    average_waiting_time_s: float
    congestion_score: float
    tls_count: int


def collect_network_metrics(conn) -> NetworkMetrics:
    try:
        vehicle_ids = list(conn.vehicle.getIDList())
    except Exception:
        vehicle_ids = []

    vehicle_count = len(vehicle_ids)
    halted_count = 0
    speed_sum = 0.0
    total_waiting_time_s = 0.0

    for vehicle_id in vehicle_ids:
        try:
            speed = float(conn.vehicle.getSpeed(vehicle_id))
            waiting_time = float(conn.vehicle.getWaitingTime(vehicle_id))
        except Exception:
            continue

        speed_sum += max(0.0, speed)
        total_waiting_time_s += max(0.0, waiting_time)

        if speed <= 0.25:
            halted_count += 1

    average_speed_mps = speed_sum / max(1, vehicle_count)
    average_waiting_time_s = total_waiting_time_s / max(1, vehicle_count)

    congestion_score = min(
        1.0,
        halted_count / max(1, vehicle_count) * 0.65
        + min(1.0, average_waiting_time_s / 120.0) * 0.35,
    )

    try:
        tls_count = len(conn.trafficlight.getIDList())
    except Exception:
        tls_count = 0

    return NetworkMetrics(
        vehicle_count=vehicle_count,
        halted_count=halted_count,
        average_speed_mps=average_speed_mps,
        total_waiting_time_s=total_waiting_time_s,
        average_waiting_time_s=average_waiting_time_s,
        congestion_score=congestion_score,
        tls_count=tls_count,
    )