# HANDOFF — Nabta (نَبْتَة)

The project's continuation file. Read this first, then check the repo; trust the code over this file
if they disagree, and fix whichever is wrong. Detailed companions: [PLAN.md](PLAN.md) (plan, decisions,
phase status), [docs/data-dictionary.md](docs/data-dictionary.md) (sources, units, data issues),
[README.md](README.md) (commands).

---

## M. Recent changes (read this first)

- **Last updated:** 2026-10-29
- **Most recent task:** fixed the over-optimistic onion forecast (P1-1). The fix is uncommitted; the live DB is already republished.
  - **Diagnosis:** the cause was not missing Obour anchoring.
    - The model priced each crop at one "harvest month", and for onion (October + 180 days) that was March, the old-stock peak (2024: 17.6 in March, 18.3 in April, then 7.3 in May once the new crop lands).
    - Anchoring to Obour was rejected: October wholesale (17.5) is old stored crop and would raise the spring forecast.
  - **Fix:** `model/evi.py` `selling_price()` averages the harvest month and the 2 months after (`SELL_MONTHS = 3`). It's used by both `evi.recommend` and `publish.harvest_prices`, so the dashboard price and the recommendations agree.
  - **Onion cycle** corrected from 180 to 210 days (`supabase/seed.sql`, plus the live `crops` row via SQL). It's still provisional pending the ARC review; `docs/agronomy-review.xlsx` still shows the old 180.
  - **Result** (live, after `publish`):
    - onion 18.35 → 12.22 EGP/kg; tomato 9.81 → 11.19; potato 18.37 → 18.70; wheat unchanged at 15.49.
    - For a 3-feddan loam/canal winter plot: onion EVI 100 (133k profit per feddan, was 226k), tomato 61 (98k), potato 51 (80k), wheat 13 (17k). Onion is still first; see §J-1.
- **Before that:** connected GitHub through the `gh` CLI.
  - Private repo https://github.com/abdallahhesham23/nabta.
  - History rewritten to drop the AI co-author line; the user ran the force-push. `gh auth setup-git` configures git credentials.
  - All commits show only `abdallahhesham23` (verified via the API). The old history is backed up at `refs/original/refs/heads/main`.
- **Most recent verification (2026-10-29):**
  - `npm run test:db`: 4/4 pass.
  - `analytics` pytest: 24/24 pass, including 2 new selling-window tests.
  - `publish` exit 0 (204 forecasts, 17 cells).
  - Read-only in-memory scoring check against live data (nothing written).
  - `apps/mobile` `tsc --noEmit`: OK as of the last app change; the app is unchanged in this task.
- **Current blockers:**
  - WhatsApp login needs a Twilio account.
  - An Android build needs an Expo account.
  - Official ARC costs are missing for most crops.
- **Next recommended action:**
  - Commit and push this fix once the user approves.
  - Then: official ARC costs for more crops (§K P1-3), or WhatsApp login once the user has Twilio (§K P1-4).

---

## A. Project overview

**Nabta** is a decision-support app that shows Egyptian farmers the market picture *before* they plant, so they don't all plant last year's winner (herd behaviour → glut → price crash). Source proposal: `مشروع نبتة 2026.pdf` by Ahmed Abdallah Kalloub (Agricultural Bank of Egypt, Aug 2026). The PDF is gitignored because it contains a personal phone number.

**Target users:** smallholders (<5 feddan), medium (5–20) and large farms (>20). Pilot plan: 100 users and 100 control farmers in Sharqia, Beheira and Minya.

**Confirmed requirements** (proposal + user decisions recorded in PLAN.md §7):
- Arabic, right-to-left; Android first.
- **Quad dashboard per crop:** area planted, expected production, last year's production, and supply vs demand.
- Comparison with alternative crops.
- Personal recommendations from the farmer's location, soil, water and capital.
- Planting intentions and post-harvest reports.
- **17 crops:** the proposal's 15, with beans split into green/dry and ذرة split into maize/sorghum.
- Dashboard at governorate level.
- Supabase Cloud for the pilot.
- WhatsApp one-time-code login.
- Bank loan priority is **not** in the pilot.
- Public data first.

**Proposed / deferred** (not built): paid tier, B2G/B2B dashboards, ads, contract marketplace, voice assistant, satellite area estimation, iOS, food-security index, glut push alerts.

**Current stage:**
- Phase 0 (data) and Phase 1 (analytics) are done.
- Phase 2 (mobile MVP) is built and partly verified.
- Phase 3 (field pilot) and Phase 4 (scale and revenue) need people and accounts, not code.

---

## B. Technology stack and architecture (verified from files)

| Layer | Actual | Where |
|---|---|---|
| Mobile | Expo SDK 57 (`expo ~57.0.31`), React Native 0.86.3, React 19.2.3, Expo Router `~57.0.29`, TypeScript `~6.0.3`, react-native-web, expo-localization (forcesRTL) | `apps/mobile/package.json`, `app.json` |
| Backend | Supabase (Postgres 17, Auth, PostgREST). No custom API server. | project `nabta` / ref `iumdwrwagaawoyurvniu`, region eu-central-1, free plan |
| DB client in app | `@supabase/supabase-js` 2.118.0 + AsyncStorage session | `apps/mobile/src/lib/supabase.ts` |
| Analytics | Python 3.13 (venv), pandas 2.3.3, psycopg 3.3.6, pytest 8.4.2. No statsmodels or sklearn yet. | `analytics/requirements.txt` |
| Schema tests | Node 24 + `@electric-sql/pglite` 0.5.10 (in-process Postgres with a Supabase auth stub) | `package.json`, `supabase/tests/` |
| Scheduling | Windows Task Scheduler task **"Nabta Obour prices"** → `analytics/obour_daily.cmd` | dev PC only |
| Supabase CLI | used once via `npx supabase@2.48.3 init` (config only); not installed globally; not linked | `supabase/config.toml` |

**How the pieces connect**
```
FAOSTAT bulk zips ──ingest/faostat.py──┐
Obour official page ──ingest/obour.py──┼─> data/processed/*.csv ─> load.py ──> Supabase tables
data/manual/*.csv (hand-entered) ──────┘                         (nabta_loader role, session pooler)
Supabase tables ─> publish.py (model/forecast → model/dashboard → model/evi) ─> forecasts,
                                                    dashboard_cells, recommendations
Mobile app ── publishable key + RLS ──> reads public tables; signed-in farmer reads/writes own rows
```

**Key patterns and decisions**
- **Batch analytics, not an API.** The app only reads precomputed tables.
- **Each load replaces one source's rows in a single transaction.** A source is a name, or `name:detail` for hand-entered rows, e.g. `manual:almalnews-2026-08-31`.
- **Units are normalised on import:** feddan, tonnes, EGP/kg.
- **RLS everywhere.** Supabase's default grants are revoked and the grants are explicit. Farmers see only their own rows. Public reference, statistics and computed tables are read-only to anon/authenticated users.
- **Writes go through the `nabta_loader` role:** bypassrls, minimal grants, 5-minute statement timeout, 2-minute idle-in-transaction timeout.
- **Planned but NOT used:** PLAN.md §2 lists React Native Paper, victory-native, TanStack Query offline cache, Sentry, the Cairo font, statsmodels/SARIMA and Python 3.12. None are in the code. The app uses its own components in `src/components/ui.tsx` and plain-View bar charts.

---

## C. Project structure

```
HANDOFF.md, PLAN.md, README.md      continuation file, plan + decisions + phase status, commands
.env.example                         env template (DATABASE_URL for nabta_loader). .env is gitignored and exists locally
.claude/launch.json                  preview config for the Expo web server
package.json                         root: PGlite dev dependency + `npm run test:db`
supabase/
  config.toml                        local CLI config (phone signup on, twilio_verify disabled, test OTP for a fake number)
  migrations/20261028000000_init.sql            schema, enums, RLS, grants
  migrations/20261029000000_phase1_outputs.sql  dashboard price/yield/revenue cols; recommendation "why" cols
  migrations/20261029010000_loader_role.sql     nabta_loader role (password set out of band)
  migrations/20261029020000_loader_timeouts.sql statement/idle timeouts for nabta_loader
  seed.sql                           27 governorates, 17 crops (agronomy PROVISIONAL)
  tests/schema.test.mjs              PGlite: seed counts, anon access, RLS isolation, constraints
analytics/
  ingest/faostat.py                  FAOSTAT bulk → faostat_{crop_stats,prices,trade}.csv (Egypt, 17 crops)
  ingest/obour.py                    official Obour page → data/obour/<date>.csv snapshot + obour_prices.csv
  load.py                            CSV → Supabase, per-source replace (faostat | obour | manual | all)
  model/forecast.py                  seasonal-naive farmgate forecast, 12 months
  model/dashboard.py                 quad dashboard cells per crop (national)
  model/evi.py                       EVI recommendations + herd spreading
  publish.py                         reads DB, runs models, writes forecasts/dashboard_cells/recommendations
  obour_daily.cmd                    scheduled: collect → load obour → publish
  tests/                             test_faostat.py, test_obour.py, test_model.py
apps/mobile/src/
  app/_layout.tsx                    stack, web dir=rtl
  app/(tabs)/index.tsx               السوق: crop list with outlook badge, forecast + Obour price
  app/(tabs)/compare.tsx             قارن: up to 3 crops side by side
  app/(tabs)/farm.tsx                مزرعتي: WhatsApp OTP login, profile, plot, intentions, harvest, recommendations
  app/crop/[id].tsx                  quad dashboard, prices, 12-month forecast bars, sources
  lib/{data,format,supabase,theme}.ts  queries + nextSeason(), Arabic formatting, client, colours
  components/ui.tsx                  Screen, Card, Stat, Chip, Button, Field, Loading…
data/
  obour/                             daily raw snapshots, COMMITTED (irreplaceable: page has no history)
  manual/costs.csv, prices.csv       hand-entered, cited figures (COMMITTED)
  templates/                         CSV headers for manual entry
  raw/, processed/                   gitignored (downloads; regenerated outputs; collector log)
docs/data-dictionary.md              units, crop↔FAOSTAT mapping, sources, interim costs, known data issues
docs/agronomy-review.xlsx            Arabic sheet for an ARC agronomist to correct crop agronomy
```

---

## D. Completed work (chronological; all 2026-10-28/29)

1. **Plan:** read the 18-page proposal and wrote PLAN.md (scope, stack, maths, data model, phases). The user answered 8 decisions (PLAN §7).
2. **Phase 0, data foundation** (`68edbab`):
   - Supabase schema and RLS, seed, PGlite tests.
   - FAOSTAT importer: national area/production/yield 1961–2024, producer prices, trade 2010–2023.
   - Data dictionary and the agronomy review sheet.
   - Finding: FAOSTAT's live API needs a login, but its bulk zips are open.
3. **Obour collector** (`ff1f839`):
   - News reports were planned, but the official page `http://www.oboormarket.org.eg/prices_ar.aspx` was found. It's HTTP only and has no history, so it's snapshotted daily.
   - Daily Windows task added (`ef2ad1a`).
4. **Supabase project** (`af2c6ab`): created on the free plan for $0 in eu-central-1. Migration and seed applied via the Supabase MCP connector; migration versions were manually aligned to the filenames. Loader written.
5. **Connection troubleshooting:**
   - The user's `.env` password was wrong; the first attempt still had the `[ ]` placeholder brackets.
   - Repeated failures led to a pooler lockout lasting about 40 minutes. A retry loop probably prolonged it.
   - **Fix:** created the `nabta_loader` role. Its password was generated locally and only a SCRAM hash was sent to Supabase. `.env` now uses this role.
6. **Phase 1, analytics** (`85b6397`):
   - Dashboard, forecast and EVI, with tests.
   - Forecast fixes found while sanity-checking:
     - The outlier rule no longer drops the real 2023–24 devaluation jump.
     - Past farmgate prices above today's Obour maximum are dropped (the 2023 orange and grape entry errors).
     - Growth capped at 15%/yr; uncapped, it showed wheat at 53 EGP/kg.
   - Data was first loaded through the MCP connector while the pooler was locked, then fully via `load all`.
7. **Phase 2, mobile app** (`56628c0`):
   - Expo SDK 57 app. Removed the template's `.claude/settings.json` (it enabled a plugin) and its LICENSE.
   - Verified in a browser at mobile size: market, crop and compare screens show live data; the login error path is graceful (Supabase auth log shows `phone_provider_disabled`).
8. **Interim costs** (`0d42a64`):
   - `data/manual/costs.csv`: tomato, onion, wheat and potato, excluding rent, from cited Al Mal news reports.
   - Wheat 2026 procurement price of 15.67 EGP/kg added as farmgate data. The wheat forecast went from about 26 to about 15.5 EGP/kg.
   - EVI scales older costs to the planting year.
   - E2E check with a temporary auth user, farmer and plot gave onion > potato > tomato > wheat. The test rows were deleted.
   - A dropped connection left a COPY stuck holding locks. The backend was terminated; data was intact.
9. **This handoff file** (2026-10-29): documentation only. Committed with `CLAUDE.md` as `1c93fd3` at the user's request.

---

## E. Current project status

- **Working and verified:**
  - FAOSTAT import, the Obour collector and its daily task, loading to Supabase.
  - The publish job.
  - Mobile market, crop and compare screens with live data.
  - RLS: PGlite tests plus live grant checks. The Supabase security advisor reports 0 issues.
- **Implemented, not verified:**
  - The signed-in farm tab: profile, plot, intentions, harvest form, recommendations list. It needs working login.
  - Native Android rendering: only the web build has been run.
- **Partial:**
  - Recommendations cover only the 4 crops with cost rows.
  - The forecast is a weak baseline.
- **Not implemented:**
  - Glut push alerts.
  - Offline cache.
  - Adding app planting intentions (10+ farms per cell) into dashboard cells.
  - Governorate-level dashboard cells.
  - SARIMA forecasting with a backtest.
  - EAS build.
- **Build and test status (2026-10-29):** all suites green; see §H.
- **Deployment:**
  - Supabase is live.
  - The app is not deployed anywhere: no store build, no hosted web.
  - Code is on GitHub as a private repo: `origin` = https://github.com/abdallahhesham23/nabta, in sync with local `main`.
- **Live DB counts (2026-10-29):**

  | Table | Rows |
  |---|---:|
  | crop_stats | 1088 |
  | prices | 950 (927 FAOSTAT + 22 Obour + 1 manual) |
  | trade | 229 |
  | costs | 4 |
  | forecasts | 204 |
  | dashboard_cells | 17 |
  | recommendations | 0 (no farmers yet) |
  | farmers | 0 |

---

## F. Feature tracker

| Feature | Status | Where | Notes / remaining |
|---|---|---|---|
| FAOSTAT ingest | VERIFIED | `analytics/ingest/faostat.py` | national, yearly |
| Obour daily collector | VERIFIED | `ingest/obour.py`, `obour_daily.cmd` | 2 snapshots (10-26, 10-29); runs only while logged in |
| Schema + RLS | VERIFIED | `supabase/migrations/` | PGlite tests + live checks |
| Loader (`load.py`) | VERIFIED | `analytics/load.py` | sources faostat/obour/manual |
| Quad dashboard cells | VERIFIED | `model/dashboard.py` | national only; "area now" = FAOSTAT 2024 harvested area |
| Price forecast | IMPLEMENTED — weak baseline | `model/forecast.py`, `evi.selling_price` | selling-window pricing added 2026-10-29; onion still optimistic (§J-1) |
| EVI recommendations | TESTED + E2E once | `model/evi.py`, `publish.py` | 4 crops with costs |
| Herd spreading | TESTED (unit only) | `model/evi.py` | can't matter at pilot scale |
| Mobile market/crop/compare | VERIFIED (web build) | `apps/mobile/src/app/` | native device not run |
| WhatsApp OTP login | BLOCKED | `farm.tsx`, Supabase Auth | needs Twilio Verify + Meta-approved WhatsApp sender |
| Farm profile/plot/intentions/harvest | IMPLEMENTED — NOT VERIFIED | `farm.tsx` | blocked by login |
| Intention aggregation into dashboard (10+ farms) | NOT STARTED | `model/dashboard.py` | |
| Glut push alerts | NOT STARTED | — | needs Expo/FCM project |
| Offline cache | NOT STARTED | — | |
| Android build (EAS) | BLOCKED | — | needs Expo account (user) |
| Governorate data (CAPMAS) | BLOCKED | `data/templates/crop_stats.csv` | censusinfo.capmas.gov.eg unreachable from here; manual entry |
| Crop agronomy review | BLOCKED | `docs/agronomy-review.xlsx`, `seed.sql` | waiting on an ARC agronomist |
| Git remote / backup | VERIFIED | `origin` (private) | pushed via `gh`; history shows only the user |
| Phase 3 pilot, Phase 4 | NOT STARTED / DEFERRED | PLAN.md §6 | need people/partners |

---

## G. Database, data and integrations

- **Tables** (see the init migration for columns and constraints):
  - **Reference:** `governorates`, `markaz`, `crops`.
  - **Statistics:** `crop_stats`, `prices`, `costs`, `trade`. A null `gov_id` means national; a null `season` means all year.
  - **Farmer data:** `farmers` (PK = `auth.users.id`), `plots`, `intentions`, `harvest_reports`. One harvest report per intention.
  - **Computed:** `forecasts`, `dashboard_cells` (unique on crop/season/year/gov, nulls not distinct), `recommendations`.
- **Enums:** `season`, `soil_type`, `water_source`, `price_granularity`, `intention_status`, `market_outlook`.
- **Constraints:** non-negative quantities; month 1–12; EVI 0–100; one stats row per (crop, gov, season, year, source).
- **Migrations:**
  - Applied to the live DB via the Supabase MCP `apply_migration`. After each one, the version in `supabase_migrations.schema_migrations` was **manually updated** to match the filename. Do the same for new migrations, or `supabase db push` will try to reapply them.
  - Live versions: `20261028000000`, `20261029000000`, `20261029010000`, `20261029020000`.
- **Sources:** FAOSTAT bulk files (QCL, PP, SCL); the official Obour page; `data/manual` (cited news figures and the official wheat price). Full details in [docs/data-dictionary.md](docs/data-dictionary.md).
- **Env vars:**
  - `DATABASE_URL` in `/.env`: the session pooler URI for user `nabta_loader.<ref>`, port 5432.
  - The app embeds the Supabase URL and **publishable** key in `src/lib/supabase.ts`. It's public by design; RLS limits it.
- **Auth:**
  - Phone OTP over the WhatsApp channel; the phone provider is currently **disabled** on the hosted project.
  - For local CLI dev only, `config.toml` has a fixed test OTP for a fake number.
- **Integration constraints:**
  - The Supabase pooler locks out an IP after repeated failed passwords. Don't loop retries.
  - The Obour site is HTTP only and slow; the statistics page needs an account, so don't use it.
  - The FAOSTAT live API needs a login, so use the bulk files.
- **Postgres password:** not known to us. The jobs never need it; use `nabta_loader`. To rotate its password: `alter role nabta_loader login password '<SCRAM hash>'`.
- **Test data rule:** production has no farmers. The E2E test used a temporary `auth.users` row, which was deleted. Clean up any future test rows.

---

## H. Testing and verification

| Command (from repo root unless noted) | Covers | Last result (2026-10-29) |
|---|---|---|
| `npm run test:db` | migrations + seed in PGlite, anon access, RLS isolation, constraints | 4/4 pass |
| `cd analytics && .venv/Scripts/python -m pytest -q` | FAOSTAT parsing, Obour parsing/date logic, dashboard, forecast, EVI incl. spreading, cost growth, selling window | 24/24 pass |
| `cd apps/mobile && npx tsc --noEmit` | app typecheck | OK |
| Manual, browser at 375×812 | market, crop (maize), compare, login error | OK; month-label overlap fixed afterwards, but only confirmed via tsc, not re-screenshotted |
| Manual, E2E publish with a temporary farm | recommendations written and correct | OK; test rows deleted |

**Gaps:**
- No tests for `load.py` or `publish.py` I/O. A PGlite socket attempt failed because it doesn't support COPY; they were verified against the real DB instead.
- No UI or E2E automated tests.
- No lint config: `apps/mobile/AGENTS.md` suggests `npx expo lint`, which isn't set up.
- No native device run.
- No forecast backtest.

---

## I. Important decisions and constraints

The user's decisions are in PLAN.md §7. The rest:

| Decision | Why | Consequence |
|---|---|---|
| Official Obour page instead of news reports | primary source, structured | must run daily; a missed day is lost |
| Costs exclude land rent | rent depends on owner vs tenant | potato cost basis unclear (may include rent) |
| Crops without a cost are not ranked | ranking on revenue alone favours expensive crops | only 4 crops get recommendations now |
| Growth cap of 15%/yr | 2022–24 devaluation isn't a trend | assumption; revisit with Obour history |
| Seasonal-naive forecast, not SARIMA | FAOSTAT monthly prices are sparse | ±30% band; known onion bias |
| Separate `nabta_loader` role | postgres password unknown; least privilege | role password lives only in local `.env` |
| Expo SDK 57, not 58 | 58 was weeks old | upgrade later with `npx expo install --fix` |
| Templates' `.claude/settings.json` removed | it would enable a plugin without the user's say | — |
| Proposal PDF gitignored | contains a personal phone number | keep it out of any pushed repo |
| No commits/pushes unless the task authorises it | user's handoff instruction | past commits were made under the user's "complete all phases" / "continue" instructions |
| User is the sole committer; no AI `Co-Authored-By` line | user's explicit request, 2026-10-29 | rule recorded in `CLAUDE.md`; overrides the default attribution reminder |
| GitHub via `gh` CLI, private repo | the GitHub MCP connector needs OAuth in the session and can't push a local repo | `gh` signed in as `abdallahhesham23`, token stored in the Windows keyring |

---

## J. Known bugs, risks and limitations

1. **Onion is still somewhat optimistic** (partly fixed 2026-10-29). Severity: medium.
   - Fixed: pricing at the pre-harvest peak (selling window + 210-day cycle). Onion went from 18.35 to 12.22 EGP/kg, and profit per feddan from 226k to 133k.
   - Remaining: onion still ranks first for loam winter plots. The reported spring-2026 glut (about 4 EGP/kg farmgate, Al Mal, 21 Apr 2026) isn't in FAOSTAT, whose data ends in 2024. The seasonal index comes from only 2 years of monthly data (2020, 2024).
   - Reproduce: score a 3-feddan loam/canal plot, as in the read-only check under §M.
   - Next step: wait for Obour daily history to cover the April–June 2027 harvest; or load Ministry/CAPMAS monthly onion prices for 2025–26 into `data/manual/prices.csv` (months of a year count only if there are 3 or more).
   - Don't anchor to the current Obour price: October wholesale is old stored crop.
2. **The forecast is weak in general:** a fixed ±30% band, no backtest, and the 15% growth is an assumption. Wheat is anchored to the procurement price; the other crops aren't.
3. **The dashboard's "area now" is the FAOSTAT 2024 harvested area**, not this season's planting. Labelled as such in the app.
4. **Interim costs are news-sourced and mixed in age:** 2023–2026, scaled at 15%/yr. Potato may include rent.
5. **The Windows task only runs while the user is logged in.** Snapshots aren't auto-committed. `NextRunTime` showed 10:00 instead of the configured 11:00 after Egypt's DST change on 29 Oct. Not investigated; harmless.
6. **Resolved 2026-10-29:** the code was a single copy; it's now on the private GitHub repo. `data/obour/` snapshots are only backed up once they're committed and pushed.
7. **Preview tooling:**
   - The app's `preview_start` looked for `.claude/launch.json` in an old scratch folder and rejects absolute `cwd`.
   - Workaround: from `apps/mobile`, run `node node_modules/expo/bin/cli start --web --port 8081` in the background, then open `http://localhost:8081`.
   - `npx expo start` once failed with an npm/sigstore error on restart.
   - Stopping the background task may leave node listening on 8081; kill the PID.
8. **Pooler hang after a dropped COPY:** mitigated by the role timeouts. If it recurs, check `pg_stat_activity` for an `active` `nabta_loader` session waiting on `ClientRead`.
9. **The crop agronomy in `seed.sql` is provisional:** seasons, water, soils and cycle days feed the EVI filters.

---

## K. Pending tasks and next steps

**P0:** none. (The history-rewrite push was done and verified on 2026-10-29.)

**P1:**
1. **Done 2026-10-29 (uncommitted): onion forecast bias**, fixed via the selling window rather than Obour anchoring (why: §J-1).
   - Left: the onion data gap in §J-1.
   - Left: update `docs/agronomy-review.xlsx`, which still shows onion at 180 days.
2. **Done 2026-10-29: backed up the code** to the private GitHub repo (history rewritten to drop AI attribution; verified).
3. **Get official ARC costs per feddan for the other crops.**
   - Where: `data/manual/costs.csv` or `data/templates/costs.csv`, then `python -m load manual` and `python -m publish`.
   - Accept when: recommendations cover all non-perennial crops.
4. **WhatsApp login.**
   - Needs: the user's Twilio Verify service with a Meta-approved WhatsApp sender, configured in Supabase Auth → Phone.
   - Then verify every farm-tab flow with a real phone.
5. **Android build.**
   - Needs: the user's Expo account.
   - Then: `npx eas-cli@latest build -p android --profile preview` (no `eas.json` yet) and test on a 2 GB RAM phone.

**P2:**
- Add app planting intentions into `dashboard_cells`, only where a cell has 10+ farms.
- Governorate-level cells from CAPMAS data.
- Glut push alerts.
- Offline cache.
- Apply the agronomist's corrections to `seed.sql`.
- Set up lint.
- Automate committing `data/obour/`.

**P3:**
- SARIMA with a backtest once about 2 years of Obour data exist.
- Weather data and a Random Forest yield model.
- Phase 4 items (PLAN.md §6).

---

## L. Setup and continuation

**Prerequisites:**
- Node 24 (verified), Python 3.13 (verified), git. No Docker is needed.
- GitHub CLI at `C:\Program Files\GitHub CLI\gh.exe`, signed in as `abdallahhesham23`.
- Clone with `gh repo clone abdallahhesham23/nabta`. Then create `.env` from `.env.example`; the loader password isn't in git, so issue a new one per `.env.example`.

```bash
npm install && npm run test:db                                # schema tests
cd analytics && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q
cp ../.env.example ../.env    # then fill DATABASE_URL (nabta_loader); never commit .env
.venv/Scripts/python -m ingest.faostat     # ~130 MB download on first run
.venv/Scripts/python -m ingest.obour       # today's auction snapshot
.venv/Scripts/python -m load all && .venv/Scripts/python -m publish
cd ../apps/mobile && npm install && npx tsc --noEmit
node node_modules/expo/bin/cli start --web --port 8081        # web preview (see §J-7)
```

**New migrations:**
1. Add a file to `supabase/migrations/`.
2. Run `npm run test:db`.
3. Apply it (Supabase MCP `apply_migration`, or the CLI once linked).
4. Align its version in `supabase_migrations.schema_migrations`.

**Session start:**
1. Read this file.
2. Run `git log --oneline` and `git status`.
3. Run the three test commands.
4. Check the tail of `data/processed/obour_collector.log` and the task's `Get-ScheduledTaskInfo -TaskName 'Nabta Obour prices'`.
5. Fix any drift here.
