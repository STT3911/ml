from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class _UserProfile:
    user_id: str
    preferred_hour: int
    second_hour: int
    base_duration: float
    duration_jitter: float
    byte_scale: float
    up_down_ratio: float
    packets_per_second: float
    iat_scale: float
    activity_bias: float


def _sample_session_start(rng: np.random.Generator, base_day: pd.Timestamp, profile: _UserProfile) -> pd.Timestamp:
    chosen_hour = profile.preferred_hour if rng.random() < 0.65 else profile.second_hour
    minute = int(rng.integers(0, 60))
    day_shift = int(rng.integers(0, 30))
    return base_day + pd.Timedelta(days=day_shift, hours=chosen_hour, minutes=minute)


def _mode_transform(mode: str) -> tuple[float, float, float]:
    mode = mode.lower()
    if mode == "vpn":
        return 1.12, 1.20, 1.08
    if mode == "proxy":
        return 1.18, 1.28, 1.03
    return 1.0, 1.0, 1.0


def generate_synthetic_flows(
    n_users: int = 8,
    sessions_per_mode: int = 18,
    modes: tuple[str, ...] = ("direct", "vpn"),
    flows_per_session_min: int = 8,
    flows_per_session_max: int = 22,
    random_state: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    base_day = pd.Timestamp("2026-01-01 00:00:00")

    profiles: list[_UserProfile] = []
    for index in range(n_users):
        profiles.append(
            _UserProfile(
                user_id=f"user_{index + 1:02d}",
                preferred_hour=int(rng.integers(7, 12)),
                second_hour=int(rng.integers(18, 23)),
                base_duration=float(rng.uniform(2.0, 18.0)),
                duration_jitter=float(rng.uniform(0.7, 3.5)),
                byte_scale=float(rng.uniform(600.0, 6000.0)),
                up_down_ratio=float(rng.uniform(0.2, 1.8)),
                packets_per_second=float(rng.uniform(3.0, 18.0)),
                iat_scale=float(rng.uniform(0.3, 2.5)),
                activity_bias=float(rng.uniform(0.4, 1.5)),
            )
        )

    rows: list[dict[str, object]] = []
    for profile in profiles:
        for mode in modes:
            duration_mul, iat_mul, byte_mul = _mode_transform(mode)
            for _ in range(sessions_per_mode):
                session_start = _sample_session_start(rng, base_day, profile)
                current_time = session_start
                flows_in_session = int(rng.integers(flows_per_session_min, flows_per_session_max + 1))

                for _flow_index in range(flows_in_session):
                    gap_seconds = max(
                        0.0,
                        rng.gamma(shape=1.6, scale=profile.iat_scale * iat_mul) - profile.activity_bias,
                    )
                    current_time = current_time + pd.Timedelta(seconds=float(gap_seconds))

                    duration = max(
                        0.2,
                        rng.normal(profile.base_duration * duration_mul, profile.duration_jitter),
                    )
                    bytes_total = max(120.0, rng.lognormal(np.log(profile.byte_scale * byte_mul), 0.45))
                    bytes_up = bytes_total * profile.up_down_ratio / (1.0 + profile.up_down_ratio)
                    bytes_down = max(1.0, bytes_total - bytes_up)
                    packets_total = max(2.0, bytes_total / rng.uniform(220.0, 900.0))
                    pkts_up = max(1.0, packets_total * profile.up_down_ratio / (1.0 + profile.up_down_ratio))
                    pkts_down = max(1.0, packets_total - pkts_up)

                    flow_iat_mean = max(0.001, gap_seconds + rng.normal(profile.iat_scale * iat_mul, 0.2))
                    flow_iat_std = max(0.001, rng.normal(flow_iat_mean / 2.0, 0.1))
                    flow_iat_min = max(0.0001, flow_iat_mean - flow_iat_std)
                    flow_iat_max = flow_iat_mean + flow_iat_std
                    fwd_iat_mean = max(0.001, flow_iat_mean * rng.uniform(0.7, 1.2))
                    bwd_iat_mean = max(0.001, flow_iat_mean * rng.uniform(0.7, 1.2))
                    fwd_iat_std = max(0.001, flow_iat_std * rng.uniform(0.7, 1.3))
                    bwd_iat_std = max(0.001, flow_iat_std * rng.uniform(0.7, 1.3))
                    active_mean = max(0.1, duration * rng.uniform(0.55, 0.95))
                    idle_mean = max(0.0, duration - active_mean)
                    active_std = max(0.001, active_mean * rng.uniform(0.05, 0.25))
                    idle_std = max(0.001, max(idle_mean, 0.05) * rng.uniform(0.05, 0.25))

                    end_time = current_time + pd.Timedelta(seconds=float(duration))
                    rows.append(
                        {
                            "user_id": profile.user_id,
                            "mode": mode,
                            "start_time": current_time,
                            "end_time": end_time,
                            "duration": float(duration),
                            "bytes_up": float(bytes_up),
                            "bytes_down": float(bytes_down),
                            "pkts_up": float(pkts_up),
                            "pkts_down": float(pkts_down),
                            "flow_iat_mean": float(flow_iat_mean),
                            "flow_iat_std": float(flow_iat_std),
                            "flow_iat_min": float(flow_iat_min),
                            "flow_iat_max": float(flow_iat_max),
                            "fwd_iat_mean": float(fwd_iat_mean),
                            "fwd_iat_std": float(fwd_iat_std),
                            "fwd_iat_min": float(max(0.0001, fwd_iat_mean - fwd_iat_std)),
                            "fwd_iat_max": float(fwd_iat_mean + fwd_iat_std),
                            "bwd_iat_mean": float(bwd_iat_mean),
                            "bwd_iat_std": float(bwd_iat_std),
                            "bwd_iat_min": float(max(0.0001, bwd_iat_mean - bwd_iat_std)),
                            "bwd_iat_max": float(bwd_iat_mean + bwd_iat_std),
                            "active_mean": float(active_mean),
                            "active_std": float(active_std),
                            "active_min": float(max(0.05, active_mean - active_std)),
                            "active_max": float(active_mean + active_std),
                            "idle_mean": float(idle_mean),
                            "idle_std": float(idle_std),
                            "idle_min": 0.0,
                            "idle_max": float(idle_mean + idle_std),
                            "bytes_per_sec": float(bytes_total / duration),
                            "pkts_per_sec": float(packets_total / duration),
                        }
                    )
                    current_time = end_time

    flows = pd.DataFrame(rows)
    return flows.sort_values(["user_id", "start_time"]).reset_index(drop=True)
