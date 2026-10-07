# Archive Page Now

This is the pywb instance used by the Archive Page Now service of Arquivo.pt.

## Create a virtual environment

With `uv`:

```bash
uv venv --seed venv -p python3.9.23
. venv/bin/activate
uv pip install -r requirements.txt
```

With virtualenv:
```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt --upgrade
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

