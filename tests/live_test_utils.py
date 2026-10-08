"""Helpers shared by the live_connect_guard tests: a fake DNS and a local
http server, standing in for both internal services and public hosts."""
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


REAL_GETADDRINFO = socket.getaddrinfo

PUBLIC_IP = '93.184.215.14'
PUBLIC_IP_2 = '93.184.215.15'
PUBLIC_IPV6 = '2606:2800:21f:cb07:6820:80da:af6b:8b2c'


def addr_infos(ips, port, type=socket.SOCK_STREAM, proto=0):
    return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, type or socket.SOCK_STREAM, proto, '',
             (ip, port or 0, 0, 0) if ':' in ip else (ip, port or 0))
            for ip in ips]


class FakeDNS(object):
    """``socket.getaddrinfo`` replacement.

    ``hosts`` maps a host name to its addresses, or to a list of answers,
    one per lookup (the last one is repeated), like a DNS rebinding domain
    with TTL 0. Other hosts (eg. ``localhost``) use the real resolver.
    """
    def __init__(self, hosts):
        self.hosts = hosts
        self.lookups = []

    def __call__(self, host, port, family=0, type=0, proto=0, flags=0):
        if host not in self.hosts or flags & socket.AI_NUMERICHOST:
            return REAL_GETADDRINFO(host, port, family, type, proto, flags)

        answers = self.hosts[host]
        if answers and isinstance(answers[0], list):
            ips = answers[min(len(self.lookups_for(host)), len(answers) - 1)]
        else:
            ips = answers

        self.lookups.append((host, ips))
        return addr_infos(ips, port, type, proto)

    def lookups_for(self, host):
        return [ips for name, ips in self.lookups if name == host]


class RedirectConnections(object):
    """``create_connection`` replacement for the guard module: records the
    address the guard connects to and connects to the local server instead,
    so connections to "public" addresses can be tested without network."""
    def __init__(self, local_port, create_connection, refused=()):
        self.local_port = local_port
        self.create_connection = create_connection
        self.refused = refused
        self.calls = []

    def __call__(self, address, timeout=None, **kwargs):
        self.calls.append((address, timeout, kwargs))
        if address[0] in self.refused:
            raise ConnectionRefusedError('refused: %s' % address[0])
        return self.create_connection(('127.0.0.1', self.local_port), timeout, **kwargs)

    @property
    def addresses(self):
        return [address[0] for address, timeout, kwargs in self.calls]


class LocalServer(object):
    """http server on 127.0.0.1, ``files`` maps a path to its content,
    served with Range support, other paths return ``body``."""
    def __init__(self, body=b'INTERNAL SECRET', files=None):
        self.body = body
        self.files = files or {}
        self.requests = []

        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                server.requests.append((self.command, self.path, dict(self.headers)))
                content = server.files.get(self.path, server.body)
                status = 200
                range_header = self.headers.get('Range')
                if range_header:
                    start, end = range_header.split('=', 1)[1].split('-')
                    end = int(end) if end else len(content) - 1
                    content = content[int(start):end + 1]
                    status = 206

                self.send_response(status)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            do_HEAD = do_GET

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, args=(0.05,), daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.httpd.server_close()
