# Evidence dashboard

Minimal Evidence site over the exported `dex_marts.duckdb` snapshot.

**Live:** https://dex-trades-canonical.vercel.app/  
Pages: [Benchmarks](https://dex-trades-canonical.vercel.app/benchmarks) ·
[Orderflow](https://dex-trades-canonical.vercel.app/orderflow)

Demo snapshot (`source_kind=seed_demo`) covers all enabled pools in `config/pools.yaml`.
Warehouse exports set `source_kind=warehouse` after a real backfill.

## Local (recommended for exploring)

```bash
# from repo root — either warehouse export or offline seed:
#   make transform && make snapshot
#   make seed-dashboard
cd dashboard
npm install
npm run sources
npm run dev
```

Pages: index (canonical trades) and **orderflow** (MEV-lite proxies + fee recipient).

Do **not** open `dex_marts.duckdb` in DuckDB’s desktop UI via a Windows absolute path
(`C:\...`). DuckDB parses `c:` as a catalog name and errors with
`Catalog "c:" does not exist`. Use Evidence, or open the file from a relative path /
forward-slash path.

## Deploy on Vercel

Repo-root `vercel.json` builds the `dashboard/` Evidence app (install → sources → build).
Connect the GitHub repo in Vercel (same pattern as lp-history-reconstructor).

If the site asks for a login, disable **Deployment Protection**
(Vercel project → Settings → Deployment Protection).

The committed snapshot at `sources/dex/dex_marts.duckdb` lets the site build without a live RPC.
