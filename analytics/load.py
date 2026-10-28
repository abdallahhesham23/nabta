"""Load processed CSVs into the Supabase database.

    python -m load faostat | obour | all       (from analytics/)

Each (table, source) is replaced in one transaction: readers see the old rows until commit.
Needs DATABASE_URL (Supabase → Connect → Session pooler URI) in the environment or in ../.env.
"""
import csv
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / 'data/processed'
SOURCES = {
    'faostat': [('crop_stats', 'faostat_crop_stats.csv'), ('prices', 'faostat_prices.csv'),
                ('trade', 'faostat_trade.csv')],
    'obour': [('prices', 'obour_prices.csv')],
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


def replace(cur, table: str, path: Path, source: str) -> int:
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    i = header.index('source')
    if any(r[i] != source for r in body):  # never let one source's file wipe another's rows
        raise ValueError(f'{path.name} has rows whose source is not {source!r}')
    cur.execute(sql.SQL('delete from {} where source = %s').format(sql.Identifier(table)), [source])
    cols = sql.SQL(', ').join(map(sql.Identifier, header))
    with cur.copy(sql.SQL('copy {} ({}) from stdin').format(sql.Identifier(table), cols)) as copy:
        for r in body:
            copy.write_row([v if v != '' else None for v in r])
    cur.execute(sql.SQL('select count(*) from {} where source = %s').format(sql.Identifier(table)), [source])
    loaded = cur.fetchone()[0]
    assert loaded == len(body), f'{table}: loaded {loaded} rows, file has {len(body)}'
    return loaded


def main(which: str) -> None:
    names = list(SOURCES) if which == 'all' else [which]
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:  # one transaction
        for source in names:
            for table, file in SOURCES[source]:
                print(f'{table} <- {file}: {replace(cur, table, PROCESSED / file, source)} rows', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in [*SOURCES, 'all']:
        sys.exit(f'usage: python -m load {"|".join([*SOURCES, "all"])}')
    main(sys.argv[1])
