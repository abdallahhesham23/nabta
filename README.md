# Nabta (نَبْتَة)

Decision-support platform that shows Egyptian farmers the market picture before planting.
Plan and status: [PLAN.md](PLAN.md). Data sources and units: [docs/data-dictionary.md](docs/data-dictionary.md).

## Layout

```
apps/mobile/  Expo app (Android first, also runs on web): market dashboard, crop comparison, farm
supabase/     config, migrations (schema + RLS), seed, schema tests (PGlite, no Docker)
analytics/    importers (FAOSTAT, Obour), loader, model/ (dashboard, forecast, EVI), publish job
data/obour/      daily Obour market price snapshots (committed, irreplaceable)
data/raw/        downloaded source files (gitignored)
data/processed/  importer and model output, shaped like the DB tables (gitignored)
data/templates/  CSV headers for manually entered sources (CAPMAS, ARC costs)
```

## Mobile app

```bash
cd apps/mobile
npm install
npx expo start --web       # browser preview; `npx expo start` + Expo Go for a phone
npx tsc --noEmit           # typecheck
```

It reads public data with the publishable key (`src/lib/supabase.ts`); row-level security limits
what that key can do. Login is a WhatsApp one-time code, which works once Twilio Verify with a
WhatsApp sender is configured in Supabase Auth → Phone. Until then the market and compare tabs
work and the farm tab shows a "not ready yet" message.

## Analytics

```bash
npm install
npm run test:db                          # migrations + seed in PGlite, check RLS

cd analytics
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt   # Windows path
.venv/Scripts/python -m pytest
.venv/Scripts/python -m ingest.faostat   # downloads ~130 MB on first run, writes data/processed/faostat_*.csv
.venv/Scripts/python -m ingest.obour     # run DAILY: saves data/obour/<date>.csv
.venv/Scripts/python -m load all         # replace each source's rows in Supabase (needs .env)
.venv/Scripts/python -m load manual      # just the hand-entered data/manual/*.csv (costs, wheat price)
.venv/Scripts/python -m publish          # forecasts, dashboard cells, recommendations -> Supabase
```

`data/obour/` holds one raw snapshot per auction day and is committed: the market's page has no
history, so a day that isn't collected is lost.

On the dev PC, the Windows scheduled task **"Nabta Obour prices"** runs `analytics/obour_daily.cmd`
daily at 11:00 (or at next login if the PC was off): collect → load → publish, logging to
`data/processed/obour_collector.log`. It runs only while the user is logged in. New snapshots are
not committed automatically: commit `data/obour/` now and then.

## Supabase

Project **nabta** (`iumdwrwagaawoyurvniu`, eu-central-1, free plan). The jobs connect as
`nabta_loader` through the session pooler; see `.env.example`.

New migrations: add a file under `supabase/migrations/`, run `npm run test:db`, then apply it.
