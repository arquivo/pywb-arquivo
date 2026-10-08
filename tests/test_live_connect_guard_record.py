import json
import os
import subprocess
import sys

from live_test_utils import PUBLIC_IP


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TESTS_DIR)


def record(tmp_path, **env):
    out = subprocess.run([sys.executable, os.path.join(TESTS_DIR, 'record_app.py'), str(tmp_path)],
                         cwd=str(tmp_path), env=dict(os.environ, PYTHONPATH=ROOT_DIR, **env),
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1]), out.stderr


def test_record_without_guard(tmp_path):
    # the rebinding domain reproduction: allowed by the filter, recorded from loopback
    results, stderr = record(tmp_path, PYWB_LIVE_CONNECT_GUARD='false')

    assert results['rebind_status'] == 200
    assert results['rebind_body_has_secret'] is True
    assert results['warc_has_secret'] is True
    assert results['server_paths'] == ['/secret']


def test_record_with_guard(tmp_path):
    results, stderr = record(tmp_path)

    # a public page is still recorded, through the recorder calls to the internal warcserver on localhost
    assert results['public_status'] == 200
    assert results['public_body'] == 'PUBLIC PAGE'
    assert results['warc_has_public_page'] is True

    # a rebinding domain is allowed by the filter, but the connection is blocked
    assert results['rebind_status'] != 200
    assert results['rebind_body_has_secret'] is False
    assert results['warc_has_secret'] is False
    assert ['127.0.0.1'] in results['rebind_lookups']
    assert results['server_paths'] == ['/page']
    assert results['connected_to'] == [PUBLIC_IP]

    assert 'live_url_filter blocked: connection to rebind.example.com' in stderr
