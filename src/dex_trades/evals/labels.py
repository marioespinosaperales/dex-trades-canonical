"""Noise-label rubric mirrored from dbt ``int_dex_trades``.

Kept in Python so unit tests and the QC scorecard share one executable rubric.
"""

from __future__ import annotations

from collections import defaultdict


def is_dust(
    amount_sold: float,
    amount_bought: float,
    *,
    volume_quote_stable: float | None,
    quote_is_stable: bool,
    dust_token: float = 1e-6,
    dust_usdc: float = 1.0,
) -> bool:
    """Mirror dbt dust rule."""
    if quote_is_stable and volume_quote_stable is not None and volume_quote_stable < dust_usdc:
        return True
    return amount_sold < dust_token and amount_bought < dust_token


def is_self_churn(rows: list[dict]) -> list[bool]:
    """Mirror dbt self-churn: same tx/pool/trader with reverse directions."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        groups[key].append(r)

    flags = []
    for r in rows:
        key = (r["tx_hash"], r["pool_address"], r["trader"])
        peers = groups[key]
        dirs = {p["direction"] for p in peers if p["direction"] in ("0_to_1", "1_to_0")}
        flags.append(len(peers) >= 2 and len(dirs) >= 2 and r["direction"] in dirs)
    return flags


def annotate_rows(
    rows: list[dict],
    *,
    dust_token: float = 1e-6,
    dust_usdc: float = 1.0,
) -> list[dict]:
    """Return copies with is_dust / is_self_churn / is_clean attached."""
    churn = is_self_churn(rows)
    out: list[dict] = []
    for row, churn_flag in zip(rows, churn, strict=True):
        dust = is_dust(
            float(row.get("amount_sold", 0.0)),
            float(row.get("amount_bought", 0.0)),
            volume_quote_stable=row.get("volume_quote_stable"),
            quote_is_stable=bool(row.get("quote_is_stable", True)),
            dust_token=dust_token,
            dust_usdc=dust_usdc,
        )
        annotated = dict(row)
        annotated["is_dust"] = dust
        annotated["is_self_churn"] = churn_flag
        annotated["is_clean"] = not dust and not churn_flag
        out.append(annotated)
    return out
