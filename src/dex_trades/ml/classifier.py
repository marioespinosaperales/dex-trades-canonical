"""Train a noise classifier on weak labels from the auditable rubric."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from dex_trades.ml.dataset import FEATURE_COLUMNS, xy_from_frame


@dataclass(frozen=True)
class TrainedNoiseModel:
    pipeline: Pipeline
    feature_columns: list[str]
    metrics: dict[str, Any]
    y_test: np.ndarray
    y_pred: np.ndarray


def train_noise_classifier(
    frame,
    *,
    seed: int = 42,
    test_size: float = 0.25,
) -> TrainedNoiseModel:
    x, y = xy_from_frame(frame)
    if len(np.unique(y)) < 2:
        raise ValueError("Need both clean and noisy labels to train")

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=seed,
        stratify=y,
    )
    pipeline = Pipeline(
        steps=[
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    random_state=seed,
                    class_weight="balanced",
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    y_pred = pipeline.predict(x_test)
    from dex_trades.ml.compare import classification_metrics

    metrics = classification_metrics(y_test, y_pred)
    metrics["n_train"] = int(len(y_train))
    metrics["n_test"] = int(len(y_test))
    metrics["feature_columns"] = list(FEATURE_COLUMNS)
    return TrainedNoiseModel(
        pipeline=pipeline,
        feature_columns=list(FEATURE_COLUMNS),
        metrics=metrics,
        y_test=y_test,
        y_pred=y_pred,
    )
