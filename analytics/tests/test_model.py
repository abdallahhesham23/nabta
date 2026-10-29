from datetime import date

import pandas as pd
import pytest

from model import dashboard, evi, forecast


def stats(crop, rows):
    return pd.DataFrame([{'crop_id': crop, 'year': y, 'area_feddan': a, 'production_t': p} for y, a, p in rows])


# ------------------------------------------------------------------ dashboard

def test_dashboard_cell_math():
    s = stats('tomato', [(2021, 100, 1000), (2022, 100, 1200), (2023, 100, 1100), (2024, 150, 1500)])
    t = pd.DataFrame([{'crop_id': 'tomato', 'year': y, 'export_t': 100, 'import_t': 0} for y in (2022, 2023, 2024)])
    c = dashboard.cells(s, t, {"tomato": 5.0}, 2025).iloc[0]
    # yield over last 3 years = 3800 / 350; expected = 150 × that
    assert c.expected_prod_t == round(150 * 3800 / 350)
    assert (c.year, c.data_year, c.last_year_prod_t) == (2025, 2024, 1500)
    assert c.demand_t == round((1200 + 1100 + 1500) / 3)
    assert c.outlook == 'surplus'                       # 1629 vs 1267 usual absorption
    assert c.revenue_egp_per_feddan == round(5.0 * 1000 * 3800 / 350)


def test_dashboard_without_trade_has_no_outlook():
    c = dashboard.cells(stats('wheat', [(2024, 10, 30)]), pd.DataFrame(columns=['crop_id', 'year', 'export_t', 'import_t']), {}, 2025).iloc[0]
    assert c.outlook is None and c.price_egp_per_kg is None


@pytest.mark.parametrize('gap,expected', [(0.06, 'surplus'), (0.05, 'balanced'), (-0.2, 'deficit')])
def test_outlook_band(gap, expected):
    assert dashboard.outlook(gap) == expected


# ------------------------------------------------------------------ forecast

def prices(crop, rows):
    return pd.DataFrame([{'crop_id': crop, 'market': 'farmgate', 'price_date': d, 'granularity': g, 'avg_egp_per_kg': v}
                         for d, g, v in rows])


def test_outliers_spikes_go_but_lasting_jumps_stay():
    # shaped like dry beans: 17 -> 50 -> 75 EGP/kg is the real devaluation jump
    a = pd.Series({2020: 4.0, 2021: 40.0, 2022: 5.0, 2023: 17.0, 2024: 50.0, 2025: 75.0})
    assert forecast.drop_outliers(a).index.tolist() == [2020, 2022, 2023, 2024, 2025]
    assert forecast.drop_outliers(a, ceiling=60).index.tolist() == [2020, 2022, 2023, 2024]


def test_monthly_mean_beats_yearly_figure_when_3_plus_months():
    p = prices('maize', [('2022-01-01', 'year', 9.4)] + [(f'2022-0{m}-01', 'month', 6.0) for m in (1, 2, 3)]
               + [('2023-01-01', 'year', 14.4), ('2023-02-01', 'month', 1.0)])
    assert forecast.annual_series(p).to_dict() == {2022: 6.0, 2023: 14.4}


def test_forecast_skips_value_above_wholesale_and_applies_growth():
    p = prices('citrus', [('2021-01-01', 'year', 4.0), ('2022-01-01', 'year', 5.0), ('2023-01-01', 'year', 70.0)])
    f = forecast.forecast_crop(p, date(2023, 7, 1), months=1, ceiling=13.5)[0]
    # level = 5.0 (2022), growth 25% capped to 15%, mid-2022 -> mid-July 2023 = 1 + 1/24 years
    expected = 5.0 * 1.15 ** (1 + 1 / 24)
    assert f['price_egp_per_kg'] == pytest.approx(expected, abs=0.01)
    assert f['lower_egp_per_kg'] == pytest.approx(expected * 0.7, abs=0.01)


def test_forecast_seasonal_index_from_monthly_data():
    p = prices('tomato', [('2024-01-01', 'month', 2.0), ('2024-04-01', 'month', 4.0), ('2024-07-01', 'month', 6.0)])
    jan, jul = (forecast.forecast_crop(p, date(2024, m, 1), months=1)[0] for m in (1, 7))
    assert jul['price_egp_per_kg'] / jan['price_egp_per_kg'] == pytest.approx(3.0)


# ------------------------------------------------------------------ recommendations

CROPS = pd.DataFrame([
    {'id': 'potato', 'seasons': ['winter'], 'soils': ['sandy', 'loam'], 'water_need': 'medium', 'cycle_days': 110},
    {'id': 'onion', 'seasons': ['winter'], 'soils': ['clay', 'loam'], 'water_need': 'medium', 'cycle_days': 180},
    {'id': 'maize', 'seasons': ['summer'], 'soils': ['clay', 'loam'], 'water_need': 'high', 'cycle_days': 120},
])


def model_inputs(demand=1_000_000):
    cells = pd.DataFrame([{'crop_id': c, 'yield_t_per_feddan': 10.0, 'gap_pct': 0.0, 'demand_t': demand}
                          for c in ('potato', 'onion', 'maize')])
    months = [date(2026, m, 1) for m in range(10, 13)] + [date(2027, m, 1) for m in range(1, 10)]
    fc = pd.DataFrame([{'crop_id': c, 'target_month': m, 'price_egp_per_kg': p, 'lower_egp_per_kg': p * 0.7,
                        'upper_egp_per_kg': p * 1.3} for c, p in (('potato', 6.0), ('onion', 5.0), ('maize', 9.0))
                       for m in months])
    costs = pd.DataFrame([{'crop_id': c, 'year': 2025, 'total_egp_per_feddan': 20000} for c in ('potato', 'onion', 'maize')])
    return cells, fc, costs


def plots(rows):
    return pd.DataFrame([{'id': i, 'farmer_id': f'f{i}', 'area_feddan': a, 'soil': s, 'water_source': 'canal'}
                         for i, (a, s) in enumerate(rows, start=1)])


def farmers(n, capital=None):
    return pd.DataFrame([{'id': f'f{i}', 'capital_egp': capital} for i in range(1, n + 1)])


def test_next_season_and_harvest_month():
    assert evi.next_season(date(2026, 10, 29)) == ('winter', date(2026, 10, 1))
    assert evi.next_season(date(2026, 11, 2)) == ('summer', date(2027, 3, 1))
    assert evi.harvest_month(date(2026, 10, 1), 110) == date(2027, 1, 1)


def test_ranks_by_profit_filters_season_soil_and_capital():
    cells, fc, costs = model_inputs()
    r = evi.recommend(plots([(2, 'loam'), (2, 'sandy'), (2, 'loam')]), farmers(3).assign(capital_egp=[None, None, 10000]),
                      CROPS, cells, fc, costs, date(2026, 10, 29))
    p1 = r[r.plot_id == 1]
    assert p1.crop_id.tolist() == ['potato', 'onion']     # maize is a summer crop
    assert p1.evi.tolist()[0] == 100
    assert r[r.plot_id == 2].crop_id.tolist() == ['potato']  # onion doesn't suit sandy soil
    assert r[r.plot_id == 3].empty                            # 2 feddan × 20k cost > 10k capital
    assert p1.expected_profit_egp_per_feddan.iloc[0] == round(6.0 * 1000 * 10 - 20000 * 1.15)  # 2025 cost grown to 2026


def test_crops_without_cost_data_are_not_ranked():
    cells, fc, costs = model_inputs()
    r = evi.recommend(plots([(1, None)]), farmers(1), CROPS, cells, fc, costs[costs.crop_id != 'potato'], date(2026, 10, 29))
    assert r.crop_id.tolist() == ['onion']


def test_spreading_moves_later_plots_off_the_crowded_crop():
    cells, fc, costs = model_inputs(demand=300)  # tiny market: 20 feddan × 10 t floods it
    r = evi.recommend(plots([(20, None), (20, None)]), farmers(2), CROPS, cells, fc, costs, date(2026, 10, 29))
    top = r[r['rank'] == 1].set_index('plot_id').crop_id
    assert (top[1], top[2]) == ('potato', 'onion')
