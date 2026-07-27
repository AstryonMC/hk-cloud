"""Unit tests for the ``import requests.py`` download script.

The script has no functions or classes and runs top-to-bottom at import time,
issuing a real HTTP request. To test it "as-is" without modifying it, these
tests read its source and ``exec`` it in an isolated namespace with
``requests.get`` mocked and the working directory pointed at a temp folder, so
no network access or real file writes to the repo occur.
"""

import os
from pathlib import Path
from unittest import mock

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "import requests.py"


class FakeResponse:
    """Minimal stand-in for a ``requests`` streaming response."""

    def __init__(self, chunks, headers=None, raise_exc=None):
        self._chunks = chunks
        self.headers = headers or {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def iter_content(self, chunk_size=8192):
        for chunk in self._chunks:
            yield chunk


def run_script(fake_response, workdir):
    """Exec the script with ``requests.get`` returning ``fake_response``.

    Returns the captured stdout produced by the script.
    """
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    get_mock = mock.Mock(return_value=fake_response)

    from io import StringIO

    stdout = StringIO()
    prev_cwd = os.getcwd()
    os.chdir(workdir)
    try:
        with mock.patch("requests.get", get_mock), mock.patch(
            "sys.stdout", stdout
        ):
            exec(compile(source, str(SCRIPT_PATH), "exec"), {"__name__": "__main__"})
    finally:
        os.chdir(prev_cwd)

    run_script.last_get_mock = get_mock
    return stdout.getvalue()


def test_filename_from_content_disposition(tmp_path):
    resp = FakeResponse(
        chunks=[b"hello ", b"world"],
        headers={"Content-Disposition": 'attachment; filename="report.pdf"'},
    )

    output = run_script(resp, tmp_path)

    written = tmp_path / "report.pdf"
    assert written.exists()
    assert written.read_bytes() == b"hello world"
    assert "report.pdf" in output


def test_filename_falls_back_to_url_path(tmp_path):
    resp = FakeResponse(chunks=[b"data"], headers={})

    run_script(resp, tmp_path)

    # The URL path basename is ``rhSfNJVk-...`` derived from the hardcoded URL.
    files = [p for p in tmp_path.iterdir() if p.is_file()]
    assert len(files) == 1
    assert files[0].read_bytes() == b"data"


def test_default_filename_when_no_disposition_and_empty_path(tmp_path):
    # A Content-Disposition without ``filename=`` should be ignored, and an
    # empty basename should fall back to the default name.
    resp = FakeResponse(
        chunks=[b"x"],
        headers={"Content-Disposition": "inline"},
    )

    with mock.patch(
        "urllib.parse.urlparse",
        return_value=mock.Mock(path="/"),
    ):
        run_script(resp, tmp_path)

    assert (tmp_path / "archivo_descargado").exists()


def test_request_is_made_with_headers_and_streaming(tmp_path):
    resp = FakeResponse(chunks=[b"a"], headers={})

    run_script(resp, tmp_path)

    get_mock = run_script.last_get_mock
    get_mock.assert_called_once()
    _, kwargs = get_mock.call_args
    assert kwargs["stream"] is True
    assert "User-Agent" in kwargs["headers"]


def test_raise_for_status_propagates(tmp_path):
    resp = FakeResponse(
        chunks=[b"a"],
        headers={},
        raise_exc=RuntimeError("HTTP 404"),
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        run_script(resp, tmp_path)

    # Nothing should have been written when the request fails.
    assert list(tmp_path.iterdir()) == []
