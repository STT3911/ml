from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    roc_auc_score,
    roc_curve,
)

from .features import select_feature_columns
from .modeling import HybridUserIdentifier
from .types import PipelineConfig


def top_k_accuracy(y_true: pd.Series, topk: Iterable[list[str]], k: int = 3) -> float:
    pairs = zip(y_true.astype(str).tolist(), list(topk))
    hits = [truth in predictions[:k] for truth, predictions in pairs]
    return float(np.mean(hits)) if hits else 0.0


def compute_eer(y_true_binary: np.ndarray, scores: np.ndarray) -> float | None:
    if len(np.unique(y_true_binary)) < 2:
        return None
    fpr, tpr, _ = roc_curve(y_true_binary, scores)
    fnr = 1.0 - tpr
    idx = int(np.argmin(np.abs(fpr - fnr)))
    return float((fpr[idx] + fnr[idx]) / 2.0)


def compute_far_frr(y_true_binary: np.ndarray, scores: np.ndarray, threshold: float) -> tuple[float | None, float | None]:
    if len(y_true_binary) == 0:
        return None, None
    predicted_unknown = scores >= threshold
    far = float(np.mean(~predicted_unknown[y_true_binary == 1])) if np.any(y_true_binary == 1) else None
    frr = float(np.mean(predicted_unknown[y_true_binary == 0])) if np.any(y_true_binary == 0) else None
    return far, frr


def _plot_confusion_matrix(
    y_true: pd.Series,
    y_pred: pd.Series,
    output_path: Path,
    title: str,
) -> None:
    labels = sorted(set(y_true.astype(str)).union(set(y_pred.astype(str))))
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_roc_curve(y_true_binary: np.ndarray, scores: np.ndarray, output_path: Path, title: str) -> None:
    if len(np.unique(y_true_binary)) < 2:
        return
    fpr, tpr, _ = roc_curve(y_true_binary, scores)
    auc = roc_auc_score(y_true_binary, scores)
    plt.figure(figsize=(6, 6))
    plt.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_quality_drop(results: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(7, 5))
    sns.barplot(data=results, x="scenario", y="accuracy", hue="scenario", palette="viridis", legend=False)
    plt.ylabel("Accuracy")
    plt.xlabel("Scenario")
    plt.title("Quality across scenarios")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def evaluate_predictions(
    predictions: pd.DataFrame,
    scenario_name: str,
    unknown_threshold: float,
) -> dict[str, float | int | None]:
    y_true = predictions["true_user_id"].astype(str)
    y_pred = predictions["pred_user_id"].astype(str)
    known_mask = y_true != "unknown"
    known_predictions = predictions.loc[known_mask]

    metrics: dict[str, float | int | None] = {
        "scenario": scenario_name,
        "num_samples": int(len(predictions)),
        "num_known_samples": int(known_mask.sum()),
        "num_unknown_samples": int((~known_mask).sum()),
    }

    if not known_predictions.empty:
        metrics["accuracy"] = float(
            accuracy_score(known_predictions["true_user_id"], known_predictions["pred_user_id"])
        )
        metrics["macro_f1"] = float(
            f1_score(
                known_predictions["true_user_id"],
                known_predictions["pred_user_id"],
                average="macro",
                zero_division=0,
            )
        )
        metrics["top3_accuracy"] = top_k_accuracy(
            known_predictions["true_user_id"],
            known_predictions["top3_candidates"],
            k=3,
        )
    else:
        metrics["accuracy"] = None
        metrics["macro_f1"] = None
        metrics["top3_accuracy"] = None

    binary_unknown = (y_true == "unknown").astype(int).to_numpy()
    risk_scores = predictions["final_risk_score"].to_numpy()
    if len(np.unique(binary_unknown)) >= 2:
        metrics["roc_auc"] = float(roc_auc_score(binary_unknown, risk_scores))
        metrics["eer"] = compute_eer(binary_unknown, risk_scores)
        far, frr = compute_far_frr(binary_unknown, risk_scores, threshold=unknown_threshold)
        metrics["far"] = far
        metrics["frr"] = frr
    else:
        metrics["roc_auc"] = None
        metrics["eer"] = None
        metrics["far"] = None
        metrics["frr"] = None

    return metrics


def run_experiment(
    session_features: pd.DataFrame,
    scenario_name: str,
    train_modes: list[str],
    test_modes: list[str],
    config: PipelineConfig,
    holdout_users: list[str] | None = None,
) -> tuple[dict[str, float | int | None], pd.DataFrame]:
    data = session_features.copy()
    holdout_users = [str(user) for user in (holdout_users or [])]
    feature_columns = select_feature_columns(data)

    train_mask = data["mode"].isin(train_modes)
    test_mask = data["mode"].isin(test_modes)

    if holdout_users:
        train_mask &= ~data["user_id"].astype(str).isin(holdout_users)

    train_df = data.loc[train_mask].copy()
    test_df = data.loc[test_mask].copy()
    if train_df.empty or test_df.empty:
        raise ValueError(f"Scenario '{scenario_name}' has empty train or test split.")

    X_train = train_df[feature_columns]
    y_train = train_df["user_id"].astype(str)
    X_test = test_df[feature_columns]
    y_test = test_df["user_id"].astype(str).copy()
    y_test.loc[y_test.isin(holdout_users)] = "unknown"

    model = HybridUserIdentifier(
        classifier_name=config.classifier_name,
        alpha=config.alpha,
        confidence_threshold=config.confidence_threshold,
        unknown_threshold=config.unknown_threshold,
        random_state=config.random_state,
    )
    model.fit(X_train, y_train)
    predictions = model.predict_with_details(X_test, true_users=y_test)
    predictions["mode"] = test_df["mode"].values
    predictions["session_id"] = test_df["session_id"].values
    predictions["scenario"] = scenario_name
    predictions["is_unknown_true"] = predictions["true_user_id"].eq("unknown")
    predictions["is_unknown_pred"] = predictions["pred_user_id"].eq("unknown")

    metrics = evaluate_predictions(
        predictions=predictions,
        scenario_name=scenario_name,
        unknown_threshold=config.unknown_threshold,
    )
    return metrics, predictions


def run_all_experiments(
    session_features: pd.DataFrame,
    output_dir: str | Path,
    config: PipelineConfig | None = None,
) -> dict[str, dict[str, float | int | None]]:
    config = config or PipelineConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    users = sorted(session_features["user_id"].astype(str).unique().tolist())
    holdout_count = max(1, len(users) // 5)
    holdout_users = users[-holdout_count:]
    available_modes = {mode.lower() for mode in session_features["mode"].astype(str).unique()}
    known_modes = [mode for mode in ["direct", "vpn", "proxy"] if mode in available_modes]
    tunneled_modes = [mode for mode in ["vpn", "proxy"] if mode in available_modes]

    scenarios = [
        ("direct_to_tunneled", ["direct"], tunneled_modes),
        ("mixed", known_modes, known_modes),
        ("open_set", known_modes, known_modes),
    ]

    metrics_bundle: dict[str, dict[str, float | int | None]] = {}
    summary_rows: list[dict[str, float | int | None]] = []

    for scenario_name, train_modes, test_modes in scenarios:
        if not train_modes or not test_modes:
            continue
        current_holdout = holdout_users if scenario_name == "open_set" else None
        metrics, predictions = run_experiment(
            session_features=session_features,
            scenario_name=scenario_name,
            train_modes=train_modes,
            test_modes=test_modes,
            config=config,
            holdout_users=current_holdout,
        )
        metrics_bundle[scenario_name] = metrics
        summary_rows.append(metrics)

        predictions_path = output_dir / f"predictions_{scenario_name}.csv"
        predictions.to_csv(predictions_path, index=False)

        _plot_confusion_matrix(
            y_true=predictions["true_user_id"],
            y_pred=predictions["pred_user_id"],
            output_path=plots_dir / f"confusion_{scenario_name}.png",
            title=f"Confusion Matrix: {scenario_name}",
        )
        _plot_roc_curve(
            y_true_binary=predictions["is_unknown_true"].astype(int).to_numpy(),
            scores=predictions["final_risk_score"].to_numpy(),
            output_path=plots_dir / f"roc_{scenario_name}.png",
            title=f"ROC Curve: {scenario_name}",
        )

    summary = pd.DataFrame(summary_rows)
    _plot_quality_drop(summary.fillna(0.0), plots_dir / "quality_summary.png")
    summary.to_csv(output_dir / "metrics_summary.csv", index=False)

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics_bundle, handle, indent=2)

    return metrics_bundle
