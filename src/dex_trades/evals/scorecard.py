"""QC scorecard for DEX trade quality labels and their impact on volume metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from dex_trades.evals.labels import annotate_rows
from dex_trades.settings import PROJECT_ROOT


@dataclass
class Scorecard:
    generated_at: str
    source: str
    label_distribution: dict[str, Any] = field(default_factory=dict)
    volume_impact: dict[str, Any] = field(default_factory=dict)
    threshold_sweep: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "source": self.source,
            "label_distribution": self.label_distribution,
            "volume_impact": self.volume_impact,
            "threshold_sweep": self.threshold_sweep,
            "caveats": self.caveats,
        }


def label_distribution(rows: list[dict]) -> dict[str, Any]:
    n = len(rows)
    dust = sum(1 for r in rows if r.get("is_dust"))
    churn = sum(1 for r in rows if r.get("is_self_churn"))
    clean = sum(1 for r in rows if r.get("is_clean"))
    return {
        "trades": n,
        "dust": dust,
        "self_churn": churn,
        "clean": clean,
        "dust_rate": round(dust / n, 4) if n else 0.0,
        "self_churn_rate": round(churn / n, 4) if n else 0.0,
        "clean_rate": round(clean / n, 4) if n else 0.0,
    }


def volume_impact(rows: list[dict]) -> dict[str, Any]:
    def vol(rs: list[dict]) -> float:
        return float(sum(float(r.get("volume_quote_stable") or 0.0) for r in rs))

    total = vol(rows)
    clean = vol([r for r in rows if r.get("is_clean")])
    noisy = total - clean
    return {
        "total_volume_quote_stable": round(total, 6),
        "clean_volume_quote_stable": round(clean, 6),
        "noisy_volume_quote_stable": round(noisy, 6),
        "noise_share_of_volume": round(noisy / total, 4) if total else 0.0,
    }


def threshold_sweep(
    rows: list[dict],
    thresholds: list[float] | None = None,
    *,
    dust_token: float = 1e-6,
) -> list[dict[str, Any]]:
    """How dust threshold choice moves clean rate and clean volume (benchmark slice)."""
    thresholds = thresholds or [0.1, 0.5, 1.0, 5.0, 10.0]
    results = []
    for thr in thresholds:
        annotated = annotate_rows(rows, dust_token=dust_token, dust_usdc=thr)
        dist = label_distribution(annotated)
        impact = volume_impact(annotated)
        results.append(
            {
                "dust_usdc_threshold": thr,
                "clean_rate": dist["clean_rate"],
                "dust_rate": dist["dust_rate"],
                "clean_volume_quote_stable": impact["clean_volume_quote_stable"],
                "noise_share_of_volume": impact["noise_share_of_volume"],
            }
        )
    return results


def load_fixture_rows(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected list of trades in {path}")
    return payload


def load_warehouse_rows(duckdb_path: Path) -> list[dict] | None:
    if not duckdb_path.exists():
        return None
    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        tables = {r[0] for r in con.execute("show tables").fetchall()}
        table = "int_dex_trades" if "int_dex_trades" in tables else None
        if table is None and "mart_dex_trades" in tables:
            table = "mart_dex_trades"
        if table is None:
            return None
        cols = [
            "amount_sold",
            "amount_bought",
            "volume_quote_stable",
            "is_dust",
            "is_self_churn",
            "is_clean",
            "tx_hash",
            "pool_address",
            "trader",
            "direction",
        ]
        # Some columns may be missing on older snapshots — select available ones.
        present = {r[0] for r in con.execute(f"describe {table}").fetchall()}
        select_cols = [c for c in cols if c in present]
        if "is_clean" not in select_cols:
            return None
        frame = con.execute(f"select {', '.join(select_cols)} from {table}").fetchdf()
        return frame.to_dict(orient="records")
    finally:
        con.close()


def build_scorecard_from_rows(
    rows: list[dict],
    *,
    source: str,
    already_labeled: bool = False,
    dust_usdc: float = 1.0,
) -> Scorecard:
    base_rows = rows if already_labeled else annotate_rows(rows, dust_usdc=dust_usdc)
    # For threshold sweep, strip labels and re-annotate from raw fields.
    raw_for_sweep = [
        {
            "amount_sold": r.get("amount_sold", 0.0),
            "amount_bought": r.get("amount_bought", 0.0),
            "volume_quote_stable": r.get("volume_quote_stable"),
            "quote_is_stable": r.get("quote_is_stable", True),
            "tx_hash": r.get("tx_hash", ""),
            "pool_address": r.get("pool_address", ""),
            "trader": r.get("trader", ""),
            "direction": r.get("direction", ""),
        }
        for r in rows
    ]
    caveats: list[str] = []
    impact = volume_impact(base_rows)
    if impact["noise_share_of_volume"] > 0.5:
        caveats.append(
            "Noise share of volume > 50%: total volume is a poor proxy for economic "
            "activity — prefer clean aggregates."
        )
    sweep = threshold_sweep(raw_for_sweep)
    if len({row["clean_rate"] for row in sweep}) == 1:
        caveats.append(
            "Dust threshold sweep did not change clean_rate on this sample — "
            "fixture may lack borderline dust trades."
        )

    return Scorecard(
        generated_at=datetime.now(UTC).isoformat(),
        source=source,
        label_distribution=label_distribution(base_rows),
        volume_impact=impact,
        threshold_sweep=sweep,
        caveats=caveats,
    )


def render_markdown(scorecard: Scorecard) -> str:
    lines = [
        "# DEX trades QC scorecard",
        "",
        f"Generated: `{scorecard.generated_at}`",
        f"Source: `{scorecard.source}`",
        "",
        "## Label distribution",
        "",
        "```json",
        json.dumps(scorecard.label_distribution, indent=2),
        "```",
        "",
        "## Clean vs total volume impact",
        "",
        "```json",
        json.dumps(scorecard.volume_impact, indent=2),
        "```",
        "",
        "## Dust threshold sensitivity",
        "",
        "| dust_usdc_threshold | clean_rate | dust_rate | clean_volume | noise_share |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in scorecard.threshold_sweep:
        lines.append(
            f"| {row['dust_usdc_threshold']} | {row['clean_rate']} | {row['dust_rate']} | "
            f"{row['clean_volume_quote_stable']} | {row['noise_share_of_volume']} |"
        )
    lines.extend(["", "## Caveats", ""])
    if scorecard.caveats:
        lines.extend(f"- {c}" for c in scorecard.caveats)
    else:
        lines.append("- None recorded.")
    lines.append("")
    return "\n".join(lines)


def write_scorecard(
    scorecard: Scorecard,
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "qc_scorecard.md"
    json_path = out_dir / "qc_scorecard.json"
    md_path.write_text(render_markdown(scorecard), encoding="utf-8")
    json_path.write_text(json.dumps(scorecard.to_dict(), indent=2) + "\n", encoding="utf-8")
    return md_path
