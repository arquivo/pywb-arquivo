"""pywb WSGI application with the Arquivo.pt extensions, used by uwsgi.ini
instead of ``pywb.apps.wayback``.

It adds the ``lmdb://`` path resolver (:mod:`pywb_arquivo.lmdb_path_resolver`)
to the ``archive_paths`` of the pywb config before creating the application.
"""
# like pywb.apps.wayback, monkey patch before importing anything else
from gevent.monkey import patch_all; patch_all()

from pywb_arquivo import lmdb_path_resolver  # noqa: E402
lmdb_path_resolver.install()

from pywb.apps.wayback import application  # noqa: E402, F401
