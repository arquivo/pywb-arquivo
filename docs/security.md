# Security: SSRF protection of save and patching

## The issue

The `save` and `patching` instances request urls chosen by their users:

- `save` fetches a page from the live web and records it in a WARC
  (`/save/record/...`);
- `patching` fills missing resources by fetching them from other web archives
  (eg. the Internet Archive) and from the live web.

Without restrictions, this is a server-side request forgery (SSRF): a user can
make pywb request a service that is only reachable from the server, like
`http://127.0.0.1:8081/`, a host on a private network, a cloud metadata
service (`169.254.169.254`) or the Arquivo.pt internal infrastructure. With
`save` it is worse, as the response is recorded and can then be replayed, so
the internal content is exposed to anyone.

### DNS rebinding

Checking the url before the request is not enough. The check resolves the
host name, then urllib3 resolves it again when connecting. A DNS rebinding
domain, with a TTL of 0, answers a public address to the first lookup and an
internal one (eg. `127.0.0.1`) to the next, so the check sees the public
address and pywb connects to the internal one. Public services provide such
domains, eg. `http://<public-ip-hex>.7f000001.rbndr.us/`.

## Fix 1: `live_url_filter`, check the url before the request

`save` and `patching` use a pywb
[fork](https://github.com/arquivo/pywb/tree/arquivo-2.9.0-live-url-filter)
with the `live_url_filter` config option (proposed upstream in
[webrecorder/pywb#1032](https://github.com/webrecorder/pywb/pull/1032)),
set on their `config.yaml` to
[`pywb_arquivo.live_url_filter`](../pywb_arquivo/live_url_filter.py):

```yaml
live_url_filter: pywb_arquivo.live_url_filter:is_url_allowed
```

pywb calls it before every request to the live web or to a remote web
archive, including the redirects it follows, and before the video info
requests. A url is blocked when its host:

- is in a blocked domain, by default `arquivo.pt` and all its subdomains;
- resolves to a non public address: private networks, loopback, link-local,
  carrier-grade NAT, reserved, multicast, ..., including the IPv6 forms that
  embed one of those IPv4 addresses (IPv4-mapped, 6to4, Teredo, NAT64);
- resolves to a blocked network, by default the Arquivo.pt public networks
  `194.210.235.0/26` and `2001:690:a00:1039::/64`.

IP literals in other forms, like `0x7f.1` or `2130706433`, are parsed as the
connection would parse them. When loading from another web archive, the
original url host is also checked, without resolving it.

The blocked domains and networks can be changed with the comma separated
`PYWB_LIVE_BLOCKED_DOMAINS` and `PYWB_LIVE_BLOCKED_NETWORKS` (IPs or CIDRs)
environment variables.

## Fix 2: `live_connect_guard`, check the address when connecting

Against DNS rebinding, [`pywb_arquivo.live_connect_guard`](../pywb_arquivo/live_connect_guard.py)
checks the address pywb actually connects to. When opening a connection, it
resolves the host once, drops the addresses blocked by `live_url_filter` and
connects only to an allowed one. If none is left, the request fails and it logs:

```
live_url_filter blocked: connection to <host>:<port>, resolved to <addresses>
```

The host name is kept on the connection, so the `Host` header, TLS SNI and
certificate checks are unchanged.

It is installed when `pywb_arquivo.live_url_filter` is imported, so only on
`save` and `patching`, and only on the pywb adapters used for the live web and
remote web archives (`DefaultAdapters.live_adapter` and `remote_adapter`,
including the ones created later by `PywbHttpAdapter`). urllib3 and `socket`
are not patched globally, so the other requests keep working: WARC records
loaded over http from an internal host, and the recorder calls to the internal
warcserver on `localhost`.

It can be disabled with `PYWB_LIVE_CONNECT_GUARD=false` (or `0`, `no`, `off`),
as a rollback switch, which logs a warning.

As pywb retries failed connections (`Retry(3)`), a blocked request can log the
blocked message up to 4 times.

## Limitations

- A SOCKS proxy (`SOCKS_HOST`) or an http proxy from the environment
  (`HTTP_PROXY`, `HTTPS_PROXY`) resolves the host on the proxy, so the
  connection check doesn't apply. None is set on `save` or `patching`.
- `youtube-dl` / `yt-dlp` makes its own requests after the filter check of the
  video info url. It is not installed on `save`.
- `live_connect_guard` relies on urllib3 1.26 internals (`_new_conn`,
  `_dns_host`), so it must be checked again when the `urllib3==1.26.9` pin
  changes.

Network level egress rules on the servers are an additional layer, managed
outside this repository.

## Tests

- [`tests/test_live_url_filter.py`](../tests/test_live_url_filter.py): the
  blocked domains, addresses and IP literal forms.
- [`tests/test_live_connect_guard.py`](../tests/test_live_connect_guard.py):
  a resolver that changes its answer reproduces the rebinding with plain
  urllib3, and is blocked on the pywb live and remote adapters; public hosts
  still connect; the `localhost` and http WARC record requests are not
  affected.
- [`tests/test_live_connect_guard_record.py`](../tests/test_live_connect_guard_record.py):
  records with a pywb app configured like `save`. A public page is recorded,
  a rebinding domain is blocked, and with the guard disabled the same domain
  is recorded, which confirms the test reproduces the attack.

```bash
uv pip install "$(grep '^pywb @' save/requirements.txt)" urllib3==1.26.9 'setuptools<81' pytest mock
python -m pytest tests
```
