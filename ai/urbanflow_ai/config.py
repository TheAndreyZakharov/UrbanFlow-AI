from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


TrainingSignalScope = Literal["osm_only", "all_intersections"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"


@dataclass(frozen=True)
class RewardWeights:
    queue: float = 2.6
    wait_time: float = 0.095
    stopped: float = 2.2
    congestion: float = 5.0
    low_speed: float = 0.45
    switch_penalty: float = 1.4
    emergency_bonus: float = 3.0
    throughput_bonus: float = 0.25


@dataclass(frozen=True)
class PolicyWeights:
    halted: float = 3.0
    vehicles: float = 1.0
    waiting_time: float = 0.04
    occupancy: float = 1.6
    low_speed: float = 0.65
    downstream_penalty: float = 0.35
    emergency: float = 7.0


@dataclass(frozen=True)
class RuntimeControllerConfig:
    min_green_ticks: int = 12
    max_green_ticks: int = 45
    min_yellow_ticks: int = 3
    action_interval_ticks: int = 3
    switch_margin: float = 4.0
    max_controlled_lanes_per_tls: int = 64
    model_version: str = "urbanflow_tls_v1"


@dataclass(frozen=True)
class TrainingConfig:
    signal_scope: TrainingSignalScope = "osm_only"
    start_vehicles: int = 60
    max_vehicles: int = 800
    vehicle_step: int = 80
    steps_per_level: int = 900
    pedestrians_count: int = 220
    random_events_enabled: bool = True
    output_dir: str = str(MODELS_DIR / "tls_osm_only")


@dataclass(frozen=True)
class UrbanFlowModelConfig:
    runtime: RuntimeControllerConfig = RuntimeControllerConfig()
    policy: PolicyWeights = PolicyWeights()
    reward: RewardWeights = RewardWeights()

    def to_dict(self) -> dict:
        return asdict(self)


def model_output_dir_for_scope(signal_scope: TrainingSignalScope) -> Path:
    if signal_scope == "all_intersections":
        return MODELS_DIR / "tls_all_intersections"

    return MODELS_DIR / "tls_osm_only"