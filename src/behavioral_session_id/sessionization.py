from __future__ import annotations

from typing import Iterable

import pandas as pd

from .types import BASE_FLOW_COLUMNS


def validate_flow_dataframe(df: pd.DataFrame) -> None:
    missing = BASE_FLOW_COLUMNS.difference(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Flow dataframe is missing required columns: {missing_list}")


def ensure_timestamps(df: pd.DataFrame, columns: Iterable[str] = ("start_time", "end_time")) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if not pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = pd.to_datetime(result[column], errors="raise", utc=False)
    return result


def assign_sessions(
    df: pd.DataFrame,
    threshold_minutes: int = 60,
    split_on_mode: bool = True,
) -> pd.DataFrame:
    validate_flow_dataframe(df)
    result = ensure_timestamps(df)
    result = result.sort_values(["user_id", "start_time", "end_time"]).reset_index(drop=True)

    threshold = pd.Timedelta(minutes=threshold_minutes)
    previous_end = result.groupby("user_id")["end_time"].shift(1)
    previous_mode = result.groupby("user_id")["mode"].shift(1)
    gap = result["start_time"] - previous_end

    new_user = result["user_id"] != result["user_id"].shift(1)
    new_gap = gap.isna() | (gap > threshold)
    session_break = new_user | new_gap
    if split_on_mode:
        mode_switch = previous_mode.notna() & (result["mode"] != previous_mode)
        session_break = session_break | mode_switch

    result["gap_from_prev_seconds"] = gap.dt.total_seconds().fillna(0.0).clip(lower=0.0)
    result["session_index"] = session_break.cumsum()
    result["session_id"] = (
        result["user_id"].astype(str)
        + "_"
        + result["mode"].astype(str)
        + "_s"
        + result["session_index"].astype(str)
    )

    return result
