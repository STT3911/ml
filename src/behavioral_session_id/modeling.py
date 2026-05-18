from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

try:
    from catboost import CatBoostClassifier
except ImportError:  # pragma: no cover - optional dependency
    CatBoostClassifier = None


@dataclass
class _UserAnomalyModel:
    scaler: StandardScaler
    detector: IsolationForest
    q05: float
    q95: float


class HybridUserIdentifier:
    def __init__(
        self,
        classifier_name: str = "catboost",
        alpha: float = 0.5,
        confidence_threshold: float = 0.45,
        unknown_threshold: float = 0.60,
        random_state: int = 42,
        classifier_params: dict | None = None,
        anomaly_params: dict | None = None,
    ) -> None:
        self.classifier_name = classifier_name
        self.alpha = alpha
        self.confidence_threshold = confidence_threshold
        self.unknown_threshold = unknown_threshold
        self.random_state = random_state
        self.classifier_params = classifier_params or {}
        self.anomaly_params = anomaly_params or {}
        self.classifier = None
        self.feature_columns: list[str] = []
        self.user_models: dict[str, _UserAnomalyModel] = {}

    def _build_classifier(self):
        if self.classifier_name == "catboost" and CatBoostClassifier is not None:
            default_params = {
                "iterations": 300,
                "depth": 6,
                "learning_rate": 0.05,
                "loss_function": "MultiClass",
                "verbose": False,
                "random_seed": self.random_state,
            }
            default_params.update(self.classifier_params)
            return CatBoostClassifier(**default_params)

        default_params = {
            "n_estimators": 300,
            "max_depth": 12,
            "min_samples_leaf": 2,
            "random_state": self.random_state,
            "class_weight": "balanced",
        }
        default_params.update(self.classifier_params)
        return RandomForestClassifier(**default_params)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "HybridUserIdentifier":
        self.feature_columns = list(X.columns)
        self.classifier = self._build_classifier()
        self.classifier.fit(X, y)

        default_anomaly_params = {
            "n_estimators": 200,
            "contamination": "auto",
            "random_state": self.random_state,
        }
        default_anomaly_params.update(self.anomaly_params)

        self.user_models = {}
        for user_id in sorted(pd.Series(y).astype(str).unique()):
            user_mask = pd.Series(y).astype(str) == user_id
            user_X = X.loc[user_mask]
            if len(user_X) < 3:
                continue

            scaler = StandardScaler()
            scaled = scaler.fit_transform(user_X)
            detector = IsolationForest(**default_anomaly_params)
            detector.fit(scaled)
            scores = detector.decision_function(scaled)
            q05 = float(np.quantile(scores, 0.05))
            q95 = float(np.quantile(scores, 0.95))
            self.user_models[user_id] = _UserAnomalyModel(
                scaler=scaler,
                detector=detector,
                q05=q05,
                q95=q95,
            )

        return self

    def _batch_anomaly_scores(self, predicted_users: np.ndarray, X: pd.DataFrame) -> np.ndarray:
        scores = np.ones(len(predicted_users), dtype=float)
        predicted_series = pd.Series(predicted_users, index=X.index, name="predicted_user")
        for user_id, indices in predicted_series.groupby(predicted_series).groups.items():
            model = self.user_models.get(str(user_id))
            if model is None:
                continue
            subset = X.loc[indices]
            scaled = model.scaler.transform(subset)
            raw_scores = model.detector.decision_function(scaled)
            denom = model.q95 - model.q05
            if denom:
                normalized = 1.0 - (raw_scores - model.q05) / denom
            else:
                normalized = np.zeros_like(raw_scores)
            position = X.index.get_indexer(indices)
            scores[position] = np.clip(normalized, 0.0, 1.0)
        return scores

    def predict_with_details(self, X: pd.DataFrame, true_users: pd.Series | None = None) -> pd.DataFrame:
        if self.classifier is None:
            raise RuntimeError("Model must be fitted before calling predict.")

        probabilities = self.classifier.predict_proba(X)
        class_labels = np.array(self.classifier.classes_).astype(str)
        top_indices = np.argsort(probabilities, axis=1)[:, ::-1]

        top_labels = class_labels[top_indices[:, :3]]
        predicted_users = top_labels[:, 0]
        confidences = probabilities[np.arange(len(X)), top_indices[:, 0]]

        anomaly_scores = self._batch_anomaly_scores(predicted_users, X)
        final_risks = self.alpha * (1.0 - confidences) + (1.0 - self.alpha) * anomaly_scores
        final_risks = np.clip(final_risks, 0.0, 1.0)

        unknown_mask = (confidences < self.confidence_threshold) | (anomaly_scores > self.unknown_threshold)
        final_labels = np.where(unknown_mask, "unknown", predicted_users)

        true_series = (
            true_users.astype(str).reindex(X.index).fillna("").to_numpy()
            if true_users is not None
            else np.full(len(X), "", dtype=object)
        )

        return pd.DataFrame(
            {
                "pred_user_id": final_labels,
                "predicted_known_user": predicted_users,
                "confidence": confidences,
                "anomaly_score": anomaly_scores,
                "final_risk_score": final_risks,
                "top3_candidates": [list(row) for row in top_labels],
                "true_user_id": true_series,
            },
            index=X.index,
        )
