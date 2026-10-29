"""Load processed CSVs into the Supabase database.

    python -m load faostat | obour | manual | all       (from analytics/)

Each (table, source) is replaced in one transaction: readers see the old rows until commit.
A row's source is the source name, or "name:detail" to cite where a hand-entered figure came from
(e.g. manual:almalnews-2026-08-31); all of a source's rows are replaced together.
Needs DATABASE_URL (Supabase → Connect → Session pooler URI) in the environment or in ../.env.
"""
import csv
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SOURCES = {
    'faostat': [('crop_stats', 'processed/faostat_crop_stats.csv'), ('prices', 'processed/faostat_prices.csv'),
                ('trade', 'processed/faostat_trade.csv')],
    'obour': [('prices', 'processed/obour_prices.csv')],
    'manual': [('costs', 'manual/costs.csv'), ('prices', 'manual/prices.csv')],  # hand-entered, committed
}


def database_url() -> str:
    if url := os.environ.get('DATABASE_URL'):
        return url
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            key, _, value = line.partition('=')
            if key.strip() == 'DATABASE_URL' and value.strip():
                return value.strip().strip('"\'')
    sys.exit('DATABASE_URL not set: add it to .env (see .env.example)')


def copy_rows(cur, table: str, columns: list[str], rows) -> None:
    cols = sql.SQL(', ').join(map(sql.Identifier, columns))
    with cur.copy(sql.SQL('copy {} ({}) from stdin').format(sql.Identifier(table), cols)) as copy:
        for r in rows:
            copy.write_row(r)


def replace(cur, table: str, path: Path, source: str) -> int:
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    i = header.index('source')
    if any(r[i] != source and not r[i].startswith(source + ':') for r in body):
        raise ValueError(f'{path.name} has rows whose source is not {source!r}')  # never wipe another source
    match = sql.SQL('where source = %s or source like %s')
    params = [source, source + ':%']
    cur.execute(sql.SQL('delete from {} ').format(sql.Identifier(table)) + match, params)
    copy_rows(cur, table, header, ([v if v != '' else None for v in r] for r in body))
    cur.execute(sql.SQL('select count(*) from {} ').format(sql.Identifier(table)) + match, params)
    loaded = cur.fetchone()[0]
    assert loaded == len(body), f'{table}: loaded {loaded} rows, file has {len(body)}'
    return loaded


def main(which: str) -> None:
    names = list(SOURCES) if which == 'all' else [which]
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:  # one transaction
        for source in names:
            for table, file in SOURCES[source]:
                print(f'{table} <- {file}: {replace(cur, table, DATA / file, source)} rows', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in [*SOURCES, 'all']:
        sys.exit(f'usage: python -m load {"|".join([*SOURCES, "all"])}')
    main(sys.argv[1])
