import io
import json

import pytest
import redis
from pywb.warcserver.resource.pathresolvers import RedisResolver

from pywb_arquivo.lmdb_path_index import load
from pywb_arquivo.path_index_benchmark import index_files, main, make_resolvers, page_cache_bytes, possible_paths


class FakeRedis:
    """The few Redis commands used by pywb's RedisResolver and the benchmark, on a dict."""

    def __init__(self, hashes):
        self.hashes = hashes

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def info(self, section):
        if section == 'cpu':
            return {'used_cpu_user': '1.5', 'used_cpu_sys': '0.5'}
        return {'used_memory': 1024 ** 2, 'used_memory_rss': 2 * 1024 ** 2}


@pytest.fixture
def fake_redis(monkeypatch):
    hashes = {}
    monkeypatch.setattr(redis.StrictRedis, 'from_url', classmethod(lambda cls, url, **kwargs: FakeRedis(hashes)))
    return hashes


def load_redis(hashes, key, tsv):
    """Like path-index-to-redis: only the first path of each WARC file name."""
    with open(tsv) as lines:
        for line in lines:
            name, path = line.rstrip('\n').split('\t')[:2]
            hashes.setdefault(key, {})[name] = path


def test_generate_load_and_run(tmp_path, capsys):
    tsv = str(tmp_path / 'AWP.tsv')
    env_path = str(tmp_path / 'pathindex.lmdb')
    results = tmp_path / 'results.json'

    assert main(['generate', '--size', '0.001', tsv]) == 0
    load(env_path, 'branchA', [tsv], out=io.StringIO())
    assert main(['run', '--tsv', tsv, '--lmdb', 'lmdb://' + env_path + '?db=branchA', '--sample', '100',
                 '--lookups', '50', '--workers', '1,2', '--cold', '--json', str(results)]) == 0

    out = capsys.readouterr().out
    assert 'same results (lmdb): 110/110' in out
    data = json.loads(results.read_text())
    assert data['mismatches'] == {'lmdb': 0}
    assert [(row['kind'], row['workers'], row['lookups']) for row in data['results']] == [
        ('tsv', 1, 50), ('lmdb', 1, 50), ('tsv', 2, 100), ('lmdb', 2, 100)]


def test_run_reports_different_results(tmp_path, capsys):
    tsv = tmp_path / 'AWP.tsv'
    tsv.write_text('a.warc.gz\t/data/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')
    env_path = str(tmp_path / 'pathindex.lmdb')
    other = tmp_path / 'other.tsv'
    other.write_text('a.warc.gz\t/other/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')
    load(env_path, 'branchA', [str(other)], out=io.StringIO())

    assert main(['run', '--tsv', str(tsv), '--lmdb', 'lmdb://' + env_path + '?db=branchA', '--sample', '2',
                 '--miss-ratio', '0', '--lookups', '5', '--workers', '1']) == 1
    assert 'same results (lmdb): 1/2, eg. a.warc.gz' in capsys.readouterr().out


def test_run_with_redis(tmp_path, capsys, fake_redis):
    tsv = str(tmp_path / 'AWP.tsv')
    env_path = str(tmp_path / 'pathindex.lmdb')
    results = tmp_path / 'results.json'
    assert main(['generate', '--size', '0.001', tsv]) == 0
    load(env_path, 'branchA', [tsv], out=io.StringIO())
    load_redis(fake_redis, 'pathindex:branchA', tsv)

    assert main(['run', '--tsv', tsv, '--lmdb', 'lmdb://' + env_path + '?db=branchA',
                 '--redis', 'redis://localhost:6379/0/pathindex:branchA', '--sample', '100', '--lookups', '50',
                 '--workers', '1,2', '--cold', '--json', str(results)]) == 0

    out = capsys.readouterr().out
    assert 'same results (lmdb): 110/110' in out
    assert 'same results (redis): 110/110' in out
    assert 'redis memory: 1 MiB, resident 2 MiB' in out
    data = json.loads(results.read_text())
    assert data['mismatches'] == {'lmdb': 0, 'redis': 0}
    assert [(row['kind'], row['workers']) for row in data['results']] == [
        ('tsv', 1), ('lmdb', 1), ('redis', 1), ('tsv', 2), ('lmdb', 2), ('redis', 2)]
    redis_rows = [row for row in data['results'] if row['kind'] == 'redis']
    # the fake server CPU time doesn't change
    assert [(row['server_cpu_us'], row['page_cache_mib']) for row in redis_rows] == [(0, None), (0, None)]
    assert all(row['server_cpu_us'] is None for row in data['results'] if row['kind'] != 'redis')


def test_run_compares_only_the_first_path_with_redis(tmp_path, capsys, fake_redis):
    tsv = tmp_path / 'AWP.tsv'
    tsv.write_text('a.warc.gz\t/data/a.warc.gz\t/backup/a.warc.gz\nb.warc.gz\t/data/b.warc.gz\n')
    fake_redis['pathindex:branchA'] = {'a.warc.gz': '/data/a.warc.gz', 'b.warc.gz': '/other/b.warc.gz'}

    assert main(['run', '--tsv', str(tsv), '--redis', 'redis://localhost:6379/0/pathindex:branchA',
                 '--sample', '2', '--miss-ratio', '0', '--lookups', '5', '--workers', '1']) == 1
    assert 'same results (redis): 1/2, eg. b.warc.gz' in capsys.readouterr().out


def test_run_needs_lmdb_or_redis(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(['run', '--tsv', str(tmp_path / 'AWP.tsv')])
    assert '--lmdb, --redis or both' in capsys.readouterr().err


def test_redis_resolvers_and_paths(fake_redis):
    fake_redis['pathindex:branchA'] = {'a.warc.gz': '/data/a.warc.gz'}
    resolver, = make_resolvers('redis', ['redis://localhost:6379/0/pathindex:branchA'])

    assert isinstance(resolver, RedisResolver)
    assert list(possible_paths(resolver, 'a.warc.gz')) == ['/data/a.warc.gz']
    assert list(possible_paths(resolver, 'missing.warc.gz')) == []
    assert index_files('redis', ['redis://localhost:6379/0/pathindex:branchA']) == []


def test_index_files_of_an_environment_are_counted_once(tmp_path):
    env_path = str(tmp_path / 'pathindex.lmdb')
    assert index_files('lmdb', ['lmdb://' + env_path + '?db=branchA', 'lmdb://' + env_path + '?db=branchB']) == [
        env_path + '/data.mdb']
    assert index_files('tsv', ['a.tsv', 'b.tsv', 'a.tsv']) == ['a.tsv', 'b.tsv']


def test_page_cache_bytes(tmp_path):
    path = tmp_path / 'file'
    path.write_bytes(b'x' * 10000)
    path.read_bytes()

    assert page_cache_bytes(str(path)) > 0
    (tmp_path / 'empty').write_bytes(b'')
    assert page_cache_bytes(str(tmp_path / 'empty')) == 0
