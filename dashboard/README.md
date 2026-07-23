# Evidence dashboard

Minimal Evidence site over the exported `dex_marts.duckdb` snapshot.

## Local (recommended for exploring)

```bash
# from repo root, after make transform && make snapshot
cd dashboard
npm install
npm run sources
npm run dev
```

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
