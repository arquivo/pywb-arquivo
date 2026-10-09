# Live web requests filter

The `save` (ArchivePageNow) and `patching` pywb instances fetch pages from the live web and from
other web archives, for any url requested by a user. Without restrictions, they could be used to
request, and record, content from the Arquivo.pt internal infrastructure or any other host only
reachable from the pywb servers (Server-Side Request Forgery, SSRF).

To prevent it, those instances use the pywb `live_url_filter` config option with the
[`pywb_arquivo.live_url_filter`](../pywb_arquivo/live_url_filter.py) implementation.

## How it works

pywb calls the filter before every request to the live web, or to a remote web archive
(eg. the Internet Archive memento source used by `patching`), as `is_url_allowed(url, cdx)`:

* `url` is the url pywb is about to connect to;
* `cdx` is the capture being loaded, `cdx['url']` is the original url.

The request is only made if the filter returns `True`. If it returns a false value, or raises an
exception, pywb doesn't make the request, responds with an HTTP 400 error and logs a warning:

```
WARNING:warcserver:live_url_filter blocked: http://127.0.0.1:8081/
```

The check is made by pywb when looking up the live index and when loading the resource, including
video urls (`VideoLoader`), before `youtube-dl`/`yt-dlp` extracts the video info.

pywb doesn't follow redirects when fetching, the redirect is sent to the browser and the new url is
checked when it is requested.

The `live_url_filter` option is available on upstream [pywb](https://github.com/webrecorder/pywb)
([webrecorder/pywb#1032](https://github.com/webrecorder/pywb/pull/1032)), see its
[documentation](https://github.com/webrecorder/pywb/blob/main/docs/manual/configuring.rst#filtering-live-web-requests).
pywb only provides the hook, the filter implementation is in this repository.

## What is blocked

The host of `url` is resolved and **all** its addresses must be allowed. A request is blocked when:

* the url has no host or can't be parsed (urllib3 is used, the same parser used by pywb to connect);
* the host doesn't resolve, as pywb couldn't connect to it anyway;
* the host is a blocked domain, or one of its subdomains, by default `arquivo.pt`
  (the domain check matches `www.arquivo.pt`, but not `notarquivo.pt` or `arquivo.pt.example.com`);
* any of the host addresses isn't public, as reported by Python's `ipaddress`
  (`is_global`): private networks, loopback, link-local (eg. cloud metadata `169.254.169.254`),
  carrier-grade NAT, unspecified, reserved, documentation, ... and multicast addresses;
* any of the host addresses is in a blocked network, by default the Arquivo.pt public networks
  `194.210.235.0/26` and `2001:690:a00:1039::/64`.

The host is normalized before the checks, so alternative notations of the same address or host are
also blocked:

* IPv4 alternative notations, resolved by the system, eg. `0x7f000001`, `2130706433`, `0177.1`,
  `127.1`;
* IPv6 addresses that embed an IPv4 address, whose IPv4 address is also checked: IPv4-mapped
  (`::ffff:127.0.0.1`), 6to4 (`2002::/16`), Teredo, NAT64 (`64:ff9b::/96`), and the deprecated
  IPv4-compatible (`::127.0.0.1`) and IPv4-translated (`::ffff:0:a.b.c.d`) forms. NAT64 of a
  public address is allowed;
* IPv6 zone ids (`fe80::1%eth0`), trailing dots (`arquivo.pt.`), upper case and unicode
  alternative dots in host names.

### Loading from another web archive

When `url` differs from the original url (`cdx['url']`), pywb is loading the capture from another
web archive (eg. `https://web.archive.org/web/<timestamp>id_/<original url>`):

* the web archive host, from `url`, is resolved and checked as above;
* the original url host is **not** resolved, as it isn't contacted, only blocked domains and IP
  literals are checked. So `http://10.0.0.1/` or `http://www.arquivo.pt/` captures aren't
  loaded from the Internet Archive, but `http://private.example.com/` is.

## Where it is enabled

| pywb instance | `live_url_filter` | Reason                                                                 |
|---------------|-------------------|------------------------------------------------------------------------|
| save          | enabled           | records any url from the live web                                      |
| patching      | enabled           | records missing resources from the Internet Archive and the live web   |
| framed        | disabled          | only loads from the `memento+https://arquivo.pt/wayback/` index        |
| unframed      | disabled          | only loads from the `memento+https://arquivo.pt/wayback/` index        |

The framed and unframed instances don't fetch user provided urls, and the filter would block them,
as they load content from `arquivo.pt`.

It is enabled on the instance `config.yaml`:

```yaml
# Block requests to Arquivo.pt internal infrastructure and private networks
live_url_filter: pywb_arquivo.live_url_filter:is_url_allowed
```

The [`pywb_arquivo`](../pywb_arquivo) package is copied to the save and patching Docker images,
from the `pywb_arquivo` build context. When running without Docker, add the repository root to the
`PYTHONPATH`, see [`save/README.md`](../save/README.md).

## Configuration

The blocked domains and networks can be changed with environment variables, comma separated.
When set, they replace the defaults.

| Environment variable         | Default                                         | Description                                 |
|------------------------------|-------------------------------------------------|---------------------------------------------|
| `PYWB_LIVE_BLOCKED_DOMAINS`  | `arquivo.pt`                                    | domains blocked, including their subdomains |
| `PYWB_LIVE_BLOCKED_NETWORKS` | `194.210.235.0/26,2001:690:a00:1039::/64`       | IPs or CIDRs blocked, besides non public    |

For example, to also block `fccn.pt`:

```bash
PYWB_LIVE_BLOCKED_DOMAINS=arquivo.pt,fccn.pt
```

The variables are read when the module is imported, so the instance must be restarted after
changing them.

## Limitations

The filter is an application level check, it should be complemented by network egress rules on
the save and patching servers:

* **DNS rebinding**: the filter resolves the host, but pywb resolves it again when connecting, so
  a host name that resolves to a public address on the check and to an internal address on the
  connection isn't blocked by the filter. It is blocked by
  [`live_connect_guard`](../pywb_arquivo/live_connect_guard.py), installed when the filter is
  imported, which checks the address again when connecting, see [security.md](security.md);
* **Default networks**: the blocked networks default to the Arquivo.pt public networks, they must
  be kept up to date (`PYWB_LIVE_BLOCKED_NETWORKS`) if the Arquivo.pt addresses change.

## Tests

The filter tests are in [`tests/test_live_url_filter.py`](../tests/test_live_url_filter.py).
Run them with:

```bash
uv run pytest
```

To check it on a running instance, eg. with `docker compose up`, a blocked url returns an HTTP 400
error and a public url is recorded:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8586/save/record/mp_/http://127.0.0.1/
# 400
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8586/save/record/mp_/https://www.fccn.pt/
# 200
```

The tests and examples must only use generic host names (eg. `backend.example.com`) and
documentation addresses ([RFC 5737](https://www.rfc-editor.org/rfc/rfc5737) IPv4,
`2001:db8::/32` IPv6), never Arquivo.pt server names or internal addresses.

## History

* The `live_url_filter` option was first added to a pywb fork,
  [`arquivo/pywb@arquivo-2.9.0-live-url-filter`](https://github.com/arquivo/pywb/tree/arquivo-2.9.0-live-url-filter),
  and contributed upstream as [webrecorder/pywb#1032](https://github.com/webrecorder/pywb/pull/1032).
* Since [#43](https://github.com/arquivo/pywb-arquivo/pull/43) all the pywb instances use upstream
  pywb, locked by commit on [`uv.lock`](../uv.lock), and the fork is no longer used.
