import io
import multiprocessing
import os
import random
import subprocess
import sys
from io import BytesIO

import pytest
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from werkzeug.test import Client
from werkzeug.wrappers import Response

from pywb.indexer.cdxindexer import write_cdx_index
from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin, PathIndexResolver, PrefixResolver
from pywb.warcserver.warcserver import WarcServer

from pywb_arquivo import lmdb_path_resolver
from pywb_arquivo.lmdb_path_index import load
from pywb_arquivo.lmdb_path_resolver import LMDBPathIndexResolver, install


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def close_environments():
    yield
    lmdb_path_resolver.close_environments()


@pytest.fixture
def installed():
    make_best_resolver = DefaultResolverMixin.__dict__['make_best_resolver']
    install()
    yield
    DefaultResolverMixin.make_best_resolver = make_best_resolver


@pytest.fixture
def env_path(tmp_path):
    return str(tmp_path / 'pathindex.lmdb')


def load_tsv(env_path, db_name, path, text, **kwargs):
    path.write_bytes(text.encode('utf-8'))
    load(env_path, db_name, [str(path)], out=io.StringIO(), **kwargs)


def load_tsv_process(env_path, db_name, path, text, *args):
    """load on another process, as the environment can only be opened once per process"""
    path.write_bytes(text.encode('utf-8'))
    subprocess.run([sys.executable, '-m', 'pywb_arquivo.lmdb_path_index', 'load', '--env', env_path,
                    '--db', db_name, *args, str(path)], cwd=ROOT_DIR, check=True, capture_output=True)


def random_path_index(rnd, size):
    lines = []
    for i in range(size):
        name = 'AWP{0}-{1:014d}-{2:05d}.arc.gz'.format(rnd.randint(1, 30), rnd.randint(0, 10 ** 14), i)
        lines.append('{0}\t/data/{1}/{0}'.format(name, rnd.randint(1, 9)))
        if rnd.random() < 0.1:
            lines.append('{0}\t/mirror/{0}\thttp://example.org/{0}'.format(name))
        if rnd.random() < 0.05:
            lines[-1] += ' \r'
    lines.append('nação-çá.warc.gz\t/data/nação-çá.warc.gz')
    lines.append('prefix.warc\t/data/prefix.warc')
    lines.append('prefix.warc.gz\t/data/prefix.warc.gz')
    lines.sort(key=lambda line: line.partition('\t')[0].encode('utf-8'))
    return '\n'.join(lines) + '\n'


def test_same_results_as_path_index_resolver(tmp_path, env_path):
    rnd = random.Random(1672)
    tsv = tmp_path / 'AWP.tsv'
    load_tsv(env_path, 'branchA', tsv, random_path_index(rnd, 5000))

    names = [line.partition('\t')[0] for line in tsv.read_text('utf-8').splitlines()]
    names += [name + '.missing' for name in rnd.sample(names, 500)]
    names += [name[:-3] for name in rnd.sample(names, 500)]
    names += ['', 'prefix', 'prefix.war', 'zzz.warc.gz', 'x' * 600]

    tsv_resolver = PathIndexResolver(str(tsv))
    lmdb_resolver = LMDBPathIndexResolver(env_path, 'branchA')
    for name in names:
        assert lmdb_resolver(name, {}) == list(tsv_resolver(name, {})), name

    assert lmdb_resolver('prefix.warc', {}) == ['/data/prefix.warc']
    assert lmdb_resolver('nação-çá.warc.gz', {}) == ['/data/nação-çá.warc.gz']


@pytest.mark.parametrize('uri, env_path, db_name', [
    ('lmdb:///data/warcIndex/pathindex.lmdb?db=branchA', '/data/warcIndex/pathindex.lmdb', 'branchA'),
    ('lmdb:///data/warc%20index/?db=branch%20B', '/data/warc index', 'branch B'),
    ('lmdb:///data/pathindex.lmdb', '/data/pathindex.lmdb', None),
])
def test_from_uri(uri, env_path, db_name):
    resolver = LMDBPathIndexResolver.from_uri(uri)

    assert (resolver.env_path, resolver.db_name) == (env_path, db_name)


@pytest.mark.parametrize('uri', ['lmdb://host/data/pathindex.lmdb', 'lmdb://', 'file:///data/pathindex.lmdb'])
def test_from_uri_invalid(uri):
    with pytest.raises(ValueError):
        LMDBPathIndexResolver.from_uri(uri)


def test_install_adds_the_lmdb_scheme(installed, tmp_path):
    install()

    resolvers = DefaultResolverMixin.make_resolvers(['lmdb:///data/pathindex.lmdb?db=branchA',
                                                     'lmdb:///data/pathindex.lmdb?db=branchB',
                                                     str(tmp_path) + '/'])

    assert [type(resolver) for resolver in resolvers] == [LMDBPathIndexResolver, LMDBPathIndexResolver,
                                                          PrefixResolver]
    assert [resolver.db_name for resolver in resolvers[:2]] == ['branchA', 'branchB']


def test_creating_the_resolver_does_not_open_the_environment(installed, env_path):
    DefaultResolverMixin.make_resolvers(['lmdb://' + env_path + '?db=branchA'])

    assert env_path not in lmdb_path_resolver._environments


def test_missing_environment_and_database(tmp_path, env_path, monkeypatch, caplog):
    monkeypatch.setattr(lmdb_path_resolver, 'RETRY_INTERVAL', 3600)
    resolver_a = LMDBPathIndexResolver(env_path, 'branchA')
    resolver_b = LMDBPathIndexResolver(env_path, 'branchB')

    assert resolver_a('a.warc.gz', {}) == []
    assert 'not available' in caplog.text

    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/branchA/a.warc.gz\n')

    # retried only after the retry interval
    assert resolver_a('a.warc.gz', {}) == []
    resolver_a._retry_at = 0
    assert resolver_a('a.warc.gz', {}) == ['/branchA/a.warc.gz']

    # a missing branchB database doesn't affect branchA
    assert resolver_b('a.warc.gz', {}) == []
    assert resolver_a('a.warc.gz', {}) == ['/branchA/a.warc.gz']


def test_named_databases_are_independent(tmp_path, env_path):
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/branchA/a.warc.gz\n')
    load_tsv(env_path, 'branchB', tmp_path / 'B.tsv', 'a.warc.gz\t/branchB/a.warc.gz\nb.warc.gz\t/branchB/b\n')
    resolver_a = LMDBPathIndexResolver(env_path, 'branchA')
    resolver_b = LMDBPathIndexResolver(env_path, 'branchB')

    assert resolver_a('a.warc.gz', {}) == ['/branchA/a.warc.gz']
    assert resolver_a('b.warc.gz', {}) == []
    assert resolver_b('a.warc.gz', {}) == ['/branchB/a.warc.gz']
    assert resolver_b('b.warc.gz', {}) == ['/branchB/b']

    # both share the same environment
    assert len(lmdb_path_resolver._environments) == 1


def test_sees_the_updates_of_the_loader(tmp_path, env_path):
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/old/a.warc.gz\n', map_size=1024 * 1024)
    resolver = LMDBPathIndexResolver(env_path, 'branchA')
    assert resolver('a.warc.gz', {}) == ['/old/a.warc.gz']

    # the loader grows the map beyond the size known by the resolver
    big = ''.join('{0:08d}.warc.gz\t/data/{1}/{0:08d}.warc.gz\n'.format(i, 'x' * 400) for i in range(40000))
    load_tsv_process(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/new/a.warc.gz\n' + big,
                     '--drop', '--map-size', '1')

    assert resolver('a.warc.gz', {}) == ['/new/a.warc.gz']
    assert resolver('00039999.warc.gz', {}) == ['/data/{0}/00039999.warc.gz'.format('x' * 400)]
    assert lmdb_path_resolver.get_environment(env_path).info()['map_size'] == 1024 ** 3


def lookup_in_worker(resolver, names, queue):
    queue.put([resolver(name, {}) for name in names])


def test_workers_forked_after_creating_the_resolver(tmp_path, env_path):
    # uwsgi creates the pywb app, and the resolvers, before forking the workers
    text = ''.join('{0:05d}.warc.gz\t/data/{0:05d}.warc.gz\n'.format(i) for i in range(1000))
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', text)
    resolver = LMDBPathIndexResolver(env_path, 'branchA')

    context = multiprocessing.get_context('fork')
    queue = context.Queue()
    names = ['{0:05d}.warc.gz'.format(i) for i in range(0, 1000, 7)] + ['missing.warc.gz']
    workers = [context.Process(target=lookup_in_worker, args=(resolver, names, queue)) for _ in range(4)]
    for worker in workers:
        worker.start()
    results = [queue.get(timeout=30) for _ in workers]
    for worker in workers:
        worker.join(timeout=30)
        assert worker.exitcode == 0

    expected = [['/data/' + name] for name in names[:-1]] + [[]]
    assert results == [expected] * 4
    assert resolver('00007.warc.gz', {}) == ['/data/00007.warc.gz']


def test_worker_forked_after_opening_does_not_close_the_parent_environment(tmp_path, env_path):
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/data/a.warc.gz\n')
    resolver = LMDBPathIndexResolver(env_path, 'branchA')
    assert resolver('a.warc.gz', {}) == ['/data/a.warc.gz']

    context = multiprocessing.get_context('fork')
    queue = context.Queue()
    worker = context.Process(target=lookup_in_worker, args=(resolver, ['a.warc.gz'], queue))
    worker.start()
    queue.get(timeout=30)
    worker.join(timeout=30)

    assert resolver('a.warc.gz', {}) == ['/data/a.warc.gz']


def write_warc(path):
    writer = WARCWriter(BytesIO(), gzip=True)
    http_headers = StatusAndHeaders('200 OK', [('Content-Type', 'text/plain')], protocol='HTTP/1.0')
    record = writer.create_warc_record('http://example.com/', 'response', payload=BytesIO(b'ARCHIVED PAGE'),
                                       http_headers=http_headers)
    with open(str(path), 'wb') as out:
        WARCWriter(out, gzip=True).write_record(record)


@pytest.fixture
def warc_collection(tmp_path):
    branch_a = tmp_path / 'branchA'
    branch_b = tmp_path / 'branchB'
    branch_a.mkdir()
    branch_b.mkdir()
    write_warc(branch_b / 'test.warc.gz')

    index = tmp_path / 'index.cdxj'
    with open(str(index), 'wb') as out, open(str(branch_b / 'test.warc.gz'), 'rb') as warc:
        write_cdx_index(out, warc, 'test.warc.gz', cdxj=True)
    return index, branch_a, branch_b


def replay(env_path, index):
    app = WarcServer(config_file=None, custom_config={
        'collections': {'wayback': {
            'index_paths': str(index),
            'archive_paths': ['lmdb://' + env_path + '?db=branchA', 'lmdb://' + env_path + '?db=branchB'],
        }},
        'enable_auto_colls': False,
    })
    return Client(app, Response).get('/wayback/resource?url=http://example.com/')


@pytest.mark.parametrize('branch_a_tsv', [
    # the WARC file is missing on the branch A database
    'other.warc.gz\t{branch_a}/other.warc.gz\n',
    # the WARC file is missing on the branch A disk
    'test.warc.gz\t{branch_a}/test.warc.gz\n',
])
def test_warcserver_loads_from_the_secondary_branch(installed, tmp_path, env_path, warc_collection, branch_a_tsv):
    index, branch_a, branch_b = warc_collection
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', branch_a_tsv.format(branch_a=branch_a))
    load_tsv(env_path, 'branchB', tmp_path / 'B.tsv', 'test.warc.gz\t{0}/test.warc.gz\n'.format(branch_b))

    res = replay(env_path, index)

    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data


def test_warcserver_with_a_missing_secondary_branch(installed, tmp_path, env_path, warc_collection):
    index, branch_a, branch_b = warc_collection
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'test.warc.gz\t{0}/test.warc.gz\n'.format(branch_b))

    res = replay(env_path, index)

    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data


def test_wsgi_application_installs_the_resolver():
    code = ('import pywb_arquivo.wayback\n'
            'from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin\n'
            'print(type(DefaultResolverMixin.make_best_resolver("lmdb:///data/x?db=branchA")).__name__)\n')
    env = dict(os.environ, PYTHONPATH=ROOT_DIR, PYWB_CONFIG_FILE=os.path.join(ROOT_DIR, 'unframed', 'config.yaml'))
    out = subprocess.run([sys.executable, '-c', code], cwd=os.path.join(ROOT_DIR, 'unframed'), env=env,
                         capture_output=True, text=True, check=True).stdout

    assert out.split()[-1] == 'LMDBPathIndexResolver'


def test_lookup_errors_skip_the_resolver(tmp_path, env_path, caplog):
    load_tsv(env_path, 'branchA', tmp_path / 'A.tsv', 'a.warc.gz\t/data/a.warc.gz\n')
    resolver = LMDBPathIndexResolver(env_path, 'branchA')
    assert resolver('a.warc.gz', {}) == ['/data/a.warc.gz']

    lmdb_path_resolver.get_environment(env_path).close()

    assert resolver('a.warc.gz', {}) == []
    assert 'lookup failed' in caplog.text
