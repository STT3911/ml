"""Application-as-identity proxy experiment on ISCX-VPN-NonVPN-2016.

The ARFF files do not contain user_id, so a strict user-identification
experiment is impossible on this dataset. As a proxy, we treat each
application class (BROWSING, VOIP, FT, CHAT, P2P, MAIL, STREAMING) as
a 'behavioral identity'. This tests the same hypothesis the user-ID
task tests: do time-based flow features preserve behavioral identity
when the traffic is wrapped in a VPN tunnel?

Scenarios:
  - direct_to_vpn: train on non-VPN flows, test on VPN flows
  - mixed:         stratified split across (application, mode)
  - open_set:      hide one rare application from training, expect
                   the hybrid model to flag it as 'unknown'

This is NOT a user-identification experiment. The artifacts are
labeled accordingly so the proxy nature stays explicit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score, roc_curve

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from behavioral_session_id.iscx_vpn import impute_with_reference, load_arff_tolerant
from behavioral_session_id.modeling import HybridUserIdentifier


FEATURE_COLUMNS = [
    "duration", "total_fiat", "total_biat", "min_fiat", "min_biat",
    "max_fiat", "max_biat", "mean_fiat", "mean_biat",
    "flowPktsPerSecond", "flowBytesPerSecond",
    "min_flowiat", "max_flowiat", "mean_flowiat", "std_flowiat",
    "min_active", "mean_active", "max_active", "std_active",
    "min_idle", "mean_idle", "max_idle", "std_idle",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-arff", type=str, default="data/TimeBasedFeatures-Dataset-15s.arff")
    parser.add_argument("--output-dir", type=str, default="artifacts/iscx_userid_proxy")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--holdout-app", type=str, default="MAIL",
                        help="Application class hidden from training in the open_set scenario.")
    return parser.parse_args()


def prepare_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["mode"] = np.where(df["class1"].str.startswith("VPN-"), "vpn", "direct")
    df["app_id"] = df["class1"].str.replace("VPN-", "", regex=False)
    features = df[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    features = features.replace([np.inf, -np.inf], np.nan)
    df[FEATURE_COLUMNS] = features
    return df


def fit_hybrid(X_train: pd.DataFrame, y_train: pd.Series, random_state: int) -> HybridUserIdentifier:
    model = HybridUserIdentifier(
        classifier_name="random_forest",
        alpha=0.5,
        confidence_threshold=0.45,
        unknown_threshold=0.60,
        random_state=random_state,
    )
    model.fit(X_train, y_train)
    return model


def evaluate(predictions: pd.DataFrame, scenario: str) -> dict:
    y_true = predictions["true_user_id"].astype(str)
    y_pred = predictions["pred_user_id"].astype(str)
    known_mask = y_true != "unknown"
    metrics: dict = {"scenario": scenario, "num_samples": int(len(predictions))}
    if known_mask.any():
        metrics["accuracy"] = float(accuracy_score(y_true[known_mask], y_pred[known_mask]))
        metrics["macro_f1"] = float(f1_score(y_true[known_mask], y_pred[known_mask],
                                             average="macro", zero_division=0))
        top3 = predictions.loc[known_mask, "top3_candidates"].tolist()
        truth = y_true[known_mask].tolist()
        metrics["top3_accuracy"] = float(np.mean([t in cands[:3] for t, cands in zip(truth, top3)]))
    binary_unknown = (y_true == "unknown").astype(int).to_numpy()
    if len(np.unique(binary_unknown)) >= 2:
        scores = predictions["final_risk_score"].to_numpy()
        metrics["roc_auc_unknown"] = float(roc_auc_score(binary_unknown, scores))
        fpr, tpr, _ = roc_curve(binary_unknown, scores)
        fnr = 1.0 - tpr
        idx = int(np.argmin(np.abs(fpr - fnr)))
        metrics["eer"] = float((fpr[idx] + fnr[idx]) / 2.0)
    return metrics


def plot_confusion(predictions: pd.DataFrame, path: Path, title: str) -> None:
    labels = sorted(set(predictions["true_user_id"].astype(str)) |
                    set(predictions["pred_user_id"].astype(str)))
    mat = confusion_matrix(predictions["true_user_id"], predictions["pred_user_id"], labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(mat, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.xlabel("Predicted")
    plt.ylabel("True (application proxy for user_id)")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def plot_per_app_accuracy(predictions: pd.DataFrame, path: Path) -> None:
    df = predictions.copy()
    df["correct"] = df["true_user_id"] == df["pred_user_id"]
    per_app = df[df["true_user_id"] != "unknown"].groupby("true_user_id")["correct"].mean().reset_index()
    plt.figure(figsize=(8, 5))
    sns.barplot(data=per_app, x="true_user_id", y="correct", hue="true_user_id",
                palette="viridis", legend=False)
    plt.ylim(0.0, 1.0)
    plt.ylabel("Per-app accuracy (direct → vpn)")
    plt.xlabel("Application (user proxy)")
    plt.title("Behavioral persistence through VPN tunnel")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def run_scenario(scenario: str, train_df: pd.DataFrame, test_df: pd.DataFrame,
                 holdout_apps: list[str], random_state: int) -> tuple[dict, pd.DataFrame]:
    train_medians = train_df[FEATURE_COLUMNS].median(numeric_only=True)
    X_train = impute_with_reference(train_df[FEATURE_COLUMNS], train_medians)
    X_test = impute_with_reference(test_df[FEATURE_COLUMNS], train_medians)
    y_train = train_df["app_id"].astype(str)
    y_test_raw = test_df["app_id"].astype(str)
    y_test = y_test_raw.where(~y_test_raw.isin(holdout_apps), other="unknown")

    model = fit_hybrid(X_train, y_train, random_state)
    predictions = model.predict_with_details(X_test, true_users=y_test)
    predictions["true_user_id"] = y_test.values
    predictions["scenario"] = scenario
    predictions["mode"] = test_df["mode"].values
    return evaluate(predictions, scenario), predictions


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    raw = load_arff_tolerant(args.input_arff)
    frame = prepare_frame(raw)
    print(f"Loaded {len(frame)} flows; apps={sorted(frame['app_id'].unique())}")
    print(frame.groupby(["app_id", "mode"]).size().unstack(fill_value=0))

    summary: list[dict] = []
    all_predictions: list[pd.DataFrame] = []

    # Scenario 1: direct -> vpn
    direct = frame[frame["mode"] == "direct"]
    vpn = frame[frame["mode"] == "vpn"]
    metrics, preds = run_scenario("direct_to_vpn", direct, vpn, holdout_apps=[],
                                  random_state=args.random_state)
    summary.append(metrics)
    all_predictions.append(preds)
    preds.to_csv(out_dir / "predictions_direct_to_vpn.csv", index=False)
    plot_confusion(preds, plots_dir / "confusion_direct_to_vpn.png",
                   "Application-as-identity: train direct, test VPN")
    plot_per_app_accuracy(preds, plots_dir / "per_app_accuracy_direct_to_vpn.png")

    # Scenario 2: mixed (stratified on app x mode)
    rng = np.random.default_rng(args.random_state)
    test_mask = np.zeros(len(frame), dtype=bool)
    for (_, _), idx in frame.groupby(["app_id", "mode"]).groups.items():
        n_test = max(1, int(round(len(idx) * 0.25)))
        chosen = rng.choice(np.array(idx), size=n_test, replace=False)
        test_mask[frame.index.get_indexer(chosen)] = True
    train_df_mixed = frame[~test_mask]
    test_df_mixed = frame[test_mask]
    metrics, preds = run_scenario("mixed", train_df_mixed, test_df_mixed, holdout_apps=[],
                                  random_state=args.random_state)
    summary.append(metrics)
    all_predictions.append(preds)
    preds.to_csv(out_dir / "predictions_mixed.csv", index=False)
    plot_confusion(preds, plots_dir / "confusion_mixed.png",
                   "Application-as-identity: mixed direct+VPN")

    # Scenario 3: open_set — hide one app from training
    holdout = [args.holdout_app.upper()]
    train_df_os = frame[(frame["mode"] == "direct") & (~frame["app_id"].isin(holdout))]
    test_df_os = frame[frame["mode"] == "vpn"]
    metrics, preds = run_scenario("open_set", train_df_os, test_df_os, holdout_apps=holdout,
                                  random_state=args.random_state)
    summary.append(metrics)
    all_predictions.append(preds)
    preds.to_csv(out_dir / "predictions_open_set.csv", index=False)
    plot_confusion(preds, plots_dir / "confusion_open_set.png",
                   f"Open-set: {holdout[0]} unseen during training")

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(out_dir / "metrics_summary.csv", index=False)
    with (out_dir / "metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    disclaimer = (
        "PROXY EXPERIMENT.\n"
        "ISCX-VPN-NonVPN-2016 has no user_id, so this run substitutes the\n"
        "application class (BROWSING, VOIP, CHAT, ...) for user identity.\n"
        "It tests the SAME hypothesis the user-ID task tests --- whether\n"
        "time-based flow features preserve behavioral identity through a\n"
        "VPN tunnel --- but the identities are application behaviors, not\n"
        "individual users. Do not present these numbers as user-level\n"
        "identification accuracy.\n"
    )
    (out_dir / "DISCLAIMER.txt").write_text(disclaimer, encoding="utf-8")

    print("\n=== Proxy experiment summary ===")
    print(summary_df.to_string(index=False))
    print(f"\nArtifacts saved to {out_dir}")


if __name__ == "__main__":
    main()
