from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from joblib import load
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from behavioral_session_id.iscx_vpn import load_arff_tolerant, prepare_features_for_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test saved VPN/non-VPN model on an ISCX ARFF file.")
    parser.add_argument("--model", type=str, default="artifacts/iscx_vpn/15s/model.joblib")
    parser.add_argument("--input-arff", type=str, default="data/TimeBasedFeatures-Dataset-15s.arff")
    parser.add_argument("--output-csv", type=str, default="artifacts/iscx_vpn/manual_test_predictions.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = load(args.model)
    model = bundle["model"]
    feature_columns = bundle["feature_columns"]
    reference_medians = (
        pd.Series(bundle["train_medians"]) if "train_medians" in bundle else None
    )

    raw = load_arff_tolerant(args.input_arff)
    features = prepare_features_for_model(raw, feature_columns, reference_medians=reference_medians)
    probabilities = pd.DataFrame(model.predict_proba(features), columns=model.classes_)
    predictions = pd.Series(model.predict(features), name="pred_label")

    output = pd.DataFrame({"pred_label": predictions})
    if "vpn" in probabilities.columns:
        output["vpn_probability"] = probabilities["vpn"]

    if "class1" in raw.columns:
        true_label = raw["class1"].astype(str).str.startswith("VPN-").map({True: "vpn", False: "non_vpn"})
        output["true_label"] = true_label
        accuracy = accuracy_score(true_label, predictions)
        print(f"accuracy={accuracy:.4f}")
        if "vpn_probability" in output.columns:
            print(f"roc_auc={roc_auc_score(true_label.eq('vpn').astype(int), output['vpn_probability']):.4f}")
        print(classification_report(true_label, predictions, zero_division=0))

    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    print(f"Predictions saved to {output_path}")


if __name__ == "__main__":
    main()
