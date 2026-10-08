"""Check the address pywb connects to, when connecting to the live web or to
a remote web archive, on the instances using ``live_url_filter``.

``live_url_filter`` resolves the host before pywb connects, and urllib3
resolves it again when connecting, so a DNS rebinding domain (TTL 0, a public
address first and an internal one next) gets past the filter.

This resolves the host once when opening the connection, drops the addresses
rejected by the filter (``is_ip_blocked``) and connects only to an allowed
one. The host name is kept on the connection, so the ``Host`` header, TLS SNI
and certificate checks are unchanged.

It is only installed on ``DefaultAdapters.live_adapter`` and
``remote_adapter``, used by pywb for the live web and remote (eg. memento)
archives, and on the adapters created later by ``PywbHttpAdapter``.
Other requests, like WARC records loaded over http (``HttpLoader``) or the
recorder calls to the internal warcserver on ``localhost``, are not changed.

It is installed when ``pywb_arquivo.live_url_filter`` is imported, and can be
disabled with ``PYWB_LIVE_CONNECT_GUARD=false``.
"""
import logging
import os
import socket
from socket import error as SocketError
from socket import timeout as SocketTimeout

from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError
from urllib3.util.connection import allowed_gai_family, create_connection


logger = logging.getLogger('warcserver')

# set by install(): returns True if an IP address is not allowed
is_ip_blocked = None


def is_enabled():
    return os.environ.get('PYWB_LIVE_CONNECT_GUARD', 'true').strip().lower() not in ('false', '0', 'no', 'off')


class GuardedConnectionMixin(object):
    def _new_conn(self):
        """Same as urllib3 ``HTTPConnection._new_conn``, but only connects to
        the allowed addresses of a single host resolution.
        """
        extra_kw = {}
        if self.source_address:
            extra_kw['source_address'] = self.source_address

        if self.socket_options:
            extra_kw['socket_options'] = self.socket_options

        try:
            addr_infos = socket.getaddrinfo(self._dns_host.strip('[]'), self.port,
                                            allowed_gai_family(), socket.SOCK_STREAM)
        except (SocketError, UnicodeError) as e:
            raise NewConnectionError(self, 'Failed to establish a new connection: %s' % e)

        addresses = []
        for addr_info in addr_infos:
            if addr_info[4][0] not in addresses:
                addresses.append(addr_info[4][0])

        allowed = [addr for addr in addresses if not is_ip_blocked(addr)]
        if not allowed:
            logger.warning('live_url_filter blocked: connection to %s:%s, resolved to %s',
                           self.host, self.port, ', '.join(addresses) or 'no address')
            raise NewConnectionError(self, 'Blocked by live_url_filter: %s resolves to a blocked address'
                                     % self.host)

        err = None
        for addr in allowed:
            try:
                return create_connection((addr, self.port), self.timeout, **extra_kw)
            except SocketError as e:
                err = e

        if isinstance(err, SocketTimeout):
            raise ConnectTimeoutError(
                self, 'Connection to %s timed out. (connect timeout=%s)' % (self.host, self.timeout))

        raise NewConnectionError(self, 'Failed to establish a new connection: %s' % err)


class GuardedHTTPConnection(GuardedConnectionMixin, HTTPConnection):
    pass


class GuardedHTTPSConnection(GuardedConnectionMixin, HTTPSConnection):
    pass


class GuardedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = GuardedHTTPConnection


class GuardedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = GuardedHTTPSConnection


GUARDED_POOL_CLASSES_BY_SCHEME = {
    'http': GuardedHTTPConnectionPool,
    'https': GuardedHTTPSConnectionPool,
}


def guard_pool_manager(pool_manager):
    pool_manager.pool_classes_by_scheme = dict(GUARDED_POOL_CLASSES_BY_SCHEME)
    # drop any pool created before, with the default connection classes
    pool_manager.clear()


def install(ip_blocked_func):
    """Install the guard on the pywb live and remote adapters, if enabled.

    ``ip_blocked_func(addr)`` returns True if pywb must not connect to the
    IP address ``addr``.
    """
    global is_ip_blocked

    if not is_enabled():
        logger.warning('live_url_filter connection guard disabled by PYWB_LIVE_CONNECT_GUARD')
        return False

    from pywb.warcserver.http import DefaultAdapters, PywbHttpAdapter

    is_ip_blocked = ip_blocked_func

    # adapters created later, eg. by WarcServer with a certificates config
    if not getattr(PywbHttpAdapter.init_poolmanager, 'live_connect_guard', False):
        orig_init_poolmanager = PywbHttpAdapter.init_poolmanager

        def init_poolmanager(self, *args, **kwargs):
            orig_init_poolmanager(self, *args, **kwargs)
            guard_pool_manager(self.poolmanager)

        init_poolmanager.live_connect_guard = True
        PywbHttpAdapter.init_poolmanager = init_poolmanager

    guard_pool_manager(DefaultAdapters.live_adapter.poolmanager)
    guard_pool_manager(DefaultAdapters.remote_adapter.poolmanager)
    return True
