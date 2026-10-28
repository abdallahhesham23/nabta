# Nabta (نَبْتَة) — Build Plan

Source: `مشروع نبتة 2026.pdf` (Ahmed Abdallah Kalloub, Agricultural Bank of Egypt, Aug 2026).

## 1. What we are building (from the proposal)

An Arabic-first Android app that helps Egyptian farmers pick **what to plant** by showing them the market picture *before* planting, then recommending crops that fit their own land, water and capital.

Core idea: farmers all plant last year's winner (herd behaviour, a bad Nash equilibrium) → glut → price crash. If every farmer sees the same aggregate data (how much is already planted, expected supply vs demand), they spread out.

### MVP scope (Android, pilot of 200 farmers in Sharqia, Beheira, Minya)

| # | Feature | Notes |
|---|---------|-------|
| 1 | Sign-up with phone number | Farmers have phones, not email |
| 2 | Farm profile | Governorate/markaz, area (feddan), soil type, water source, available capital, past crops |
| 3 | **Quad dashboard** (التقرير الرباعي) per crop + season | (a) area planted now nationally, (b) expected production this season, (c) last year's production, (d) supply/demand gap → price outlook |
| 4 | Crop comparison | The crop the farmer wants vs. 2–3 alternatives, side by side on the same numbers |
| 5 | Personalised recommendation (EVI score) | Ranked crops with the numbers behind them, never a bare verdict |
| 6 | Planting intention + post-harvest report | Farmer records what they planted, then actual yield and price — feeds the model |
| 7 | Glut early-warning push alerts | "Tomato area in your region is 40% above last year" |
| 8 | Operator data import | Load ministry / CAPMAS / Obour market / export council files |

**17 crops:** tomato, potato, strawberry, green beans, dry beans, wheat, maize, sorghum, onion, garlic, cucumber, pepper, citrus, grapes, mango, olives, dates. (The proposal's 15, with beans and ذرة each split in two.)

### Deferred (later phases, named so nobody builds them early)
Multi-plot management + paid tier for large farms (1,000 EGP/yr), B2G/B2B dashboards and report sales, targeted ads, contract marketplace (1% commission), expert consultations, in-app learning content, food-security index, iOS and public website, Egyptian-dialect voice assistant, satellite crop-area estimation, weather-driven yield model.

## 2. Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Mobile app | **Expo (React Native) + TypeScript** | Android first, iOS later from the same code. Solid RTL/Arabic. Over-the-air updates via EAS let us fix things mid-pilot without Play Store review. Same language as the later web dashboards. |
| UI | React Native Paper (Material 3), Cairo / Noto Kufi Arabic font | Ready-made accessible components; large touch targets and text for older farmers |
| Charts | `victory-native` | Bar/line charts for the quad dashboard |
| Offline cache | TanStack Query with persisted cache | Rural connectivity: last-fetched dashboard still opens offline |
| Backend | **Supabase** (Postgres, Auth, Row Level Security, Storage, Edge Functions) | No custom API server to write or run. Phone OTP auth built in. Open source and self-hostable, so it can move to an Egyptian data centre if the bank or the data-protection law (Law 151/2020) requires it. |
| Login codes | Supabase phone auth via Twilio Verify, **WhatsApp channel** | Cheaper than SMS and farmers already use WhatsApp. Needs a Meta-approved WhatsApp sender. |
| Push notifications | Expo Notifications (FCM underneath) | Glut alerts, season reminders |
| Analytics / ML | **Python 3.12**: pandas, statsmodels (SARIMA), scikit-learn, pytest | Runs as **scheduled batch jobs** that write forecasts into Postgres tables. The app only reads precomputed numbers, so there's no ML server to host. |
| Job scheduler | GitHub Actions cron (pilot), later a cron container next to Supabase | Daily price ingest, weekly forecast and EVI refresh |
| Operator panel | Supabase Studio + a CSV/Excel import script (MVP) → Next.js admin later | Operators already get a table editor for free |
| Weather (phase 2) | Open-Meteo API | Free, no key |
| Error tracking | Sentry (Expo SDK) | Crashes from low-end Android devices in the field |

### Honest corrections to the proposal's ML plan
- **LSTM is out for now.** Five years of monthly prices is ~60 points per crop, too little for a neural net, and it will overfit. SARIMA plus a seasonal-naive baseline will do better. Revisit LSTM if daily Obour data spanning many years turns up.
- **Random Forest for yield** needs per-region weather and input data. That's phase 2, once weather is wired in. MVP yield = official average yield per feddan per governorate.
- **"Real-time" area data** won't come from the ministry, which publishes seasonally. The truly live part is (a) daily wholesale prices and (b) planting intentions from app users. The dashboard should label each number with its source and date.

## 3. How the numbers are computed

### Quad dashboard (per crop × season × region)
1. **Area planted now** = latest ministry area estimate, plus the delta from app planting intentions once user numbers are meaningful.
2. **Expected production** = area × average yield per feddan (governorate level, from ARC/ministry).
3. **Last year's production** = official figure.
4. **Supply/demand gap** = expected supply − expected demand, where demand ≈ last 3-year average of (production + imports − exports). The gap % maps to a price outlook band using the SARIMA forecast adjusted by a simple price-elasticity factor fitted on history.

### EVI (Economic Viability Index), per farmer × candidate crop
```
expected_profit/feddan = forecast_price × expected_yield − production_cost
risk = forecast price spread (upper − lower) + glut penalty (if gap > 0)
EVI = expected_profit/feddan adjusted for risk, scaled 0–100
```
Hard filters first: season, soil compatibility, water need vs. water source, cost/feddan × area ≤ capital.

### Game-theory step (breaking the herd)
Recommendations are not computed independently per farmer. After ranking, the job tracks **recommended + intended area per crop per region**. Once a crop's projected supply closes its demand gap, its EVI for later farmers is penalised, so the system spreads farmers across crops instead of sending everyone to the same "best" crop. This is the concrete, testable version of the proposal's "Nash equilibrium" section.

### Privacy rule
Farmers see **aggregates only**. Any region/crop cell built from fewer than 10 farms is merged up to the governorate level. No individual farm is ever shown to another user.

## 4. Data model (Postgres, first migration)

```
governorates, markaz            -- reference
crops                           -- 15 crops: season(s), water need, soil suitability, cycle length
seasons                         -- summer / winter / nili, by year
crop_stats      (crop, gov, season, year, area_feddan, production_t, yield_t_per_feddan, source)
prices          (crop, market, date, granularity, min, max, avg EGP/kg, source)
costs           (crop, gov, year, seeds, fertiliser, pesticide, labour, irrigation, total)
trade           (crop, year, month, exports_t, imports_t, source)
farmers         (auth user id, name, phone, gov, markaz, soil, water_source, capital, experience)
plots           (farmer, area_feddan, soil, water_source)       -- 1 plot in MVP, many later
intentions      (plot, crop, season, area, status: planned|planted|harvested)
harvest_reports (intention, yield_t, price_received, sold_at)
forecasts       (crop, target_month, price, lower, upper, model, run_at)
dashboard_cells (crop, season, region, area_now, expected_prod, last_year_prod, gap_pct, outlook, updated_at)
recommendations (farmer, season, crop, evi, expected_profit, risk, rank, run_at)
```
RLS: farmers read/write only their own rows; reference, aggregate and forecast tables are read-only to everyone; writes only by the service role (batch jobs).

## 5. Repository layout

```
nabta/
  apps/mobile/          Expo app (expo-router, TypeScript)
  supabase/
    migrations/         SQL schema + RLS policies
    seed.sql            crops, governorates, sample stats
    functions/          edge functions (only if needed, e.g. push fan-out)
  analytics/
    ingest/             one importer per source (ministry xlsx, CAPMAS, Obour, export council)
    forecast/           SARIMA per crop, writes `forecasts`
    evi/                dashboard cells + EVI + game-theory spreading
    tests/              pytest: EVI math, gap model, spreading cap, importers on fixture files
  data/raw/             source files (gitignored if licensed/sensitive)
  docs/                 data dictionary, source log
```

## 6. Phases

### Phase 0: Data foundation (start now; this is the critical path)
Nothing in the app is meaningful without the data. Collect 2020–2025 for the 15 crops:
- Public, available today: FAOSTAT (Egypt area/production/trade by crop, yearly), CAPMAS annual agricultural bulletins, Ministry of Agriculture Economic Affairs Sector bulletins, Obour market published wholesale prices.
- Via partnership (the bank's role): governorate/season area estimates, ARC production costs, export council monthly data.
- Deliverable: `docs/data-dictionary.md`, filled tables in Postgres, one importer + test per source.
- **Status (2026-10-28):** schema + RLS + seed done and tested. FAOSTAT importer done (national area/production 1961–2024, trade 2010–2023). Blocker: FAOSTAT monthly prices are too sparse for SARIMA, so the price forecast needs Obour or Ministry monthly prices. CAPMAS governorate × season data is still to be entered by hand.

### Phase 1: Backend + analytics core
- Supabase project, schema migration, RLS, seed.
- Importers, SARIMA forecasts with a backtest report (MAPE per crop vs. seasonal-naive), dashboard_cells, EVI, spreading step.
- pytest covering EVI, gap and spreading logic.

### Phase 2: Mobile MVP
- Phone OTP sign-in → farm profile wizard (icons + short Arabic labels, one question per screen).
- Quad dashboard per crop, crop comparison, recommendations list with "why" breakdown.
- Record planting intention; post-harvest report; push alerts.
- RTL throughout, large text, works on a 2 GB RAM Android phone, offline last-view.
- Internal testing build via EAS → Play Store closed testing track.

### Phase 3: Field pilot (one full season)
- 100 users + 100 control farmers in Sharqia, Beheira, Minya, onboarded at bank branches.
- Measure: income vs. control, loss rate, forecast accuracy (MAPE), alert precision.
- Weekly forecast/EVI refresh; WhatsApp support line.
- Add weather (Open-Meteo) and Random Forest yield model if pilot data allows.

### Phase 4: Scale + revenue (after pilot results)
Multi-plot + paid tier, Next.js web dashboard for ministry/bank/B2B, iOS build, voice/Egyptian-dialect assistant, wholesale-market buyer linking, contracts.

## 7. Decisions (answered 2026-10-28)

1. **Data:** start with public sources only (FAOSTAT + CAPMAS + Obour).
2. **Price history:** collect daily Obour prices. Changed on 2026-10-29: the market's own public price page turned up, so the collector reads that instead of news reports. It has no history, so it must run daily from now on.
3. **Hosting:** Supabase Cloud for the pilot. Move to an Egyptian host later if the bank or Law 151/2020 requires it.
4. **Login:** one-time codes over WhatsApp (Twilio Verify).
5. **Bank loan priority:** not in the pilot. Bank branches only help farmers register.
6. **Dashboard regions:** governorate level. Markaz is kept only in the farmer profile.
7. **Crops:** beans split into green and dry; ذرة split into maize and sorghum (17 crops).
8. **Crop agronomy:** to be verified by an ARC agronomist via `docs/agronomy-review.xlsx`.

## 8. Risks I see in the plan itself
- Forecast quality is capped by data quality. Phase 0 can slip, and everything waits on it.
- The spreading mechanism only bites once enough farmers in a region use the app. At pilot scale (100 users) it is mostly a demo; national area data carries the dashboard.
- Projected figures in the proposal (35 bn EGP savings, 15–25% income lift) are hypotheses to be measured in Phase 3, not inputs to the software.
