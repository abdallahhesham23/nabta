"""Snapshot today's wholesale prices from the Obour market's official page.

    python -m ingest.obour            (from analytics/; run once a day)

The page shows only the latest morning auction, no history, so every run saves the full item list
to data/obour/<auction date>.csv (committed: a missed day can't be recovered). It then rebuilds
data/processed/obour_prices.csv, one row per crop per day, shaped like the `prices` table.
"""
import csv
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

URL = 'http://www.oboormarket.org.eg/prices_ar.aspx'  # HTTPS times out; the site only serves HTTP
SOURCE = 'obour'

CARD = re.compile(
    r"class='status'>([^<]*)</span>.*?<h5[^>]*>([^<]*)</h5>.*?"
    r"من سعر : <strong>\s*([^<]*)</strong> الى سعر : <strong>\s*([^<]*)</strong>", re.S)
PAGE_DATE = re.compile(r'تاريخ اليوم : (\d{1,2})/(\d{1,2})/(\d{4})')

# Item name (normalised) -> crop. Varieties of one crop are combined; excluded items are
# different products sold under a similar name.
CROP_PATTERNS = [
    ('tomato', r'^طماطم'),
    ('potato', r'^بطاطس'),
    ('onion', r'^بصل (ابيض|احمر)'),           # not بصل اخضر (green onion bunches)
    ('green_bean', r'^فاصوليا'),
    ('pepper', r'^فلفل (رومي|حامي)'),          # not فلفل الوان (coloured bell peppers)
    ('cucumber', r'^خيار'),
    ('garlic', r'^ثوم'),
    ('citrus', r'^برتقال'),                   # oranges only, same rule as the FAOSTAT price series
    ('grape', r'^عنب'),
    ('mango', r'^مانجو'),
    ('date', r'^بلح'),
    ('strawberry', r'^فراوله'),
    ('olive', r'^زيتون'),
]


def norm(s: str) -> str:
    """Normalise Arabic spelling variants the page mixes (tatweel, alef/yaa/taa marbuta forms)."""
    s = s.replace('ـ', '')
    s = re.sub('[أإآ]', 'ا', s).replace('ى', 'ي').replace('ة', 'ه')
    return re.sub(r'\s+', ' ', s).strip()


def crop_for(item: str) -> str | None:
    n = norm(item)
    return next((crop for crop, pat in CROP_PATTERNS if re.search(pat, n)), None)


def page_date(html: str, today: date) -> date:
    """The page writes M/D/YYYY, but read it both ways and keep the one near today, so a
    format change can't silently shift dates. Fails if neither is within the last 10 days."""
    m = PAGE_DATE.search(html)
    if not m:
        raise ValueError('auction date not found on page; layout changed?')
    a, b, y = map(int, m.groups())
    candidates = []
    for month, day in {(a, b), (b, a)}:
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if today - timedelta(days=10) <= d <= today + timedelta(days=1):
            candidates.append(d)
    if not candidates:
        raise ValueError(f'auction date {m.group(0)} is not within the last 10 days of {today}')
    return min(candidates, key=lambda d: abs(d - today))


def parse_items(html: str) -> list[dict]:
    items = []
    for unit, name, lo, hi in CARD.findall(html):
        lo, hi = float(lo), float(hi)
        items.append({'item': name.strip(), 'unit': unit.strip(),
                      'min_egp': lo, 'max_egp': hi if hi > 0 else lo})  # max 0 = single price
    if len(items) < 20:
        raise ValueError(f'only {len(items)} items parsed; layout changed?')
    return items


def to_prices(day: date, items: list[dict]) -> list[dict]:
    """One `prices` row per crop: widest min..max across its varieties, mean of variety midpoints."""
    by_crop: dict[str, list[dict]] = {}
    for it in items:
        crop = crop_for(it['item'])
        if crop and it['unit'] == 'كيلو':
            by_crop.setdefault(crop, []).append(it)
    return [{
        'crop_id': crop, 'market': 'obour', 'price_date': day.isoformat(), 'granularity': 'day',
        'min_egp_per_kg': min(i['min_egp'] for i in its),
        'max_egp_per_kg': max(i['max_egp'] for i in its),
        'avg_egp_per_kg': round(sum((i['min_egp'] + i['max_egp']) / 2 for i in its) / len(its), 3),
        'source': SOURCE,
    } for crop, its in sorted(by_crop.items())]


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(root: Path = Path(__file__).resolve().parents[2], today: date | None = None) -> None:
    today = today or date.today()
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (Nabta price collector)'})
    html = urllib.request.urlopen(req, timeout=90).read().decode('utf-8', errors='replace')
    day, items = page_date(html, today), parse_items(html)

    snap_dir = root / 'data/obour'
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap = snap_dir / f'{day.isoformat()}.csv'
    print(f'{day}: {len(items)} items' + (' (already saved)' if snap.exists() else ''), file=sys.stderr)
    if not snap.exists():
        write_csv(snap, items)

    rows = []
    for f in sorted(snap_dir.glob('*.csv')):
        with open(f, encoding='utf-8') as fh:
            saved = [{**r, 'min_egp': float(r['min_egp']), 'max_egp': float(r['max_egp'])} for r in csv.DictReader(fh)]
        rows += to_prices(date.fromisoformat(f.stem), saved)
    (root / 'data/processed').mkdir(parents=True, exist_ok=True)
    write_csv(root / 'data/processed/obour_prices.csv', rows)
    print(f'obour_prices: {len(rows)} rows from {len(list(snap_dir.glob("*.csv")))} days', file=sys.stderr)


if __name__ == '__main__':
    main()
