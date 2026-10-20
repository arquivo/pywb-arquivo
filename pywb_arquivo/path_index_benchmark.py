"""Benchmark the WARC file name resolution of the TSV path index (pywb's
``PathIndexResolver``), of the LMDB path index (``LMDBPathIndexResolver``) and,
optionally, of a Redis path index (pywb's ``RedisResolver``).

Run it on the server with the real path indexes, after loading them with
:mod:`pywb_arquivo.lmdb_path_index`::

    python -m pywb_arquivo.path_index_benchmark run \\
        --tsv /data/warcIndex/branchA/AWP1.tsv --tsv /data/warcIndex/branchA/AWP2.tsv \\
        --lmdb 'lmdb:///data/warcIndex/pathindex.lmdb?db=branchA' --workers 1,4,16

``--redis redis://localhost:6379/0/pathindex:branchA`` adds pywb's Redis
resolver, with the hashes loaded by ``path-index-to-redis`` (replay-cdxj-indexing-tools).

Or generate a synthetic sorted TSV path index to try it::

    python -m pywb_arquivo.path_index_benchmark generate --size 1 /tmp/bench/AWP.tsv

Each implementation resolves the same random sample of WARC file names (with
some missing ones), like pywb: each resolver is tried in order until one
returns a path. The resolvers are created before forking the worker
processes, like the uWSGI workers.

It reports the lookup latency (p50, p95, p99), the throughput of all the
workers, the CPU time and major page faults per lookup, and how much of the
index files is on the page cache after the run. ``--cold`` drops the index
files from the page cache before each run, without root, unless they are
mapped by other processes (eg. pywb). For Redis, it also reports the CPU time
of the Redis server per lookup, and its memory instead of the page cache.
"""
import argparse
import ctypes
import json
import mmap
import multiprocessing
import os
import random
import resource
import sys
import time

import redis
from pywb.warcserver.resource.pathresolvers import PathIndexResolver, RedisResolver

from pywb_arquivo.lmdb_path_resolver import LMDBPathIndexResolver, close_environments


MISSING_SUFFIX = '.missing'


def sample_names(tsv_files, size, rnd):
    """Sample WARC file names at random offsets of the TSV files, weighted by size."""
    sizes = [os.path.getsize(path) for path in tsv_files]
    names = set()
    attempts = 0
    while len(names) < size and attempts < size * 10:
        attempts += 1
        path = rnd.choices(tsv_files, weights=sizes)[0]
        with open(path, 'rb') as reader:
            reader.seek(rnd.randrange(max(os.path.getsize(path), 1)))
            reader.readline()
            line = reader.readline()
            if not line:
                # past the last line
                reader.seek(0)
                line = reader.readline()
        name, sep, _ = line.rstrip().partition(b'\t')
        if sep and name:
            names.add(name.decode('utf-8'))
    return sorted(names)


def make_resolvers(kind, paths):
    if kind == 'tsv':
        return [PathIndexResolver(path) for path in paths]
    if kind == 'redis':
        return [RedisResolver(uri) for uri in paths]
    return [LMDBPathIndexResolver.from_uri(uri) for uri in paths]


def possible_paths(resolver, name):
    """The paths of a resolver, as pywb's ``ResolvingLoader`` reads them: a string or an iterable."""
    paths = resolver(name, {})
    if not paths:
        return ()
    if isinstance(paths, str):
        return (paths,)
    return paths


def resolve_first(resolvers, name):
    """Return the first path of the first resolver with paths, as pywb on a successful load."""
    for resolver in resolvers:
        for path in possible_paths(resolver, name):
            return path
    return None


def first_paths(resolvers, name):
    """All the paths of the first resolver with paths, the ones pywb tries."""
    for resolver in resolvers:
        paths = list(possible_paths(resolver, name))
        if paths:
            return paths
    return []


def check_same_results(tsv_resolvers, other, names, queue):
    """The names each kind resolves differently from the TSV path index.

    Redis keeps only the first path of each WARC file name (``path-index-to-redis``), so only that one is compared.
    """
    mismatches = {}
    for kind, resolvers in other.items():
        paths = resolve_first if kind == 'redis' else first_paths
        mismatches[kind] = [name for name in names if paths(tsv_resolvers, name) != paths(resolvers, name)]
    queue.put(mismatches)


def run_worker(resolvers, names, barrier, queue):
    lookups = [None] * len(names)
    barrier.wait()
    usage = resource.getrusage(resource.RUSAGE_SELF)
    for i, name in enumerate(names):
        start = time.perf_counter_ns()
        resolve_first(resolvers, name)
        lookups[i] = time.perf_counter_ns() - start
    end_usage = resource.getrusage(resource.RUSAGE_SELF)
    close_environments()
    queue.put({
        'latencies': lookups,
        'cpu': (end_usage.ru_utime + end_usage.ru_stime) - (usage.ru_utime + usage.ru_stime),
        'majflt': end_usage.ru_majflt - usage.ru_majflt,
        'inblock': end_usage.ru_inblock - usage.ru_inblock,
    })


def run(kind, paths, names, workers, lookups, rnd, context):
    resolvers = make_resolvers(kind, paths)
    servers = redis_servers(paths) if kind == 'redis' else []
    server_cpu = sum(redis_cpu(server) for server in servers)
    barrier = context.Barrier(workers + 1)
    queue = context.Queue()
    processes = []
    for _ in range(workers):
        worker_names = [rnd.choice(names) for _ in range(lookups)]
        process = context.Process(target=run_worker, args=(resolvers, worker_names, barrier, queue))
        process.start()
        processes.append(process)

    barrier.wait()
    start = time.perf_counter()
    results = [queue.get() for _ in processes]
    elapsed = time.perf_counter() - start
    for process in processes:
        process.join()
    server_cpu = sum(redis_cpu(server) for server in servers) - server_cpu

    latencies = sorted(latency for result in results for latency in result['latencies'])
    total = len(latencies)
    return {
        'kind': kind,
        'workers': workers,
        'lookups': total,
        'throughput': total / elapsed,
        'mean_us': sum(latencies) / total / 1000,
        'p50_us': percentile(latencies, 50) / 1000,
        'p95_us': percentile(latencies, 95) / 1000,
        'p99_us': percentile(latencies, 99) / 1000,
        'max_us': latencies[-1] / 1000,
        'cpu_us': sum(result['cpu'] for result in results) / total * 1e6,
        'server_cpu_us': server_cpu / total * 1e6 if servers else None,
        'majflt': sum(result['majflt'] for result in results) / total,
        'inblock': sum(result['inblock'] for result in results) / total,
    }


def percentile(values, pct):
    return values[min(len(values) - 1, int(len(values) * pct / 100))]


def redis_servers(uris):
    """A client of each Redis server of the ``redis://host:port/db/key`` uris."""
    servers = dict.fromkeys('/'.join(uri.split('/')[:4]) for uri in uris)
    return [redis.StrictRedis.from_url(server) for server in servers]


def redis_cpu(server):
    """CPU seconds used by the Redis server so far, of all its clients."""
    info = server.info('cpu')
    return float(info['used_cpu_user']) + float(info['used_cpu_sys'])


def redis_memory(uris):
    """Memory and resident memory of the Redis servers, in bytes."""
    infos = [server.info('memory') for server in redis_servers(uris)]
    return sum(int(info['used_memory']) for info in infos), sum(int(info['used_memory_rss']) for info in infos)


def index_files(kind, paths):
    if kind == 'tsv':
        return list(dict.fromkeys(paths))
    if kind == 'redis':
        # in the Redis server memory
        return []
    # the named databases of an environment share its data.mdb
    return list(dict.fromkeys(os.path.join(resolver.env_path, 'data.mdb') for resolver in make_resolvers(kind, paths)))


def drop_page_cache(files):
    for path in files:
        fd = os.open(path, os.O_RDONLY)
        try:
            # dirty pages, eg. of a file just written, aren't dropped
            os.fsync(fd)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)


def page_cache_bytes(path):
    """Bytes of ``path`` on the page cache, using mincore(), or None if not supported."""
    size = os.path.getsize(path)
    if not size:
        return 0
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.mmap.restype = ctypes.c_void_p
        libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_long]
        libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p]
    except (OSError, AttributeError):
        return None

    page_size = mmap.PAGESIZE
    fd = os.open(path, os.O_RDONLY)
    try:
        addr = libc.mmap(None, size, mmap.PROT_READ, mmap.MAP_SHARED, fd, 0)
        if addr in (None, ctypes.c_void_p(-1).value):
            return None
        try:
            vec = (ctypes.c_ubyte * ((size + page_size - 1) // page_size))()
            if libc.mincore(addr, size, vec) != 0:
                return None
            return sum(page & 1 for page in bytes(vec)) * page_size
        finally:
            libc.munmap(addr, size)
    finally:
        os.close(fd)


def mib(value):
    return '-' if value is None else '{0:.0f}'.format(value / 1024 ** 2)


def benchmark(args):
    rnd = random.Random(args.seed)
    context = multiprocessing.get_context('fork')
    names = sample_names(args.tsv, args.sample, rnd)
    missing = int(len(names) * args.miss_ratio)
    names += [name + MISSING_SUFFIX for name in rnd.sample(names, missing)]
    print('sample: {0} WARC file names, {1} missing'.format(len(names), missing))

    kinds = [(kind, paths) for kind, paths in (('tsv', args.tsv), ('lmdb', args.lmdb), ('redis', args.redis))
             if paths]
    files = {kind: index_files(kind, paths) for kind, paths in kinds}
    for kind, paths in files.items():
        if kind != 'redis':
            print('{0} files: {1} MiB'.format(kind, mib(sum(os.path.getsize(path) for path in paths))))
    memory = None
    if args.redis:
        memory = redis_memory(args.redis)
        print('redis memory: {0} MiB, resident {1} MiB'.format(mib(memory[0]), mib(memory[1])))

    # on another process, so this one doesn't keep the LMDB files mapped
    queue = context.Queue()
    process = context.Process(target=check_same_results, args=(
        make_resolvers('tsv', args.tsv), {kind: make_resolvers(kind, paths) for kind, paths in kinds[1:]}, names,
        queue))
    process.start()
    mismatches = queue.get()
    process.join()
    for kind, different in mismatches.items():
        print('same results ({0}): {1}/{2}{3}'.format(kind, len(names) - len(different), len(names),
                                                       ', eg. ' + ', '.join(different[:5]) if different else ''))

    rows = []
    for workers in args.workers:
        for kind, paths in kinds:
            if args.cold:
                drop_page_cache(files[kind])
            row = run(kind, paths, names, workers, args.lookups, rnd, context)
            cached = [page_cache_bytes(path) for path in files[kind]]
            row['page_cache_mib'] = None if kind == 'redis' or None in cached else sum(cached) / 1024 ** 2
            rows.append(row)

    print_table(rows, args.cold)
    if args.json:
        with open(args.json, 'w') as out:
            json.dump({'cold': args.cold, 'sample': len(names),
                       'mismatches': {kind: len(different) for kind, different in mismatches.items()},
                       'tsv': args.tsv, 'lmdb': args.lmdb, 'redis': args.redis, 'files_mib': {
                           kind: sum(os.path.getsize(path) for path in paths) / 1024 ** 2
                           for kind, paths in files.items() if kind != 'redis'},
                       'redis_memory_mib': None if memory is None else {
                           'used': memory[0] / 1024 ** 2, 'resident': memory[1] / 1024 ** 2},
                       'results': rows}, out, indent=2)
    return 1 if any(mismatches.values()) else 0


def print_table(rows, cold):
    print()
    print('page cache: ' + ('cold' if cold else 'warm'))
    print('| resolver | workers | lookups/s | mean µs | p50 µs | p95 µs | p99 µs | max µs | CPU µs/lookup '
          '| server CPU µs/lookup | major faults/lookup | block reads/lookup | page cache MiB |')
    print('|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|')
    for row in rows:
        print('| {kind} | {workers} | {throughput:,.0f} | {mean_us:.1f} | {p50_us:.1f} | {p95_us:.1f} | '
              '{p99_us:.1f} | {max_us:,.0f} | {cpu_us:.1f} | {server_cpu} | {majflt:.3f} | {inblock:.3f} | {cache} |'
              .format(cache='-' if row['page_cache_mib'] is None else '{0:.0f}'.format(row['page_cache_mib']),
                      server_cpu='-' if row['server_cpu_us'] is None else '{0:.1f}'.format(row['server_cpu_us']),
                      **row))


def generate(args):
    """Write a sorted synthetic TSV path index of about ``--size`` GiB."""
    rnd = random.Random(args.seed)
    target = int(args.size * 1024 ** 3)
    written = lines = 0
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8', newline='\n') as out:
        collection = 0
        while written < target:
            collection += 1
            timestamp = 19960101000000 + collection * 1000000
            for serial in range(rnd.randint(50000, 150000)):
                timestamp += rnd.randint(1, 600)
                name = 'AWP{0:04d}-{1:014d}-{2:05d}-crawler{3:02d}.example.org.warc.gz'.format(
                    collection, timestamp, serial % 100000, rnd.randint(1, 20))
                line = '{0}\thttp://storage{1:02d}.example.org:8080/data/collections/AWP{2:04d}/{0}\n'.format(
                    name, rnd.randint(1, 40), collection)
                out.write(line)
                written += len(line)
                lines += 1
                if written >= target:
                    break
    print('{0}: {1} lines, {2} MiB'.format(args.output, lines, mib(written)))
    return 0


def main(args=None):
    parser = argparse.ArgumentParser(prog='python -m pywb_arquivo.path_index_benchmark',
                                     description='Benchmark the TSV, the LMDB and the Redis path indexes.')
    commands = parser.add_subparsers(dest='command', required=True)

    run_parser = commands.add_parser('run', help='compare the TSV, the LMDB and the Redis path indexes')
    run_parser.add_argument('--tsv', action='append', required=True, help='TSV path index, in pywb order')
    run_parser.add_argument('--lmdb', action='append',
                            help='LMDB path index uri, eg. lmdb:///data/pathindex.lmdb?db=branchA, in pywb order')
    run_parser.add_argument('--redis', action='append',
                            help='Redis path index uri, eg. redis://localhost:6379/0/pathindex:branchA, in pywb order')
    run_parser.add_argument('--sample', type=int, default=20000, help='WARC file names to sample')
    run_parser.add_argument('--miss-ratio', type=float, default=0.1, help='missing WARC file names ratio')
    run_parser.add_argument('--lookups', type=int, default=20000, help='lookups per worker')
    run_parser.add_argument('--workers', type=lambda value: [int(n) for n in value.split(',')], default=[1, 4],
                            help='comma separated number of worker processes (default: 1,4)')
    run_parser.add_argument('--cold', action='store_true', help='drop the index files from the page cache first')
    run_parser.add_argument('--seed', type=int, default=1672)
    run_parser.add_argument('--json', help='also write the results to this json file')

    generate_parser = commands.add_parser('generate', help='generate a synthetic TSV path index')
    generate_parser.add_argument('--size', type=float, default=1, help='size in GiB (default: %(default)s)')
    generate_parser.add_argument('--seed', type=int, default=1672)
    generate_parser.add_argument('output', help='TSV file to write')

    args = parser.parse_args(args)
    if args.command == 'run' and not (args.lmdb or args.redis):
        parser.error('run: compare with --lmdb, --redis or both')
    if args.command == 'run':
        return benchmark(args)
    return generate(args)


if __name__ == '__main__':
    sys.exit(main())
