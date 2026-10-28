import zipfile

import pandas as pd
import pytest

from ingest import faostat

COLS = ['Area Code', 'Item Code', 'Element Code', 'Year', 'Months', 'Value']


def make_zip(tmp_path, rows):
    name = 'Fake_E_All_Data_(Normalized)'
    path = tmp_path / f'{name}.zip'
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr(f'{name}.csv', pd.DataFrame(rows, columns=COLS).to_csv(index=False))
    return path


def test_crop_stats_converts_units_sums_citrus_and_drops_other_countries(tmp_path):
    df = faostat.read_egypt(make_zip(tmp_path, [
        ['59', '388', '5312', '2024', None, '42008.3'],    # tomato area, ha
        ['59', '388', '5510', '2024', None, '6000000'],    # tomato production, t
        ['59', '490', '5312', '2024', None, '420.083'],    # oranges
        ['59', '495', '5312', '2024', None, '420.083'],    # tangerines -> same crop
        ['59', '490', '5510', '2024', None, '10000'],
        ['2', '388', '5312', '2024', None, '999'],         # Afghanistan, dropped
        ['59', '999', '5312', '2024', None, '1'],          # item we don't track, dropped
    ]))
    s = faostat.crop_stats(df).set_index('crop_id')
    assert s.loc['tomato', 'area_feddan'] == 100000.0
    assert s.loc['tomato', 'yield_t_per_feddan'] == 60.0
    assert s.loc['citrus', 'area_feddan'] == 2000.0
    assert set(s.index) == {'tomato', 'citrus'}
    assert (s['source'] == 'faostat').all()


def test_prices_split_annual_and_monthly_and_use_primary_item_only(tmp_path):
    df = faostat.read_egypt(make_zip(tmp_path, [
        ['59', '388', '5530', '2024', 'Annual value', '6574'],
        ['59', '388', '5530', '2024', 'October', '18059.4'],
        ['59', '388', '5532', '2024', 'Annual value', '130'],   # USD element, ignored
        ['59', '495', '5530', '2024', 'Annual value', '9000'],  # tangerine: not the citrus price series
        ['59', '490', '5530', '2024', 'Annual value', '8000'],
    ]))
    p = faostat.prices(df)
    tom = p[p.crop_id == 'tomato'].set_index('granularity')
    assert tom.loc['year', 'avg_egp_per_kg'] == pytest.approx(6.574)
    assert str(tom.loc['month', 'price_date']) == '2024-10-01'
    assert p[p.crop_id == 'citrus'].avg_egp_per_kg.tolist() == [8.0]
    assert len(p) == 3


def test_trade_sums_exports_and_imports(tmp_path):
    df = faostat.read_egypt(make_zip(tmp_path, [
        ['59', '490', '5910', '2023', None, '100'],
        ['59', '495', '5910', '2023', None, '50'],
        ['59', '490', '5610', '2023', None, '8'],
        ['59', '490', '5510', '2023', None, '3700000'],   # production row in SUA, ignored here
    ]))
    t = faostat.trade(df).iloc[0]
    assert (t.crop_id, t.year, t.export_t, t.import_t) == ('citrus', 2023, 150, 8)
