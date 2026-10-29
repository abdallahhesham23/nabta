import subprocess

import commit_snapshots as cs


def run(cwd, *args):
    subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True)


def repo(tmp_path):
    """A clone of a bare 'remote', with one pushed commit and a snapshot folder."""
    remote, root = tmp_path / 'remote.git', tmp_path / 'work'
    run(tmp_path, 'init', '-q', '--bare', '-b', 'main', str(remote))
    run(tmp_path, 'clone', '-q', str(remote), str(root))
    for k, v in (('user.name', 'Test Farmer'), ('user.email', 'farmer@example.com')):
        run(root, 'config', k, v)
    (root / 'data/obour').mkdir(parents=True)
    (root / 'README').write_text('x')
    run(root, 'add', '.')
    run(root, 'commit', '-q', '-m', 'init')
    run(root, 'push', '-q', '-u', 'origin', 'main')
    return root


def log(root, ref='HEAD'):
    return cs.git(root, 'log', '--format=%s|%an', ref)


def test_new_snapshot_is_committed_and_pushed_without_touching_other_changes(tmp_path):
    root = repo(tmp_path)
    (root / 'data/obour/2026-10-30.csv').write_text('item\n')
    (root / 'README').write_text('user edit, not theirs to commit')
    run(root, 'add', 'README')  # even a staged user change stays out of the snapshot commit

    assert cs.main(root) == 'committed and pushed'
    assert log(root, 'origin/main').splitlines()[0] == 'Obour prices up to 2026-10-30|Test Farmer'
    assert 'README' in cs.git(root, 'diff', '--cached', '--name-only')     # still staged, uncommitted
    assert 'Co-Authored-By' not in cs.git(root, 'log', '-1', '--format=%B')
    assert cs.main(root) == 'nothing new'


def test_does_not_push_the_users_unpushed_commits(tmp_path):
    root = repo(tmp_path)
    (root / 'README').write_text('local work')
    run(root, 'commit', '-q', '-am', 'my local work')
    (root / 'data/obour/2026-10-30.csv').write_text('item\n')

    assert cs.main(root) == 'committed; not pushed: 1 other unpushed commit(s)'
    assert log(root, 'origin/main').splitlines()[0] == 'init|Test Farmer'


def test_skips_off_main(tmp_path):
    root = repo(tmp_path)
    run(root, 'checkout', '-q', '-b', 'feature')
    (root / 'data/obour/2026-10-30.csv').write_text('item\n')
    assert cs.main(root) == 'skipped: not on main'
