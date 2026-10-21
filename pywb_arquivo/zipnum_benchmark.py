"""Benchmark the ZipNum queries with the secondary index (``.idx``) on the
file (pywb's ``ZipNumIndexSource``) and on LMDB (``LMDBZipNumIndexSource``).

Run it on the server with a ZipNum, after loading its ``.idx`` with
:mod:`pywb_arquivo.lmdb_zipnum_index`::

    python -m pywb_arquivo.zipnum_benchmark run --idx /data/zipnum/RAQ2019/RAQ2019.idx \\
        --lmdb 'lmdb:///data/zipnum/idx.lmdb?db=RAQ2019' --workers 1,4,16

The urlkeys of the queries are sampled from the ``.idx``, or from the CDXJ
files the ZipNum was built from (``--cdxj``), which gives keys of every block
and not only of their first lines. Most queries are exact, like the replay
ones, the others are prefix and domain queries, and some urlkeys are missing.
The queries are of the first page, with pywb's ``max_blocks`` (10 by default).

Each query is timed in two parts: the lookups on the ``.idx`` (pywb's
``compute_page_range``) and the read of the blocks of CDX lines on the shards
(``idx_to_cdx``). ``--idx-only`` times only the first part, for an ``.idx``
without its shards, eg. one of the size of the production indexes made with
``generate``::

    python -m pywb_arquivo.zipnum_benchmark generate --lines 6500000 --block-size 3000 \\
        --cdxj /data/indexes_cdx/RAQ2019.cdxj --cdxj /data/indexes_cdx/SAWP5.cdxj /data/bench/big-3000.idx

It reports the latency of the queries (p50, p95, p99) and of their ``.idx``
part, the throughput of all the workers, the CPU time, major page faults and
block reads per query, and how much of the ``.idx`` (or of the LMDB
``data.mdb``) and of the shards is on the page cache after the run. ``--cold``
drops them from the page cache before each run, without root, unless they are
mapped by other processes (eg. pywb). Before the runs, it checks that both
return the same ``.idx`` and CDX lines for every query of the sample.
"""
import argparse
import heapq
import itertools
import json
import multiprocessing
import os
import queue
import random
import resource
import sys
import time

from pywb.utils.binsearch import INDEX_FILE_BUFFER_SIZE
from pywb.warcserver.index.cdxobject import CDXObject
from pywb.warcserver.index.query import CDXQuery
from pywb.warcserver.index.zipnum import ZipNumIndexSource

from pywb_arquivo.lmdb_path_resolver import close_environments
from pywb_arquivo.lmdb_zipnum import LMDBZipNumIndexSource
from pywb_arquivo.path_index_benchmark import drop_page_cache, mib, page_cache_bytes, percentile


# appended to the urlkeys of the missing queries
MISSING_SUFFIX = b'/zipnum-benchmark-missing'

# share of the queries of each match type, the others are exact
PREFIX_RATIO = 0.1
DOMAIN_RATIO = 0.1


def sample_urlkeys(paths, size, rnd):
    """Sample urlkeys at random offsets of the ``.idx`` or CDXJ files, weighted by size."""
    sizes = [os.path.getsize(path) for path in paths]
    urlkeys = set()
    attempts = 0
    while len(urlkeys) < size and attempts < size * 10:
        attempts += 1
        path = rnd.choices(paths, weights=sizes)[0]
        with open(path, 'rb') as reader:
            reader.seek(rnd.randrange(max(os.path.getsize(path), 1)))
            reader.readline()
            line = reader.readline()
            if not line:
                # past the last line
                reader.seek(0)
                line = reader.readline()
        urlkey = line.split(b' ', 1)[0].split(b'\t', 1)[0]
        if urlkey and not urlkey.startswith(b'!'):
            urlkeys.add(urlkey)
    return sorted(urlkeys)


def inc_last_byte(key):
    return key[:-1] + bytes([key[-1] + 1])


def make_queries(urlkeys, miss_ratio, rnd):
    """``(match type, key, end key)`` of the queries of the urlkeys, as pywb's ``calc_search_range``."""
    queries = []
    for urlkey in urlkeys:
        if rnd.random() < miss_ratio:
            urlkey += MISSING_SUFFIX
        host, sep, path = urlkey.partition(b')')
        kind = rnd.random()
        if kind < DOMAIN_RATIO and sep:
            queries.append(('domain', host + b')/', host + b'-'))
        elif kind < DOMAIN_RATIO + PREFIX_RATIO and b'/' in path:
            prefix = host + sep + path[:path.rindex(b'/') + 1]
            queries.append(('prefix', prefix, inc_last_byte(prefix)))
        else:
            queries.append(('exact', urlkey, urlkey + b'!'))
    return queries


def cdx_query(key, end_key):
    query = CDXQuery({'url': 'http://zipnum-benchmark/'})
    query.set_key(key, end_key)
    return query


def make_source(kind, idx, lmdb_uri, max_blocks):
    config = {'type': 'zipnum', 'path': idx, 'max_blocks': max_blocks}
    if kind == 'file':
        return ZipNumIndexSource(idx, config)
    return LMDBZipNumIndexSource(idx, dict(config, lmdb=lmdb_uri))


def open_idx(source):
    if isinstance(source, LMDBZipNumIndexSource):
        reader = source.open_idx()
        if reader is None:
            raise RuntimeError('LMDB .idx not available: ' + source.config['lmdb'])
        return reader
    return open(source.summary, 'rb', buffering=INDEX_FILE_BUFFER_SIZE)


def idx_lines(source, query):
    """The ``.idx`` lines of the first page of the query, as pywb's ``_do_load_cdx``."""
    reader = open_idx(source)
    try:
        return list(source.compute_page_range(reader, query))
    finally:
        reader.close()


def cdx_lines(source, lines, query):
    """The CDX lines of the blocks of the ``.idx`` lines, as pywb's ``_do_load_cdx``."""
    return [CDXObject(line) for block in source.idx_to_cdx(lines, query) for line in block]


def check_same_results(sources, queries, idx_only, results):
    """The queries LMDB returns differently from the ``.idx`` file, and the
    size of the pages of the LMDB database."""
    try:
        reader = open_idx(sources[1])
    except RuntimeError as e:
        results.put(e)
        return
    stat = reader.txn.stat(reader.db)
    lmdb_size = (stat['branch_pages'] + stat['leaf_pages'] + stat['overflow_pages']) * stat['psize']
    reader.close()

    mismatches = []
    for _, key, end_key in queries:
        query = cdx_query(key, end_key)
        lines = [idx_lines(source, query) for source in sources]
        same = lines[0] == lines[1]
        if same and not idx_only:
            same = [str(cdx) for cdx in cdx_lines(sources[0], lines[0], query)] == \
                [str(cdx) for cdx in cdx_lines(sources[1], lines[1], query)]
        if not same:
            mismatches.append(key.decode('utf-8', 'replace'))
    close_environments()
    results.put((mismatches, lmdb_size))


def run_worker(source, queries, idx_only, barrier, results):
    idx_times = [None] * len(queries)
    times = [None] * len(queries)
    blocks = cdx = 0
    # opens the LMDB environment, once per worker like on uWSGI
    idx_lines(source, cdx_query(*queries[0][1:]))
    barrier.wait()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    for i, (_, key, end_key) in enumerate(queries):
        query = cdx_query(key, end_key)
        start = time.perf_counter_ns()
        lines = idx_lines(source, query)
        idx_end = time.perf_counter_ns()
        if not idx_only:
            cdx += len(cdx_lines(source, lines, query))
        end = time.perf_counter_ns()
        idx_times[i] = idx_end - start
        times[i] = end - start
        blocks += len(lines)
    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    close_environments()
    results.put({
        'times': times,
        'idx_times': idx_times,
        'exact_times': [t for t, query in zip(times, queries) if query[0] == 'exact'],
        'blocks': blocks,
        'cdx': cdx,
        'cpu': (end_usage.ru_utime + end_usage.ru_stime) - (usage.ru_utime + usage.ru_stime),
        'majflt': end_usage.ru_majflt - usage.ru_majflt,
        'inblock': end_usage.ru_inblock - usage.ru_inblock,
    })


class WorkerTimeout(Exception):
    pass


def collect(processes, results, timeout):
    """The result of each process, killing them all if they don't finish in ``timeout`` seconds."""
    deadline = time.monotonic() + timeout
    collected = []
    try:
        for _ in processes:
            collected.append(results.get(timeout=max(deadline - time.monotonic(), 0.1)))
    except queue.Empty:
        for process in processes:
            process.kill()
        raise WorkerTimeout('{0} of {1} workers did not finish in {2} s'.format(
            len(processes) - len(collected), len(processes), timeout))
    finally:
        for process in processes:
            process.join(timeout=max(deadline - time.monotonic(), 1))
    return collected


def run(kind, source, worker_queries, idx_only, timeout, context):
    """Run the queries of each worker on its own process, all at the same time."""
    workers = len(worker_queries)
    barrier = context.Barrier(workers + 1)
    results = context.Queue()
    processes = []
    for queries in worker_queries:
        process = context.Process(target=run_worker, args=(source, queries, idx_only, barrier, results))
        process.start()
        processes.append(process)

    barrier.wait(timeout=timeout)
    start = time.perf_counter()
    collected = collect(processes, results, timeout)
    elapsed = time.perf_counter() - start

    times = sorted(t for result in collected for t in result['times'])
    idx_times = sorted(t for result in collected for t in result['idx_times'])
    exact_times = sorted(t for result in collected for t in result['exact_times']) or [0]
    total = len(times)
    return {
        'kind': kind,
        'workers': workers,
        'queries': total,
        'throughput': total / elapsed,
        'mean_us': sum(times) / total / 1000,
        'p50_us': percentile(times, 50) / 1000,
        'p95_us': percentile(times, 95) / 1000,
        'p99_us': percentile(times, 99) / 1000,
        'max_us': times[-1] / 1000,
        'idx_mean_us': sum(idx_times) / total / 1000,
        'idx_p50_us': percentile(idx_times, 50) / 1000,
        'idx_p99_us': percentile(idx_times, 99) / 1000,
        'exact_p50_us': percentile(exact_times, 50) / 1000,
        'exact_p99_us': percentile(exact_times, 99) / 1000,
        'blocks': sum(result['blocks'] for result in collected) / total,
        'cdx': sum(result['cdx'] for result in collected) / total,
        'cpu_us': sum(result['cpu'] for result in collected) / total * 1e6,
        'majflt': sum(result['majflt'] for result in collected) / total,
        'inblock': sum(result['inblock'] for result in collected) / total,
    }


def index_files(source):
    if isinstance(source, LMDBZipNumIndexSource):
        return [os.path.join(source.env_path, 'data.mdb')]
    return [source.summary]


def shard_files(source):
    resolver = source.loc_resolver
    return sorted({path for paths in getattr(resolver, 'loc_map', {}).values() for path in paths
                   if os.path.isfile(path)})


def files_size(paths):
    return sum(os.path.getsize(path) for path in paths if os.path.exists(path))


def cached_mib(files):
    cached = [page_cache_bytes(path) for path in files if os.path.exists(path)]
    return None if None in cached else sum(cached) / 1024 ** 2


def benchmark(args):
    rnd = random.Random(args.seed)
    context = multiprocessing.get_context('fork')
    # created before forking the workers, like the uWSGI workers, LMDB is opened by each worker
    sources = {kind: make_source(kind, args.idx, args.lmdb, args.max_blocks) for kind in ('file', 'lmdb')}
    shards = shard_files(sources['file'])
    if not args.idx_only and not shards:
        print('error: no shards found, use --idx-only to time only the .idx', file=sys.stderr)
        return 1

    urlkeys = sample_urlkeys(args.cdxj or [args.idx], args.sample, rnd)
    queries = make_queries(urlkeys, args.miss_ratio, rnd)
    print('sample: {0} queries ({1}), {2} missing'.format(
        len(queries), ', '.join('{0} {1}'.format(sum(1 for q in queries if q[0] == kind), kind)
                                for kind in ('exact', 'prefix', 'domain')),
        sum(1 for q in queries if q[1].endswith(MISSING_SUFFIX))))
    files = {kind: index_files(source) for kind, source in sources.items()}
    for kind, paths in files.items():
        print('{0} .idx: {1} MiB'.format(kind, mib(files_size(paths))))
    print('shards: {0} files, {1} MiB'.format(len(shards), mib(files_size(shards))))

    # on another process, so this one doesn't keep the LMDB files mapped
    results = context.Queue()
    process = context.Process(target=check_same_results, args=(
        [sources['file'], sources['lmdb']], queries, args.idx_only, results))
    process.start()
    checked = collect([process], results, args.timeout)[0]
    if isinstance(checked, Exception):
        print('error: {0}'.format(checked), file=sys.stderr)
        return 1
    mismatches, lmdb_size = checked
    print('lmdb database: {0} MiB, {1:.2f}x the .idx'.format(mib(lmdb_size), lmdb_size / files_size([args.idx])))
    print('same results: {0}/{1}{2}'.format(len(queries) - len(mismatches), len(queries),
                                            ', eg. ' + ', '.join(mismatches[:5]) if mismatches else ''))

    rows = []
    for workers in args.workers:
        # the same queries on both
        worker_queries = [[rnd.choice(queries) for _ in range(args.lookups)] for _ in range(workers)]
        for kind, source in sources.items():
            if args.cold:
                drop_page_cache(files[kind] + shards)
            try:
                row = run(kind, source, worker_queries, args.idx_only, args.timeout, context)
            except WorkerTimeout as e:
                print('{0}, {1} workers: {2}'.format(kind, workers, e), file=sys.stderr)
                row = {'kind': kind, 'workers': workers, 'error': str(e)}
            row['idx_cache_mib'] = cached_mib(files[kind])
            row['shards_cache_mib'] = cached_mib(shards)
            rows.append(row)

    print_table(rows, args.cold, args.idx_only)
    if args.json:
        with open(args.json, 'w') as out:
            json.dump({'cold': args.cold, 'idx_only': args.idx_only, 'max_blocks': args.max_blocks,
                       'sample': len(queries), 'mismatches': len(mismatches), 'idx': args.idx, 'lmdb': args.lmdb,
                       'lmdb_db_mib': lmdb_size / 1024 ** 2,
                       'idx_mib': {kind: files_size(paths) / 1024 ** 2 for kind, paths in files.items()},
                       'shards_mib': files_size(shards) / 1024 ** 2,
                       'results': rows}, out, indent=2)
    return 1 if mismatches or any('error' in row for row in rows) else 0


def print_table(rows, cold, idx_only):
    print()
    print('page cache: {0}{1}'.format('cold' if cold else 'warm', ', .idx only' if idx_only else ''))
    print('| .idx | workers | queries/s | mean µs | p50 µs | p95 µs | p99 µs | max µs | exact p50 µs | exact p99 µs '
          '| .idx mean µs | .idx p50 µs | .idx p99 µs | blocks/query | CPU µs/query | major faults/query '
          '| block reads/query | .idx page cache MiB | shards page cache MiB |')
    print('|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|')
    for row in rows:
        cache = ['-' if row[name] is None else '{0:.0f}'.format(row[name])
                 for name in ('idx_cache_mib', 'shards_cache_mib')]
        if 'error' in row:
            print('| {kind} | {workers} | {error} |'.format(**row))
            continue
        print('| {kind} | {workers} | {throughput:,.0f} | {mean_us:.1f} | {p50_us:.1f} | {p95_us:.1f} | '
              '{p99_us:.1f} | {max_us:,.0f} | {exact_p50_us:.1f} | {exact_p99_us:.1f} | {idx_mean_us:.1f} | '
              '{idx_p50_us:.1f} | {idx_p99_us:.1f} | '
              '{blocks:.2f} | {cpu_us:.1f} | {majflt:.3f} | {inblock:.3f} | {0} | {1} |'.format(*cache, **row))


def cdxj_first_fields(paths):
    """The ``urlkey timestamp`` of the lines of the sorted CDXJ files, merged."""
    def first_fields(path):
        with open(path, 'rb') as reader:
            for line in reader:
                if not line.startswith(b'!'):
                    yield line.partition(b' {')[0].rstrip(b'\n')

    return heapq.merge(*(first_fields(path) for path in paths))


def generate(args):
    """Write an ``.idx`` of about ``--lines`` lines and its ``.loc``, from the
    lines of the CDXJ files, without shards: each ``.idx`` line has the
    ``urlkey timestamp`` of every n-th CDXJ line, and the part, offset and
    length of a block of ``--block-size`` lines of about 100 bytes compressed
    each, in shards of 100 MB."""
    rnd = random.Random(args.seed)
    total = sum(os.path.getsize(path) for path in args.cdxj) / args.line_size
    step = max(int(total / args.lines), 1)
    base = os.path.splitext(os.path.basename(args.output))[0]
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    shard = offset = lines = 0
    with open(args.output, 'wb') as out:
        for first_field in itertools.islice(cdxj_first_fields(args.cdxj), 0, None, step):
            if not offset or offset > 100 * 1024 ** 2:
                shard += 1
                offset = 0
            length = int(args.block_size * 100 * rnd.uniform(0.5, 1.5))
            lines += 1
            out.write(b'%s\t%s-%05d.cdx.gz\t%d\t%d\t%d\n' % (first_field, base.encode('utf-8'), shard, offset,
                                                             length, lines))
            offset += length

    with open(os.path.splitext(args.output)[0] + '.loc', 'w') as out:
        for part in range(1, shard + 1):
            out.write('{0}-{1:05d}.cdx.gz\t{0}-{1:05d}.cdx.gz\n'.format(base, part))
    print('{0}: {1} lines, every {2} CDXJ lines, {3} MiB'.format(args.output, lines, step,
                                                                 mib(os.path.getsize(args.output))))
    return 0


def main(args=None):
    parser = argparse.ArgumentParser(prog='python -m pywb_arquivo.zipnum_benchmark',
                                     description='Benchmark the ZipNum .idx on the file and on LMDB.')
    commands = parser.add_subparsers(dest='command', required=True)

    run_parser = commands.add_parser('run', help='compare the .idx file and the LMDB .idx')
    run_parser.add_argument('--idx', required=True, help='ZipNum .idx file, with its .loc')
    run_parser.add_argument('--lmdb', required=True, help='LMDB .idx uri, eg. lmdb:///data/idx.lmdb?db=RAQ2019')
    run_parser.add_argument('--cdxj', action='append', help='sample the urlkeys from these CDXJ files')
    run_parser.add_argument('--idx-only', action='store_true', help="time only the .idx, don't read the shards")
    run_parser.add_argument('--max-blocks', type=int, default=ZipNumIndexSource.DEFAULT_MAX_BLOCKS,
                            help='pywb max_blocks of the index (default: %(default)s)')
    run_parser.add_argument('--sample', type=int, default=20000, help='urlkeys to sample')
    run_parser.add_argument('--miss-ratio', type=float, default=0.1, help='missing urlkeys ratio')
    run_parser.add_argument('--lookups', type=int, default=5000, help='queries per worker')
    run_parser.add_argument('--workers', type=lambda value: [int(n) for n in value.split(',')], default=[1, 4],
                            help='comma separated number of worker processes (default: 1,4)')
    run_parser.add_argument('--cold', action='store_true', help='drop the .idx and shards from the page cache first')
    run_parser.add_argument('--timeout', type=float, default=1800,
                            help='seconds to wait for the workers of each run (default: %(default)s)')
    run_parser.add_argument('--seed', type=int, default=1675)
    run_parser.add_argument('--json', help='also write the results to this json file')

    generate_parser = commands.add_parser('generate', help='generate an .idx without shards from CDXJ files')
    generate_parser.add_argument('--cdxj', action='append', required=True, help='sorted CDXJ file')
    generate_parser.add_argument('--lines', type=int, required=True, help='about how many .idx lines to write')
    generate_parser.add_argument('--block-size', type=int, default=3000, help='CDXJ lines per block')
    generate_parser.add_argument('--line-size', type=int, default=550,
                                 help='average size of the CDXJ lines, to estimate their number')
    generate_parser.add_argument('--seed', type=int, default=1675)
    generate_parser.add_argument('output', help='.idx file to write')

    args = parser.parse_args(args)
    if args.command == 'run':
        return benchmark(args)
    return generate(args)


if __name__ == '__main__':
    sys.exit(main())
