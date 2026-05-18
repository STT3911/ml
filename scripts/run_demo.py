from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from behavioral_session_id.evaluation import run_all_experiments
from behavioral_session_id.features import build_session_features
from behavioral_session_id.pipeline import load_flows
from behavioral_session_id.sessionization import assign_sessions
from behavioral_session_id.synthetic_data import generate_synthetic_flows
from behavioral_session_id.types import PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the behavioral session identification pipeline.")
    parser.add_argument("--input-csv", type=str, default="", help="Path to flow CSV. If omitted, synthetic data is used.")
    parser.add_argument("--output-dir", type=str, default="artifacts/demo", help="Directory for artifacts.")
    parser.add_argument("--session-threshold-minutes", type=int, default=60, help="Primary session threshold.")
    parser.add_argument("--comparison-threshold-minutes", type=int, default=30, help="Additional threshold.")
    parser.add_argument("--classifier", type=str, default="catboost", choices=["catboost", "random_forest"])
    parser.add_argument("--alpha", type=float, default=0.5, help="Weight for final risk score.")
    parser.add_argument("--confidence-threshold", type=float, default=0.45)
    parser.add_argument("--unknown-threshold", type=float, default=0.60)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--synthetic-users", type=int, default=8)
    parser.add_argument("--synthetic-sessions-per-mode", type=int, default=18)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input_csv:
        flows = load_flows(args.input_csv)
    else:
        flows = generate_synthetic_flows(
            n_users=args.synthetic_users,
            sessions_per_mode=args.synthetic_sessions_per_mode,
            random_state=args.random_state,
        )
        flows.to_csv(output_dir / "synthetic_flows.csv", index=False)

    config = PipelineConfig(
        session_threshold_minutes=args.session_threshold_minutes,
        comparison_threshold_minutes=args.comparison_threshold_minutes,
        classifier_name=args.classifier,
        alpha=args.alpha,
        confidence_threshold=args.confidence_threshold,
        unknown_threshold=args.unknown_threshold,
        random_state=args.random_state,
    )

    for threshold in [config.session_threshold_minutes, config.comparison_threshold_minutes]:
        threshold_dir = output_dir / f"threshold_{threshold}m"
        threshold_dir.mkdir(parents=True, exist_ok=True)
        sessionized = assign_sessions(flows, threshold_minutes=threshold)
        sessionized.to_csv(threshold_dir / "sessionized_flows.csv", index=False)
        session_features = build_session_features(sessionized)
        session_features.to_csv(threshold_dir / "session_features.csv", index=False)
        run_all_experiments(session_features=session_features, output_dir=threshold_dir, config=config)

    comparison_rows: list[dict[str, object]] = []
    for threshold in [config.session_threshold_minutes, config.comparison_threshold_minutes]:
        metrics_path = output_dir / f"threshold_{threshold}m" / "metrics_summary.csv"
        metrics = pd.read_csv(metrics_path)
        metrics["threshold_minutes"] = threshold
        comparison_rows.append(metrics)

    comparison = pd.concat(comparison_rows, ignore_index=True)
    comparison.to_csv(output_dir / "threshold_comparison.csv", index=False)
    print(f"Artifacts saved to {output_dir}")


if __name__ == "__main__":
    main()
