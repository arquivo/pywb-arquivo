import socket

import pytest
from unittest.mock import patch

from pywb_arquivo import live_url_filter
from pywb_arquivo.live_url_filter import is_url_allowed


REAL_GETADDRINFO = socket.getaddrinfo

FAKE_DNS = {
    'public.example.com': ['93.184.215.14', '2606:2800:21f:cb07:6820:80da:af6b:8b2c'],
    'private.example.com': ['10.1.2.3'],
    'mixed.example.com': ['93.184.215.14', '127.0.0.1'],
    'web.archive.org': ['207.241.237.3'],
    'www.notarquivo.pt': ['93.184.215.14'],
    'arquivo.pt.example.com': ['93.184.215.14'],
}


def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host in FAKE_DNS and not flags & socket.AI_NUMERICHOST:
        return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, type, proto, '', (ip, 0))
                for ip in FAKE_DNS[host]]

    # only allow parsing IP literals, never query the real DNS
    return REAL_GETADDRINFO(host, port, family, type, proto, flags | socket.AI_NUMERICHOST)


@pytest.fixture(autouse=True)
def fake_dns():
    with patch('socket.getaddrinfo', fake_getaddrinfo):
        yield


def live_cdx(url):
    return {'url': url, 'load_url': url, 'is_live': 'true'}


@pytest.mark.parametrize('url', [
    'http://public.example.com/',
    'https://public.example.com:8443/path?q=1',
    'http://93.184.215.14/',
    'http://[2606:2800:21f:cb07:6820:80da:af6b:8b2c]/',
    'http://www.notarquivo.pt/',
    'http://arquivo.pt.example.com/',
    'http://194.210.235.64/',
    'http://[2001:690:a00:103a::1]/',
    # NAT64 of a public address
    'http://[64:ff9b::5db8:d70e]/',
])
def test_allowed(url):
    assert is_url_allowed(url, live_cdx(url)) is True
    assert is_url_allowed(url) is True


@pytest.mark.parametrize('url', [
    # private, loopback, link-local, cgnat, reserved, unspecified, multicast
    'http://10.0.0.1/',
    'http://172.16.5.4:8080/',
    'http://192.168.1.1/',
    'http://127.0.0.1:6379/',
    'http://127.1/',
    'http://localhost/',
    'http://169.254.169.254/latest/meta-data/',
    'http://100.64.0.1/',
    'http://0.0.0.0:8080/',
    'http://240.0.0.1/',
    'http://224.0.0.1/',
    # alternative IPv4 notations
    'http://2130706433/',
    'http://0x7f000001/',
    'http://0x7f.0.0.1/',
    'http://0177.0.0.1/',
    # IPv6 and IPv4 embedded in IPv6
    'http://[::1]/',
    'http://[::]/',
    'http://[fe80::1]/',
    'http://[fc00::1]/',
    'http://[::ffff:10.0.0.1]/',
    'http://[::ffff:7f00:1]/',
    'http://[2002:0a00:0001::1]/',
    'http://[64:ff9b::a00:1]/',
    'http://[64:ff9b:1::a00:1]/',
    'http://[::127.0.0.1]/',
    'http://[::10.0.0.1]/',
    'http://[::5db8:d70e]/',
    'http://[::ffff:0:a00:1]/',
    'http://[::ffff:0:5db8:d70e]/',
    'http://[4000::1]/',
    # host names resolving to private addresses
    'http://private.example.com/',
    'http://mixed.example.com/',
    # arquivo.pt and its subdomains
    'http://arquivo.pt/',
    'https://ARQUIVO.PT./',
    'http://my_backend_server.arquivo.pt:8080/',
    'http://backend.arquivo.pt/',
    # Arquivo.pt public networks
    'http://194.210.235.1/',
    'http://194.210.235.63:8080/',
    'http://[2001:690:a00:1039::1]/',
    'http://[::ffff:194.210.235.10]/',
    'http://user:pass@sub.arquivo.pt/',
    'http://sub.arquivo。pt/',
    # not resolvable, or no host
    'http://does-not-exist.invalid/',
    'http:///path',
    'file:///etc/passwd',
])
def test_blocked(url):
    assert is_url_allowed(url, live_cdx(url)) is False


def test_remote_archive_load():
    load_url = 'https://web.archive.org/web/2020id_/'

    for orig_url in ['http://public.example.com/', 'http://does-not-exist.invalid/']:
        assert is_url_allowed(load_url + orig_url, {'url': orig_url}) is True

    for orig_url in ['http://10.0.0.1/', 'http://0x7f000001/', 'http://www.arquivo.pt/']:
        assert is_url_allowed(load_url + orig_url, {'url': orig_url}) is False

    # the original host is not resolved, it is not contacted
    assert is_url_allowed(load_url + 'http://private.example.com/',
                          {'url': 'http://private.example.com/'}) is True

    # the archive host itself must be public
    assert is_url_allowed('http://10.0.0.1/web/2020id_/http://public.example.com/',
                          {'url': 'http://public.example.com/'}) is False


def test_blocked_networks_and_domains():
    with patch.object(live_url_filter, 'BLOCKED_NETWORKS', [live_url_filter.ipaddress.ip_network('93.184.215.0/24')]), \
         patch.object(live_url_filter, 'BLOCKED_DOMAINS', ['example.com', 'arquivo.pt']):
        assert is_url_allowed('http://93.184.215.14/') is False
        assert is_url_allowed('http://public.example.com/') is False
        assert is_url_allowed('http://arquivo.pt/') is False
        assert is_url_allowed('http://207.241.237.3/') is True


def test_env_config(monkeypatch):
    import importlib

    monkeypatch.setenv('PYWB_LIVE_BLOCKED_DOMAINS', ' arquivo.pt , .fccn.pt. ')
    monkeypatch.setenv('PYWB_LIVE_BLOCKED_NETWORKS', '93.184.215.14, 2001:db8::/32')
    try:
        importlib.reload(live_url_filter)
        assert live_url_filter.BLOCKED_DOMAINS == ['arquivo.pt', 'fccn.pt']
        assert [str(n) for n in live_url_filter.BLOCKED_NETWORKS] == ['93.184.215.14/32', '2001:db8::/32']
        assert live_url_filter.is_url_allowed('http://93.184.215.14/') is False
        # the defaults are replaced
        assert live_url_filter.is_url_allowed('http://194.210.235.1/') is True
        assert live_url_filter.is_url_allowed('http://www.fccn.pt/') is False
    finally:
        monkeypatch.delenv('PYWB_LIVE_BLOCKED_DOMAINS')
        monkeypatch.delenv('PYWB_LIVE_BLOCKED_NETWORKS')
        importlib.reload(live_url_filter)
