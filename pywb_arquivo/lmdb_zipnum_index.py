"""Load a ZipNum secondary index (``.idx``) into an LMDB named database, used
by :mod:`pywb_arquivo.lmdb_zipnum` instead of the ``.idx`` file::

    # load the .idx of a ZipNum into a new database
    python -m pywb_arquivo.lmdb_zipnum_index load --env /data/zipnum/idx.lmdb --db RAQ2019 \\
        /data/zipnum/RAQ2019/RAQ2019.idx

    # replace it, after the ZipNum is rebuilt
    python -m pywb_arquivo.lmdb_zipnum_index load --drop --env /data/zipnum/idx.lmdb --db RAQ2019 \\
        /data/zipnum/RAQ2019/RAQ2019.idx

    # validate the .idx and check what would change, without writing
    python -m pywb_arquivo.lmdb_zipnum_index load --dry-run ...

    # number of entries of each database
    python -m pywb_arquivo.lmdb_zipnum_index stats --env /data/zipnum/idx.lmdb

A ZipNum is rebuilt as a whole, so the database is always loaded from a whole
``.idx``: loading into a database that has entries needs ``--drop``. The load
is a single LMDB write transaction, the pywb instances keep reading the
previous version until it is committed, and a failed load changes nothing.
Other databases of the same environment are not changed.

The ``.idx`` is validated before anything is written, as pywb would return
wrong results otherwise: each line must have the ``urlkey timestamp``, part,
offset, length and line number fields, separated by tabs; the line number must
be the 1-based number of the line (older ``.idx`` files have 1 on every line);
and the lines must be sorted by their first field.
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass

import lmdb

from pywb_arquivo.lmdb_path_index import DEFAULT_MAP_SIZE_GIB, GIB, stats
from pywb_arquivo.lmdb_path_resolver import MAX_DBS
from pywb_arquivo.lmdb_zipnum import KEY_PREFIX_SIZE, idx_entry


IDX_LINE = re.compile(rb'([^\t]+)\t([^\t]+)\t([0-9]+)\t([0-9]+)\t([0-9]+)\n')


class InvalidIdxError(ValueError):
    pass


@dataclass
class LoadStats:
    lines: int = 0
    long_keys: int = 0
    repeated_keys: int = 0
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    dropped: int = 0

    def __str__(self):
        return ', '.join('{0}={1}'.format(name, getattr(self, name)) for name in self.__dataclass_fields__)


def iter_idx(reader, stats):
    """Yield the LMDB ``(key, value)`` entries of a ``.idx``, validating it."""
    prev = None
    for lineno, line in enumerate(reader, 1):
        match = IDX_LINE.fullmatch(line)
        if not match:
            raise InvalidIdxError('line {0}: expected urlkey timestamp, part, offset, length and line number, '
                                  'separated by tabs: {1!r}'.format(lineno, line[:200]))

        if int(match.group(5)) != lineno:
            raise InvalidIdxError('line {0}: the line number field is {1}, rebuild the .idx with the line '
                                  'numbers'.format(lineno, int(match.group(5))))

        # the order of the lines with the same first field is kept by the line number
        first_field = match.group(1) + b'\t'
        if prev is not None and first_field < prev:
            raise InvalidIdxError('line {0}: not sorted, the .idx must be sorted by its first field'
                                  .format(lineno))
        if first_field == prev:
            stats.repeated_keys += 1
        if len(first_field) > KEY_PREFIX_SIZE + 1:
            stats.long_keys += 1
        prev = first_field

        stats.lines += 1
        yield idx_entry(line[:-1], lineno)


def load(env_path, db_name, path, drop=False, dry_run=False, map_size=DEFAULT_MAP_SIZE_GIB * GIB, out=None):
    """Load the ``.idx`` file ``path`` into the ``db_name`` database of the
    ``env_path`` LMDB environment, and return the :class:`LoadStats`."""
    if not db_name:
        raise ValueError('The LMDB named database is required')
    if not os.path.isfile(path):
        raise FileNotFoundError('ZipNum .idx not found: ' + path)

    name = db_name.encode('utf-8')
    out = out or sys.stdout

    if dry_run:
        return _load_dry_run(env_path, name, path, drop, out)

    env = lmdb.open(env_path, map_size=map_size, max_dbs=MAX_DBS, readahead=False)
    try:
        with env.begin(write=True) as txn:
            # created on the load transaction, so a failed load doesn't add it
            db = env.open_db(name, txn=txn)
            stats = _check_drop(txn, db, db_name, drop)
            if stats.dropped:
                txn.drop(db, delete=False)
            with open(path, 'rb') as reader:
                # the keys are sorted, append them to the end of the database
                consumed, stats.added = txn.cursor(db).putmulti(iter_idx(reader, stats), append=True)
            if stats.added != consumed:
                raise InvalidIdxError('{0} of {1} lines were not added'.format(consumed - stats.added, consumed))
    finally:
        env.close()

    _print(out, '', path, stats)
    return stats


def _load_dry_run(env_path, name, path, drop, out):
    txn = None
    env = None
    if os.path.exists(os.path.join(env_path, 'data.mdb')):
        env = lmdb.open(env_path, readonly=True, max_dbs=MAX_DBS, readahead=False)
    try:
        try:
            db = env.open_db(name, create=False) if env else None
        except lmdb.NotFoundError:
            db = None
        if db is not None:
            txn = env.begin(db=db)

        stats = _check_drop(txn, db, name.decode('utf-8'), drop) if txn else LoadStats()
        with open(path, 'rb') as reader:
            for key, value in iter_idx(reader, stats):
                old = txn.get(key) if txn else None
                if old is None:
                    stats.added += 1
                elif old == value:
                    stats.unchanged += 1
                else:
                    stats.updated += 1
        stats.dropped -= stats.unchanged + stats.updated
    finally:
        if txn:
            txn.abort()
        if env:
            env.close()

    _print(out, '[dry-run] ', path, stats)
    return stats


def _check_drop(txn, db, db_name, drop):
    entries = txn.stat(db)['entries']
    if entries and not drop:
        raise ValueError('The database {0} has {1} entries, replace them with --drop'.format(db_name, entries))
    return LoadStats(dropped=entries)


def _print(out, prefix, path, stats):
    print('{0}{1}: {2}'.format(prefix, path, stats), file=out)


def main(args=None):
    parser = argparse.ArgumentParser(prog='python -m pywb_arquivo.lmdb_zipnum_index',
                                     description='Load ZipNum secondary indexes (.idx) into an LMDB database.')
    commands = parser.add_subparsers(dest='command', required=True)

    load_parser = commands.add_parser('load', help='load a ZipNum .idx into an LMDB database')
    load_parser.add_argument('--env', required=True, help='LMDB environment directory, created if missing')
    load_parser.add_argument('--db', required=True, help='LMDB named database, eg. the collection name')
    load_parser.add_argument('--drop', '--recreate', action='store_true',
                             help='replace the entries of the database')
    load_parser.add_argument('--dry-run', action='store_true',
                             help="validate the .idx and show what would change, don't write")
    load_parser.add_argument('--map-size', type=int, default=DEFAULT_MAP_SIZE_GIB,
                             help='max size of the LMDB environment in GiB (default: %(default)s)')
    load_parser.add_argument('path', help='ZipNum .idx file')

    stats_parser = commands.add_parser('stats', help='show the number of entries of each database')
    stats_parser.add_argument('--env', required=True, help='LMDB environment directory')

    args = parser.parse_args(args)
    try:
        if args.command == 'load':
            load(args.env, args.db, args.path, drop=args.drop, dry_run=args.dry_run,
                 map_size=args.map_size * GIB)
        else:
            stats(args.env)
    except (OSError, ValueError, lmdb.Error) as e:
        if isinstance(e, lmdb.MapFullError):
            e = '{0}, use a bigger --map-size'.format(e)
        print('error: {0}'.format(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
