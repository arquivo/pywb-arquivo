"""Load the TSV path indexes of pywb's ``PathIndexResolver`` into an LMDB
database, used by :mod:`pywb_arquivo.lmdb_path_resolver`.

Each TSV line has the WARC file name and its paths (or urls), separated by
tabs. Each LMDB named database (eg. one per branch) maps the WARC file name to
the tab separated list of its paths::

    # load or update the paths of a collection on the branch A database
    python -m pywb_arquivo.lmdb_path_index load --env /data/warcIndex/pathindex.lmdb --db branchA \\
        /data/warcIndex/branchA/AWP1.tsv

    # check what would change, without writing
    python -m pywb_arquivo.lmdb_path_index load --dry-run ...

    # recreate the branch A database from all the TSV files of a directory
    python -m pywb_arquivo.lmdb_path_index load --env /data/warcIndex/pathindex.lmdb --db branchA \\
        --drop --pattern '.*\\.tsv' /data/warcIndex/branchA/

    # number of entries of each database
    python -m pywb_arquivo.lmdb_path_index stats --env /data/warcIndex/pathindex.lmdb

Loading adds the new WARC files and replaces the paths of the existing ones,
keeping the other WARC files of the database, so it can be run once for each
updated collection. ``--drop`` empties the database first, ``--strict`` fails
instead of replacing paths.

Each run is a single LMDB write transaction, the pywb instances keep reading
the previous version of the database until it is committed, even with
``--drop``. Other databases of the same environment are not changed. A WARC
file on more than one TSV file, or on non-consecutive lines, fails the load.
"""
import argparse
import os
import re
import sys
from array import array
from collections import Counter
from dataclasses import dataclass

import lmdb

from pywb_arquivo.lmdb_path_resolver import MAX_DBS, MAX_KEY_SIZE, MAX_READERS


GIB = 1024 ** 3

# LMDB reserves the address space but only uses the disk space of the data
DEFAULT_MAP_SIZE_GIB = 64

# max WARC file names shown on the errors
MAX_REPORTED = 10

# max hashes of the WARC file names loaded more than once that are looked up on the TSV files, enough
# to show the first ones, as different names with the same hash are very rare
MAX_DUPLICATED_HASHES = 1000


@dataclass
class LoadStats:
    files: int = 0
    lines: int = 0
    skipped: int = 0
    unsorted: int = 0
    keys: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    dropped: int = 0

    def __iadd__(self, other):
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))
        return self

    def __str__(self):
        return ', '.join('{0}={1}'.format(name, getattr(self, name)) for name in self.__dataclass_fields__)


class _KeyHashes:
    """The hashes of the WARC file names of a load, to find the ones loaded
    more than once. 8 bytes per name, against about 100 bytes on a set of the
    names (1.4 GiB for the 14.6 M WARC files of a branch)."""

    def __init__(self):
        self._buckets = [array('q') for _ in range(256)]

    def add(self, key):
        h = hash(key)
        self._buckets[h & 255].append(h)

    def duplicated(self, limit):
        """Return the hashes added more than once, stopping after ``limit`` of them."""
        hashes = set()
        for bucket in self._buckets:
            if len(set(bucket)) != len(bucket):
                hashes.update(h for h, count in Counter(bucket).items() if count > 1)
                if len(hashes) >= limit:
                    break
        return hashes


def _find_duplicates(files, hashes):
    """Return the WARC file names with one of the ``hashes`` that are on more
    than one file, or on non-consecutive lines, with the files of each one."""
    found = {}
    if hashes:
        for path in files:
            with open(path, 'rb') as reader:
                for key, _ in iter_path_index(reader, LoadStats()):
                    if hash(key) in hashes:
                        found.setdefault(key, []).append(path)
    # the other ones have the same hash of a different name
    return {key: paths for key, paths in found.items() if len(paths) > 1}


def _first(items):
    return ', '.join(items[:MAX_REPORTED]) + (', ...' if len(items) > MAX_REPORTED else '')


def find_files(paths, pattern=None):
    """Return the files to load: the files of ``paths`` and the files of the
    directories of ``paths`` whose name fully matches the ``pattern`` regex."""
    regex = re.compile(pattern) if pattern else None
    files = []
    for path in paths:
        if os.path.isdir(path):
            names = sorted(name for name in os.listdir(path)
                           if os.path.isfile(os.path.join(path, name)) and
                           (not regex or regex.fullmatch(name)))
            files.extend(os.path.join(path, name) for name in names)
        elif os.path.isfile(path):
            files.append(path)
        else:
            raise FileNotFoundError('Path index not found: ' + path)
    return files


def iter_path_index(reader, stats):
    """Yield the ``(warc_filename, paths)`` of a sorted TSV path index, as bytes.

    The lines are parsed like pywb's ``PathIndexResolver``: trailing white
    space is removed and the paths of consecutive lines of the same WARC file
    are joined. Lines without paths, or with a key too long for LMDB, are
    skipped.
    """
    key = value = prev_key = None
    for line in reader:
        stats.lines += 1
        line = line.rstrip()
        line_key, sep, line_value = line.partition(b'\t')
        if not sep or not line_key or len(line_key) > MAX_KEY_SIZE:
            stats.skipped += 1
            continue

        if prev_key is not None and line_key < prev_key:
            stats.unsorted += 1
        prev_key = line_key

        if line_key == key:
            value += b'\t' + line_value
            continue

        if key is not None:
            yield key, value
        key, value = line_key, line_value

    if key is not None:
        yield key, value


def load(env_path, db_name, paths, pattern=None, drop=False, dry_run=False, strict=False,
         map_size=DEFAULT_MAP_SIZE_GIB * GIB, out=None):
    """Load the TSV path indexes of ``paths`` into the ``db_name`` database
    of the ``env_path`` LMDB environment, and return the :class:`LoadStats`.

    Raise ``ValueError``, without changing the database, if a WARC file is on
    more than one file, or on non-consecutive lines, or, if ``strict``, if the
    paths of a WARC file already on the database would be replaced.
    """
    if not db_name:
        raise ValueError('The LMDB named database is required')

    files = find_files(paths, pattern)
    name = db_name.encode('utf-8')
    out = out or sys.stdout

    if dry_run:
        return _load_dry_run(env_path, name, files, drop, strict, out)

    env = lmdb.open(env_path, map_size=map_size, max_dbs=MAX_DBS, max_readers=MAX_READERS, readahead=False)
    try:
        # free the reader slots of killed pywb workers, LMDB only does it when no other process
        # has the environment open: they would keep the old versions of the database, growing
        # data.mdb, and fill the reader table
        stale = env.reader_check()
        if stale:
            print('cleared {0} stale readers'.format(stale), file=out)

        with env.begin(write=True) as txn:
            # created on the load transaction, a failed load doesn't create it
            db = env.open_db(name, txn=txn)
            return _load_files(txn, db, files, drop, False, strict, out)
    finally:
        env.close()


def _load_dry_run(env_path, name, files, drop, strict, out):
    if not os.path.exists(os.path.join(env_path, 'data.mdb')):
        return _load_files(None, None, files, drop, True, strict, out)

    env = lmdb.open(env_path, readonly=True, max_dbs=MAX_DBS, max_readers=MAX_READERS, readahead=False)
    try:
        try:
            db = env.open_db(name, create=False)
        except lmdb.NotFoundError:
            return _load_files(None, None, files, drop, True, strict, out)

        with env.begin(db=db) as txn:
            return _load_files(txn, db, files, drop, True, strict, out)
    finally:
        env.close()


def _load_files(txn, db, files, drop, dry_run, strict, out):
    total = LoadStats()
    prefix = '[dry-run] ' if dry_run else ''
    hashes = _KeyHashes()
    replaced = []

    if drop and txn:
        total.dropped = txn.stat(db)['entries']
        if not dry_run:
            txn.drop(db, delete=False)
        print('{0}dropped {1} entries'.format(prefix, total.dropped), file=out)

    for path in files:
        stats = LoadStats(files=1)
        with open(path, 'rb') as reader:
            for key, value in iter_path_index(reader, stats):
                hashes.add(key)
                stats.keys += 1
                old = txn.get(key, db=db) if txn and not (drop and dry_run) else None
                if old is None:
                    stats.added += 1
                elif old == value:
                    stats.unchanged += 1
                    continue
                else:
                    stats.updated += 1
                    if strict and len(replaced) <= MAX_REPORTED:
                        replaced.append(key)

                if not dry_run:
                    txn.put(key, value, db=db)

        print('{0}{1}: {2}'.format(prefix, path, stats), file=out)
        total += stats

    # checked before committing, a failed load doesn't change the database
    duplicates = _find_duplicates(files, hashes.duplicated(MAX_DUPLICATED_HASHES))
    if duplicates:
        raise ValueError('WARC files on more than one file, or on non-consecutive lines, nothing was loaded: '
                         + _first(['{0} ({1})'.format(key.decode('utf-8', 'replace'), ', '.join(paths))
                                   for key, paths in duplicates.items()]))
    if strict and total.updated:
        raise ValueError('--strict: the paths of {0} WARC files would be replaced, nothing was loaded: {1}'.format(
            total.updated, _first([key.decode('utf-8', 'replace') for key in replaced])))

    print('{0}total: {1}'.format(prefix, total), file=out)
    return total


def stats(env_path, out=None):
    """Print the number of entries of each named database of ``env_path``."""
    out = out or sys.stdout
    env = lmdb.open(env_path, readonly=True, max_dbs=MAX_DBS, max_readers=MAX_READERS)
    try:
        with env.begin() as txn:
            names = [key for key, _ in txn.cursor()]
        info = env.info()
        print('map_size={0} last_txnid={1} readers={2}/{3}'.format(
            info['map_size'], info['last_txnid'], info['num_readers'], info['max_readers']), file=out)
        for name in names:
            try:
                db = env.open_db(name, create=False)
            except lmdb.Error:
                # a plain key of the main database, not a named database
                continue
            with env.begin(db=db) as txn:
                print('{0}: entries={1}'.format(name.decode('utf-8'), txn.stat(db)['entries']), file=out)
    finally:
        env.close()


def main(args=None):
    parser = argparse.ArgumentParser(prog='python -m pywb_arquivo.lmdb_path_index',
                                     description='Load TSV path indexes into an LMDB database.')
    commands = parser.add_subparsers(dest='command', required=True)

    load_parser = commands.add_parser('load', help='load or update TSV path indexes into an LMDB database')
    load_parser.add_argument('--env', required=True, help='LMDB environment directory, created if missing')
    load_parser.add_argument('--db', required=True, help='LMDB named database, eg. branchA')
    load_parser.add_argument('--drop', '--recreate', action='store_true',
                             help='empty the database before loading')
    load_parser.add_argument('--dry-run', action='store_true', help="show what would change, don't write")
    load_parser.add_argument('--strict', action='store_true',
                             help='fail, without writing, if the paths of a WARC file on the database would change')
    load_parser.add_argument('--pattern', help='regex that the names of the files of a directory must fully match')
    load_parser.add_argument('--map-size', type=int, default=DEFAULT_MAP_SIZE_GIB,
                             help='max size of the LMDB environment in GiB (default: %(default)s)')
    load_parser.add_argument('paths', nargs='+', help='TSV path index files or directories')

    stats_parser = commands.add_parser('stats', help='show the number of entries of each database')
    stats_parser.add_argument('--env', required=True, help='LMDB environment directory')

    args = parser.parse_args(args)
    try:
        if args.command == 'load':
            load(args.env, args.db, args.paths, pattern=args.pattern, drop=args.drop,
                 dry_run=args.dry_run, strict=args.strict, map_size=args.map_size * GIB)
        else:
            stats(args.env)
    except (OSError, ValueError, re.error, lmdb.Error) as e:
        if isinstance(e, lmdb.MapFullError):
            e = '{0}, use a bigger --map-size'.format(e)
        print('error: {0}'.format(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
