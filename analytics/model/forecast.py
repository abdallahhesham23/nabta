"""Baseline farmgate price forecast per crop, monthly, 12 months ahead.

price(month) = level × seasonal index(month) × (1 + growth) ^ (years since the level's year)

- level: latest yearly farmgate price (mean of the months when a year has 3+ monthly figures),
  skipping FAOSTAT entry errors: a one-year spike 3× off both neighbours, or a past farmgate price
  above today's top Obour wholesale price (e.g. oranges 2023 at 70 EGP/kg). Lasting jumps, like the
  2023–24 devaluation, are kept.
- seasonal index: average ratio of each month to its year's mean, over the years with monthly data
- growth: median year-on-year change of the last 3 years, clipped to 0..15%. The 2022–24 jumps
  were a one-off devaluation; projecting them forward tripled prices in 3 years.

shortcut: a fixed ±30% band and no model fitting, because FAOSTAT monthly prices are too sparse
for SARIMA; switch to SARIMA on Obour daily prices once ~2 years of snapshots exist.
"""
from datetime import date

import pandas as pd

MODEL = 'seasonal_naive_v1'
BAND = 0.30
OUTLIER_RATIO = 3
MAX_GROWTH = 0.15  # shortcut: assumed cap near recent food inflation; revisit with Obour history


def annual_series(p: pd.DataFrame) -> pd.Series:
    """Yearly farmgate price: mean of the year's months if there are 3+, else the yearly figure."""
    p = p.assign(y=pd.to_datetime(p.price_date).dt.year)
    yearly = p[p.granularity == 'year'].groupby('y').avg_egp_per_kg.mean()
    months = p[p.granularity == 'month'].groupby('y').avg_egp_per_kg
    monthly = months.mean()[months.count() >= 3]
    return monthly.combine_first(yearly).sort_index()


def off(a: float, b: float) -> bool:
    return not 1 / OUTLIER_RATIO <= a / b <= OUTLIER_RATIO


def drop_outliers(a: pd.Series, ceiling: float | None = None) -> pd.Series:
    if ceiling:
        a = a[a <= ceiling]
    v, keep = a.tolist(), []
    for i in range(len(v)):
        prev = v[keep[-1]] if keep else None
        if prev is not None and i < len(v) - 1 and off(v[i], prev) and off(v[i], v[i + 1]):
            continue  # one-year spike
        keep.append(i)
    return a.iloc[keep]


def seasonal_index(p: pd.DataFrame) -> dict[int, float]:
    m = p[p.granularity == 'month'].assign(d=lambda x: pd.to_datetime(x.price_date))
    if m.empty:
        return {}
    m = m.assign(y=m.d.dt.year, mo=m.d.dt.month)
    m['ratio'] = m.avg_egp_per_kg / m.groupby('y').avg_egp_per_kg.transform('mean')
    return m.groupby('mo').ratio.mean().to_dict()


def forecast_crop(p: pd.DataFrame, start: date, months: int = 12, ceiling: float | None = None) -> list[dict]:
    a = drop_outliers(annual_series(p), ceiling)
    if a.empty:
        return []
    level_year, level = int(a.index[-1]), float(a.iloc[-1])
    growth = (a / a.shift(1)).dropna().tail(3).median() - 1 if len(a) > 1 else 0.0
    growth = min(max(growth, 0.0), MAX_GROWTH)
    season = seasonal_index(p)
    out = []
    for k in range(months):
        target = (pd.Timestamp(start).to_period('M') + k).to_timestamp().date()
        years = (target.year + (target.month - 0.5) / 12) - (level_year + 0.5)
        price = level * season.get(target.month, 1.0) * (1 + growth) ** years
        out.append({'target_month': target, 'price_egp_per_kg': round(price, 2),
                    'lower_egp_per_kg': round(price * (1 - BAND), 2),
                    'upper_egp_per_kg': round(price * (1 + BAND), 2)})
    return out


def forecasts(prices: pd.DataFrame, start: date) -> pd.DataFrame:
    """prices: rows of the prices table. Uses farmgate prices (what farmers are paid)."""
    farm = prices[prices.market == 'farmgate']
    # ceiling = today's top wholesale price: one day's average is too narrow for seasonal crops
    obour = prices[prices.market == 'obour'].sort_values('price_date').groupby('crop_id').max_egp_per_kg.last()
    rows = [{'crop_id': crop, 'market': 'farmgate', 'model': MODEL, **r}
            for crop, p in farm.groupby('crop_id') for r in forecast_crop(p, start, ceiling=obour.get(crop))]
    return pd.DataFrame(rows)
