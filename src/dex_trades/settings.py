"""Load and validate project configuration.

Declarative config lives in ``config/*.yaml``. Secrets enter ONLY via
environment variables (``DEX_`` prefix), never via YAML.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class ChainConfig(BaseModel):
    name: str
    chain_id: int
    rpc_env: str
    confirmations: int = 12


class ChainsFile(BaseModel):
    chains: list[ChainConfig] = Field(min_length=1)


class PoolConfig(BaseModel):
    name: str
    chain: str
    address: str
    protocol: str  # uniswap_v2 | uniswap_v3
    enabled: bool = True
    fee_tier: int | None = None
    token0_symbol: str
    token1_symbol: str
    token0_decimals: int = Field(ge=0, le=18)
    token1_decimals: int = Field(ge=0, le=18)
    token0_address: str
    token1_address: str
    quote_is_stable: bool = True
    quote_token: str = "token0"  # token0 | token1


class PoolsFile(BaseModel):
    pools: list[PoolConfig] = Field(min_length=1)


class PipelineConfig(BaseModel):
    data_dir: Path = Path("./data")
    checkpoint_dir: Path = Path("./data/checkpoints")
    duckdb_path: Path = Path("./warehouse/dex.duckdb")
    chunk_size: int = Field(default=10, ge=1, le=10_000)
    lookback_blocks: int = Field(default=5000, ge=1)
    confirmations: int = Field(default=12, ge=0)
    rpc_timeout_seconds: float = 30.0
    rpc_max_retries: int = 5
    rpc_backoff_seconds: float = 1.5
    dust_token_threshold: float = 1e-6
    dust_usdc_threshold: float = 1.0

    def resolve(self, root: Path) -> PipelineConfig:
        return self.model_copy(
            update={
                "data_dir": (root / self.data_dir).resolve(),
                "checkpoint_dir": (root / self.checkpoint_dir).resolve(),
                "duckdb_path": (root / self.duckdb_path).resolve(),
            }
        )


class Secrets(BaseSettings):
    """Secrets and env overrides. Example: DEX_ETH_RPC_URL=https://..."""

    model_config = SettingsConfigDict(env_prefix="DEX_", env_file=".env", extra="ignore")

    eth_rpc_url: str | None = None
    base_rpc_url: str | None = None
    arb_rpc_url: str | None = None
    avax_rpc_url: str | None = None


class Settings(BaseModel):
    chains: list[ChainConfig]
    pools: list[PoolConfig]
    pipeline: PipelineConfig
    secrets: Secrets

    @model_validator(mode="after")
    def _pool_chains_exist(self) -> Settings:
        names = {c.name for c in self.chains}
        for pool in self.pools:
            if pool.chain not in names:
                raise ValueError(f"Pool {pool.name} references unknown chain {pool.chain}")
        return self

    def chain_by_name(self, name: str) -> ChainConfig:
        for chain in self.chains:
            if chain.name == name:
                return chain
        raise KeyError(name)


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def get_settings(config_dir: Path | None = None) -> Settings:
    config_dir = config_dir or CONFIG_DIR
    chains = ChainsFile.model_validate(_load_yaml(config_dir / "chains.yaml")).chains
    pools = PoolsFile.model_validate(_load_yaml(config_dir / "pools.yaml")).pools
    pipeline = PipelineConfig.model_validate(_load_yaml(config_dir / "pipelines.yaml"))
    return Settings(
        chains=chains,
        pools=pools,
        pipeline=pipeline.resolve(PROJECT_ROOT),
        secrets=Secrets(),
    )


def rpc_url_for_chain(chain: ChainConfig, settings: Settings | None = None) -> str:
    """Resolve RPC URL for a chain from DEX_ env vars (or the named rpc_env)."""
    settings = settings or get_settings()
    mapping = {
        "DEX_ETH_RPC_URL": settings.secrets.eth_rpc_url,
        "DEX_BASE_RPC_URL": settings.secrets.base_rpc_url,
        "DEX_ARB_RPC_URL": settings.secrets.arb_rpc_url,
        "DEX_AVAX_RPC_URL": settings.secrets.avax_rpc_url,
    }
    url = mapping.get(chain.rpc_env) or os.environ.get(chain.rpc_env)
    if not url:
        raise RuntimeError(
            f"{chain.rpc_env} is not set. Copy .env.example to .env and add your Alchemy HTTPS URL."
        )
    HttpUrl(url)
    return url
