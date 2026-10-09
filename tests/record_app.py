"""Record with a pywb FrontEndApp configured like the save instance (gevent,
recorder calling the internal warcserver on localhost, live_url_filter),
run in a subprocess by test_live_connect_guard_record.py, as pywb's gevent
monkey patching must not leak into the other tests.

Prints a JSON object with the results. With ``PYWB_LIVE_CONNECT_GUARD=false``
only the rebinding domain is recorded, to check that the test reproduces it.
"""
from gevent import monkey; monkey.patch_all()  # noqa: E702, as pywb.apps.frontendapp

import glob
import gzip
import json
import os
import sys
import time

from unittest.mock import patch
from werkzeug.test import Client
from werkzeug.wrappers import Response

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_test_utils import FakeDNS, LocalServer, PUBLIC_IP, RedirectConnections  # noqa: E402


class RebindingDNS(FakeDNS):
    """rebinding domain answering the public address to the filter lookups
    (no port) and the loopback address to every lookup when connecting"""
    def __call__(self, host, port, family=0, type=0, proto=0, flags=0):
        if host == 'rebind.example.com':
            self.hosts[host] = [PUBLIC_IP] if port is None else ['127.0.0.1']
        return super(RebindingDNS, self).__call__(host, port, family, type, proto, flags)


def read_warcs(collections_root):
    data = b''
    for name in glob.glob(os.path.join(collections_root, '*', 'archive', '*.warc.gz')):
        with gzip.open(name) as fh:
            data += fh.read()
    return data


def main(work_dir):
    from pywb.apps.frontendapp import FrontEndApp
    from pywb_arquivo import live_connect_guard

    # recorded into a directory collection, like save/collections/save
    collections_root = os.path.join(work_dir, 'collections')
    for name in ('archive', 'indexes'):
        os.makedirs(os.path.join(collections_root, 'save', name))
    results = {}

    dns = RebindingDNS({'public.example.com': [PUBLIC_IP]})
    with LocalServer(files={'/page': b'PUBLIC PAGE'}) as server, patch('socket.getaddrinfo', dns):
        redirect = RedirectConnections(server.port, live_connect_guard.create_connection)
        with patch('pywb_arquivo.live_connect_guard.create_connection', redirect):
            app = FrontEndApp(custom_config={
                'collections_root': collections_root,
                'collections': {'live': '$live'},
                'recorder': {
                    'source_coll': 'live',
                    'source_filter': 'live',
                    'rollover_idle_secs': 1,
                    'filename_template': 'live-{timestamp}-{random}.warc.gz',
                },
                'live_url_filter': 'pywb_arquivo.live_url_filter:is_url_allowed',
            })
            client = Client(app, Response)

            # without the guard, the redirect to the local server isn't used
            if live_connect_guard.is_enabled():
                public = client.get('/save/record/id_/http://public.example.com:%d/page' % server.port)
                results['public_status'] = public.status_code
                results['public_body'] = public.get_data(as_text=True)

            rebind = client.get('/save/record/id_/http://rebind.example.com:%d/secret' % server.port)
            results['rebind_status'] = rebind.status_code
            results['rebind_body_has_secret'] = b'INTERNAL SECRET' in rebind.get_data()

            # wait for the recorder to write and close the WARC
            for _ in range(50):
                warcs = read_warcs(collections_root)
                if b'PUBLIC PAGE' in warcs or b'INTERNAL SECRET' in warcs:
                    break
                time.sleep(0.1)

            results['warc_has_public_page'] = b'PUBLIC PAGE' in warcs
            results['warc_has_secret'] = b'INTERNAL SECRET' in warcs
            results['server_paths'] = [path for method, path, headers in server.requests]
            results['connected_to'] = redirect.addresses
            results['rebind_lookups'] = dns.lookups_for('rebind.example.com')

    print(json.dumps(results))


if __name__ == '__main__':
    main(sys.argv[1])
