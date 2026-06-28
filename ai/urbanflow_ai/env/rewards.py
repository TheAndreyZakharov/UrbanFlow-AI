from __future__ import annotations

from dataclasses import dataclass

from urbanflow_ai.config import RewardWeights
from urbanflow_ai.env.observations import TlsObservation


@dataclass(frozen=True)
class RewardBreakdown:
    reward: float
    queue_penalty: float
    wait_penalty: float
    stopped_penalty: float
    congestion_penalty: float
    low_speed_penalty: float
    switch_penalty: float
    throughput_bonus: float


def tls_reward(
    observation: TlsObservation,
    switched: bool,
    weights: RewardWeights,
) -> RewardBreakdown:
    queue_penalty = observation.total_halted_count * weights.queue
    wait_penalty = observation.total_waiting_time_s * weights.wait_time
    stopped_penalty = observation.total_halted_count * weights.stopped

    congestion_penalty = 0.0
    low_speed_penalty = 0.0

    for lane in observation.lanes.values():
        congestion_penalty += lane.occupancy * weights.congestion
        low_speed_penalty += lane.low_speed_score * max(1, lane.vehicle_count) * weights.low_speed

    switch_penalty = weights.switch_penalty if switched else 0.0
    throughput_bonus = max(0.0, observation.average_speed_mps) * weights.throughput_bonus

    reward = (
        throughput_bonus
        - queue_penalty
        - wait_penalty
        - stopped_penalty
        - congestion_penalty
        - low_speed_penalty
        - switch_penalty
    )

    return RewardBreakdown(
        reward=reward,
        queue_penalty=queue_penalty,
        wait_penalty=wait_penalty,
        stopped_penalty=stopped_penalty,
        congestion_penalty=congestion_penalty,
        low_speed_penalty=low_speed_penalty,
        switch_penalty=switch_penalty,
        throughput_bonus=throughput_bonus,
    )


def network_reward(
    observations: list[TlsObservation],
    switches: int,
    weights: RewardWeights,
) -> RewardBreakdown:
    if not observations:
        return RewardBreakdown(
            reward=0.0,
            queue_penalty=0.0,
            wait_penalty=0.0,
            stopped_penalty=0.0,
            congestion_penalty=0.0,
            low_speed_penalty=0.0,
            switch_penalty=0.0,
            throughput_bonus=0.0,
        )

    total_queue = 0.0
    total_wait = 0.0
    total_stopped = 0.0
    total_congestion = 0.0
    total_low_speed = 0.0
    total_throughput = 0.0

    for observation in observations:
        total_queue += observation.total_halted_count * weights.queue
        total_wait += observation.total_waiting_time_s * weights.wait_time
        total_stopped += observation.total_halted_count * weights.stopped
        total_throughput += max(0.0, observation.average_speed_mps) * weights.throughput_bonus

        for lane in observation.lanes.values():
            total_congestion += lane.occupancy * weights.congestion
            total_low_speed += lane.low_speed_score * max(1, lane.vehicle_count) * weights.low_speed

    switch_penalty = switches * weights.switch_penalty

    reward = (
        total_throughput
        - total_queue
        - total_wait
        - total_stopped
        - total_congestion
        - total_low_speed
        - switch_penalty
    )

    return RewardBreakdown(
        reward=reward,
        queue_penalty=total_queue,
        wait_penalty=total_wait,
        stopped_penalty=total_stopped,
        congestion_penalty=total_congestion,
        low_speed_penalty=total_low_speed,
        switch_penalty=switch_penalty,
        throughput_bonus=total_throughput,
    )