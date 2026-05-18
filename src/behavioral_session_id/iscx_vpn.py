from __future__ import annotations

import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split


def load_arff_tolerant(path: str | Path) -> pd.DataFrame:
    """Read ISCX ARFF files that contain extra commas and occasional blanks."""
    path = Path(path)
    attributes: list[str] = []
    data_rows: list[str] = []
    in_data = False

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%"):
            continue

        lower = line.lower()
        if lower.startswith("@attribute"):
            parts = line.split()
            if len(parts) < 2:
                continue
            attributes.append(parts[1].strip("'\""))
        elif lower.startswith("@data"):
            in_data = True
        elif in_data:
            data_rows.append(line)

    if not attributes:
        raise ValueError(f"No ARFF attributes found in {path}")
    if not data_rows:
        raise ValueError(f"No ARFF data rows found in {path}")

    frame = pd.read_csv(
        io.StringIO("\n".join(data_rows)),
        header=None,
        names=attributes,
        na_values=["", "?"],
        engine="python",
    )
    frame["source_file"] = path.name
    return frame


def prepare_vpn_dataset(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    data = frame.copy()
    if "class1" not in data.columns:
        raise ValueError("Expected ARFF label column 'class1'.")

    labels = data["class1"].astype(str)
    vpn_target = labels.str.startswith("VPN-").map({True: "vpn", False: "non_vpn"})
    app_target = labels.str.replace("VPN-", "", regex=False)

    feature_columns = [column for column in data.columns if column not in {"class1", "source_file"}]
    features = data[feature_columns].apply(pd.to_numeric, errors="coerce")
    features = features.replace([float("inf"), float("-inf")], pd.NA)
    return features, vpn_target, app_target


def impute_with_reference(features: pd.DataFrame, reference_medians: pd.Series) -> pd.DataFrame:
    aligned = reference_medians.reindex(features.columns)
    return features.fillna(aligned).fillna(0.0)


def prepare_features_for_model(
    frame: pd.DataFrame,
    feature_columns: list[str],
    reference_medians: pd.Series | None = None,
) -> pd.DataFrame:
    data = frame.copy()
    features = data.reindex(columns=feature_columns)
    features = features.apply(pd.to_numeric, errors="coerce")
    features = features.replace([float("inf"), float("-inf")], pd.NA)
    if reference_medians is None:
        reference_medians = features.median(numeric_only=True)
    return impute_with_reference(features, reference_medians)


def _plot_confusion(y_true: pd.Series, y_pred: pd.Series, output_path: Path, title: str) -> None:
    labels = sorted(set(y_true.astype(str)).union(set(y_pred.astype(str))))
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(6, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels)
    plt.title(title)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_class_distribution(labels: pd.Series, output_path: Path, title: str) -> None:
    counts = labels.value_counts().rename_axis("label").reset_index(name="count")
    plt.figure(figsize=(8, 5))
    sns.barplot(data=counts, x="label", y="count", hue="label", palette="viridis", legend=False)
    plt.title(title)
    plt.xlabel("Class")
    plt.ylabel("Count")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_feature_importance(importance: pd.DataFrame, output_path: Path, top_n: int = 15) -> None:
    top = importance.head(top_n).sort_values("importance", ascending=True)
    plt.figure(figsize=(8, 6))
    sns.barplot(data=top, x="importance", y="feature", hue="feature", palette="mako", legend=False)
    plt.title(f"Top {top_n} Feature Importances")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_probability_distribution(y_true: pd.Series, scores: pd.Series, output_path: Path) -> None:
    plot_data = pd.DataFrame({"true_label": y_true.astype(str), "vpn_probability": scores.astype(float)})
    plt.figure(figsize=(8, 5))
    sns.histplot(
        data=plot_data,
        x="vpn_probability",
        hue="true_label",
        bins=30,
        stat="density",
        common_norm=False,
        element="step",
    )
    plt.title("Predicted VPN Probability Distribution")
    plt.xlabel("P(VPN)")
    plt.ylabel("Density")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_precision_recall(y_true: pd.Series, scores: pd.Series, output_path: Path) -> float:
    y_binary = y_true.eq("vpn").astype(int)
    precision, recall, _ = precision_recall_curve(y_binary, scores)
    average_precision = float(average_precision_score(y_binary, scores))
    plt.figure(figsize=(6, 6))
    plt.plot(recall, precision, label=f"AP = {average_precision:.3f}")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("VPN Detection Precision-Recall")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()
    return average_precision


def _plot_error_by_application(
    app_target: pd.Series,
    y_true: pd.Series,
    y_pred: pd.Series,
    output_path: Path,
) -> None:
    data = pd.DataFrame(
        {
            "application": app_target.astype(str),
            "true_label": y_true.astype(str),
            "correct": y_true.astype(str).eq(y_pred.astype(str)),
        }
    )
    rates = (
        data.groupby(["application", "true_label"], as_index=False)["correct"]
        .mean()
        .assign(error_rate=lambda frame: 1.0 - frame["correct"])
    )
    pivot = rates.pivot(index="application", columns="true_label", values="error_rate").fillna(0.0)
    plt.figure(figsize=(7, 5))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="Reds", vmin=0.0, vmax=max(0.1, float(pivot.max().max())))
    plt.title("Error Rate by Application")
    plt.xlabel("Traffic mode")
    plt.ylabel("Application")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_correlation_heatmap(features: pd.DataFrame, output_path: Path, max_features: int = 15) -> None:
    variances = features.var(numeric_only=True).sort_values(ascending=False)
    selected = variances.head(max_features).index.tolist()
    if len(selected) < 2:
        return
    corr = features[selected].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr, cmap="coolwarm", center=0.0, square=True)
    plt.title("Correlation Heatmap of High-Variance Features")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def _plot_roc(y_true: pd.Series, scores: pd.Series, output_path: Path) -> float:
    y_binary = y_true.eq("vpn").astype(int)
    auc = float(roc_auc_score(y_binary, scores))
    fpr, tpr, _ = roc_curve(y_binary, scores)

    plt.figure(figsize=(6, 6))
    plt.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("VPN Detection ROC")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()
    return auc


def plot_metrics_comparison(summary: pd.DataFrame, output_path: str | Path) -> None:
    output_path = Path(output_path)
    plot_data = summary.copy()
    plot_data["window"] = plot_data["dataset"].str.extract(r"Dataset-(.*)\.arff", expand=False)
    melted = plot_data.melt(
        id_vars=["window"],
        value_vars=["accuracy", "macro_f1", "vpn_precision", "vpn_recall", "roc_auc"],
        var_name="metric",
        value_name="value",
    )
    plt.figure(figsize=(9, 5))
    sns.lineplot(data=melted, x="window", y="value", hue="metric", marker="o")
    plt.ylim(0.84, 1.0)
    plt.title("VPN Detection Metrics by Time Window")
    plt.xlabel("Time window")
    plt.ylabel("Metric value")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def train_vpn_classifier(
    input_arff: str | Path,
    output_dir: str | Path,
    random_state: int = 42,
    test_size: float = 0.25,
) -> dict[str, float | int | str]:
    input_arff = Path(input_arff)
    output_dir = Path(output_dir)
    plots_dir = output_dir / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    raw = load_arff_tolerant(input_arff)
    features, vpn_target, app_target = prepare_vpn_dataset(raw)
    _plot_class_distribution(raw["class1"].astype(str), plots_dir / "class_distribution.png", "Raw Class Distribution")
    _plot_class_distribution(vpn_target, plots_dir / "vpn_distribution.png", "VPN / Non-VPN Distribution")

    split = train_test_split(
        features,
        vpn_target,
        app_target,
        test_size=test_size,
        random_state=random_state,
        stratify=vpn_target,
    )
    X_train_raw, X_test_raw, y_train, y_test, app_train, app_test = split

    train_medians = X_train_raw.median(numeric_only=True)
    X_train = impute_with_reference(X_train_raw, train_medians)
    X_test = impute_with_reference(X_test_raw, train_medians)

    _plot_correlation_heatmap(X_train, plots_dir / "feature_correlation_heatmap.png")

    model = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=random_state,
        n_jobs=1,
    )
    model.fit(X_train, y_train)

    predictions = pd.Series(model.predict(X_test), index=X_test.index, name="pred_label")
    probabilities = pd.DataFrame(model.predict_proba(X_test), index=X_test.index, columns=model.classes_)
    vpn_scores = probabilities["vpn"] if "vpn" in probabilities.columns else 1.0 - probabilities.iloc[:, 0]

    metrics: dict[str, float | int | str] = {
        "dataset": input_arff.name,
        "num_rows": int(len(raw)),
        "num_features": int(features.shape[1]),
        "num_train": int(len(X_train)),
        "num_test": int(len(X_test)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "macro_f1": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
        "vpn_precision": float(precision_score(y_test, predictions, pos_label="vpn", zero_division=0)),
        "vpn_recall": float(recall_score(y_test, predictions, pos_label="vpn", zero_division=0)),
        "roc_auc": _plot_roc(y_test, vpn_scores, plots_dir / "roc_vpn_detection.png"),
        "average_precision": _plot_precision_recall(y_test, vpn_scores, plots_dir / "precision_recall_vpn.png"),
    }

    _plot_confusion(y_test, predictions, plots_dir / "confusion_vpn_detection.png", "VPN Detection")
    _plot_probability_distribution(y_test, vpn_scores, plots_dir / "vpn_probability_distribution.png")
    _plot_error_by_application(app_test, y_test, predictions, plots_dir / "error_by_application.png")

    report = classification_report(y_test, predictions, zero_division=0, output_dict=True)
    with (output_dir / "classification_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    prediction_rows = pd.DataFrame(
        {
            "true_label": y_test,
            "pred_label": predictions,
            "vpn_probability": vpn_scores,
            "application_label": app_test,
        }
    ).sort_index()
    prediction_rows.to_csv(output_dir / "predictions.csv", index=False)

    importance = pd.DataFrame(
        {
            "feature": features.columns,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance.to_csv(output_dir / "feature_importance.csv", index=False)
    _plot_feature_importance(importance, plots_dir / "feature_importance_top15.png")

    raw.to_csv(output_dir / "converted_arff.csv", index=False)
    dump(
        {
            "model": model,
            "feature_columns": features.columns.tolist(),
            "classes": model.classes_.tolist(),
            "source_dataset": input_arff.name,
            "train_medians": train_medians.to_dict(),
        },
        output_dir / "model.joblib",
    )
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
    pd.DataFrame([metrics]).to_csv(output_dir / "metrics_summary.csv", index=False)
    return metrics
