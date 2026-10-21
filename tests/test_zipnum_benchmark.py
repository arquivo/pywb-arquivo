import io
import multiprocessing
import random
import time

import pytest

from pywb_arquivo import lmdb_path_resolver, zipnum_benchmark
from pywb_arquivo.lmdb_zipnum_index import load
from tests.zipnum_test_utils import build_zipnum, cdxj_line


@pytest.fixture(autouse=True)
def close_environments():
    yield
    lmdb_path_resolver.close_environments()


def sample_lines(size=3000):
    rnd = random.Random(1675)
    urls = ['http://{0}/{1}/page{2}'.format(host, path, i) for host in ('example.com', 'www.example.org', 'arquivo.pt')
            for path in ('a', 'b/c') for i in range(size // 30)]
    return sorted(cdxj_line(rnd.choice(urls), rnd.randint(19960101000000, 20251231235959)) for _ in range(size))


@pytest.fixture
def zipnum(tmp_path):
    cdxj = tmp_path / 'test.cdxj'
    lines = sample_lines()
    cdxj.write_bytes(b''.join(lines))
    idx = build_zipnum(str(tmp_path / 'zipnum'), lines, 20, shards=3)
    env_path = str(tmp_path / 'idx.lmdb')
    load(env_path, 'test', idx, out=io.StringIO())
    return idx, 'lmdb://{0}?db=test'.format(env_path), str(cdxj)


def test_queries_like_pywb():
    rnd = random.Random(1)
    queries = zipnum_benchmark.make_queries([b'com,example)/a/b', b'com,example)/', b'pt,arquivo)/x?y=1'], 0.3, rnd)
    for kind, key, end_key in queries:
        assert key < end_key
        if kind == 'exact':
            assert end_key == key + b'!'
        elif kind == 'domain':
            assert key.endswith(b')/') and end_key.endswith(b'-')
        else:
            assert key.endswith(b'/')


@pytest.mark.parametrize('extra', [[], ['--idx-only'], ['--cold'], ['--max-blocks', '2']])
def test_run(zipnum, tmp_path, capsys, extra):
    idx, lmdb_uri, cdxj = zipnum
    json_path = str(tmp_path / 'results.json')

    assert zipnum_benchmark.main(['run', '--idx', idx, '--lmdb', lmdb_uri, '--cdxj', cdxj, '--sample', '200',
                                  '--lookups', '100', '--workers', '1,2', '--json', json_path] + extra) == 0

    out = capsys.readouterr().out
    assert 'same results: 200/200' in out
    assert out.count('| file |') == 2 and out.count('| lmdb |') == 2


def test_run_samples_the_idx(zipnum, capsys):
    idx, lmdb_uri, _ = zipnum

    assert zipnum_benchmark.main(['run', '--idx', idx, '--lmdb', lmdb_uri, '--sample', '50', '--lookups', '20',
                                  '--workers', '1']) == 0
    assert 'same results: ' in capsys.readouterr().out


def test_run_without_the_lmdb_idx(zipnum, tmp_path, capsys):
    idx, _, _ = zipnum

    assert zipnum_benchmark.main(['run', '--idx', idx, '--lmdb', 'lmdb://{0}?db=test'.format(tmp_path / 'missing'),
                                  '--sample', '20', '--lookups', '20', '--workers', '1', '--timeout', '20']) == 1


def sleep_worker(results):
    time.sleep(60)


def test_workers_timeout():
    context = multiprocessing.get_context('fork')
    results = context.Queue()
    processes = [context.Process(target=sleep_worker, args=(results,)) for _ in range(2)]
    for process in processes:
        process.start()

    start = time.monotonic()
    with pytest.raises(zipnum_benchmark.WorkerTimeout, match='2 of 2 workers did not finish in 0.5 s'):
        zipnum_benchmark.collect(processes, results, 0.5)

    assert time.monotonic() - start < 10
    assert not any(process.is_alive() for process in processes)


def test_generate(tmp_path, capsys):
    cdxj = []
    for i, lines in enumerate((sample_lines(2000), sample_lines(1000)[::2])):
        cdxj.append(tmp_path / '{0}.cdxj'.format(i))
        cdxj[-1].write_bytes(b''.join(lines))
    idx = str(tmp_path / 'big' / 'big.idx')

    assert zipnum_benchmark.main(['generate', '--lines', '100', '--block-size', '30', '--line-size', '100',
                                  '--cdxj', str(cdxj[0]), '--cdxj', str(cdxj[1]), idx]) == 0

    # valid, loaded without errors
    stats = load(str(tmp_path / 'idx.lmdb'), 'big', idx, out=io.StringIO())
    assert 80 <= stats.lines <= 200
    assert (tmp_path / 'big' / 'big.loc').read_text().startswith('big-00001.cdx.gz\tbig-00001.cdx.gz\n')
    assert zipnum_benchmark.main(['run', '--idx', idx, '--lmdb', 'lmdb://{0}?db=big'.format(tmp_path / 'idx.lmdb'),
                                  '--idx-only', '--sample', '50', '--lookups', '20', '--workers', '1']) == 0
    # without the shards, only the .idx
    assert zipnum_benchmark.main(['run', '--idx', idx, '--lmdb', 'lmdb://{0}?db=big'.format(tmp_path / 'idx.lmdb'),
                                  '--sample', '50', '--lookups', '20', '--workers', '1']) == 1
