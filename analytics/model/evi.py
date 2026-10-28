"""Crop recommendations per farm plot: the EVI (economic viability index, 0–100).

For the next planting season, each crop that fits the plot is scored:
    profit/feddan = forecast price at harvest × 1000 × yield − production cost
    risk          = forecast band width + expected glut (supply above usual demand)
                    + 0.2 if a high-water crop is on well water
    score         = profit × (1 − risk, floored at 10%);   EVI = score as % of the plot's best score

Crops without production-cost data are left out: ranking on revenue alone would push farmers
toward expensive crops. Perennials (fruit trees) are a multi-year decision and are not ranked.

Herd spreading: plots are scored one after another, and each plot's top crop adds its expected
harvest to that crop's supply, so later plots see a bigger glut for crops already recommended.
"""
from datetime import date, timedelta

import pandas as pd

PLANT_MONTH = {'summer': 3, 'nili': 8, 'winter': 10}
WELL_PENALTY = 0.2
TOP = 5


def next_season(today: date) -> tuple[str, date]:
    """The season planting this month, or the next one to come."""
    starts = sorted((date(today.year + (m < today.month), m, 1), s) for s, m in PLANT_MONTH.items())
    return starts[0][1], starts[0][0]


def next_plant(seasons, today: date) -> date | None:
    """Earliest upcoming planting date among a crop's seasons (None for perennials)."""
    dates = [date(today.year + (PLANT_MONTH[s] < today.month), PLANT_MONTH[s], 1) for s in seasons if s in PLANT_MONTH]
    return min(dates, default=None)


def harvest_month(plant: date, cycle_days: int) -> date:
    d = plant + timedelta(days=int(cycle_days))
    return date(d.year, d.month, 1)


def recommend(plots: pd.DataFrame, farmers: pd.DataFrame, crops: pd.DataFrame, cells: pd.DataFrame,
              forecasts: pd.DataFrame, costs: pd.DataFrame, today: date) -> pd.DataFrame:
    season, plant = next_season(today)
    cell = cells.set_index('crop_id')
    cost = costs.sort_values('year').groupby('crop_id').total_egp_per_feddan.last()
    fc = forecasts.set_index(['crop_id', 'target_month'])
    capital = farmers.set_index('id').capital_egp
    added_supply: dict[str, float] = {}
    rows = []

    for plot in plots.sort_values('id').itertuples():
        scored = []
        for c in crops.itertuples():
            if season not in c.seasons or c.id not in cell.index or c.id not in cost.index:
                continue
            if plot.soil and plot.soil not in c.soils:
                continue
            key = (c.id, harvest_month(plant, c.cycle_days))
            if key not in fc.index:
                continue
            f, cl = fc.loc[key], cell.loc[c.id]
            if pd.isna(cl.yield_t_per_feddan):
                continue
            total_cost = cost[c.id] * plot.area_feddan
            if pd.notna(capital.get(plot.farmer_id)) and total_cost > capital[plot.farmer_id]:
                continue
            gap = 0.0
            if pd.notna(cl.gap_pct) and pd.notna(cl.demand_t):
                gap = cl.gap_pct / 100 + added_supply.get(c.id, 0) / cl.demand_t
            risk = (f.upper_egp_per_kg - f.lower_egp_per_kg) / f.price_egp_per_kg / 2 + max(gap, 0)
            if c.water_need == 'high' and plot.water_source == 'well':
                risk += WELL_PENALTY
            profit = f.price_egp_per_kg * 1000 * cl.yield_t_per_feddan - cost[c.id]
            scored.append({'crop_id': c.id, 'score': profit * max(1 - risk, 0.1), 'profit': profit,
                           'risk': risk, 'price': f.price_egp_per_kg, 'yield': cl.yield_t_per_feddan,
                           'cost': cost[c.id]})
        if not scored:
            continue
        best = max(s['score'] for s in scored)
        scored.sort(key=lambda s: -s['score'])
        for rank, s in enumerate(scored[:TOP], start=1):
            rows.append({
                'farmer_id': plot.farmer_id, 'plot_id': plot.id, 'season': season, 'year': plant.year,
                'crop_id': s['crop_id'], 'rank': rank,
                'evi': round(max(s['score'], 0) / best * 100, 1) if best > 0 else 0.0,
                'expected_profit_egp_per_feddan': round(s['profit']), 'risk': round(s['risk'], 3),
                'expected_price_egp_per_kg': s['price'], 'yield_t_per_feddan': s['yield'],
                'cost_egp_per_feddan': s['cost'],
            })
        top = scored[0]
        added_supply[top['crop_id']] = added_supply.get(top['crop_id'], 0) + plot.area_feddan * top['yield']
    return pd.DataFrame(rows)
