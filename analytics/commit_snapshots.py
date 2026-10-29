"""Commit (and push) new Obour price snapshots so they're backed up on GitHub.

    python -m commit_snapshots        (from analytics/; run by obour_daily.cmd after ingest.obour)

Commits only data/obour/ (the user's other changes, staged or not, are left alone), under the
repo's configured author. Pushes only when that commit is the sole one not yet on the remote, so
the user's own unpushed work is never pushed for them. Does nothing off the main branch.
"""
import subprocess
import sys
from pathlib import Path

SNAPSHOTS = 'data/obour'


def git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def main(root: Path = Path(__file__).resolve().parents[1]) -> str:
    if git(root, 'rev-parse', '--abbrev-ref', 'HEAD') != 'main':
        return 'skipped: not on main'
    if not git(root, 'status', '--porcelain', '--', SNAPSHOTS):
        return 'nothing new'
    newest = sorted(p.stem for p in (root / SNAPSHOTS).glob('*.csv'))[-1]
    git(root, 'add', '--', SNAPSHOTS)
    git(root, 'commit', '-q', '-m', f'Obour prices up to {newest}', '--', SNAPSHOTS)
    try:
        ahead = int(git(root, 'rev-list', '--count', '@{u}..HEAD'))
    except subprocess.CalledProcessError:
        return 'committed; not pushed: no upstream'
    if ahead != 1:
        return f'committed; not pushed: {ahead - 1} other unpushed commit(s)'
    git(root, 'push', '-q')
    return 'committed and pushed'


if __name__ == '__main__':
    print(f'commit_snapshots: {main()}', file=sys.stderr)
