## pywb-arquivo

At [Arquivo.pt](https://arquivo.pt) anyone can search for information published since 1996.

One software component, that is responsible for the reproduction of preserved pages is the Wayback. [Arquivo.pt](https://arquivo.pt) uses [pywb](https://github.com/webrecorder/pywb) Wayback written in python by Ilya Kreymer.

This repository contains [Arquivo.pt](https://arquivo.pt)'s branding customizations for our instance of pywb.

## Development workflow

This repository uses the simplified two-branch workflow.

* `master` for production-ready branch
* `development` for new features

## Instances

We use different pywb instances for a different proposes.

| pywb instance type | port | pywb wayback description                                                      |
|--------------------|------|-------------------------------------------------------------------------------|
| framed             | 8081 | The normal wayback                                                            |
| unframed/noframe   | 8082 | Wayback without the Arquivo.pt branding                                       |
| patching           | 8586 | Wayback that tries to fill missing resources by harvesting from other sources |
| save               | 8083 | Wayback that archives a live page                                             |

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

All the pywb instances share the same Python version and dependencies, defined on the
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
docker compose build && docker compose run pywb-arquivo-framed
```

## Development using uv

Create the virtual environment with the locked dependencies and activate it.

```bash
uv sync
. .venv/bin/activate
```

## Local cdx files

If you prefer to use your local cdx files you need to change the pywb instance `config.yaml` file. For example: [`framed/config.yaml`](framed/config.yaml):

```bash
CDX_FOLDER=/my-folder-to/indexes_cdx docker compose run pywb-arquivo-framed
```

## Production

For production you need to review the `uwsgi.ini` and `config.yaml` files.

## Monitoring

Each instance enables the uWSGI stats server on the `/tmp/uwsgi-stats.sock` unix socket (change it with the
`STATS_SOCKET` environment variable), so it isn't reachable from the network. To monitor the uWSGI workers
directly inside the docker container, run [uwsgitop](https://github.com/xrmx/uwsgitop):

```bash
docker compose exec pywb-arquivo-framed uwsgitop /tmp/uwsgi-stats.sock
```

