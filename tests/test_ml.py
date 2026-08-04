from pathlib import Path

from dex_trades.ml.classifier import train_noise_classifier
from dex_trades.ml.compare import write_report
from dex_trades.ml.dataset import (
    FEATURE_COLUMNS,
    build_feature_frame,
    expand_synthetic_rows,
    load_trade_rows,
)

FIXTURE = Path(__file__).parent / "fixtures" / "golden_trades.json"


def test_feature_columns_and_labels():
    rows = expand_synthetic_rows(load_trade_rows(FIXTURE), n_extra=40, seed=0)
    frame = build_feature_frame(rows)
    assert set(FEATURE_COLUMNS).issubset(frame.columns)
    assert frame["is_noisy"].nunique() == 2
    assert len(frame) > 40


def test_classifier_recovers_rubric_on_holdout(tmp_path):
    rows = expand_synthetic_rows(load_trade_rows(FIXTURE), n_extra=80, seed=42)
    frame = build_feature_frame(rows)
    model = train_noise_classifier(frame, seed=42)
    assert model.metrics["f1_noisy"] >= 0.75
    assert model.metrics["accuracy"] >= 0.75
    report = {
        "generated_at": "test",
        "source": str(FIXTURE),
        "n_rows_augmented": len(frame),
        "metrics": model.metrics,
        "caveats": ["unit test"],
    }
    out = write_report(report, artifacts_dir=tmp_path)
    assert out.exists()
    assert "DEX trades ML label report" in out.read_text(encoding="utf-8")


def test_orderflow_classifier_holdout(tmp_path):
    rows = expand_synthetic_rows(load_trade_rows(FIXTURE), n_extra=80, seed=7)
    frame = build_feature_frame(rows)
    model = train_noise_classifier(frame, seed=7, label="is_orderflow_interesting")
    assert model.metrics["f1_noisy"] >= 0.7
    out = write_report(
        {
            "generated_at": "test",
            "source": str(FIXTURE),
            "n_rows_augmented": len(frame),
            "metrics": model.metrics,
            "caveats": ["orderflow proxy labels"],
        },
        artifacts_dir=tmp_path,
        stem="ml_orderflow_report",
    )
    assert out.name == "ml_orderflow_report.md"
