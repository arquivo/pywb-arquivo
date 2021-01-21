## pywb-arquivo

At Arquivo.pt anyone can search for information published since 1996.

One software component, that is responsible for the reproduction of preserved pages is the Wayback. Arquivo.pt uses [pywb](https://github.com/ikreymer/pywb) Wayback written in python by Ilya Kreymer.

This repository contains Arquivo.pt's branding customizations for our instance of pywb.


## Docker

Run using docker compose:
```bash
docker-compose up
```

For production you need to review the uwsgi.ini and config.yaml files.

