"""Offline regression for the explicitly invoked feed download."""

import bz2
import json

import httpx
import pytest

from rag.scripts import validate_reputation_live as live


@pytest.mark.parametrize("compressed", [False, True])
@pytest.mark.parametrize("redirect", [False, True])
def test_download_valid_feed(monkeypatch, tmp_path, compressed, redirect):
    payload = json.dumps(
        [{"verified": "yes", "online": "yes", "url": "https://example.com/a"}]
    ).encode()
    calls = []
    real_client = httpx.Client

    def handler(request):
        calls.append(request.url.host)
        if redirect and len(calls) == 1:
            return httpx.Response(
                302,
                headers={
                    "location": "https://cdn.phishtank.com/datadumps/verified_online.json?Signature=test"
                },
            )
        return httpx.Response(
            200, content=bz2.compress(payload) if compressed else payload
        )

    monkeypatch.setattr(live, "FEED", tmp_path / "feed.json")
    monkeypatch.setattr(
        live.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    assert live.download() == 0
    assert live.FEED.read_bytes() == payload
    assert calls == (
        ["data.phishtank.com", "cdn.phishtank.com"]
        if redirect
        else ["data.phishtank.com"]
    )


@pytest.mark.parametrize(
    "location",
    [
        "https://evil.example/datadumps/x.json",
        "http://cdn.phishtank.com/datadumps/x.json",
        "https://cdn.phishtank.com.evil.example/datadumps/x.json",
        "https://cdn.phishtank.com/other.json",
        "https://user@cdn.phishtank.com/datadumps/x.json",
    ],
)
def test_block_redirect(location):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(302, headers={"location": location})

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client,
        pytest.raises(ValueError),
        live.feed_response(client, "https://data.phishtank.com/data/online-valid.json"),
    ):
        pass
    assert calls == ["data.phishtank.com"]


def test_no_second_redirect(monkeypatch, tmp_path):
    calls = []
    real_client = httpx.Client

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(
            302,
            headers={
                "location": "https://cdn.phishtank.com/datadumps/verified_online.json"
            },
        )

    monkeypatch.setattr(live, "FEED", tmp_path / "feed.json")
    monkeypatch.setattr(
        live.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    assert live.download() == 1
    assert not live.FEED.exists()
    assert len(calls) == 2


@pytest.mark.parametrize(
    "status,payload", [(403, b""), (200, b"<html>error</html>"), (200, b"[]")]
)
def test_preserve_existing_feed(monkeypatch, tmp_path, status, payload):
    real_client = httpx.Client

    def handler(request):
        return httpx.Response(status, content=payload)

    monkeypatch.setattr(live, "FEED", tmp_path / "feed.json")
    live.FEED.write_bytes(b"previous snapshot")
    monkeypatch.setattr(
        live.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    if status == 200:
        with pytest.raises(ValueError):
            live.download()
    else:
        assert live.download() == 1
    assert live.FEED.read_bytes() == b"previous snapshot"
    assert list(tmp_path.iterdir()) == [live.FEED]
