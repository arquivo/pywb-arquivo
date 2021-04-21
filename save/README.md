```
virtualenv venv --python=python3
. venv/bin/activate
pip install -r requirements.txt --upgrade
wb-manager init save
uwsgi --ini uwsgi.ini
```

# Capture a page using

http://localhost:8586/save/record/https://www.fccn.pt/

