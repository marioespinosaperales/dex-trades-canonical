# dex-trades-canonical

**Raw fragmented DEX Swap events → canonical `dex.trades` → maintainable dbt SQL → noise filters → accountable methodology.**

Built for the Allium-shaped interview loop: semantic financial abstraction over Uniswap V2/V3 on
**Ethereum, Base, Arbitrum, and Avalanche**, with dust and same-tx self-churn flags that stay in
the table (filterable, not deleted).

```mermaid
flowchart LR
  alchemy["Alchemy eth_getLogs"] --> indexer["Indexer Python"]
  indexer --> parquet["Hive Parquet swaps"]
  parquet --> duck["DuckDB raw"]
  duck --> stg["dbt stg_raw_swaps"]
  stg --> trades["dbt int_dex_trades"]
  trades --> marts["mart_dex_volume / mart_dex_trades"]
  marts --> evidence["Evidence snapshot"]
```

## Allium gap mapping

| Gap | How this repo answers |
|---|---|
| Semantic gap | One grain: `(chain, tx_hash, log_index)` → sold/bought, human amounts, pool price |
| Standardization | Same schema for V2 and V3 across Eth / Base / Arbitrum / Avalanche |
| Infra / maintainability | Config YAML + pydantic, chunked RPC, Hive Parquet, dbt staging → marts |
| Accountability | Documented dust + self-churn rules; flags retained for audit |

## Scope (v1)

- Chains: Ethereum + Base + Arbitrum + Avalanche (Alchemy HTTPS)
- Protocols: Uniswap V2 + Uniswap V3
- Output: `int_dex_trades` / `mart_dex_trades` + `mart_dex_volume_by_protocol`
- Out of v1: Solana, Curve, lending.liquidations, full factory discovery

**Next:** Solana / Curve with the same `dex.trades` schema (`chain × protocol × pool`).

## Canonical columns

Grain: one row per Swap log.

- Identity: `chain`, `chain_id`, `protocol`, `pool` (e.g. `USDC/WETH`), `pool_address`, `block_number`, `block_time` (nullable), `tx_hash`, `log_index`
- Economics: `trader`, `token_sold`, `token_bought`, `amount_sold`, `amount_bought`, raw counterparts
- Price/volume: `price_token1_per_token0`, `volume_token0`, `volume_quote_stable` (USDC-as-quote when configured)
- Quality: `is_dust`, `is_self_churn`, `is_clean`

## Methodology: noise filters

### `is_dust`

A trade is dust when either:

1. The pool is stable-quoted and `volume_quote_stable` &lt; `$1` (configurable `dust_usdc_threshold`), or
2. Both human amounts are below `1e-6` (`dust_token_threshold`)

### `is_self_churn`

Same `tx_hash` has ≥2 swaps on the **same pool** for the **same trader** with reverse directions (`0_to_1` and `1_to_0`). Simple wash / router round-trip proxy — not a full MEV classifier.

### `is_clean`

`not is_dust and not is_self_churn`. Volume marts expose both total and clean aggregates.

## Quickstart

```bash
uv sync
cp .env.example .env   # set DEX_ETH_RPC_URL and DEX_BASE_RPC_URL

make backfill          # index lookback (~5k blocks) per pool
make transform         # DuckDB load + dbt build
make snapshot          # Evidence DuckDB under dashboard/sources/dex/

make lint && make test
```

Alchemy Free: `chunk_size: 10` (same `eth_getLogs` cap as sibling LP repo).

## Default pools

| Chain | Protocol | Pair | Address |
|---|---|---|---|
| Ethereum | V3 0.05% | USDC/WETH | `0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640` |
| Ethereum | V2 | USDC/WETH | `0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc` |
| Base | V3 0.05% | WETH/USDC | `0xd0b53D9277642d899DF5C87A3966A349A798F224` |
| Arbitrum | V3 0.05% | WETH/USDC | `0xC6962004f452be9203591991d15f6b388e09E8D0` |
| Avalanche | V3 0.05% | WAVAX/USDC | `0xfAe3f424a0a47706811521E3ee268f00cFb5c45E` |

## Repository layout

```
config/           chains, pools, pipeline (YAML; secrets via DEX_ env)
src/dex_trades/   RPC, V2/V3 Swap decode, backfill, Parquet, DuckDB
dbt/              stg → int_dex_trades → volume marts + tests
dashboard/        Evidence over marts snapshot
tests/            real-shaped Swap fixtures + noise unit tests
```

## Portfolio

Sibling projects:

- [crypto-market-elt](https://github.com/marioespinosaperales/crypto-market-elt) — API ELT → dbt marts
- [lp-history-reconstructor](https://github.com/marioespinosaperales/lp-history-reconstructor) — Uniswap LP event sourcing + fees/IL
