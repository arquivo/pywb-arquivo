"""WSGI middleware for the Arquivo.pt pywb instances that fetch from the live
web (save and patching), that sends frame requests upstream as documents.

pywb loads the page being recorded inside an iframe, so the browser sends
``Sec-Fetch-Dest: iframe`` on its requests and pywb forwards that header to
the live site. Sites that refuse to be framed, such as Facebook, then answer
with an error page instead of the page itself, and that error page is what
gets recorded.

The page and the links followed from it are loaded in the same iframe as the
frames embedded in the page, and they can't be told apart by their headers,
so every ``iframe`` and ``frame`` request is sent upstream as ``document``.
"""

FRAME_DESTINATIONS = ('iframe', 'frame')


class SecFetchDestMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ.get('HTTP_SEC_FETCH_DEST', '').lower() in FRAME_DESTINATIONS:
            environ['HTTP_SEC_FETCH_DEST'] = 'document'

        return self.app(environ, start_response)
