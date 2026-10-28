"""The quad dashboard (التقرير الرباعي): national numbers per crop for the next planning year.

    area now          = latest official area (farmers' app intentions get added once a cell has 10+ farms)
    expected prod     = area now × average yield of the last 3 years
    last year prod    = latest official production
    supply vs demand  = (expected prod + usual imports) vs what the market usually absorbs
                        (production + imports, i.e. home use + exports), 3-year averages
"""
import pandas as pd

YEARS = 3
OUTLOOK_BAND = 0.05  # gap within ±5% of usual absorption counts as balanced


def outlook(gap: float) -> str:
    return 'surplus' if gap > OUTLOOK_BAND else 'deficit' if gap < -OUTLOOK_BAND else 'balanced'


def cells(stats: pd.DataFrame, trade: pd.DataFrame, harvest_price: dict[str, float], year: int) -> pd.DataFrame:
    """stats: national crop_stats rows; trade: yearly trade rows; harvest_price: crop -> EGP/kg;
    year: the planning year the cells are for."""
    rows = []
    for crop, s in stats.dropna(subset=['area_feddan', 'production_t']).groupby('crop_id'):
        s = s.sort_values('year')
        latest = s.iloc[-1]
        recent = s.tail(YEARS)
        yld = recent.production_t.sum() / recent.area_feddan.sum()
        expected = latest.area_feddan * yld

        t = trade[trade.crop_id == crop].merge(s[['year', 'production_t']], on='year').sort_values('year').tail(YEARS)
        gap = None
        if len(t):
            imports = t.import_t.fillna(0)
            demand = (t.production_t + imports).mean()
            gap = (expected + imports.mean()) / demand - 1

        price = harvest_price.get(crop)
        rows.append({
            'crop_id': crop, 'season': None, 'year': year, 'gov_id': None,
            'data_year': int(latest.year),
            'area_now_feddan': round(latest.area_feddan, 1),
            'expected_prod_t': round(expected),
            'last_year_prod_t': round(latest.production_t),
            'demand_t': round(demand) if gap is not None else None,
            'gap_pct': round(gap * 100, 1) if gap is not None else None,
            'outlook': outlook(gap) if gap is not None else None,
            'yield_t_per_feddan': round(yld, 3),
            'price_egp_per_kg': round(price, 2) if price else None,
            'revenue_egp_per_feddan': round(price * 1000 * yld) if price else None,
        })
    return pd.DataFrame(rows)
