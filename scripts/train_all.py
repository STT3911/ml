"""
Train all models and save artifacts in the standard structure:

    artifacts/
        demo/               <- user identification on synthetic data
        iscx_vpn/
            15s/            <- VPN/non-VPN classifier, window 15s
            30s/
            60s/
            120s/
            metrics_comparison.csv
            metrics_comparison.png

Usage (synthetic data only):
    python scripts/train_all.py

Usage (with real user flow CSV):
    python scripts/train_all.py --input-csv data/flows.csv

Usage (with ISCX ARFF files in data/):
    python scripts/train_all.py --data-dir data
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from behavioral_session_id.evaluation import run_all_experiments
from behavioral_session_id.features import build_session_features
from behavioral_session_id.iscx_vpn import plot_metrics_comparison, train_vpn_classifier
from behavioral_session_id.pipeline import load_flows
from behavioral_session_id.sessionization import assign_sessions
from behavioral_session_id.synthetic_data import generate_synthetic_flows
from behavioral_session_id.types import PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train all models and save artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--output-dir", default="artifacts", help="Root artifacts directory.")
    parser.add_argument("--input-csv", default="", help="User flow CSV (optional; synthetic data used if omitted).")
    parser.add_argument("--data-dir", default="data", help="Directory with ISCX .arff files.")
    parser.add_argument("--classifier", default="catboost", choices=["catboost", "random_forest"])
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def _discover_arff(data_dir: Path) -> list[Path]:
    return sorted(
        p for p in data_dir.glob("TimeBasedFeatures-Dataset-*.arff")
        if not any(tag in p.name for tag in ("-AllinOne", "-NO-VPN", "-VPN.arff"))
    )


def _step(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def train_demo(args: argparse.Namespace, output_dir: Path) -> None:
    _step("1 / 2  —  User identification (behavioral pipeline)")
    demo_dir = output_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    if args.input_csv:
        flows = load_flows(args.input_csv)
        print(f"  Loaded flows from {args.input_csv}")
    else:
        flows = generate_synthetic_flows(n_users=8, sessions_per_mode=18, random_state=args.random_state)
        flows.to_csv(demo_dir / "synthetic_flows.csv", index=False)
        print("  Generated synthetic flows (8 users, 18 sessions/mode)")

    config = PipelineConfig(
        session_threshold_minutes=60,
        comparison_threshold_minutes=30,
        classifier_name=args.classifier,
        random_state=args.random_state,
    )

    for threshold in [config.session_threshold_minutes, config.comparison_threshold_minutes]:
        threshold_dir = demo_dir / f"threshold_{threshold}m"
        threshold_dir.mkdir(parents=True, exist_ok=True)
        sessionized = assign_sessions(flows, threshold_minutes=threshold)
        sessionized.to_csv(threshold_dir / "sessionized_flows.csv", index=False)
        session_features = build_session_features(sessionized)
        session_features.to_csv(threshold_dir / "session_features.csv", index=False)
        run_all_experiments(session_features=session_features, output_dir=threshold_dir, config=config)
        print(f"  threshold={threshold}m  -> {threshold_dir}")

    rows = []
    for threshold in [config.session_threshold_minutes, config.comparison_threshold_minutes]:
        m = pd.read_csv(demo_dir / f"threshold_{threshold}m" / "metrics_summary.csv")
        m["threshold_minutes"] = threshold
        rows.append(m)
    pd.concat(rows, ignore_index=True).to_csv(demo_dir / "threshold_comparison.csv", index=False)
    print(f"\n  Done -> {demo_dir}")


def train_iscx(args: argparse.Namespace, output_dir: Path) -> None:
    _step("2 / 2  —  VPN/non-VPN classification (ISCX)")
    iscx_dir = output_dir / "iscx_vpn"
    iscx_dir.mkdir(parents=True, exist_ok=True)

    arff_files = _discover_arff(Path(args.data_dir))
    if not arff_files:
        print(f"  No ISCX ARFF files found in '{args.data_dir}' — skipping.")
        print("  Put TimeBasedFeatures-Dataset-<window>.arff files there to enable this step.")
        return

    print(f"  Found {len(arff_files)} ARFF file(s): {[f.name for f in arff_files]}")
    rows = []
    for arff_file in arff_files:
        window = arff_file.stem.replace("TimeBasedFeatures-Dataset-", "")
        t0 = time.monotonic()
        metrics = train_vpn_classifier(
            input_arff=arff_file,
            output_dir=iscx_dir / window,
            random_state=args.random_state,
        )
        elapsed = time.monotonic() - t0
        rows.append(metrics)
        acc = metrics.get("accuracy", 0)
        auc = metrics.get("roc_auc", 0)
        print(f"  window={window:>4s}  accuracy={acc:.3f}  roc_auc={auc:.3f}  ({elapsed:.0f}s)")

    summary = pd.DataFrame(rows).sort_values("dataset")
    summary.to_csv(iscx_dir / "metrics_comparison.csv", index=False)
    plot_metrics_comparison(summary, iscx_dir / "metrics_comparison.png")
    print(f"\n  Done -> {iscx_dir}")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output root: {output_dir.resolve()}")
    t_total = time.monotonic()

    train_demo(args, output_dir)
    train_iscx(args, output_dir)

    elapsed = time.monotonic() - t_total
    print(f"\n{'='*60}")
    print(f"  All done in {elapsed:.0f}s")
    print(f"  Artifacts: {output_dir.resolve()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
