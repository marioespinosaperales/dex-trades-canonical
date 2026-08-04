"""CLI: ``uv run python -m dex_trades.ml`` → artifacts/ml_label_report.md

Use ``--target orderflow`` for orderflow_interesting holdout report.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dex_trades.ml.classifier import train_noise_classifier
from dex_trades.ml.compare import compare_to_rubric, write_report
from dex_trades.ml.dataset import build_feature_frame, expand_synthetic_rows, load_trade_rows
from dex_trades.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "golden_trades.json"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="DEX trades rubric-vs-model ML report")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--target",
        choices=("noise", "orderflow"),
        default="noise",
        help="Weak-label target: is_noisy or is_orderflow_interesting",
    )
    args = parser.parse_args(argv)

    if not args.fixture.exists():
        logger.error("Fixture not found: %s", args.fixture)
        return 1

    label = "is_noisy" if args.target == "noise" else "is_orderflow_interesting"
    stem = "ml_label_report" if args.target == "noise" else "ml_orderflow_report"

    base = load_trade_rows(args.fixture)
    rows = expand_synthetic_rows(base, seed=args.seed)
    frame = build_feature_frame(rows)
    model = train_noise_classifier(frame, seed=args.seed, label=label)
    metrics = compare_to_rubric(model.y_test, model.y_pred)
    metrics.update({k: v for k, v in model.metrics.items() if k not in metrics})

    caveats = [
        "ML complements the rule rubric; it does not replace auditable flags.",
        "Training labels are weak labels from the rubric itself (agreement ≠ external truth).",
    ]
    if args.target == "orderflow":
        caveats.append(
            "Orderflow/sandwich flags are structural proxies — not proof of MEV."
        )
    if metrics.get("f1_noisy", 0.0) < 0.7:
        caveats.append("F1 on holdout is below 0.7 — treat model as exploratory.")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(args.fixture),
        "target": label,
        "n_rows_augmented": int(len(frame)),
        "metrics": metrics,
        "caveats": caveats,
    }
    path = write_report(report, stem=stem)
    logger.info(
        "Wrote ML report → %s (target=%s f1=%.3f)",
        path,
        label,
        metrics.get("f1_noisy", 0.0),
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
