"""Atomic orderflow study: noise filters vs structural orderflow proxies."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dex_trades.evals.labels import annotate_rows
from dex_trades.ml.dataset import expand_synthetic_rows, load_trade_rows
from dex_trades.settings import PROJECT_ROOT


def summarize_orderflow(rows: list[dict]) -> dict[str, Any]:
    annotated = annotate_rows(rows)
    n = len(annotated)

    def rate(key: str) -> float:
        return round(sum(1 for r in annotated if r.get(key)) / n, 4) if n else 0.0

    def vol(pred) -> float:
        return float(sum(float(r.get("volume_quote_stable") or 0.0) for r in annotated if pred(r)))

    total_vol = vol(lambda _r: True)
    clean_vol = vol(lambda r: r.get("is_clean"))
    interesting_vol = vol(lambda r: r.get("is_orderflow_interesting"))
    sandwich_vol = vol(lambda r: r.get("is_potential_sandwich_leg"))

    return {
        "trades": n,
        "rates": {
            "dust": rate("is_dust"),
            "self_churn": rate("is_self_churn"),
            "clean": rate("is_clean"),
            "multi_swap_tx": rate("is_multi_swap_tx"),
            "same_block_pool_burst": rate("is_same_block_pool_burst"),
            "potential_sandwich_leg": rate("is_potential_sandwich_leg"),
            "orderflow_interesting": rate("is_orderflow_interesting"),
        },
        "volume": {
            "total_quote_stable": round(total_vol, 4),
            "clean_quote_stable": round(clean_vol, 4),
            "interesting_quote_stable": round(interesting_vol, 4),
            "sandwich_proxy_quote_stable": round(sandwich_vol, 4),
            "interesting_share_of_volume": (
                round(interesting_vol / total_vol, 4) if total_vol else 0.0
            ),
            "clean_share_of_volume": round(clean_vol / total_vol, 4) if total_vol else 0.0,
        },
    }


def build_orderflow_report(
    *,
    fixture: Path,
    seed: int = 42,
    augment: bool = True,
) -> dict[str, Any]:
    base = load_trade_rows(fixture)
    rows = expand_synthetic_rows(base, seed=seed) if augment else list(base)
    # Ensure synthetic rows have block/log for sandwich heuristics when missing.
    for i, r in enumerate(rows):
        r.setdefault("block_number", 10_000 + i)
        r.setdefault("log_index", 1)
    summary = summarize_orderflow(rows)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(fixture),
        "augmented": augment,
        "hypothesis": (
            "Multi-swap and sandwich-proxy structure inflates total volume beyond what "
            "dust/self-churn filters remove; noise labels alone understate toxic orderflow."
        ),
        "method": (
            "Annotate swaps with auditable proxies (multi-swap tx, same-block pool burst, "
            "A→B→A sandwich-leg heuristic) and compare volume shares vs clean filters."
        ),
        "evidence": summary,
        "limitations": [
            "No mempool, relay bids, or timing data — proxies are not sandwich proof.",
            "fee_recipient (when enriched) is a PBS/builder address proxy, not bundle proof.",
            "Routers and aggregators can produce multi-swap patterns without MEV.",
            "Fixture + synthetic augmentation is for methodology demo, not mainnet incidence.",
        ],
        "product_implications": [
            "Analytics layer: expose retained orderflow flags so customers can filter "
            "interesting vs clean volume separately.",
            "PBS join: fee_recipient lets you ask whether interesting flow concentrates "
            "under certain builders (see make enrich-blocks + Evidence orderflow page).",
            "Networking product angle: the next measurements that matter are inclusion delay "
            "and propagation asymmetry for contended pool/block flow — not just trade counts.",
            "Next: relay catalogs, mempool arrival vs on-chain inclusion, Xatu-style latency.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Orderflow / MEV-lite research report",
        "",
        f"Generated: `{report.get('generated_at')}`",
        f"Source: `{report.get('source')}`",
        "",
        "## Hypothesis",
        "",
        str(report.get("hypothesis", "")),
        "",
        "## Method",
        "",
        str(report.get("method", "")),
        "",
        "## Evidence",
        "",
        "```json",
        json.dumps(report.get("evidence", {}), indent=2),
        "```",
        "",
        "## Limitations",
        "",
    ]
    for item in report.get("limitations", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Product implications", ""])
    for item in report.get("product_implications", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_orderflow_report(
    report: dict[str, Any],
    *,
    artifacts_dir: Path | None = None,
) -> Path:
    out_dir = artifacts_dir or (PROJECT_ROOT / "artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "research_orderflow.md"
    json_path = out_dir / "research_orderflow.json"
    md_path.write_text(render_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return md_path
