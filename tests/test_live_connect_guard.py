import logging
import os
import socket
import subprocess
import sys
from io import BytesIO

import pytest
import requests
from mock import patch
from urllib3 import PoolManager
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError
from urllib3.poolmanager import pool_classes_by_scheme
from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from werkzeug.test import Client
from werkzeug.wrappers import Response

from pywb.indexer.cdxindexer import write_cdx_index

from pywb.utils.loaders import BlockLoader
from pywb.warcserver.http import DefaultAdapters, PywbHttpAdapter
from pywb.warcserver.liveurlfilter import LiveUrlFilter
from pywb.warcserver.resource.responseloader import LiveResourceException, LiveWebLoader
from pywb.warcserver.warcserver import WarcServer

from pywb_arquivo import live_connect_guard
from pywb_arquivo.live_connect_guard import (GuardedHTTPConnection, GuardedHTTPConnectionPool,
                                             GuardedHTTPSConnectionPool)
from pywb_arquivo.live_url_filter import is_url_allowed

from live_test_utils import (FakeDNS, LocalServer, PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6,
                             RedirectConnections)


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GUARDED_POOL_CLASSES = {'http': GuardedHTTPConnectionPool, 'https': GuardedHTTPSConnectionPool}


@pytest.fixture
def server():
    with LocalServer() as server:
        yield server


@pytest.fixture
def dns():
    dns = FakeDNS({
        'public.example.com': [PUBLIC_IP],
        'mixed.example.com': ['127.0.0.1', '10.1.2.3', PUBLIC_IP, '192.168.0.1', PUBLIC_IP_2, PUBLIC_IPV6],
        # rebinding domain: public address on the first lookup, loopback next
        'rebind.example.com': [[PUBLIC_IP], ['127.0.0.1']],
        'internal.example.com': ['127.0.0.1'],
        # host resolving to a blocked address, like the arcproxy hosts
        'backend.arquivo.pt': ['127.0.0.1'],
    })
    with patch('socket.getaddrinfo', dns):
        yield dns


@pytest.fixture
def redirect(server):
    redirect = RedirectConnections(server.port, live_connect_guard.create_connection)
    with patch('pywb_arquivo.live_connect_guard.create_connection', redirect):
        yield redirect


@pytest.fixture
def restore_pywb():
    live_adapter = DefaultAdapters.live_adapter
    remote_adapter = DefaultAdapters.remote_adapter
    func = LiveUrlFilter.func
    yield
    DefaultAdapters.live_adapter = live_adapter
    DefaultAdapters.remote_adapter = remote_adapter
    LiveUrlFilter.func = func


def live_get(url, is_live=True):
    """request ``url`` as pywb does for a live (or remote, not live) load"""
    return LiveWebLoader()._do_request('GET', url, None, {}, {}, is_live)


def assert_blocked_logged(caplog, host):
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(m.startswith('live_url_filter blocked: connection to ' + host) for m in messages), messages


# Installation
def test_installed_on_default_adapters():
    assert live_connect_guard.is_ip_blocked is not None
    assert DefaultAdapters.live_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    assert DefaultAdapters.remote_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES


def test_urllib3_default_pool_classes_not_changed():
    assert pool_classes_by_scheme['http'].__name__ == 'HTTPConnectionPool'
    assert pool_classes_by_scheme['https'].__name__ == 'HTTPSConnectionPool'
    assert PoolManager().pool_classes_by_scheme is pool_classes_by_scheme


def test_installed_on_adapters_created_later(restore_pywb):
    assert PywbHttpAdapter().poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES

    # WarcServer replaces both adapters when the config has a certificates section
    WarcServer(config_file=None, custom_config={
        'certificates': {'cert_reqs': 'CERT_REQUIRED'},
        'live_url_filter': 'pywb_arquivo.live_url_filter:is_url_allowed',
        'enable_auto_colls': False,
    })
    assert DefaultAdapters.live_adapter.cert_reqs == 'CERT_REQUIRED'
    assert DefaultAdapters.live_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES
    assert DefaultAdapters.remote_adapter.poolmanager.pool_classes_by_scheme == GUARDED_POOL_CLASSES


def test_install_twice_wraps_once():
    init_poolmanager = PywbHttpAdapter.init_poolmanager
    assert live_connect_guard.install(live_connect_guard.is_ip_blocked)
    assert PywbHttpAdapter.init_poolmanager is init_poolmanager


def run_python(code, **env):
    env = dict(os.environ, PYTHONPATH=ROOT_DIR, **env)
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT_DIR, env=env,
                          capture_output=True, text=True, check=True).stdout.split()


CHECK_INSTALLED = '''
from pywb_arquivo import live_url_filter
from pywb.warcserver.http import DefaultAdapters, PywbHttpAdapter
for adapter in (DefaultAdapters.live_adapter, DefaultAdapters.remote_adapter, PywbHttpAdapter()):
    print(adapter.poolmanager.pool_classes_by_scheme['http'].__name__)
    print(adapter.poolmanager.pool_classes_by_scheme['https'].__name__)
print(getattr(PywbHttpAdapter.init_poolmanager, 'live_connect_guard', False))
'''


@pytest.mark.parametrize('value', ['false', 'False', '0', 'no', 'off'])
def test_disabled_by_env(value):
    assert run_python(CHECK_INSTALLED, PYWB_LIVE_CONNECT_GUARD=value) == \
        ['HTTPConnectionPool', 'HTTPSConnectionPool'] * 3 + ['False']


@pytest.mark.parametrize('value', [None, 'true', ''])
def test_enabled_by_default(value):
    env = {} if value is None else {'PYWB_LIVE_CONNECT_GUARD': value}
    assert run_python(CHECK_INSTALLED, **env) == \
        ['GuardedHTTPConnectionPool', 'GuardedHTTPSConnectionPool'] * 3 + ['True']


def test_not_installed_without_live_url_filter():
    # framed, unframed and check don't configure the filter
    code = CHECK_INSTALLED.replace('from pywb_arquivo import live_url_filter', 'import pywb_arquivo')
    assert run_python(code) == ['HTTPConnectionPool', 'HTTPSConnectionPool'] * 3 + ['False']


# DNS rebinding
def test_rebinding_reproduction_without_guard(dns, server):
    # Finding 1: the filter sees the public address, urllib3 connects to loopback
    url = 'http://rebind.example.com:%d/' % server.port
    assert is_url_allowed(url) is True
    res = PoolManager().request('GET', url, retries=False)
    assert res.status == 200
    assert res.data == b'INTERNAL SECRET'


@pytest.mark.parametrize('is_live', [True, False])
def test_rebinding_blocked(dns, server, caplog, is_live):
    url = 'http://rebind.example.com:%d/' % server.port
    assert is_url_allowed(url) is True

    with pytest.raises(LiveResourceException):
        live_get(url, is_live)

    assert server.requests == []
    # one lookup by the filter, then one per connection attempt (Retry(3))
    assert dns.lookups_for('rebind.example.com') == [[PUBLIC_IP]] + [['127.0.0.1']] * 4
    assert_blocked_logged(caplog, 'rebind.example.com:%d' % server.port)


def test_rebinding_blocked_live_index_session(dns, server, caplog):
    # LiveIndexSource sends a HEAD request with a session using the live adapter
    sesh = requests.Session()
    sesh.mount('http://', DefaultAdapters.live_adapter)
    dns.hosts['rebind.example.com'] = ['127.0.0.1']

    with pytest.raises(requests.exceptions.ConnectionError):
        sesh.head('http://rebind.example.com:%d/' % server.port)

    assert server.requests == []
    assert_blocked_logged(caplog, 'rebind.example.com')


@pytest.mark.parametrize('host', ['internal.example.com', '127.0.0.1', 'localhost', '[::1]', '0x7f.1', '2130706433'])
def test_blocked_hosts(dns, server, caplog, host):
    # the guard doesn't depend on the filter being called first
    with pytest.raises(LiveResourceException):
        live_get('http://%s:%d/' % (host, server.port))

    assert server.requests == []


def test_blocked_error(dns, server, caplog):
    pool = GuardedHTTPConnectionPool('internal.example.com', server.port, retries=False)
    with pytest.raises(NewConnectionError) as e:
        pool.urlopen('GET', '/', retries=False)

    assert 'Blocked by live_url_filter: internal.example.com resolves to a blocked address' in str(e.value)
    assert_blocked_logged(caplog, 'internal.example.com:%d, resolved to 127.0.0.1' % server.port)


# Allowed connections
def test_public_host_connects(dns, server, redirect):
    res = live_get('http://public.example.com:%d/path?q=1' % server.port)
    assert res.status == 200
    assert res.read() == b'INTERNAL SECRET'

    assert redirect.addresses == [PUBLIC_IP]
    # the connection keeps the host name
    assert server.requests[0][1] == '/path?q=1'
    assert server.requests[0][2]['Host'] == 'public.example.com:%d' % server.port


def test_public_host_connects_remote_adapter(dns, server, redirect):
    res = live_get('http://public.example.com:%d/web/2020/http://example.com/' % server.port, is_live=False)
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP]


def test_public_ip_literal_connects(dns, server, redirect):
    res = live_get('http://%s:%d/' % (PUBLIC_IP, server.port))
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP]


def test_mixed_addresses_only_public(dns, server, redirect):
    # the first public address refuses the connection, the next public is tried
    redirect.refused = (PUBLIC_IP,)
    res = live_get('http://mixed.example.com:%d/' % server.port)
    assert res.status == 200
    assert redirect.addresses == [PUBLIC_IP, PUBLIC_IP_2]


def test_mixed_addresses_all_public_fail(dns, server, redirect):
    redirect.refused = (PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6)
    conn = GuardedHTTPConnection('mixed.example.com', server.port)
    with pytest.raises(NewConnectionError) as e:
        conn.connect()

    assert 'Failed to establish a new connection' in str(e.value)
    assert redirect.addresses == [PUBLIC_IP, PUBLIC_IP_2, PUBLIC_IPV6]
    assert server.requests == []


def test_connection_options_kept(dns, server, redirect):
    socket_options = [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1), (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    conn = GuardedHTTPConnection('public.example.com', server.port, timeout=7,
                                 source_address=('127.0.0.1', 0), socket_options=socket_options)
    conn.connect()
    conn.close()

    assert redirect.calls == [((PUBLIC_IP, server.port), 7,
                               {'source_address': ('127.0.0.1', 0), 'socket_options': socket_options})]


def test_connect_timeout(dns):
    with patch('pywb_arquivo.live_connect_guard.create_connection', side_effect=socket.timeout('timed out')):
        conn = GuardedHTTPConnection('public.example.com', 80, timeout=2)
        with pytest.raises(ConnectTimeoutError) as e:
            conn.connect()

    assert 'Connection to public.example.com timed out. (connect timeout=2)' in str(e.value)


def test_host_not_resolved(dns):
    def not_found(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, 'Name or service not known')

    with patch('socket.getaddrinfo', not_found):
        conn = GuardedHTTPConnection('notfound.example.com', 80)
        with pytest.raises(NewConnectionError):
            conn.connect()


def test_https_keeps_host_name(dns, server, redirect):
    # TLS SNI and the certificate host name check use the host name, not the address
    with patch('urllib3.connection.ssl_wrap_socket', side_effect=RuntimeError('stop')) as wrap:
        with pytest.raises(RuntimeError):
            DefaultAdapters.live_adapter.poolmanager.urlopen(
                'GET', 'https://public.example.com:%d/' % server.port, retries=False)

    assert redirect.addresses == [PUBLIC_IP]
    assert wrap.call_args[1]['server_hostname'] == 'public.example.com'

    pool = DefaultAdapters.live_adapter.poolmanager.connection_from_url('https://public.example.com/')
    assert isinstance(pool, GuardedHTTPSConnectionPool)
    assert pool.host == 'public.example.com'


# Requests that must not be affected
def test_recorder_localhost_not_affected(dns, server):
    # the recorder and rewriter call the internal warcserver on localhost with requests
    url = 'http://localhost:%d/coll/resource/postreq?param.recorder.coll=coll' % server.port
    res = requests.request('GET', url)
    assert res.status_code == 200
    assert res.content == b'INTERNAL SECRET'

    assert requests.Session().get_adapter(url).poolmanager.pool_classes_by_scheme is pool_classes_by_scheme


def test_http_loader_archive_path_not_affected(dns, server):
    # WARC records loaded from an http:// archive path (arcproxy), on a host
    # resolving to a blocked address, use HttpLoader with its own session
    server.files['/arcproxy/test.warc.gz'] = b'0123456789WARC RECORD'
    url = 'http://backend.arquivo.pt:%d/arcproxy/test.warc.gz' % server.port

    assert BlockLoader().load(url, 10, 11).read() == b'WARC RECORD'
    assert server.requests[-1][2]['Range'] == 'bytes=10-20'

    # the same host is blocked for live loads
    with pytest.raises(LiveResourceException):
        live_get(url)


def write_warc(tmp_path):
    warc = BytesIO()
    writer = WARCWriter(warc, gzip=True)
    http_headers = StatusAndHeaders('200 OK', [('Content-Type', 'text/plain')], protocol='HTTP/1.0')
    writer.write_record(writer.create_warc_record('http://example.com/', 'response',
                                                  payload=BytesIO(b'ARCHIVED PAGE'),
                                                  http_headers=http_headers))

    index = tmp_path / 'index.cdxj'
    with open(str(index), 'wb') as out:
        write_cdx_index(out, BytesIO(warc.getvalue()), 'test.warc.gz', cdxj=True)

    return warc.getvalue(), index


def test_warcserver_http_archive_path_not_affected(dns, server, tmp_path, restore_pywb):
    # a collection with an http:// archive path, as used to load WARC records from arcproxy
    warc, index = write_warc(tmp_path)
    server.files['/arcproxy/test.warc.gz'] = warc

    app = WarcServer(config_file=None, custom_config={
        'collections': {'arc': {
            'index_paths': str(index),
            'archive_paths': 'http://backend.arquivo.pt:%d/arcproxy/' % server.port,
        }},
        'live_url_filter': 'pywb_arquivo.live_url_filter:is_url_allowed',
        'enable_auto_colls': False,
    })

    res = Client(app, Response).get('/arc/resource?url=http://example.com/')

    assert res.status_code == 200
    assert b'ARCHIVED PAGE' in res.data
    assert server.requests[-1][1] == '/arcproxy/test.warc.gz'
    assert server.requests[-1][2]['Range'].startswith('bytes=0-')
