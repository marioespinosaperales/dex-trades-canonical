"""Lightweight inference helpers for QC / orderflow rate reporting."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def wilson_ci(successes: int, n: int, *, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1.0 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_mean_ci(
    values: np.ndarray,
    *,
    n_boot: int = 800,
    seed: int = 42,
) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (0.0, 0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = np.array(
        [float(np.mean(rng.choice(arr, size=arr.size, replace=True))) for _ in range(n_boot)]
    )
    return (
        float(np.mean(arr)),
        float(np.percentile(means, 2.5)),
        float(np.percentile(means, 97.5)),
    )


def build_stat_tests(trades: pd.DataFrame, *, seed: int = 42) -> pd.DataFrame:
    """Return a table of named tests suitable for Evidence."""
    n = len(trades)
    rows: list[dict[str, Any]] = []
    if n == 0:
        return pd.DataFrame(
            columns=[
                "test_name",
                "hypothesis",
                "statistic",
                "p_value",
                "estimate",
                "ci_low",
                "ci_high",
                "n",
                "interpretation",
            ]
        )

    clean = trades["is_clean"].astype(bool)
    interesting = trades["is_orderflow_interesting"].astype(bool)
    dust = trades["is_dust"].astype(bool)

    for name, mask, hyp in (
        (
            "wilson_clean_rate",
            clean,
            "Clean-trade rate with Wilson 95% CI (binomial)",
        ),
        (
            "wilson_interesting_rate",
            interesting,
            "Orderflow-interesting rate with Wilson 95% CI",
        ),
        (
            "wilson_dust_rate",
            dust,
            "Dust-trade rate with Wilson 95% CI",
        ),
    ):
        k = int(mask.sum())
        lo, hi = wilson_ci(k, n)
        rows.append(
            {
                "test_name": name,
                "hypothesis": hyp,
                "statistic": round(k / n, 6),
                "p_value": None,
                "estimate": round(k / n, 6),
                "ci_low": round(lo, 6),
                "ci_high": round(hi, 6),
                "n": n,
                "interpretation": f"{k}/{n} = {k / n:.1%}; 95% CI [{lo:.1%}, {hi:.1%}]",
            }
        )

    vol = trades["volume_quote_stable"].fillna(0.0).to_numpy(dtype=float)
    noisy_share = 1.0 - float(vol[clean.to_numpy()].sum() / vol.sum()) if vol.sum() else 0.0
    # Bootstrap the noisy volume share via resampled rows
    rng = np.random.default_rng(seed)
    boot_shares = []
    clean_np = clean.to_numpy()
    for _ in range(800):
        idx = rng.integers(0, n, size=n)
        v = vol[idx]
        c = clean_np[idx]
        total = float(v.sum())
        boot_shares.append(0.0 if total <= 0 else 1.0 - float(v[c].sum() / total))
    rows.append(
        {
            "test_name": "bootstrap_noise_volume_share",
            "hypothesis": "Noise share of stable volume (1 - clean/total), bootstrap 95% CI",
            "statistic": round(noisy_share, 6),
            "p_value": None,
            "estimate": round(noisy_share, 6),
            "ci_low": round(float(np.percentile(boot_shares, 2.5)), 6),
            "ci_high": round(float(np.percentile(boot_shares, 97.5)), 6),
            "n": n,
            "interpretation": (
                f"Noise volume share={noisy_share:.1%}; "
                f"95% CI [{np.percentile(boot_shares, 2.5):.1%}, "
                f"{np.percentile(boot_shares, 97.5):.1%}]"
            ),
        }
    )

    # Mann-Whitney: do interesting trades carry different stable volume?
    vol_int = vol[interesting.to_numpy()]
    vol_plain = vol[~interesting.to_numpy()]
    if vol_int.size >= 3 and vol_plain.size >= 3:
        u_stat, p_mw = stats.mannwhitneyu(vol_int, vol_plain, alternative="two-sided")
        rows.append(
            {
                "test_name": "mannwhitney_volume_interesting_vs_other",
                "hypothesis": (
                    "H0: stable-volume distributions equal for interesting vs other trades"
                ),
                "statistic": round(float(u_stat), 4),
                "p_value": round(float(p_mw), 6),
                "estimate": round(float(np.median(vol_int) - np.median(vol_plain)), 6),
                "ci_low": None,
                "ci_high": None,
                "n": n,
                "interpretation": (
                    f"Median vol interesting={np.median(vol_int):.2f} vs "
                    f"other={np.median(vol_plain):.2f}; two-sided p={p_mw:.4g}"
                ),
            }
        )

    # Chi-square: interesting × fee_recipient (top builders collapsed)
    if "fee_recipient" in trades.columns:
        fr = trades["fee_recipient"].fillna("unknown").astype(str)
        top = fr.value_counts().head(4).index
        fr_g = fr.where(fr.isin(top), other="other")
        table = pd.crosstab(interesting, fr_g)
        if table.shape[0] >= 2 and table.shape[1] >= 2:
            chi2, p_chi, dof, _ = stats.chi2_contingency(table)
            rows.append(
                {
                    "test_name": "chi2_interesting_vs_fee_recipient",
                    "hypothesis": (
                        "H0: orderflow-interesting independent of fee_recipient (builder proxy)"
                    ),
                    "statistic": round(float(chi2), 4),
                    "p_value": round(float(p_chi), 6),
                    "estimate": float(dof),
                    "ci_low": None,
                    "ci_high": None,
                    "n": n,
                    "interpretation": (
                        f"χ²={chi2:.3f}, dof={dof}, p={p_chi:.4g} "
                        "(association ≠ sandwich proof)"
                    ),
                }
            )

    return pd.DataFrame(rows)
