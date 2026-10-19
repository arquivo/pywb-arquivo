"""pywb path resolver that looks up the location of a WARC file on an LMDB
database, an alternative to the TSV path index of pywb's ``PathIndexResolver``.

The LMDB database maps the WARC file name to the same paths (or urls) of the
TSV path index, built by :mod:`pywb_arquivo.lmdb_path_index`. A single LMDB
environment (directory) can have one named database per branch, each one
configured as an independent ``archive_paths`` entry::

    archive_paths:
      - lmdb:///data/warcIndex/pathindex.lmdb?db=branchA
      - lmdb:///data/warcIndex/pathindex.lmdb?db=branchB

pywb tries each resolver in order, so the second one is only used when the
WARC file is missing on the first database or can't be loaded from the paths
it returns. A missing environment or database is logged and skipped, it
doesn't affect the other resolvers.

pywb only knows its own resolvers, the ``lmdb://`` scheme is added by
:func:`install`, called by the :mod:`pywb_arquivo.wayback` WSGI application.

LMDB can't be used across ``fork()`` and an environment can only be opened once
per process, so the environment is opened on the first lookup, on each uWSGI
worker, and shared by all the resolvers of that process.
"""
import logging
import os
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit

import lmdb

from pywb.warcserver.resource.pathresolvers import DefaultResolverMixin


logger = logging.getLogger(__name__)

SCHEME = 'lmdb'

# max named databases on an environment, eg. one per branch
MAX_DBS = 64

# LMDB default max key size, in bytes
MAX_KEY_SIZE = 511

# seconds to wait before trying again to open a missing environment or database
RETRY_INTERVAL = 60

_lock = threading.Lock()

# environment path -> (pid, lmdb.Environment)
_environments = {}

# environments opened before fork(), never closed by the child process, as
# LMDB would release the reader slots of the parent
_inherited = []


class LMDBPathIndexResolver:
    """Resolve a WARC file name to its paths, from an LMDB named database.

    The value of each key is the tab separated list of paths of the TSV path
    index, returned in the same order as pywb's ``PathIndexResolver``.
    """

    def __init__(self, env_path, db_name=None):
        self.env_path = os.path.abspath(env_path)
        self.db_name = db_name
        self._db = None
        self._db_pid = None
        self._retry_at = 0

    @classmethod
    def from_uri(cls, uri):
        """Create a resolver from a ``lmdb:///path/to/env?db=name`` uri."""
        parts = urlsplit(uri)
        if parts.scheme != SCHEME or parts.netloc or not parts.path:
            raise ValueError('Invalid LMDB path index, expected lmdb:///path/to/env?db=name: ' + uri)

        db_names = parse_qs(parts.query).get('db')
        return cls(unquote(parts.path), db_names[-1] if db_names else None)

    def __call__(self, filename, cdx):
        key = filename.encode('utf-8')
        if not key or len(key) > MAX_KEY_SIZE:
            return []

        value = self._get(key)
        if value is None:
            return []

        return value.decode('utf-8').split('\t')

    def _get(self, key):
        opened = self._open()
        if not opened:
            return None

        env, db = opened
        try:
            try:
                with env.begin(db=db) as txn:
                    return txn.get(key)
            except lmdb.MapResizedError:
                # the loader grew the database map, adopt the new size
                env.set_mapsize(0)
                with env.begin(db=db) as txn:
                    return txn.get(key)
        except lmdb.Error as e:
            # skip this resolver, pywb doesn't handle the resolver errors
            self._db = None
            self._retry_at = time.monotonic() + RETRY_INTERVAL
            logger.warning('LMDB path index %s lookup failed, retrying in %s s: %s', self, RETRY_INTERVAL, e)
            return None

    def _open(self):
        pid = os.getpid()
        if self._db is not None and self._db_pid == pid:
            return self._db

        if time.monotonic() < self._retry_at:
            return None

        try:
            env = get_environment(self.env_path)
            name = self.db_name.encode('utf-8') if self.db_name else None
            db = env.open_db(name, create=False) if name else None
        except lmdb.Error as e:
            self._retry_at = time.monotonic() + RETRY_INTERVAL
            logger.warning('LMDB path index %s not available, retrying in %s s: %s', self, RETRY_INTERVAL, e)
            return None

        self._db = (env, db)
        self._db_pid = pid
        return self._db

    def __repr__(self):
        return "LMDBPathIndexResolver('{0}', db='{1}')".format(self.env_path, self.db_name or '')


def get_environment(env_path):
    """Return the read only LMDB environment of this process for ``env_path``."""
    pid = os.getpid()
    with _lock:
        opened = _environments.get(env_path)
        if opened and opened[0] == pid:
            return opened[1]
        if opened:
            _inherited.append(opened[1])

        # lock: needed to read a consistent snapshot while the loader writes
        # readahead: disabled as lookups are random reads
        env = lmdb.open(env_path, readonly=True, lock=True, readahead=False, max_dbs=MAX_DBS)
        _environments[env_path] = (pid, env)
        return env


def close_environments():
    """Close the environments opened by this process (eg. on tests)."""
    pid = os.getpid()
    with _lock:
        for env_path, (env_pid, env) in list(_environments.items()):
            if env_pid == pid:
                env.close()
                del _environments[env_path]


def install():
    """Add the ``lmdb://`` scheme to the pywb ``archive_paths`` resolvers."""
    make_best_resolver = DefaultResolverMixin.make_best_resolver.__func__
    if getattr(make_best_resolver, '_lmdb_installed', False):
        return

    def make_best_resolver_with_lmdb(cls, path):
        if isinstance(path, str) and path.startswith(SCHEME + '://'):
            return LMDBPathIndexResolver.from_uri(path)

        return make_best_resolver(cls, path)

    make_best_resolver_with_lmdb._lmdb_installed = True
    DefaultResolverMixin.make_best_resolver = classmethod(make_best_resolver_with_lmdb)
