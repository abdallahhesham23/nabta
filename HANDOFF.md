# HANDOFF — Nabta (نَبْتَة)

The project's continuation file. Read this first, then check the repo; trust the code over this file
if they disagree, and fix whichever is wrong. Detailed companions: [PLAN.md](PLAN.md) (plan, decisions,
phase status), [docs/data-dictionary.md](docs/data-dictionary.md) (sources, units, data issues),
[README.md](README.md) (commands).

---

## M. Recent changes (read this first)

- **Last updated:** 2026-10-29
- **Most recent task:** the user said "do them": everything on the backlog that needs no accounts. **Uncommitted.**
  1. **Save feedback** (`farm.tsx`): spinners on the profile/plot save, "سجّل", "زرعته", "حصدته" and harvest-save buttons. Fixes the old §J-10.
  2. **Glut warning** (`farm.tsx` Plans): choosing a crop whose outlook is `surplus` shows "⚠️ المعروض المتوقع … أعلى من المعتاد (+x٪)". Verified: shown for tomato (+11.5%), not for wheat.
  3. **Offline cache** (`src/lib/data.ts`): market data is stored in AsyncStorage (`nabta.market.v1`), shown at once on the next open (`stale` flag plus a note on the market tab), then refreshed.
     - Verified: data is stored (11.5 KB in the web build).
     - **Not verified:** a real offline start.
  4. **App planting intentions on the dashboard** (privacy-protected):
     - Migration `20261030000000_intentions_in_dashboard.sql` (applied live, version aligned) adds `intended_area_feddan` and `intending_farms`.
     - `dashboard.intended()` sums planned/planted intentions for the next season, per crop, **only when 10 or more distinct farms** planned it (`MIN_FARMS`).
     - `publish.py` reads them (and `read()` now takes params).
     - The crop screen shows "N مزارع ناويين يزرعوا X فدان" or the privacy message.
     - Verified:
       - Unit test.
       - The live query, run through MCP, with 19 temporary farms (10 tomato, 9 onion), fed to `intended()`: tomato (20 feddan, 10 farms), onion hidden.
       - App display for both cases.
     - **Not verified:** the live `publish` run (§J-13). The temporary farms were deleted and the tomato cell reset to null.
  5. **Lint:** `npx expo lint` set up (`eslint.config.js`, eslint ^9, eslint-config-expo ~57.0.2, `npm run lint`). It found and fixed 2 errors: unnamed tab-icon components (`_layout.tsx`), and setState-in-effect in the farm tab (now `fetchFarm()` + `.then(setData)`). Lint is clean.
  6. **Agronomy sheet:** onion's current cycle changed 180 → 210 in `docs/agronomy-review.xlsx`.
  7. **Auto-commit of Obour snapshots:** `analytics/commit_snapshots.py`, run by `obour_daily.cmd` after the collector.
     - Commits only `data/obour/` under the repo author, with no AI line.
     - Pushes only if that commit is the sole unpushed one, and skips off `main`.
     - 3 tests use temporary git repos. On the real repo it reported "nothing new".
- **Before that:** anonymous sign-in `520b2bb` (verified end to end); onion forecast fix `c012c2a`; GitHub via `gh` (private repo, history shows only the user).
- **Most recent verification (2026-10-29):**
  - pytest 28/28.
  - `npm run test:db` 4/4.
  - Mobile `tsc` OK and `expo lint` clean.
  - Browser checks of the glut warning and the intentions display.
  - All test data removed (0 users, farmers, plots, intentions, recommendations).
- **Current blockers:**
  - **The session pooler hangs from this PC since about 10:54 UTC on 29 Oct (§J-13).** `publish`/`load` time out; the HTTPS API and MCP work. The daily task will retry.
  - Phone login needs a Twilio account (§K P1-4).
  - An Android build needs an Expo account.
  - Official ARC costs are missing for most crops.
- **Next recommended action:**
  - Commit and push this batch once the user approves.
  - Confirm the next daily run (or a manual `python -m publish`) succeeds once the pooler path recovers.

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
  migrations/20261030000000_intentions_in_dashboard.sql  intended_area_feddan, intending_farms on dashboard_cells
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
  obour_daily.cmd                    scheduled: collect → commit_snapshots → load obour → publish
  commit_snapshots.py                commit (and push if safe) new data/obour/ snapshots under the repo author
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
  - RLS: PGlite tests plus live grant checks. The security advisor reports only the 5 accepted anonymous-access warnings (§J-11).
  - Anonymous sign-in and the full farm tab (profile, plot, intentions, planted/harvested, harvest report, recommendations): browser E2E against live Supabase, 2026-10-29.
- **Implemented, not verified:**
  - Native Android rendering: only the web build has been run.
  - Phone (WhatsApp) OTP login: its provider is still disabled.
- **Partial:**
  - Recommendations cover only the 4 crops with cost rows.
  - The forecast is a weak baseline.
- **Not implemented:**
  - Glut push alerts.
  - The live `publish` run of intentions on the dashboard (blocked by the pooler, §J-13).
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
| Anonymous sign-in | VERIFIED (web build) | `farm.tsx` `startAnonymously`, Supabase Auth | enabled 2026-10-29; data is lost if the app is reinstalled before a phone is linked |
| Phone OTP login (SMS/WhatsApp) | BLOCKED | `farm.tsx`, Supabase Auth | needs Twilio Verify; plan is SMS first, WhatsApp after Meta approval; then link it to the anonymous user |
| Farm profile/plot/intentions/harvest | VERIFIED (web build) | `farm.tsx` | E2E with an anonymous user 2026-10-29; native device not run |
| Intentions on dashboard (10+ farms) | TESTED; live publish not run | `dashboard.intended`, `publish.py`, `crop/[id].tsx` | app display verified; publish blocked by pooler (§J-13) |
| Glut warning (in-app, when planning a surplus crop) | VERIFIED (web) | `farm.tsx` Plans | |
| Glut push alerts | NOT STARTED | — | needs Expo/FCM project |
| Offline cache (market data) | IMPLEMENTED — storage verified | `src/lib/data.ts` | an actual offline start not tested |
| Snapshot auto-commit | TESTED | `analytics/commit_snapshots.py` | first real commit happens on the next daily run with a new snapshot |
| Mobile lint | VERIFIED | `apps/mobile/eslint.config.js`, `npm run lint` | clean |
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
  - Live versions: `20261028000000`, `20261029000000`, `20261029010000`, `20261029020000`, `20261030000000`.
  - Privacy rule: `dashboard_cells.intended_area_feddan` and `intending_farms` are only filled when 10 or more distinct farms planned the crop (`model/dashboard.py` `MIN_FARMS`).
- **Sources:** FAOSTAT bulk files (QCL, PP, SCL); the official Obour page; `data/manual` (cited news figures and the official wheat price). Full details in [docs/data-dictionary.md](docs/data-dictionary.md).
- **Env vars:**
  - `DATABASE_URL` in `/.env`: the session pooler URI for user `nabta_loader.<ref>`, port 5432.
  - The app embeds the Supabase URL and **publishable** key in `src/lib/supabase.ts`. It's public by design; RLS limits it.
- **Auth:**
  - **Anonymous sign-ins are enabled** on the hosted project (Auth → Sign In / Providers), turned on by the user on 2026-10-29. Anonymous users get the `authenticated` role with `is_anonymous = true`, so the existing `auth.uid()` policies apply unchanged.
  - Phone OTP (WhatsApp channel in the app code): the phone provider is still **disabled** on the hosted project.
  - For local CLI dev only, `config.toml` has a fixed test OTP for a fake number and `enable_anonymous_sign_ins = true`.
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
| `cd analytics && .venv/Scripts/python -m pytest -q` | FAOSTAT parsing, Obour parsing/date logic, dashboard, forecast, EVI incl. spreading, cost growth, selling window, intentions privacy threshold, snapshot auto-commit (temp git repos) | 28/28 pass |
| `cd apps/mobile && npm run lint` | ESLint (eslint-config-expo) | clean |
| `cd apps/mobile && npx tsc --noEmit` | app typecheck | OK |
| Manual, browser at 375×812 | market, crop (maize), compare, login error | OK; month-label overlap fixed afterwards, but only confirmed via tsc, not re-screenshotted |
| Manual, E2E publish with a temporary farm | recommendations written and correct | OK; test rows deleted |

**Gaps:**
- No tests for `load.py` or `publish.py` I/O. A PGlite socket attempt failed because it doesn't support COPY; they were verified against the real DB instead.
- No UI or E2E automated tests.
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
10. **Resolved 2026-10-29:** the farm-tab save buttons had no busy state. They now show a spinner.
11. **Accepted:** 5 security-advisor warnings `auth_allow_anonymous_sign_ins` (farmers, plots, intentions, harvest_reports, recommendations). They're intended, because anonymous farmers own rows, and each policy is limited to `auth.uid()`. Re-check if a policy is ever added without an `auth.uid()` condition.
12. **Slow first data load:** in the 2026-10-29 E2E test the four market queries took about 26 seconds once (all 200). Possibly the free-tier API cold start or the network. The farm tab shows a spinner until then. The market tab now shows cached data in the meantime (offline cache, 2026-10-29).
13. **Session pooler hangs from this PC** (since about 10:54 UTC, 29 Oct). Severity: medium, because the daily load and publish can't run while it lasts.
    - Symptoms:
      - TCP to the pooler on 5432 and 6543 connects, but the client never finishes the handshake.
      - The Supavisor log shows "Connection authenticated" for the attempt, then the backend sits `idle` on `ClientRead` with no query.
      - In other words, the server's replies aren't reaching the client.
    - Not affected: the HTTPS API (200 in about 1 s) and the Supabase MCP connector. The direct host `db.<ref>.supabase.co` doesn't resolve here (IPv6 only).
    - Ruled out: wrong password (no auth errors), a stuck transaction (none), the role timeouts.
    - Workaround while it lasts: run the SQL through MCP. Orphaned idle `nabta_loader` sessions can be ended with `pg_terminate_backend`.
    - Next step: retry later or from another network. If it persists, consider an Edge Function or HTTPS-based loader.

---

## K. Pending tasks and next steps

**P0:** none. (The history-rewrite push was done and verified on 2026-10-29.)

**P1:**
1. **Done 2026-10-29 (`c012c2a`): onion forecast bias**, fixed via the selling window rather than Obour anchoring (why: §J-1).
   - Left: the onion data gap in §J-1.
   - Left: update `docs/agronomy-review.xlsx`, which still shows onion at 180 days.
2. **Done 2026-10-29: backed up the code** to the private GitHub repo (history rewritten to drop AI attribution; verified).
3. **Get official ARC costs per feddan for the other crops.**
   - Where: `data/manual/costs.csv` or `data/templates/costs.csv`, then `python -m load manual` and `python -m publish`.
   - Accept when: recommendations cover all non-perennial crops.
4. **Login.** The user chose anonymous first (2026-10-29).
   1. **Done:** anonymous sign-in, verified end to end in the web build.
   2. **Next:** phone login through Twilio Verify, SMS first, switching to WhatsApp after Meta approval.
      - Needs: the user's Twilio account and Verify service, configured in Supabase Auth → Phone.
      - App work:
        - Switch `signInWithOtp` to `channel: 'sms'` until WhatsApp is approved.
        - Add a "link my number" step for anonymous users: `supabase.auth.updateUser({ phone })`, then `verifyOtp({ type: 'phone_change' })`, so their data is kept.
        - Show sign-out once the user is no longer anonymous.
      - Accept when: a real phone receives a code, and an anonymous user with data links a number and keeps their rows.
   - Alternatives considered: a local SMS gateway via the Send SMS hook; Google sign-in; bank-branch codes.
   - Abuse guard: Supabase rate-limits anonymous sign-ins per IP (`config.toml` `anonymous_users`, hosted default). Add CAPTCHA (Auth → Bot protection) before a public launch.
5. **Android build.**
   - Needs: the user's Expo account.
   - Then: `npx eas-cli@latest build -p android --profile preview` (no `eas.json` yet) and test on a 2 GB RAM phone.

**P2:** (done 2026-10-29: intentions on the dashboard, offline cache, lint, snapshot auto-commit, in-app glut warning)
- Verify a real offline start of the app (airplane mode on a device).
- Governorate-level cells from CAPMAS data.
- Glut push alerts.
- Apply the agronomist's corrections to `seed.sql`.

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
