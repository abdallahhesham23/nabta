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

On the dev PC, the Windows scheduled task **"Nabta Obour prices"** runs `analytics/obour_daily.cmd`
daily at 11:00 (or at next login if the PC was off), logging to `data/processed/obour_collector.log`.
It runs only while the user is logged in. New snapshots are not committed automatically: commit
`data/obour/` now and then.

## Supabase

Project **nabta** (`iumdwrwagaawoyurvniu`, eu-central-1, free plan): schema and seed are applied.
Load data with the loader, which replaces each source's rows in one transaction:

```bash
cp .env.example .env          # then fill in DATABASE_URL
cd analytics
.venv/Scripts/python -m load all    # faostat + obour
```

New migrations: add a file under `supabase/migrations/`, run `npm run test:db`, then apply it.
The daily task also runs `load obour` once `.env` exists.
