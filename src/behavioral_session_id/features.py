from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_AGGREGATE_COLUMNS = [
    "duration",
    "bytes_up",
    "bytes_down",
    "pkts_up",
    "pkts_down",
    "flow_iat_mean",
    "flow_iat_std",
    "flow_iat_min",
    "flow_iat_max",
    "fwd_iat_mean",
    "fwd_iat_std",
    "bwd_iat_mean",
    "bwd_iat_std",
    "active_mean",
    "active_std",
    "idle_mean",
    "idle_std",
    "bytes_per_sec",
    "pkts_per_sec",
]


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _cyclical_features(values: pd.Series, period: float, prefix: str) -> pd.DataFrame:
    angles = 2.0 * np.pi * values.astype(float) / period
    return pd.DataFrame(
        {
            f"{prefix}_sin": np.sin(angles),
            f"{prefix}_cos": np.cos(angles),
        },
        index=values.index,
    )


def _aggregate_numeric(group: pd.DataFrame, numeric_columns: Iterable[str]) -> dict[str, float]:
    features: dict[str, float] = {}
    for column in numeric_columns:
        if column not in group.columns:
            continue
        series = pd.to_numeric(group[column], errors="coerce").dropna()
        if series.empty:
            continue
        features[f"{column}_mean"] = float(series.mean())
        features[f"{column}_std"] = float(series.std(ddof=0))
        features[f"{column}_min"] = float(series.min())
        features[f"{column}_max"] = float(series.max())
        features[f"{column}_median"] = float(series.median())
        features[f"{column}_q25"] = float(series.quantile(0.25))
        features[f"{column}_q75"] = float(series.quantile(0.75))
    return features


def build_session_features(
    flows: pd.DataFrame,
    aggregate_columns: Iterable[str] | None = None,
    short_flow_seconds: float = 2.0,
    long_flow_seconds: float = 30.0,
) -> pd.DataFrame:
    if "session_id" not in flows.columns:
        raise ValueError("Flows dataframe must contain session_id. Run assign_sessions first.")

    result_rows: list[dict[str, float | str]] = []
    aggregate_columns = list(aggregate_columns or DEFAULT_AGGREGATE_COLUMNS)

    for session_id, group in flows.sort_values(["session_id", "start_time"]).groupby("session_id"):
        session_start = group["start_time"].min()
        session_end = group["end_time"].max()
        session_duration_seconds = max((session_end - session_start).total_seconds(), 1.0)

        inter_flow_gaps = (
            group["start_time"].iloc[1:].reset_index(drop=True)
            - group["end_time"].iloc[:-1].reset_index(drop=True)
        ).dt.total_seconds()
        inter_flow_gaps = inter_flow_gaps.clip(lower=0.0)

        active_time = float(group["duration"].clip(lower=0.0).sum())
        idle_time = float(inter_flow_gaps.sum()) if not inter_flow_gaps.empty else 0.0
        density = _safe_divide(active_time, session_duration_seconds)
        up_down_ratio = _safe_divide(group["bytes_up"].sum(), group["bytes_down"].sum())
        total_bytes = float(group["bytes_up"].sum() + group["bytes_down"].sum())
        total_packets = float(group["pkts_up"].sum() + group["pkts_down"].sum())

        row: dict[str, float | str] = {
            "session_id": session_id,
            "user_id": str(group["user_id"].iloc[0]),
            "mode": str(group["mode"].iloc[0]),
            "session_start": session_start.isoformat(),
            "session_end": session_end.isoformat(),
            "session_duration_seconds": float(session_duration_seconds),
            "num_flows": int(len(group)),
            "active_time_seconds": active_time,
            "idle_time_seconds": idle_time,
            "activity_density": density,
            "up_down_ratio": up_down_ratio,
            "total_bytes": total_bytes,
            "total_packets": total_packets,
            "bytes_per_session_second": _safe_divide(total_bytes, session_duration_seconds),
            "packets_per_session_second": _safe_divide(total_packets, session_duration_seconds),
            "short_flow_fraction": float((group["duration"] <= short_flow_seconds).mean()),
            "long_flow_fraction": float((group["duration"] >= long_flow_seconds).mean()),
            "burstiness": float(
                _safe_divide(
                    inter_flow_gaps.std(ddof=0) - inter_flow_gaps.mean(),
                    inter_flow_gaps.std(ddof=0) + inter_flow_gaps.mean(),
                )
            )
            if not inter_flow_gaps.empty
            else 0.0,
            "inter_flow_gap_mean": float(inter_flow_gaps.mean()) if not inter_flow_gaps.empty else 0.0,
            "inter_flow_gap_std": float(inter_flow_gaps.std(ddof=0)) if not inter_flow_gaps.empty else 0.0,
            "inter_flow_gap_median": float(inter_flow_gaps.median()) if not inter_flow_gaps.empty else 0.0,
            "inter_flow_gap_q25": float(inter_flow_gaps.quantile(0.25)) if not inter_flow_gaps.empty else 0.0,
            "inter_flow_gap_q75": float(inter_flow_gaps.quantile(0.75)) if not inter_flow_gaps.empty else 0.0,
            "hour_of_day": int(session_start.hour),
            "day_of_week": int(session_start.dayofweek),
            "is_vpn": int(str(group["mode"].iloc[0]).lower() == "vpn"),
            "is_proxy": int(str(group["mode"].iloc[0]).lower() == "proxy"),
        }

        row.update(_aggregate_numeric(group, aggregate_columns))
        result_rows.append(row)

    features = pd.DataFrame(result_rows)
    hour_features = _cyclical_features(features["hour_of_day"], period=24.0, prefix="hour")
    day_features = _cyclical_features(features["day_of_week"], period=7.0, prefix="weekday")
    features = pd.concat([features, hour_features, day_features], axis=1)

    numeric_columns = features.select_dtypes(include=[np.number]).columns
    features[numeric_columns] = features[numeric_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features


def select_feature_columns(session_features: pd.DataFrame) -> list[str]:
    excluded = {
        "session_id",
        "user_id",
        "mode",
        "session_start",
        "session_end",
        "hour_of_day",
        "day_of_week",
    }
    return [column for column in session_features.columns if column not in excluded]
