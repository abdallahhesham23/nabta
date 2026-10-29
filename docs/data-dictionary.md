# Data dictionary and source log

Schema: [`supabase/migrations/20261028000000_init.sql`](../supabase/migrations/20261028000000_init.sql).

## Units (normalised on import)

| Quantity | Unit | Conversion |
|----------|------|------------|
| Area | feddan | 1 feddan = 0.420083 ha (4,200.83 m²) |
| Quantity | tonnes | |
| Price | EGP/kg | FAOSTAT gives EGP/tonne → ÷ 1000 |
| Yield | t/feddan | production ÷ area |

`gov_id` null = national figure. `season` null = all seasons of that year combined.

## Crop IDs

| id | Arabic | FAOSTAT item(s) | Notes |
|----|--------|-----------------|-------|
| tomato | طماطم | 388 | |
| potato | بطاطس | 116 | |
| strawberry | فراولة | 544 | |
| green_bean | فاصوليا خضراء | 414 "Other beans, green" | 423 "String beans" is ~45 ha, ignored |
| dry_bean | فاصوليا جافة | 176 "Beans, dry" | |
| wheat | قمح | 15 | |
| maize | ذرة شامية | 56 | |
| sorghum | ذرة رفيعة | 83 | |
| onion | بصل | 403 | dry onions |
| garlic | ثوم | 406 | FAOSTAT calls it "Green garlic", but it is the whole garlic crop |
| cucumber | خيار | 397 | |
| pepper | فلفل | 401 | green chillies and peppers |
| citrus | موالح | 490+495+497+507+512 | area/production/trade summed; **price = oranges (490)** |
| grape | عنب | 560 | |
| mango | مانجو | 571 | includes guavas (FAOSTAT groups them) |
| olive | زيتون | 260 | |
| date | تمور | 577 | |

## Sources

| Source | Gives | Granularity | Status |
|--------|-------|-------------|--------|
| **FAOSTAT** bulk files (QCL, PP, SCL) | area, production, yield; producer prices; imports/exports | national, yearly (prices partly monthly) | **Automated:** `analytics/ingest/faostat.py`. Area/production 1961–2024, trade 2010–2023. |
| CAPMAS annual bulletin (النشرة السنوية للمساحات المحصولية والإنتاج النباتي) | area and production **by governorate and season** | governorate × season, yearly | **Manual.** Catalog at censusinfo.capmas.gov.eg wasn't reachable from the build machine; try from Egypt. Enter via `data/templates/crop_stats.csv`. |
| Ministry of Agriculture, Economic Affairs Sector bulletins | area, production, yields, costs by governorate | governorate × season | Via partnership. Same template. |
| Obour wholesale market (official page `http://www.oboormarket.org.eg/prices_ar.aspx`) | daily wholesale min/max prices for ~147 items from the morning auction | daily, latest auction only | **Automated:** `analytics/ingest/obour.py`. The page has no history, so the collector must run **every day**. Raw snapshots go to `data/obour/<date>.csv` (committed). Covers 11 of our crops: no wheat, maize, sorghum or dry beans; strawberry only in season; olives not listed. News reports (El Watan) were the fallback plan, but its archive only has ~27 past articles, so they aren't used. |
| Agricultural Research Center | production cost per feddan | crop × governorate, yearly | **Not available online.** Interim: `data/manual/costs.csv` (see below). Replace with ARC figures when they arrive. |
| Hand-entered figures (`data/manual/`, committed) | production costs; official wheat procurement price | national | `python -m load manual`. Each row's `source` cites its origin (`manual:<publisher>-<date>`). |
| Agricultural Export Council | monthly exports | monthly | Manual. Use the `trade` table with `month` set. |

`source` column values: `faostat`, `capmas`, `moa`, `obour`, `arc`, `aec`.

## Interim production costs (`data/manual/costs.csv`)

These are costs per feddan **excluding land rent**, taken from news reports quoting the head of the farmers' syndicate and growers. They are not official. The recommendation scoring scales each figure to the planting year at 15%/yr.

| Crop | EGP/feddan | Year | Basis | Source |
|------|-----------:|-----:|-------|--------|
| Tomato | 100,000 | 2026 | stated "without rent" | [Al Mal, 31 Aug 2026](https://almalnews.com/2132560/) |
| Onion | 50,000 | 2026 | 85,000 total minus 35,000 winter rent | [Al Mal, 21 Apr 2026](https://almalnews.com/2109485/) |
| Wheat | 17,800 | 2023 | itemised 23,800 minus 6,000 rent | [Al Mal, 19 Jan 2023](https://almalnews.com/1451900/) |
| Potato | 120,000 | 2024 | rent basis **not stated**, so may include rent | [Al Mal, 23 Jul 2024](https://almalnews.com/1810713/) |

Left out on purpose:
- **Maize:** the only 2026 "study" prices maize at 4 EGP/kg, a 2020-era price, so its costs aren't credible either.
- **Garlic and strawberry:** only undated or contradictory figures exist (garlic "over 25k"; strawberry quoted at up to 700k).
- **Cucumber, pepper, beans and sorghum:** no current figures found.

Crops with no cost row get no recommendation.

Wheat farmgate price for 2026: the official procurement price of 2,350 EGP/ardeb (150 kg) = 15.67 EGP/kg, with 15.00 for the lowest cleanliness grade ([CNBC Arabia, Aug 2025](https://www.cnbcarabia.com/142117/2025/27/08/)). It's loaded as a 2026 yearly farmgate price, so the forecast is anchored on it.

## Known data issues

- **Onion is still optimistic, but less so (fixed in part on 2026-10-29).**
  - The main bug: the price was read in a single "harvest month" that landed on the pre-harvest peak (old stock runs out in March and April at about 18 EGP/kg, then the price falls to about 8 in May).
  - The fix: prices now average the harvest month and the 2 months after it (`model/evi.py` `selling_price`), and onion's cycle was corrected from 180 to 210 days (October nursery → April–May harvest).
  - Onion's selling price went from 18.35 to 12.22 EGP/kg. It still ranks first for a loam winter plot (about 133k EGP profit per feddan, against tomato's 98k).
  - What's left: the reported spring-2026 glut (about 4 EGP/kg farmgate) isn't in FAOSTAT, whose data ends in 2024. Obour daily history through the 2027 harvest, or Ministry monthly prices for 2025–26, would fix this.
  - Anchoring to today's Obour price was considered and rejected: October wholesale (about 17.5) is old stored crop and would push the spring forecast *up*.

- **Price history is too thin for forecasting.** FAOSTAT has monthly Egyptian producer prices only for some crops and years: tomato, potato, wheat and maize have 36 months in 2020–2024, with 2021 and 2023 missing. The rest have one figure a year, or none. SARIMA needs a few years of unbroken monthly data, so the price forecast depends on getting Obour or Ministry monthly prices.
- **Obour prices are per variety.** The collector combines varieties into one row per crop: min = lowest min, max = highest max, avg = mean of the variety midpoints. Excluded look-alikes: coloured bell peppers, green onion bunches, lemons and other non-orange citrus. Only items priced per kilo are kept.
- **Oranges 2023 annual producer price = 70.04 EGP/kg**, about 10× its neighbours. This is likely a FAOSTAT entry error. It's kept as imported; the forecasting step must treat it as an outlier.
- **FAOSTAT area = harvested area, not planted area.** The dashboard's "area planted now" needs CAPMAS/Ministry season estimates plus farmers' planting intentions in the app.
- FAOSTAT figures for recent years are often estimated or imputed (FAO flags E/I). These flags aren't stored, so prefer CAPMAS/Ministry figures for the same year when both exist.
- FAOSTAT's SUA production figures differ slightly from QCL. Production is taken from QCL only; SUA is used just for imports and exports.
- **Crop agronomy in `seed.sql` is provisional:** seasons, water need, suitable soils and cycle length are general defaults. They're out for review by an ARC agronomist in [`agronomy-review.xlsx`](agronomy-review.xlsx); apply the corrections to `seed.sql` when it comes back.
