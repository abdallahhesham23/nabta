"""Import FAOSTAT bulk files for Egypt into CSVs shaped like the Supabase tables.

    python -m ingest.faostat            (from analytics/)

Downloads the bulk zips into data/raw/faostat/ if missing, writes data/processed/faostat_*.csv.
Load those into the crop_stats / prices / trade tables (Supabase Studio CSV import or psql \\copy).
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

BULK_URL = 'https://bulks-faostat.fao.org/production/'
FILES = {
    'production': 'Production_Crops_Livestock_E_All_Data_(Normalized)',
    'prices': 'Prices_E_All_Data_(Normalized)',
    'supply': 'SUA_Crops_Livestock_E_All_Data_(Normalized)',
}
EGYPT = '59'
HA_PER_FEDDAN = 0.420083
SOURCE = 'faostat'

# FAOSTAT item codes per Nabta crop. Quantities of several codes are summed (citrus = its parts);
# prices use the first code only, since an unweighted average of different fruits' prices is meaningless.
CROP_ITEMS = {
    'tomato': ['388'], 'potato': ['116'], 'strawberry': ['544'],
    'green_bean': ['414'],  # "Other beans, green"; 423 "String beans" is negligible in Egypt
    'dry_bean': ['176'],
    'wheat': ['15'], 'maize': ['56'], 'sorghum': ['83'], 'onion': ['403'],
    'garlic': ['406'],  # FAOSTAT names it "Green garlic" but it is Egypt's whole garlic crop
    'cucumber': ['397'], 'pepper': ['401'],
    'citrus': ['490', '495', '497', '507', '512'],  # oranges first: ~70% of Egyptian citrus
    'grape': ['560'], 'mango': ['571'], 'olive': ['260'], 'date': ['577'],
}
ITEM_TO_CROP = {code: crop for crop, codes in CROP_ITEMS.items() for code in codes}
MONTHS = {m: i for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July',
     'August', 'September', 'October', 'November', 'December'], start=1)}


def read_egypt(zip_path: Path) -> pd.DataFrame:
    """Egypt rows for our crops from one normalized bulk zip, with a crop_id column."""
    with zipfile.ZipFile(zip_path) as zf, zf.open(zip_path.stem + '.csv') as f:
        chunks = [c[(c['Area Code'] == EGYPT) & c['Item Code'].isin(ITEM_TO_CROP)]
                  for c in pd.read_csv(f, encoding='latin-1', dtype=str, chunksize=1_000_000)]
    df = pd.concat(chunks, ignore_index=True)
    df['crop_id'] = df['Item Code'].map(ITEM_TO_CROP)
    df['year'] = df['Year'].astype(int)
    df['value'] = pd.to_numeric(df['Value'])
    return df


def _sum_elements(df: pd.DataFrame, elements: dict) -> pd.DataFrame:
    x = df[df['Element Code'].isin(elements)].dropna(subset=['value'])
    out = x.pivot_table(index=['crop_id', 'year'], columns='Element Code', values='value', aggfunc='sum')
    return out.rename(columns=elements).reset_index()


def crop_stats(production: pd.DataFrame) -> pd.DataFrame:
    s = _sum_elements(production, {'5312': 'area_ha', '5510': 'production_t'})
    s['area_feddan'] = (s['area_ha'] / HA_PER_FEDDAN).round(1)
    s['yield_t_per_feddan'] = (s['production_t'] / s['area_feddan']).round(3)
    s['source'] = SOURCE
    return s[['crop_id', 'year', 'area_feddan', 'production_t', 'yield_t_per_feddan', 'source']]


def prices(raw: pd.DataFrame) -> pd.DataFrame:
    primary = {codes[0] for codes in CROP_ITEMS.values()}
    p = raw[(raw['Element Code'] == '5530') & raw['Item Code'].isin(primary)].dropna(subset=['value']).copy()
    annual = p['Months'] == 'Annual value'
    month = p['Months'].map(MONTHS).fillna(1).astype(int)
    p['price_date'] = pd.to_datetime(dict(year=p['year'], month=month, day=1)).dt.date
    p['granularity'] = annual.map({True: 'year', False: 'month'})
    p['avg_egp_per_kg'] = (p['value'] / 1000).round(3)  # LCU (EGP) per tonne -> per kg
    p['market'] = 'farmgate'
    p['source'] = SOURCE
    return p[['crop_id', 'market', 'price_date', 'granularity', 'avg_egp_per_kg', 'source']] \
        .sort_values(['crop_id', 'price_date', 'granularity']).reset_index(drop=True)


def trade(supply: pd.DataFrame) -> pd.DataFrame:
    t = _sum_elements(supply, {'5910': 'export_t', '5610': 'import_t'})
    t['source'] = SOURCE
    return t[['crop_id', 'year', 'export_t', 'import_t', 'source']]


def fetch(raw_dir: Path, name: str) -> Path:
    path = raw_dir / f'{FILES[name]}.zip'
    if not path.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f'downloading {path.name}', file=sys.stderr)
        urllib.request.urlretrieve(BULK_URL + path.name, path)
    return path


def main(root: Path = Path(__file__).resolve().parents[2]) -> None:
    raw_dir, out_dir = root / 'data/raw/faostat', root / 'data/processed'
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        'crop_stats': crop_stats(read_egypt(fetch(raw_dir, 'production'))),
        'prices': prices(read_egypt(fetch(raw_dir, 'prices'))),
        'trade': trade(read_egypt(fetch(raw_dir, 'supply'))),
    }
    for table, df in outputs.items():
        df.to_csv(out_dir / f'faostat_{table}.csv', index=False)
        print(f'{table}: {len(df)} rows, {df.crop_id.nunique()} crops')


if __name__ == '__main__':
    main()
