# Nabta (نَبْتَة)

Decision-support platform that shows Egyptian farmers the market picture before planting.
Plan: [PLAN.md](PLAN.md). Data sources and units: [docs/data-dictionary.md](docs/data-dictionary.md).

## Layout

```
supabase/     config, migrations (schema + RLS), seed, schema tests (PGlite, no Docker)
analytics/    Python importers (FAOSTAT today), later forecasting and EVI
data/obour/      daily Obour market price snapshots (committed, irreplaceable)
data/raw/        downloaded source files (gitignored)
data/processed/  importer output, shaped like the DB tables (gitignored)
data/templates/  CSV headers for manually entered sources (CAPMAS, Obour, ARC)
```

## Commands

```bash
npm install
npm run test:db                      # apply migration + seed in PGlite, check RLS
```

```bash
cd analytics
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # Windows path
.venv/Scripts/python -m pytest
.venv/Scripts/python -m ingest.faostat   # downloads ~130 MB on first run, writes data/processed/faostat_*.csv
.venv/Scripts/python -m ingest.obour     # run DAILY: saves data/obour/<date>.csv, writes data/processed/obour_prices.csv
```

`data/obour/` holds one raw snapshot per auction day and is committed: the market's page has no
history, so a day that isn't collected is lost.

Loading into a Supabase project: `npx supabase@2.48.3 link` then `npx supabase db push`, then import
`data/processed/*.csv` into `crop_stats`, `prices` and `trade` (Studio → table → Import CSV).
