from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from behavioral_session_id.iscx_vpn import plot_metrics_comparison, train_vpn_classifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train VPN/non-VPN classifier on ISCX ARFF flow features.")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory with ISCX .arff files.")
    parser.add_argument("--input-arff", type=str, default="", help="Train on one ARFF file instead of all windows.")
    parser.add_argument("--output-dir", type=str, default="artifacts/iscx_vpn", help="Directory for artifacts.")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--test-size", type=float, default=0.25)
    return parser.parse_args()


def discover_combined_arff(data_dir: Path) -> list[Path]:
    candidates = []
    for path in sorted(data_dir.glob("TimeBasedFeatures-Dataset-*.arff")):
        name = path.name
        if "-AllinOne" in name or "-NO-VPN" in name or "-VPN" in name:
            continue
        candidates.append(path)
    return candidates


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.input_arff:
        arff_files = [Path(args.input_arff)]
    else:
        arff_files = discover_combined_arff(Path(args.data_dir))

    if not arff_files:
        raise SystemExit("No combined ISCX ARFF files found.")

    rows = []
    for arff_file in arff_files:
        run_name = arff_file.stem.replace("TimeBasedFeatures-Dataset-", "")
        metrics = train_vpn_classifier(
            input_arff=arff_file,
            output_dir=output_dir / run_name,
            random_state=args.random_state,
            test_size=args.test_size,
        )
        rows.append(metrics)

    summary = pd.DataFrame(rows).sort_values("dataset")
    summary.to_csv(output_dir / "metrics_comparison.csv", index=False)
    plot_metrics_comparison(summary, output_dir / "metrics_comparison.png")
    print(f"Artifacts saved to {output_dir}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
