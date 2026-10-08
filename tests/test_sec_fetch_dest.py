import pytest

from pywb_arquivo.sec_fetch_dest import SecFetchDestMiddleware


def call(environ):
    seen = {}

    def app(environ, start_response):
        seen.update(environ)
        start_response('200 OK', [])
        return [b'ok']

    result = SecFetchDestMiddleware(app)(environ, lambda status, headers: None)
    assert result == [b'ok']
    return seen


@pytest.mark.parametrize('dest', ['iframe', 'frame', 'IFrame'])
def test_frame_sent_as_document(dest):
    assert call({'HTTP_SEC_FETCH_DEST': dest})['HTTP_SEC_FETCH_DEST'] == 'document'


@pytest.mark.parametrize('dest', ['document', 'image', 'script', 'empty'])
def test_other_destinations_unchanged(dest):
    assert call({'HTTP_SEC_FETCH_DEST': dest})['HTTP_SEC_FETCH_DEST'] == dest


def test_missing_header_not_added():
    assert 'HTTP_SEC_FETCH_DEST' not in call({'PATH_INFO': '/'})


def test_other_headers_unchanged():
    environ = call({'HTTP_SEC_FETCH_DEST': 'iframe', 'HTTP_SEC_FETCH_MODE': 'navigate',
                    'HTTP_SEC_FETCH_SITE': 'same-origin'})
    assert environ['HTTP_SEC_FETCH_MODE'] == 'navigate'
    assert environ['HTTP_SEC_FETCH_SITE'] == 'same-origin'
