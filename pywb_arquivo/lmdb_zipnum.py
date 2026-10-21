"""pywb ZipNum index source that reads the secondary index (``.idx``) from an
LMDB database instead of the ``.idx`` file, built by
:mod:`pywb_arquivo.lmdb_zipnum_index`.

It is enabled by adding the LMDB database to a ``zipnum`` index::

    index:
      type: zipnum
      path: /data/zipnum/RAQ2019/RAQ2019.idx
      lmdb: lmdb:///data/zipnum/idx.lmdb?db=RAQ2019

The shards and the ``.loc`` file (next to ``path``) are used as before. Only
the lookups on the ``.idx`` change: pywb's own ``ZipNumIndexSource`` code runs
with its ``open``, ``search``, ``iter_range`` and ``read_last_line`` functions
replaced by LMDB cursor versions, so the pages, the blocks and the CDX lines
are computed as with the ``.idx`` file. If the LMDB environment or database
isn't available, the ``.idx`` file of ``path`` is used, and LMDB is tried
again after 60 s.

Each ``.idx`` line is an LMDB entry. The key is the first field of the line
(``urlkey timestamp``), cut to its first 500 bytes as LMDB keys have at most
511, then a tab and the 8 byte big-endian line number, that keeps the order of
the file and makes the keys of consecutive blocks with the same first field
unique. The value is the rest of the line, so the line is the key without the
line number followed by the value, and is compared whole like pywb does.

pywb only knows its own index sources, the ``lmdb`` option is added by
:func:`install`, called by the :mod:`pywb_arquivo.wayback` WSGI application.
The environment is opened like the LMDB path index
(:mod:`pywb_arquivo.lmdb_path_resolver`): read only, on the first lookup of
each uWSGI worker.
"""
import itertools
import logging
import os
import struct
import time
import types

import lmdb

from pywb.utils import binsearch, loaders
from pywb.warcserver import warcserver
from pywb.warcserver.index.zipnum import ZipNumIndexSource

from pywb_arquivo.lmdb_path_resolver import RETRY_INTERVAL, get_environment, parse_uri


logger = logging.getLogger(__name__)

# bytes of the first field of the line kept on the key, the rest is on the value
KEY_PREFIX_SIZE = 500

# separates the key prefix from the line number, sorts like the tab after the
# first field of the line
KEY_SEPARATOR = b'\t'

LINENO = struct.Struct('>Q')

KEY_SUFFIX_SIZE = len(KEY_SEPARATOR) + LINENO.size


def idx_entry(line, lineno):
    """The LMDB ``(key, value)`` of an ``.idx`` line without its newline."""
    first_field = line.partition(b'\t')[0]
    prefix = first_field[:KEY_PREFIX_SIZE]
    return prefix + KEY_SEPARATOR + LINENO.pack(lineno), line[len(prefix):]


def idx_line(key, value):
    """The ``.idx`` line of an LMDB entry, without its newline."""
    return key[:-KEY_SUFFIX_SIZE] + value


class LMDBIdxReader:
    """The ``.idx`` of an LMDB named database on a read transaction, used
    instead of the ``.idx`` file object by pywb's ``ZipNumIndexSource``."""

    def __init__(self, txn, db):
        self.txn = txn
        self.db = db

    def search(self, key, prev_size=0):
        """Like pywb's ``binsearch.search`` on a sorted file: the lines from the
        first one ``>= key``, preceded by up to ``prev_size`` lines. Without
        any, the last ``prev_size`` lines."""
        cursor = self.txn.cursor(self.db)

        # no key of a line >= key is smaller than the key cut to the size of
        # the key prefix, or before a tab, that sorts first like the separator
        found = cursor.set_range(key[:KEY_PREFIX_SIZE].partition(b'\t')[0])
        while found and idx_line(cursor.key(), cursor.value()) < key:
            found = cursor.next()

        if not found:
            if prev_size and cursor.last():
                last = idx_line(cursor.key(), cursor.value())
                yield from self._lines_before(cursor, prev_size - 1)[::-1]
                yield last
            return

        match = cursor.key()
        yield from self._lines_before(cursor, prev_size)[::-1]
        cursor.set_key(match)
        for key, value in cursor:
            yield idx_line(key, value)

    def iter_range(self, start, end, prev_size=0):
        """Like pywb's ``binsearch.iter_range``: the ``search`` lines ``< end``."""
        return itertools.takewhile(lambda line: line < end, self.search(start, prev_size))

    def read_last_line(self):
        """Like pywb's ``read_last_line`` on an ``.idx`` file, with its newline."""
        cursor = self.txn.cursor(self.db)
        if not cursor.last():
            # as readlines()[-1] of an empty file
            raise IndexError('list index out of range')
        return idx_line(cursor.key(), cursor.value()) + b'\n'

    @staticmethod
    def _lines_before(cursor, size):
        lines = []
        while len(lines) < size and cursor.prev():
            lines.append(idx_line(cursor.key(), cursor.value()))
        return lines

    def close(self):
        self.txn.abort()


def _search(reader, key, prev_size=0, *args, **kwargs):
    if isinstance(reader, LMDBIdxReader):
        return reader.search(key, prev_size)
    return binsearch.search(reader, key, prev_size, *args, **kwargs)


def _iter_range(reader, start, end, prev_size=0):
    if isinstance(reader, LMDBIdxReader):
        return reader.iter_range(start, end, prev_size)
    return binsearch.iter_range(reader, start, end, prev_size)


def _read_last_line(reader, *args, **kwargs):
    if isinstance(reader, LMDBIdxReader):
        return reader.read_last_line()
    return loaders.read_last_line(reader, *args, **kwargs)


def _open_index(index, *args, **kwargs):
    if isinstance(index, LMDBIdxReader):
        return index
    return open(index, *args, **kwargs)


def _with_globals(func, **names):
    """A copy of pywb's ``func`` that uses ``names`` instead of its module globals."""
    missing = set(names) - set(func.__code__.co_names)
    if missing:
        raise ImportError('{0} no longer uses {1}, check the pywb version'.format(
            func.__qualname__, ', '.join(sorted(missing))))
    return types.FunctionType(func.__code__, dict(func.__globals__, **names), func.__name__,
                              func.__defaults__, func.__closure__)


class LMDBZipNumIndexSource(ZipNumIndexSource):
    """pywb's ``ZipNumIndexSource``, with the ``.idx`` on an LMDB named database."""

    # pywb's code, with the LMDB versions of the .idx file functions, that
    # still read the .idx file when LMDB isn't available
    _load_lmdb_cdx = _with_globals(ZipNumIndexSource._do_load_cdx, open=_open_index)
    compute_page_range = _with_globals(ZipNumIndexSource.compute_page_range, search=_search,
                                       iter_range=_iter_range, read_last_line=_read_last_line)

    def __init__(self, summary, config=None):
        super().__init__(summary, config)
        env_path, self.db_name = parse_uri(self.config.get('lmdb', ''))
        if not self.db_name:
            raise ValueError('The LMDB .idx needs a named database, eg. lmdb:///path/to/env?db=name: ' +
                             self.config['lmdb'])
        self.env_path = os.path.abspath(env_path)
        self._db = None
        self._db_pid = None
        self._retry_at = 0

    def _do_load_cdx(self, filename, query):
        reader = self.open_idx()
        if reader is None:
            return super()._do_load_cdx(filename, query)
        return self._load_lmdb_cdx(reader, query)

    def open_idx(self):
        """A reader of the ``.idx`` on a new read transaction, or None if the
        LMDB database isn't available."""
        opened = self._open()
        if not opened:
            return None

        env, db = opened
        try:
            try:
                txn = env.begin(db=db)
            except lmdb.MapResizedError:
                # the loader grew the database map, adopt the new size
                env.set_mapsize(0)
                txn = env.begin(db=db)
        except lmdb.Error as e:
            self._fail('lookup failed', e)
            return None
        return LMDBIdxReader(txn, db)

    def _open(self):
        pid = os.getpid()
        if self._db is not None and self._db_pid == pid:
            return self._db

        if time.monotonic() < self._retry_at:
            return None

        try:
            env = get_environment(self.env_path)
            db = env.open_db(self.db_name.encode('utf-8'), create=False)
        except lmdb.Error as e:
            self._fail('not available', e)
            return None

        self._db = (env, db)
        self._db_pid = pid
        return self._db

    def _fail(self, reason, error):
        self._db = None
        self._retry_at = time.monotonic() + RETRY_INTERVAL
        logger.warning('LMDB .idx %s %s, using %s, retrying in %s s: %s',
                       self.config['lmdb'], reason, self.summary, RETRY_INTERVAL, error)

    def __repr__(self):
        return 'LMDBZipNumIndexSource({0}, {1})'.format(self.summary, self.config)

    @classmethod
    def init_from_string(cls, value):
        return None

    @classmethod
    def init_from_config(cls, config):
        if config.get('type') != 'zipnum' or not config.get('lmdb'):
            return None

        return cls(config['path'], config)


def install():
    """Add the ``lmdb`` option to the pywb ``zipnum`` indexes."""
    if LMDBZipNumIndexSource not in warcserver.SOURCE_LIST:
        warcserver.register_source(LMDBZipNumIndexSource)
