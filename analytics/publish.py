"""Compute forecasts, the quad dashboard and recommendations from the database, and write them back.

    python -m publish            (from analytics/; after `load`)

All three outputs are replaced in one transaction, so the app never sees a half-updated set.
"""
import sys
from datetime import date

import pandas as pd
import psycopg

from load import copy_rows, database_url
from model import dashboard, evi, forecast


def read(conn, query: str, params: list | None = None) -> pd.DataFrame:
    cur = conn.execute(query, params)
    return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def harvest_prices(crops: pd.DataFrame, fc: pd.DataFrame, today: date) -> dict[str, float]:
    """Forecast price over each crop's next selling window; perennials get the 12-month average."""
    out = {}
    for c in crops.itertuples():
        f = fc[fc.crop_id == c.id]
        if f.empty:
            continue
        plant = evi.next_plant(c.seasons, today)
        if plant is None:
            out[c.id] = float(f.price_egp_per_kg.mean())
        elif (s := evi.selling_price(f, plant, c.cycle_days)) is not None:
            out[c.id] = float(s.price_egp_per_kg)
    return out


def write(cur, table: str, df: pd.DataFrame) -> None:
    rows = (tuple(None if pd.isna(v) else v for v in r) for r in df.itertuples(index=False))
    copy_rows(cur, table, list(df.columns), rows)
    print(f'{table}: {len(df)} rows', file=sys.stderr)


def main(today: date | None = None) -> None:
    today = today or date.today()
    with psycopg.connect(database_url()) as conn:
        stats = read(conn, "select crop_id, year, area_feddan::float, production_t::float from crop_stats "
                           "where gov_id is null and season is null and source = 'faostat'")
        trade = read(conn, "select crop_id, year, export_t::float, import_t::float from trade where month is null")
        prices = read(conn, "select crop_id, market, price_date, granularity::text, avg_egp_per_kg::float, "
                            "max_egp_per_kg::float from prices")
        crops = read(conn, "select id, seasons::text[], soils::text[], water_need, cycle_days from crops")
        costs = read(conn, "select crop_id, year, total_egp_per_feddan::float from costs where gov_id is null")
        farmers = read(conn, "select id, capital_egp::float from farmers")
        plots = read(conn, "select id, farmer_id, area_feddan::float, soil::text, water_source::text from plots")
        season, plant = evi.next_season(today)
        intentions = read(conn, "select i.crop_id, p.farmer_id, i.area_feddan::float from intentions i "
                                "join plots p on p.id = i.plot_id where i.season = %s::season and i.year = %s "
                                "and i.status in ('planned', 'planted')", [season, plant.year])

        fc = forecast.forecasts(prices, today.replace(day=1))
        cells = dashboard.cells(stats, trade, harvest_prices(crops, fc, today), plant.year, intentions)
        recs = evi.recommend(plots, farmers, crops, cells, fc, costs, today)

        with conn.cursor() as cur:
            cur.execute('delete from forecasts where model = %s', [forecast.MODEL])
            write(cur, 'forecasts', fc)
            cur.execute('delete from dashboard_cells where gov_id is null')
            write(cur, 'dashboard_cells', cells)
            cur.execute('delete from recommendations')
            if len(recs):
                write(cur, 'recommendations', recs)
            else:
                print('recommendations: 0 rows (needs production costs and farm plots)', file=sys.stderr)


if __name__ == '__main__':
    main()
