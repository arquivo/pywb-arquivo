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
See [docs/security.md](docs/security.md) for the issue, both fixes and their configuration.

Run the tests with:

```bash
uv pip install "$(grep '^pywb @' save/requirements.txt)" urllib3==1.26.9 'setuptools<81' pytest mock
python -m pytest tests
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

Install a compatible Python version, activate a virtual environment and install requirements.

```bash
uv venv --seed venv -p python3.9.23
. venv/bin/activate
uv pip install -r requirements.txt
```

## Local cdx files

If you prefer to use your local cdx files you need to change the pywb instance `config.yaml` file. For example: [`framed/config.yaml`](framed/config.yaml):

```bash
CDX_FOLDER=/my-folder-to/indexes_cdx docker compose run pywb-arquivo-framed
```

## Production

For production you need to review the `uwsgi.ini` and `config.yaml` files.

