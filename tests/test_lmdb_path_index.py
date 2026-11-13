import io
import re
import subprocess
import sys

import lmdb
import pytest

from pywb_arquivo import lmdb_path_index
from pywb_arquivo.lmdb_path_index import LoadStats, iter_path_index, load, main
from pywb_arquivo.lmdb_path_resolver import MAX_READERS


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'pathindex.lmdb')


def write(path, text):
    path.write_bytes(text.encode('utf-8'))
    return str(path)


def read_db(env_path, db_name):
    env = lmdb.open(env_path, readonly=True, max_dbs=8)
    try:
        db = env.open_db(db_name.encode('utf-8'), create=False)
        with env.begin(db=db) as txn:
            return {key.decode('utf-8'): value.decode('utf-8') for key, value in txn.cursor()}
    finally:
        env.close()


def parse(text):
    stats = LoadStats()
    entries = [(key.decode('utf-8'), value.decode('utf-8'))
               for key, value in iter_path_index(io.BytesIO(text.encode('utf-8')), stats)]
    return entries, stats


def test_iter_path_index_parses_like_path_index_resolver():
    entries, stats = parse('a.warc.gz\t/data/a.warc.gz  \r\n'
                           'b.warc.gz\t/data1/b.warc.gz\t/data2/b.warc.gz\n'
                           'b.warc.gz\t/data3/b.warc.gz\n'
                           'c.warc.gz\t\t/data/c.warc.gz\n')

    assert entries == [('a.warc.gz', '/data/a.warc.gz'),
                       ('b.warc.gz', '/data1/b.warc.gz\t/data2/b.warc.gz\t/data3/b.warc.gz'),
                       ('c.warc.gz', '\t/data/c.warc.gz')]
    assert (stats.lines, stats.skipped, stats.unsorted) == (4, 0, 0)


def test_iter_path_index_skips_invalid_lines():
    entries, stats = parse('\n'
                           'no-paths.warc.gz\n'
                           'empty-paths.warc.gz\t  \n'
                           '\t/data/no-name.warc.gz\n'
                           + 'x' * 512 + '\t/data/too-long.warc.gz\n'
                           'z.warc.gz\t/data/z.warc.gz\n')

    assert entries == [('z.warc.gz', '/data/z.warc.gz')]
    assert (stats.lines, stats.skipped) == (6, 5)


def test_iter_path_index_counts_unsorted_lines():
    entries, stats = parse('b\t/b\na\t/a\nc\t/c\n')

    assert [key for key, _ in entries] == ['b', 'a', 'c']
    assert stats.unsorted == 1


def test_load_creates_the_database(tmp_path, env_path):
    tsv = write(tmp_path / 'AWP1.tsv', 'a.warc.gz\t/data/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')

    stats = load(env_path, 'branchA', [tsv], out=io.StringIO())

    assert (stats.files, stats.keys, stats.added) == (1, 2, 2)
    assert read_db(env_path, 'branchA') == {'a.warc.gz': '/data/a.warc.gz', 'b.warc.gz': '/data/b.warc.gz'}


def test_load_updates_a_collection_keeping_the_others(tmp_path, env_path):
    awp1 = write(tmp_path / 'AWP1.tsv', 'a.warc.gz\t/old/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')
    awp2 = write(tmp_path / 'AWP2.tsv', 'x.warc.gz\t/data/x.warc.gz\n')
    load(env_path, 'branchA', [awp1, awp2], out=io.StringIO())

    awp1 = write(tmp_path / 'AWP1.tsv', 'a.warc.gz\t/new/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n'
                                        'c.warc.gz\t/data/c.warc.gz\n')
    stats = load(env_path, 'branchA', [awp1], out=io.StringIO())

    assert (stats.added, stats.updated, stats.unchanged, stats.dropped) == (1, 1, 1, 0)
    assert read_db(env_path, 'branchA') == {'a.warc.gz': '/new/a.warc.gz', 'b.warc.gz': '/data/b.warc.gz',
                                            'c.warc.gz': '/data/c.warc.gz', 'x.warc.gz': '/data/x.warc.gz'}


def test_load_drop_recreates_only_its_database(tmp_path, env_path):
    old = write(tmp_path / 'old.tsv', 'a.warc.gz\t/old/a.warc.gz\nold.warc.gz\t/old/old.warc.gz\n')
    load(env_path, 'branchA', [old], out=io.StringIO())
    load(env_path, 'branchB', [old], out=io.StringIO())

    new = write(tmp_path / 'new.tsv', 'a.warc.gz\t/new/a.warc.gz\n')
    stats = load(env_path, 'branchA', [new], drop=True, out=io.StringIO())

    assert (stats.dropped, stats.added) == (2, 1)
    assert read_db(env_path, 'branchA') == {'a.warc.gz': '/new/a.warc.gz'}
    assert read_db(env_path, 'branchB') == {'a.warc.gz': '/old/a.warc.gz', 'old.warc.gz': '/old/old.warc.gz'}


def start_reader(env_path, read):
    """Open the environment on another process, like a pywb worker, reading or not."""
    code = ('import lmdb, sys\n'
            'env = lmdb.open(sys.argv[1], readonly=True, max_dbs=8)\n'
            'txn = env.begin() if sys.argv[2] == "read" else None\n'
            'print("opened", flush=True)\n'
            'sys.stdin.read()\n')
    reader = subprocess.Popen([sys.executable, '-c', code, env_path, 'read' if read else 'open'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    assert reader.stdout.readline() == 'opened\n'
    return reader


def stop_reader(reader):
    reader.kill()
    reader.wait()
    reader.stdin.close()
    reader.stdout.close()


def test_load_clears_the_readers_of_killed_processes(tmp_path, env_path):
    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/a\n')
    load(env_path, 'branchA', [tsv], out=io.StringIO())

    # a pywb worker killed during a lookup keeps its reader slot, and the old version of the database,
    # while the other workers keep the environment open (otherwise LMDB resets the reader table)
    worker = start_reader(env_path, read=False)
    try:
        stop_reader(start_reader(env_path, read=True))

        out = io.StringIO()
        load(env_path, 'branchA', [tsv], out=out)
        assert out.getvalue().startswith('cleared 1 stale readers\n')

        out = io.StringIO()
        load(env_path, 'branchA', [tsv], out=out)
        assert 'stale readers' not in out.getvalue()
    finally:
        stop_reader(worker)


def test_load_grows_the_reader_table(tmp_path, env_path, monkeypatch):
    # an environment created with the LMDB default size, eg. by another tool
    lmdb.open(env_path).close()
    lmdb_open = lmdb.open
    sizes = []

    def open_env(*args, **kwargs):
        env = lmdb_open(*args, **kwargs)
        sizes.append(env.info()['max_readers'])
        return env

    # the size of the load itself, stats grows the table too
    monkeypatch.setattr(lmdb, 'open', open_env)
    load(env_path, 'branchA', [write(tmp_path / 'AWP1.tsv', 'a\t/a\n')], out=io.StringIO())
    monkeypatch.undo()
    assert sizes == [MAX_READERS]

    out = io.StringIO()
    lmdb_path_index.stats(env_path, out=out)
    assert MAX_READERS > 126
    assert '/{0}\n'.format(MAX_READERS) in out.getvalue()


def test_load_dry_run_does_not_create_the_environment(tmp_path, env_path):
    tsv = write(tmp_path / 'AWP1.tsv', 'a.warc.gz\t/data/a.warc.gz\n')
    out = io.StringIO()

    stats = load(env_path, 'branchA', [tsv], dry_run=True, out=out)

    assert stats.added == 1
    assert not (tmp_path / 'pathindex.lmdb').exists()
    assert '[dry-run] total:' in out.getvalue()


@pytest.mark.parametrize('drop, expected', [
    (False, (1, 1, 1, 0)),
    (True, (3, 0, 0, 3)),
])
def test_load_dry_run_does_not_change_the_database(tmp_path, env_path, drop, expected):
    load(env_path, 'branchA', [write(tmp_path / 'AWP1.tsv', 'a\t/old/a\nb\t/b\nx\t/x\n')], out=io.StringIO())
    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/new/a\nb\t/b\nc\t/c\n')

    stats = load(env_path, 'branchA', [tsv], drop=drop, dry_run=True, out=io.StringIO())

    assert (stats.added, stats.updated, stats.unchanged, stats.dropped) == expected
    assert read_db(env_path, 'branchA') == {'a': '/old/a', 'b': '/b', 'x': '/x'}


def test_load_dry_run_on_a_missing_database(tmp_path, env_path):
    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/a\n')
    load(env_path, 'branchA', [tsv], out=io.StringIO())

    stats = load(env_path, 'branchB', [tsv], drop=True, dry_run=True, out=io.StringIO())

    assert (stats.added, stats.dropped) == (1, 0)


def test_load_directory_files_matching_the_pattern(tmp_path, env_path):
    index_dir = tmp_path / 'branchA'
    index_dir.mkdir()
    (index_dir / 'subdir.tsv').mkdir()
    write(index_dir / 'AWP1.tsv', 'a\t/a\n')
    write(index_dir / 'AWP2.tsv', 'b\t/b\n')
    write(index_dir / 'AWP2.tsv.bak', 'c\t/c\n')
    write(index_dir / 'notes.txt', 'd\t/d\n')

    stats = load(env_path, 'branchA', [str(index_dir)], pattern=r'.*\.tsv', out=io.StringIO())

    assert stats.files == 2
    assert read_db(env_path, 'branchA') == {'a': '/a', 'b': '/b'}


def test_load_directory_without_pattern_loads_all_files(tmp_path, env_path):
    write(tmp_path / 'AWP1.tsv', 'a\t/a\n')
    write(tmp_path / 'other', 'b\t/b\n')

    stats = load(env_path, 'branchA', [str(tmp_path)], out=io.StringIO())

    assert stats.files == 2


def test_load_requires_a_named_database(tmp_path, env_path):
    with pytest.raises(ValueError):
        load(env_path, '', [write(tmp_path / 'AWP1.tsv', 'a\t/a\n')])


def db_exists(env_path, db_name):
    env = lmdb.open(env_path, readonly=True, max_dbs=8)
    try:
        env.open_db(db_name.encode('utf-8'), create=False)
        return True
    except lmdb.NotFoundError:
        return False
    finally:
        env.close()


@pytest.mark.parametrize('tsvs, duplicate, duplicate_files', [
    # on two files
    (['a\t/1/a\nb\t/1/b\n', 'b\t/2/b\nc\t/2/c\n'], 'b', [0, 1]),
    # on non-consecutive lines of a file
    (['a\t/1/a\nb\t/1/b\na\t/2/a\n'], 'a', [0, 0]),
    # the same lines on two files
    (['a\t/1/a\n', 'a\t/1/a\n'], 'a', [0, 1]),
])
@pytest.mark.parametrize('dry_run', [False, True])
def test_load_fails_on_warc_files_loaded_more_than_once(tmp_path, env_path, tsvs, duplicate, duplicate_files,
                                                        dry_run):
    load(env_path, 'branchA', [write(tmp_path / 'old.tsv', 'a\t/old/a\n')], out=io.StringIO())
    files = [write(tmp_path / 'AWP{0}.tsv'.format(i), text) for i, text in enumerate(tsvs)]
    error = 'WARC files on more than one file, or on non-consecutive lines, nothing was loaded: {0} ({1})'.format(
        duplicate, ', '.join(files[i] for i in duplicate_files))

    for drop in (False, True):
        with pytest.raises(ValueError, match=re.escape(error) + '$'):
            load(env_path, 'branchA', files, drop=drop, dry_run=dry_run, out=io.StringIO())
    with pytest.raises(ValueError):
        load(env_path, 'branchB', files, dry_run=dry_run, out=io.StringIO())

    assert read_db(env_path, 'branchA') == {'a': '/old/a'}
    assert not db_exists(env_path, 'branchB')


def test_load_shows_the_first_warc_files_loaded_more_than_once(tmp_path, env_path, monkeypatch):
    monkeypatch.setattr(lmdb_path_index, 'MAX_DUPLICATED_HASHES', 20)
    text = ''.join('{0:03d}\t/{0:03d}\n'.format(i) for i in range(500))
    files = [write(tmp_path / 'AWP1.tsv', text), write(tmp_path / 'AWP2.tsv', text)]

    with pytest.raises(ValueError) as error:
        load(env_path, 'branchA', files, out=io.StringIO())

    names = str(error.value).partition(': ')[2]
    assert names.endswith(', ...')
    assert names.count(' (') == lmdb_path_index.MAX_REPORTED


def test_warc_files_with_the_same_hash_are_not_duplicates(tmp_path):
    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/a\nb\t/b\n')

    # as if a and b had the same hash
    assert lmdb_path_index._find_duplicates([tsv], {hash(b'a'), hash(b'b')}) == {}


@pytest.mark.parametrize('dry_run', [False, True])
def test_load_strict_fails_if_paths_would_be_replaced(tmp_path, env_path, dry_run):
    load(env_path, 'branchA', [write(tmp_path / 'AWP1.tsv', 'a\t/old/a\nb\t/b\n')], out=io.StringIO())
    awp1 = write(tmp_path / 'AWP1.tsv', 'a\t/new/a\nb\t/b\nc\t/c\n')

    with pytest.raises(ValueError, match='^--strict: the paths of 1 WARC files would be replaced, nothing was loaded: a$'):
        load(env_path, 'branchA', [awp1], strict=True, dry_run=dry_run, out=io.StringIO())
    assert read_db(env_path, 'branchA') == {'a': '/old/a', 'b': '/b'}

    # new and unchanged WARC files, or a recreated database, don't fail
    awp2 = write(tmp_path / 'AWP2.tsv', 'b\t/b\nc\t/c\n')
    stats = load(env_path, 'branchA', [awp2], strict=True, dry_run=dry_run, out=io.StringIO())
    assert (stats.added, stats.unchanged) == (1, 1)
    stats = load(env_path, 'branchA', [awp1], strict=True, drop=True, dry_run=dry_run, out=io.StringIO())
    assert (stats.added, stats.updated) == (3, 0)


def test_main_load_and_stats(tmp_path, env_path, capsys):
    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/a\nb\t/b\n')

    assert main(['load', '--env', env_path, '--db', 'branchA', '--map-size', '1', tsv]) == 0
    assert main(['load', '--env', env_path, '--db', 'branchB', '--recreate', tsv]) == 0
    assert main(['stats', '--env', env_path]) == 0

    out = capsys.readouterr().out
    assert 'total: files=1, lines=2, skipped=0, unsorted=0, keys=2, added=2' in out
    assert 'branchA: entries=2' in out
    assert 'branchB: entries=2' in out


def test_main_reports_errors(tmp_path, env_path, capsys):
    assert main(['load', '--env', env_path, '--db', 'branchA', str(tmp_path / 'missing.tsv')]) == 1
    assert main(['load', '--env', env_path, '--db', 'branchA', '--pattern', '(', str(tmp_path)]) == 1
    assert 'error:' in capsys.readouterr().err

    tsv = write(tmp_path / 'AWP1.tsv', 'a\t/a\n')
    assert main(['load', '--env', env_path, '--db', 'branchA', tsv, tsv]) == 1
    assert 'error: WARC files on more than one file' in capsys.readouterr().err

    assert main(['load', '--env', env_path, '--db', 'branchA', tsv]) == 0
    write(tmp_path / 'AWP1.tsv', 'a\t/new/a\n')
    assert main(['load', '--env', env_path, '--db', 'branchA', '--strict', tsv]) == 1
    assert 'error: --strict: the paths of 1 WARC files would be replaced' in capsys.readouterr().err


def test_main_reports_a_full_map(tmp_path, env_path, capsys, monkeypatch):
    monkeypatch.setattr(lmdb_path_index, 'GIB', 64 * 1024)
    tsv = write(tmp_path / 'AWP1.tsv', ''.join('{0:08d}.warc.gz\t/data/{0:08d}.warc.gz\n'.format(i)
                                               for i in range(10000)))

    assert main(['load', '--env', env_path, '--db', 'branchA', '--map-size', '1', tsv]) == 1
    assert 'use a bigger --map-size' in capsys.readouterr().err
