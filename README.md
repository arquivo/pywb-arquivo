## pywb-arquivo

At [Arquivo.pt](https://arquivo.pt) anyone can search for information published since 1996.

One software component, responsible for replaying preserved pages, is the Wayback. [Arquivo.pt](https://arquivo.pt) uses [pywb](https://github.com/webrecorder/pywb) Wayback written in python by Ilya Kreymer.

This repository contains [Arquivo.pt](https://arquivo.pt)'s branding customizations for our instance of pywb.

## Development workflow

This repository uses a single `main` branch.

## Instances

We use different pywb instances for different purposes.

| pywb instance type | port | pywb wayback description                                                      |
|--------------------|------|-------------------------------------------------------------------------------|
| framed             | 8081 | The normal wayback                                                            |
| unframed/noframe   | 8082 | Wayback without the Arquivo.pt branding                                       |
| patching           | 8083 | Wayback that tries to fill missing resources by harvesting from other sources |
| save               | 8586 | Wayback that archives a live page                                             |

## Security

The `save` and `patching` instances fetch urls chosen by their users, from the live web and from other
web archives. To prevent them from requesting (and recording) Arquivo.pt internal infrastructure, they
check the url before each request ([`live_url_filter`](pywb_arquivo/live_url_filter.py)) and the address
when connecting, against DNS rebinding ([`live_connect_guard`](pywb_arquivo/live_connect_guard.py)).
See [docs/security.md](docs/security.md) for the issue, both fixes and their configuration, and
[docs/live_url_filter.md](docs/live_url_filter.md) for the details of the url filter.

Run the tests with:

```bash
uv run pytest
```

## Dependencies

All the pywb instances share the same Python version (3.14) and dependencies, defined on the
[`pyproject.toml`](pyproject.toml) and locked on the [`uv.lock`](uv.lock) using [uv](https://docs.astral.sh/uv/).
pywb is installed from a [webrecorder/pywb](https://github.com/webrecorder/pywb) commit.

To upgrade the dependencies, change the `pyproject.toml` if needed and run:

```bash
uv lock --upgrade
```

## Development using docker

Build and run using docker compose:

```bash
docker compose build && docker compose up
```

If you want to just run the `framed` pywb instance:

```bash
docker compose run --build --remove-orphans pywb-arquivo-framed
```

## Development using uv

Create the virtual environment with the locked dependencies and activate it.

```bash
uv sync
. .venv/bin/activate
```

## Local cdx files

If you prefer to use your local cdx files you need to change the pywb instance `config.yaml` file, for example
[`framed/config.yaml`](framed/config.yaml). `CDX_FOLDER` is the host folder mounted on `/data/indexes_cdx`
(the default path of the cdx indexes on the `config.yaml` files):

```bash
CDX_FOLDER=/my-folder-to/indexes_cdx docker compose run pywb-arquivo-framed
```

## Production

For production you need to review the `uwsgi.ini` and `config.yaml` files.

## Performance

The `framed` and `unframed` instances keep the captures read from the index for a url in a uWSGI cache, `pywb-index`,
shared by all the workers, for 60 seconds. The request that follows a `redirect_to_exact` redirect, the lookup of the
original of a revisit and the cdx/timemap queries for the same url then don't read the index again. It is only used for
local indexes (CDX(J) files, folders of them and ZipNum), and captures added to an index can take up to 60 seconds to be
found. The cache uses 128 MB of shared memory for up to 20000 urls; change it with the `INDEX_CACHE` environment
variable, a uWSGI [`cache2`](https://uwsgi-docs.readthedocs.io/en/latest/Caching.html) value named `pywb-index`, or
disable it with `index_cache: false` on the `config.yaml`. See "Index Cache (uWSGI)" on the pywb docs.

ZipNum index blocks are decompressed with [isal](https://pypi.org/project/isal/), about 2.5 times faster than `zlib`.

## Monitoring

Each instance enables the uWSGI stats server on the `/tmp/uwsgi-stats.sock` unix socket (change it with the
`STATS_SOCKET` environment variable), so it isn't reachable from the network. To monitor the uWSGI workers
directly inside the docker container, run [uwsgitop](https://github.com/xrmx/uwsgitop):

```bash
docker compose exec pywb-arquivo-framed uwsgitop /tmp/uwsgi-stats.sock
```

On the `framed` and `unframed` instances, the `caches` section of the stats shows the items, hits, misses and full
counters of the `pywb-index` cache (`--connect-and-read` writes the stats to stderr); the `save` and `patching`
instances don't use this cache:

```bash
docker compose exec pywb-arquivo-framed uwsgi --connect-and-read /tmp/uwsgi-stats.sock 2>&1
```

