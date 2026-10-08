"""pywb ``live_url_filter`` for the Arquivo.pt pywb instances that fetch from
the live web or from other web archives (save and patching).

It prevents those instances from being used to request (and record) content
from the Arquivo.pt internal infrastructure, by blocking requests to:

* hosts that resolve to a non public address: private networks, loopback,
  link-local, carrier-grade NAT, reserved, multicast, ...;
* hosts in a blocked domain, by default ``arquivo.pt`` and all its subdomains;
* extra blocked addresses or networks, by default the Arquivo.pt public
  networks.

Configure it on the pywb ``config.yaml``::

    live_url_filter: pywb_arquivo.live_url_filter:is_url_allowed

The blocked domains and networks can be changed with the comma separated
``PYWB_LIVE_BLOCKED_DOMAINS`` and ``PYWB_LIVE_BLOCKED_NETWORKS`` environment
variables.

This does not protect against DNS rebinding, as pywb resolves the host again
when connecting, so it should be complemented by network egress rules.
"""
import ipaddress
import os
import socket

from urllib3.exceptions import LocationParseError
from urllib3.util import parse_url


DEFAULT_BLOCKED_DOMAINS = 'arquivo.pt'

# Arquivo.pt public networks
DEFAULT_BLOCKED_NETWORKS = '194.210.235.0/26,2001:690:a00:1039::/64'

NAT64_NETWORK = ipaddress.ip_network('64:ff9b::/96')


def _split_env(name, default=''):
    return [value.strip() for value in os.environ.get(name, default).split(',') if value.strip()]


BLOCKED_DOMAINS = [domain.strip('.').lower() for domain in
                   _split_env('PYWB_LIVE_BLOCKED_DOMAINS', DEFAULT_BLOCKED_DOMAINS)]

BLOCKED_NETWORKS = [ipaddress.ip_network(network, strict=False) for network in
                    _split_env('PYWB_LIVE_BLOCKED_NETWORKS', DEFAULT_BLOCKED_NETWORKS)]


def is_url_allowed(url, cdx=None):
    """pywb live_url_filter: return True if pywb is allowed to request ``url``.

    ``url`` is the url pywb is about to connect to, its host is resolved and
    all its addresses must be public.
    ``cdx['url']`` is the original url, it differs from ``url`` when loading
    from another web archive (eg. Internet Archive), where only the host name
    and IP literals are checked, as the original host is not contacted.
    """
    if not _is_host_allowed(_get_host(url), resolve=True):
        return False

    orig_url = cdx.get('url') if cdx else None
    if orig_url and orig_url != url:
        return _is_host_allowed(_get_host(orig_url), resolve=False)

    return True


def _get_host(url):
    # parse with urllib3, the same parser used by pywb to connect
    try:
        host = parse_url(url).host
    except LocationParseError:
        return None

    if not host:
        return None

    host = host.strip('[]').rstrip('.').lower()
    try:
        # normalize unicode hosts, eg. alternative dots
        host = host.encode('idna').decode('ascii')
    except UnicodeError:
        pass

    return host


def _is_host_allowed(host, resolve):
    if not host:
        return False

    if any(host == domain or host.endswith('.' + domain) for domain in BLOCKED_DOMAINS):
        return False

    # without resolve, only parse IP literals (including forms like 0x7f.1 or 2130706433)
    flags = 0 if resolve else socket.AI_NUMERICHOST
    try:
        addr_infos = socket.getaddrinfo(host, None, 0, socket.SOCK_STREAM, 0, flags)
    except (socket.gaierror, UnicodeError, ValueError):
        # can't connect to a host that does not resolve,
        # when not resolving, it is a host name and not an IP literal
        return not resolve

    return not any(_is_ip_blocked(addr_info[4][0]) for addr_info in addr_infos)


def _is_ip_blocked(addr):
    ip = ipaddress.ip_address(addr.split('%', 1)[0])

    if ip.version == 6:
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo and ip.teredo[1])
        if not embedded and ip in NAT64_NETWORK:
            embedded = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if embedded and _is_ip_blocked(str(embedded)):
            return True

    if not ip.is_global or ip.is_multicast:
        return True

    # is_global is True for some reserved IPv6 forms that embed an IPv4
    # address, like the deprecated IPv4-compatible ::a.b.c.d or the
    # IPv4-translated ::ffff:0:a.b.c.d, the NAT64 embedded address was checked
    if ip.is_reserved and ip not in NAT64_NETWORK:
        return True

    return any(ip in network for network in BLOCKED_NETWORKS)
