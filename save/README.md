# Archive Page Now

This is the pywb instance used by the Archive Page Now service of Arquivo.pt.

## Create a virtual environment

From the repository root, create the virtual environment with the locked dependencies and activate it:

```bash
uv sync
. .venv/bin/activate
```

## Run

Run it with:

```bash
wb-manager init save
PYTHONPATH=.. uwsgi --ini uwsgi.ini
```

The `PYTHONPATH` makes the [`pywb_arquivo`](../pywb_arquivo) package, used by the `live_url_filter`, available.

# Capture a page using

http://localhost:8586/save/record/https://www.fccn.pt/

