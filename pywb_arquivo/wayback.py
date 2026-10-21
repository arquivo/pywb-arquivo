"""pywb WSGI application with the Arquivo.pt extensions, used by uwsgi.ini
instead of ``pywb.apps.wayback``.

Before creating the application, it adds to the pywb config:

- the ``lmdb://`` path resolver of the ``archive_paths``
  (:mod:`pywb_arquivo.lmdb_path_resolver`);
- the ``lmdb`` option of the ``zipnum`` indexes (:mod:`pywb_arquivo.lmdb_zipnum`).
"""
# like pywb.apps.wayback, monkey patch before importing anything else
from gevent.monkey import patch_all; patch_all()

from pywb_arquivo import lmdb_path_resolver, lmdb_zipnum  # noqa: E402
lmdb_path_resolver.install()
lmdb_zipnum.install()

from pywb.apps.wayback import application  # noqa: E402, F401
