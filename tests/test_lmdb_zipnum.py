import io
import itertools
import multiprocessing
import os
import random
import subprocess
import sys
from io import BytesIO

import lmdb
import pytest
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from werkzeug.test import Client
from werkzeug.wrappers import Response

from pywb.indexer.cdxindexer import write_cdx_index
from pywb.utils import binsearch
from pywb.utils.loaders import read_last_line
from pywb.warcserver import warcserver
from pywb.warcserver.index.cdxobject import CDXException
from pywb.warcserver.index.zipnum import ZipNumIndexSource
from pywb.warcserver.warcserver import WarcServer, init_index_source

from pywb_arquivo import lmdb_path_resolver, lmdb_zipnum, lmdb_zipnum_index
from pywb_arquivo.lmdb_zipnum import LMDBZipNumIndexSource, install
from pywb_arquivo.lmdb_zipnum_index import load
from tests.zipnum_test_utils import build_zipnum, cdxj_line


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LONG_PATH = 'http://example.com/long/' + 'a' * 600


@pytest.fixture(autouse=True)
def close_environments():
    yield
    lmdb_path_resolver.close_environments()


@pytest.fixture
def installed():
    source_list = list(warcserver.SOURCE_LIST)
    install()
    yield
    warcserver.SOURCE_LIST[:] = source_list


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'idx.lmdb')


def sample_urls(rnd):
    urls = ['http://{0}/page{1}'.format(host, i) for host in ('example.com', 'sub.example.com', 'example.org',
                                                             'arquivo.pt', 'www.fccn.pt') for i in range(40)]
    urls += ['http://example.com/page{0}?q={1}'.format(i, j) for i in range(3) for j in range(5)]
    # first fields longer than the key prefix, some only different after it
    urls += [LONG_PATH + '/{0}'.format(i) for i in range(12)]
    urls += ['http://example.com/long/{0}/{1}'.format('b' * 495, i) for i in range(4)]
    urls += ['http://example.com/nação/{0}'.format(i) for i in range(3)]
    return urls


def sample_cdxj(rnd):
    lines = []
    for url in sample_urls(rnd):
        for _ in range(rnd.choice([1, 1, 2, 3, 8, 30])):
            lines.append(cdxj_line(url, rnd.randint(19960101000000, 20251231235959), status='200'))
    # blocks starting with the same first field, with offsets that are not sorted as text
    for i in range(1000):
        lines.append(cdxj_line('http://example.org/same', 20190101000000, n=i))
    for i in range(40):
        lines.append(cdxj_line(LONG_PATH + '/same', 20200101000000, n=i))
    return sorted(lines)


def queries(rnd):
    urls = sample_urls(rnd)
    urls += ['http://example.org/same', LONG_PATH + '/same', LONG_PATH, 'http://example.com/long/',
             'http://example.com/page1/missing', 'http://example.com/pagf', 'http://other.example.com/',
             'http://a.ac/', 'http://zz.zz/', LONG_PATH + '/missing']
    for url in urls:
        yield {'url': url}
        yield {'url': url, 'showPagedIndex': 'true'}
    for url in rnd.sample(urls, 60) + ['http://example.org/same', LONG_PATH]:
        for match_type in ('prefix', 'host', 'domain'):
            yield {'url': url, 'matchType': match_type}
            yield {'url': url, 'matchType': match_type, 'showNumPages': 'true'}
            yield {'url': url, 'matchType': match_type, 'showNumPages': 'true', 'pageSize': '2'}
            for page in range(4):
                yield {'url': url, 'matchType': match_type, 'page': str(page), 'pageSize': '2'}
                yield {'url': url, 'matchType': match_type, 'page': str(page), 'pageSize': '3',
                       'showPagedIndex': 'true'}
    yield {'url': 'http://example.com/', 'matchType': 'prefix', 'page': 'x'}


def results(source, params):
    try:
        return [str(line) for line in source.load_index(dict(params))]
    except CDXException as e:
        return ['error: ' + str(e)]


def make_sources(idx, env_path, db_name='test', **config):
    file_source = ZipNumIndexSource(idx, dict(config, type='zipnum', path=idx))
    lmdb_source = LMDBZipNumIndexSource(idx, dict(config, type='zipnum', path=idx,
                                                  lmdb='lmdb://{0}?db={1}'.format(env_path, db_name)))
    return file_source, lmdb_source


def load_idx(env_path, db_name, idx, **kwargs):
    return load(env_path, db_name, idx, out=io.StringIO(), **kwargs)


@pytest.fixture(params=[1, 4, 13])
def zipnum(request, tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1675)), request.param)
    load_idx(env_path, 'test', idx)
    return idx


def test_sample_has_long_and_repeated_keys(zipnum):
    with open(zipnum, 'rb') as reader:
        lines = reader.read().splitlines()
    first_fields = [line.partition(b'\t')[0] for line in lines]

    assert max(len(field) for field in first_fields) > 600
    assert len(first_fields) - len(set(first_fields)) > 10
    # repeated first fields with offsets that don't sort as text
    assert any(line > next_line for line, next_line in zip(lines, lines[1:]))


@pytest.mark.parametrize('max_blocks', [2, 10])
def test_same_results_as_the_idx_file(zipnum, env_path, max_blocks):
    file_source, lmdb_source = make_sources(zipnum, env_path, max_blocks=max_blocks)
    rnd = random.Random(1675)

    compared = 0
    for params in queries(rnd):
        expected = results(file_source, params)
        assert results(lmdb_source, params) == expected, params
        compared += bool(expected)
    assert compared > 1000


def test_search_same_lines_as_binsearch(zipnum, env_path):
    _, lmdb_source = make_sources(zipnum, env_path)
    with open(zipnum, 'rb') as reader:
        lines = reader.read().splitlines()
    # the keys of the queries, without tabs, as the lines with the same first
    # field may not be sorted after it
    first_fields = [line.partition(b'\t')[0] for line in lines]
    keys = [field[:length] for field in first_fields for length in (5, 20, 40, 300, 499, 500, 501, 520, -2)]
    keys += [field + suffix for field in first_fields for suffix in (b'', b'\x00', b' ', b'!')]
    keys += [b'', b'0', b'~']

    for key in keys:
        reader = lmdb_source.open_idx()
        for prev_size in (0, 1, 2):
            with open(zipnum, 'rb') as idx_file:
                expected = list(itertools.islice(binsearch.search(idx_file, key, prev_size=prev_size), 20))
            lines = list(itertools.islice(reader.search(key, prev_size), len(expected) + prev_size))
            # binsearch reads from the start of a 8 KiB block, so it may have
            # less previous lines, but always the one pywb uses (prev_size=1)
            # when there is a line >= key, or without one, the last line or none
            skipped = [i for i in range(prev_size + 1) if lines[i:i + len(expected)] == expected]
            assert skipped, (key, prev_size)
            if prev_size == 0 or prev_size == 1 and expected:
                assert lines[:len(expected)] == expected, (key, prev_size)

        end = key + b'!'
        with open(zipnum, 'rb') as idx_file:
            expected = list(itertools.islice(binsearch.iter_range(idx_file, key, end, prev_size=1), 20))
        lines = list(itertools.islice(reader.iter_range(key, end, 1), 20))
        assert lines == expected or not expected and len(lines) <= 1, key
        reader.close()

    reader = lmdb_source.open_idx()
    with open(zipnum, 'rb') as idx_file:
        assert reader.read_last_line() == read_last_line(idx_file)


def test_lmdb_source_uses_pywb_code():
    assert LMDBZipNumIndexSource.compute_page_range.__code__ is ZipNumIndexSource.compute_page_range.__code__
    assert LMDBZipNumIndexSource._load_lmdb_cdx.__code__ is ZipNumIndexSource._do_load_cdx.__code__
    with pytest.raises(ImportError):
        lmdb_zipnum._with_globals(ZipNumIndexSource.compute_page_range, open=open)


def test_install_adds_the_lmdb_option(installed, tmp_path, env_path):
    install()
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)

    source = init_index_source({'type': 'zipnum', 'path': idx, 'lmdb': 'lmdb://' + env_path + '?db=test'})
    assert type(source) is LMDBZipNumIndexSource
    assert source.env_path == env_path and source.db_name == 'test'

    assert type(init_index_source({'type': 'zipnum', 'path': idx})) is ZipNumIndexSource
    assert type(init_index_source(idx)) is ZipNumIndexSource
    assert warcserver.SOURCE_LIST.count(LMDBZipNumIndexSource) == 1


@pytest.mark.parametrize('uri', ['lmdb:///data/idx.lmdb', 'lmdb://host/data/idx.lmdb?db=test', 'file:///x?db=a'])
def test_invalid_lmdb_uri(tmp_path, uri):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)

    with pytest.raises(ValueError):
        LMDBZipNumIndexSource(idx, {'type': 'zipnum', 'path': idx, 'lmdb': uri})


def test_creating_the_source_does_not_open_the_environment(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)

    make_sources(idx, env_path)

    assert not os.path.exists(env_path)


@pytest.mark.parametrize('db_name', ['test', 'other'])
def test_missing_environment_or_database_uses_the_idx_file(tmp_path, env_path, monkeypatch, caplog, db_name):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    if db_name == 'other':
        load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path, db_name=db_name)
    params = {'url': 'http://example.org/same'}
    expected = results(file_source, params)

    assert results(lmdb_source, params) == expected
    assert 'not available' in caplog.text
    assert lmdb_source.open_idx() is None

    # loaded later, used after the retry interval
    lmdb_path_resolver.close_environments()
    load_idx(env_path, db_name, idx, drop=True)
    monkeypatch.setattr(lmdb_zipnum.time, 'monotonic', lambda: lmdb_source._retry_at + 1)
    os.remove(idx)

    assert results(lmdb_source, params) == expected


def test_lookup_errors_use_the_idx_file(tmp_path, env_path, caplog):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path)
    params = {'url': 'http://example.org/same'}
    assert results(lmdb_source, params) == results(file_source, params)

    lmdb_path_resolver.get_environment(env_path).close()

    assert results(lmdb_source, params) == results(file_source, params)
    assert 'lookup failed' in caplog.text


def load_process(env_path, db_name, idx, *args):
    """load on another process, as the environment can only be opened once per process"""
    return subprocess.run([sys.executable, '-m', 'pywb_arquivo.lmdb_zipnum_index', 'load', '--env', env_path,
                           '--db', db_name, *args, idx], cwd=ROOT_DIR, check=True, capture_output=True, text=True)


def test_reload_while_reading(tmp_path, env_path):
    old_idx = build_zipnum(str(tmp_path / 'old'), sample_cdxj(random.Random(1)), 5)
    new_idx = build_zipnum(str(tmp_path / 'new'), sample_cdxj(random.Random(2)) * 1, 3)
    load_idx(env_path, 'test', old_idx, map_size=1024 ** 2)
    old_file, lmdb_source = make_sources(old_idx, env_path)
    new_file = ZipNumIndexSource(new_idx, {'type': 'zipnum', 'path': new_idx})
    params = {'url': 'http://example.com/', 'matchType': 'domain', 'showPagedIndex': 'true'}

    reading = lmdb_source.load_index(dict(params))
    first = str(next(reading))
    # a bigger map size, the reader has to adopt it
    load_process(env_path, 'test', new_idx, '--drop', '--map-size', '1')

    # the query that started before the load still reads the old .idx
    assert [first] + [str(line) for line in reading] == results(old_file, params)
    assert results(lmdb_source, params) == results(new_file, params)


def query_in_worker(source, params, queue):
    queue.put(results(source, params))
    lmdb_path_resolver.close_environments()


def test_forked_workers(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)
    file_source, lmdb_source = make_sources(idx, env_path)
    params = {'url': 'http://example.org/', 'matchType': 'domain'}
    expected = results(file_source, params)
    # opened before forking, like a uWSGI worker without lazy-apps
    assert results(lmdb_source, params) == expected

    context = multiprocessing.get_context('fork')
    queue = context.Queue()
    workers = [context.Process(target=query_in_worker, args=(lmdb_source, params, queue)) for _ in range(3)]
    for worker in workers:
        worker.start()
    worker_results = [queue.get(timeout=30) for _ in workers]
    for worker in workers:
        worker.join(timeout=30)

    assert worker_results == [expected] * 3
    assert results(lmdb_source, params) == expected


def write_warc(path):
    writer = WARCWriter(BytesIO(), gzip=True)
    http_headers = StatusAndHeaders('200 OK', [('Content-Type', 'text/plain')], protocol='HTTP/1.0')
    record = writer.create_warc_record('http://example.com/', 'response', payload=BytesIO(b'ARCHIVED PAGE'),
                                       http_headers=http_headers)
    with open(str(path), 'wb') as out:
        WARCWriter(out, gzip=True).write_record(record)


def test_warcserver_with_the_lmdb_idx(installed, tmp_path, env_path):
    write_warc(tmp_path / 'test.warc.gz')
    cdxj = BytesIO()
    with open(str(tmp_path / 'test.warc.gz'), 'rb') as warc:
        write_cdx_index(cdxj, warc, 'test.warc.gz', cdxj=True)
    lines = sorted(line + b'\n' for line in cdxj.getvalue().splitlines() if not line.startswith(b'!'))
    lines += [cdxj_line('http://example.org/{0}'.format(i), 20200101000000) for i in range(10)]
    idx = build_zipnum(str(tmp_path / 'zipnum'), sorted(lines), 2)
    load_idx(env_path, 'wayback', idx)
    # only the LMDB .idx is used
    os.remove(idx)

    app = WarcServer(config_file=None, custom_config={
        'collections': {'wayback': {
            'index': {'type': 'zipnum', 'path': idx, 'lmdb': 'lmdb://' + env_path + '?db=wayback'},
            'archive_paths': str(tmp_path) + '/',
        }},
        'enable_auto_colls': False,
    })
    client = Client(app, Response)

    res = client.get('/wayback/resource?url=http://example.com/')
    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data

    res = client.get('/wayback/index?url=http://example.org/&matchType=domain&output=text')
    assert res.status_code == 200
    assert len(res.data.splitlines()) == 10

    assert client.get('/wayback/resource?url=http://example.net/').status_code == 404


def test_wsgi_application_installs_the_lmdb_idx():
    code = ('import pywb_arquivo.wayback\n'
            'from pywb.warcserver import warcserver\n'
            'print(warcserver.SOURCE_LIST[0].__name__)\n')
    env = dict(os.environ, PYTHONPATH=ROOT_DIR, PYWB_CONFIG_FILE=os.path.join(ROOT_DIR, 'unframed', 'config.yaml'))
    out = subprocess.run([sys.executable, '-c', code], cwd=os.path.join(ROOT_DIR, 'unframed'), env=env,
                         capture_output=True, text=True, check=True).stdout

    assert out.split()[-1] == 'LMDBZipNumIndexSource'


def test_empty_database(tmp_path, env_path):
    idx = tmp_path / 'empty.idx'
    idx.write_bytes(b'')
    (tmp_path / 'empty.loc').write_bytes(b'')
    load_idx(env_path, 'test', str(idx))
    file_source, lmdb_source = make_sources(str(idx), env_path)

    for source in (file_source, lmdb_source):
        with pytest.raises(IndexError):
            results(source, {'url': 'http://example.com/'})


def test_entries_size(tmp_path, env_path):
    idx = build_zipnum(str(tmp_path / 'zipnum'), sample_cdxj(random.Random(1)), 5)
    load_idx(env_path, 'test', idx)

    env = lmdb.open(env_path, readonly=True, max_dbs=lmdb_path_resolver.MAX_DBS)
    try:
        db = env.open_db(b'test', create=False)
        with env.begin(db=db) as txn:
            entries = list(txn.cursor())
    finally:
        env.close()

    with open(idx, 'rb') as reader:
        lines = reader.read().splitlines()
    assert [lmdb_zipnum.idx_line(key, value) for key, value in entries] == lines
    assert max(len(key) for key, _ in entries) == lmdb_zipnum.KEY_PREFIX_SIZE + lmdb_zipnum.KEY_SUFFIX_SIZE
    # the key prefix isn't repeated on the value
    assert all(len(key) + len(value) == len(line) + lmdb_zipnum.KEY_SUFFIX_SIZE
               for (key, value), line in zip(entries, lines))


def db_entries(env_path):
    env = lmdb.open(env_path, readonly=True, max_dbs=lmdb_path_resolver.MAX_DBS)
    try:
        with env.begin() as txn:
            names = [key for key, _ in txn.cursor()]
        entries = {}
        for name in names:
            db = env.open_db(name, create=False)
            with env.begin(db=db) as txn:
                entries[name.decode('utf-8')] = list(txn.cursor())
        return entries
    finally:
        env.close()


def write_idx(path, lines):
    path.write_bytes(b''.join(lines))
    return str(path)


IDX_LINES = [b'com,example)/ 20200101000000\ttest-01.cdx.gz\t0\t100\t1\n',
             b'com,example)/a 20200101000000\ttest-01.cdx.gz\t100\t100\t2\n',
             b'com,example)/a 20200101000000\ttest-01.cdx.gz\t200\t100\t3\n',
             b'org,example)/ 20200101000000\ttest-02.cdx.gz\t0\t100\t4\n']


@pytest.mark.parametrize('lines, error', [
    ([b'com,example)/ 20200101000000\ttest-01.cdx.gz\t0\t100\n'], 'line 1: expected urlkey'),
    ([b'com,example)/ 20200101000000\ttest-01.cdx.gz\tx\t100\t1\n'], 'line 1: expected urlkey'),
    ([b'\ttest-01.cdx.gz\t0\t100\t1\n'], 'line 1: expected urlkey'),
    (IDX_LINES[:3] + [IDX_LINES[3][:-1]], 'line 4: expected urlkey'),
    ([line.replace(b'\t%d\n' % i, b'\t1\n') for i, line in enumerate(IDX_LINES, 1)],
     'line 2: the line number field is 1, rebuild the .idx'),
    ([IDX_LINES[1].replace(b'\t2\n', b'\t1\n'), IDX_LINES[0].replace(b'\t1\n', b'\t2\n')], 'line 2: not sorted'),
    # sorted as lines, but not by first field: the first field sorts before its tab
    ([b'com,example)/a 2020\ttest-01.cdx.gz\t0\t100\t1\n', b'com,example)/a\ttest-01.cdx.gz\t0\t100\t2\n'],
     'line 2: not sorted'),
])
def test_load_rejects_invalid_idx(tmp_path, env_path, lines, error):
    idx = write_idx(tmp_path / 'test.idx', lines)
    load_idx(env_path, 'other', write_idx(tmp_path / 'other.idx', IDX_LINES))

    for dry_run in (True, False):
        with pytest.raises(ValueError, match=error):
            load_idx(env_path, 'test', idx, dry_run=dry_run)

    # nothing is written
    assert list(db_entries(env_path)) == ['other']


def test_load_stats_and_drop(tmp_path, env_path):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)
    long_line = b'com,example)/' + b'a' * 600 + b' 20200101000000\ttest-01.cdx.gz\t100\t100\t2\n'
    long_idx = write_idx(tmp_path / 'long.idx', [IDX_LINES[0], long_line, IDX_LINES[3].replace(b'\t4\n', b'\t3\n')])
    load_idx(env_path, 'other', idx)

    stats = load_idx(env_path, 'test', idx)
    assert (stats.lines, stats.added, stats.repeated_keys, stats.long_keys, stats.dropped) == (4, 4, 1, 0, 0)

    with pytest.raises(ValueError, match='The database test has 4 entries, replace them with --drop'):
        load_idx(env_path, 'test', long_idx)

    stats = load_idx(env_path, 'test', long_idx, drop=True, dry_run=True)
    assert (stats.lines, stats.added, stats.updated, stats.unchanged, stats.dropped) == (3, 2, 0, 1, 3)
    assert db_entries(env_path)['test'] == db_entries(env_path)['other']

    stats = load_idx(env_path, 'test', long_idx, drop=True)
    assert (stats.lines, stats.added, stats.long_keys, stats.dropped) == (3, 3, 1, 4)

    entries = db_entries(env_path)
    assert [lmdb_zipnum.idx_line(key, value) + b'\n' for key, value in entries['test']] == \
        [IDX_LINES[0], long_line, IDX_LINES[3].replace(b'\t4\n', b'\t3\n')]
    # the other databases are kept
    assert [lmdb_zipnum.idx_line(key, value) + b'\n' for key, value in entries['other']] == IDX_LINES


def test_dry_run_does_not_create_the_environment(tmp_path, env_path):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)

    stats = load_idx(env_path, 'test', idx, dry_run=True)

    assert (stats.lines, stats.added, stats.dropped) == (4, 4, 0)
    assert not os.path.exists(env_path)


def test_main_load_and_stats(tmp_path, env_path, capsys):
    idx = write_idx(tmp_path / 'test.idx', IDX_LINES)

    assert lmdb_zipnum_index.main(['load', '--env', env_path, '--db', 'test', idx]) == 0
    assert 'lines=4' in capsys.readouterr().out
    assert lmdb_zipnum_index.main(['load', '--dry-run', '--env', env_path, '--db', 'test', '--recreate', idx]) == 0
    assert '[dry-run] ' in capsys.readouterr().out
    assert lmdb_zipnum_index.main(['stats', '--env', env_path]) == 0
    assert 'test: entries=4' in capsys.readouterr().out


@pytest.mark.parametrize('args, error', [
    (['--db', 'test', 'missing.idx'], 'error: ZipNum .idx not found'),
    (['--db', '', 'test.idx'], 'error: The LMDB named database is required'),
    (['--db', 'test', '--map-size', '1', 'test.idx'], 'use a bigger --map-size'),
])
def test_main_reports_errors(tmp_path, env_path, capsys, monkeypatch, args, error):
    write_idx(tmp_path / 'test.idx', [b'com,example)/%08d 2020\ttest-01.cdx.gz\t0\t100\t%d\n' % (i, i)
                                      for i in range(1, 10001)])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lmdb_zipnum_index, 'GIB', 64 * 1024)

    assert lmdb_zipnum_index.main(['load', '--env', env_path] + args) == 1
    assert error in capsys.readouterr().err
