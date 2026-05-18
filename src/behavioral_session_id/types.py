from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


BASE_FLOW_COLUMNS = {
    "user_id",
    "mode",
    "start_time",
    "end_time",
    "duration",
    "bytes_up",
    "bytes_down",
    "pkts_up",
    "pkts_down",
}


OPTIONAL_FLOW_COLUMNS = {
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_min",
    "flow_iat_max",
    "fwd_iat_mean",
    "fwd_iat_std",
    "fwd_iat_min",
    "fwd_iat_max",
    "bwd_iat_mean",
    "bwd_iat_std",
    "bwd_iat_min",
    "bwd_iat_max",
    "active_mean",
    "active_std",
    "active_min",
    "active_max",
    "idle_mean",
    "idle_std",
    "idle_min",
    "idle_max",
    "bytes_per_sec",
    "pkts_per_sec",
}


@dataclass(frozen=True)
class PipelineConfig:
    session_threshold_minutes: int = 60
    comparison_threshold_minutes: int = 30
    classifier_name: str = "catboost"
    alpha: float = 0.5
    confidence_threshold: float = 0.45
    unknown_threshold: float = 0.60
    random_state: int = 42


@dataclass(frozen=True)
class PredictionRow:
    true_user_id: str
    predicted_user_id: str
    confidence: float
    anomaly_score: float
    final_risk_score: float
    mode: str
    scenario: str
    is_unknown_true: bool
    is_unknown_pred: bool


def required_columns() -> Iterable[str]:
    return sorted(BASE_FLOW_COLUMNS)
