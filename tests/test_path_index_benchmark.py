import io
import json

from pywb_arquivo.lmdb_path_index import load
from pywb_arquivo.path_index_benchmark import index_files, main, page_cache_bytes


def test_generate_load_and_run(tmp_path, capsys):
    tsv = str(tmp_path / 'AWP.tsv')
    env_path = str(tmp_path / 'pathindex.lmdb')
    results = tmp_path / 'results.json'

    assert main(['generate', '--size', '0.001', tsv]) == 0
    load(env_path, 'branchA', [tsv], out=io.StringIO())
    assert main(['run', '--tsv', tsv, '--lmdb', 'lmdb://' + env_path + '?db=branchA', '--sample', '100',
                 '--lookups', '50', '--workers', '1,2', '--cold', '--json', str(results)]) == 0

    out = capsys.readouterr().out
    assert 'same results: 110/110' in out
    data = json.loads(results.read_text())
    assert data['mismatches'] == 0
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
    assert 'same results: 1/2, eg. a.warc.gz' in capsys.readouterr().out


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
