"""Compare learned noise predictions to the rule rubric."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from dex_trades.settings import PROJECT_ROOT


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_noisy": round(
            float(precision_score(y_true, y_pred, pos_label=1, zero_division=0.0)), 4
        ),
        "recall_noisy": round(
            float(recall_score(y_true, y_pred, pos_label=1, zero_division=0.0)), 4
        ),
        "f1_noisy": round(float(f1_score(y_true, y_pred, pos_label=1, zero_division=0.0)), 4),
        "confusion_matrix_labels_[clean,noisy]": cm,
    }


def compare_to_rubric(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Agreement between model predictions and rubric weak labels on a holdout."""
    metrics = classification_metrics(y_true, y_pred)
    n = len(y_true)
    disagree = int(np.sum(y_true != y_pred))
    metrics["disagreement_count"] = disagree
    metrics["disagreement_rate"] = round(disagree / n, 4) if n else 0.0
    metrics["note"] = (
        "Labels are weak labels from the auditable rule rubric; high agreement means "
        "the model recovers the rubric, not independent human truth."
    )
    return metrics


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DEX trades ML label report",
        "",
        "Rubric-vs-model eval: logistic regression trained on weak labels from the "
        "auditable dust/self-churn rubric.",
        "",
        "## Holdout metrics",
        "",
        "```json",
        json.dumps(report.get("metrics", {}), indent=2),
        "```",
        "",
        "## Caveats",
        "",
    ]
    for c in report.get("caveats", []):
        lines.append(f"- {c}")
    if not report.get("caveats"):
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: dict[str, Any],
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "ml_label_report.md"
    json_path = out_dir / "ml_label_report.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path
