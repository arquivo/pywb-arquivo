"""WSGI application for the Arquivo.pt pywb instances that fetch from the live
web (save and patching): pywb wrapped with the Arquivo.pt middleware.

Configure it on the uwsgi.ini::

    wsgi = pywb_arquivo.wsgi
"""
# pywb.apps.wayback applies the gevent monkey patching before loading pywb
from pywb.apps.wayback import application as pywb_application

from pywb_arquivo.sec_fetch_dest import SecFetchDestMiddleware


application = SecFetchDestMiddleware(pywb_application)
