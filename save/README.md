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
uwsgi --ini uwsgi.ini
```

# Capture a page using

http://localhost:8586/save/record/https://www.fccn.pt/

