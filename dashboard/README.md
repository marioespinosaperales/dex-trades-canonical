# Evidence dashboard

Minimal Evidence site over the exported `dex_marts.duckdb` snapshot.

```bash
# from repo root, after make transform snapshot
cd dashboard
npm install
npm run sources
npm run dev
```

The committed snapshot at `sources/dex/dex_marts.duckdb` lets the site build without a live RPC.
