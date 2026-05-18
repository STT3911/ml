from __future__ import annotations

from pathlib import Path

import pandas as pd

from .evaluation import run_all_experiments
from .features import build_session_features
from .sessionization import assign_sessions
from .types import PipelineConfig


def load_flows(input_csv: str | Path) -> pd.DataFrame:
    return pd.read_csv(input_csv)


def prepare_session_dataset(flows: pd.DataFrame, threshold_minutes: int) -> pd.DataFrame:
    sessionized = assign_sessions(flows, threshold_minutes=threshold_minutes)
    return build_session_features(sessionized)


def run_pipeline(
    flows: pd.DataFrame,
    output_dir: str | Path,
    config: PipelineConfig | None = None,
) -> dict[str, dict[str, float | int | None]]:
    config = config or PipelineConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session_features = prepare_session_dataset(flows, threshold_minutes=config.session_threshold_minutes)
    session_features.to_csv(output_dir / "session_features.csv", index=False)
    return run_all_experiments(session_features=session_features, output_dir=output_dir, config=config)
