from types import SimpleNamespace

import pytest

from services.twoch import (
    extract_thread_urls_from_board_html,
    fetch_twoch_import,
    parse_board_url,
    parse_thread_html,
    parse_thread_json,
    parse_thread_url,
)


def test_parse_thread_url_extracts_board_and_thread_id():
    parsed = parse_thread_url("https://2ch.hk/b/res/123456.html")

    assert parsed.board == "b"
    assert parsed.thread_id == "123456"
    assert parsed.normalized_url == "https://2ch.hk/b/res/123456.html"


def test_parse_thread_url_rejects_non_thread_urls():
    with pytest.raises(ValueError, match="2ch thread"):
        parse_thread_url("https://2ch.hk/b/")


def test_parse_board_url_extracts_board_and_normalizes_url():
    parsed = parse_board_url("https://2ch.hk/b")

    assert parsed.board == "b"
    assert parsed.normalized_url == "https://2ch.hk/b/"


def test_extract_thread_urls_from_board_html_deduplicates_in_page_order():
    html = """
    <html><body>
      <a href="/b/res/111.html">thread</a>
      <a href="https://2ch.hk/b/res/222.html#333">reply</a>
      <a href="/b/res/111.html#444">duplicate</a>
      <a href="/po/res/999.html">other board</a>
    </body></html>
    """

    urls = extract_thread_urls_from_board_html(html, board="b", base_url="https://2ch.hk/b/")

    assert urls == [
        "https://2ch.hk/b/res/111.html",
        "https://2ch.hk/b/res/222.html",
    ]


def test_parse_thread_html_extracts_post_texts_and_image_urls():
    html = """
    <html><body>
      <article class="post__message">первый <a href="/b/res/1.html#2">>>2</a> пост</article>
      <article class="post__message">второй пост</article>
      <a class="post__image-link" href="//2ch.hk/b/src/123.jpg">image</a>
      <a href="/b/src/456.png">image</a>
    </body></html>
    """

    thread = parse_thread_html(html, base_url="https://2ch.hk/b/res/123456.html")

    assert thread.texts == ["первый пост", "второй пост"]
    assert thread.image_urls == ["https://2ch.hk/b/src/123.jpg", "https://2ch.hk/b/src/456.png"]


def test_parse_thread_json_extracts_post_texts_and_image_urls():
    payload = {
        "threads": [
            {
                "posts": [
                    {
                        "comment": "первый <a href=\"#2\">>>2</a> пост",
                        "files": [{"path": "/b/src/123.jpg"}],
                    },
                    {"comment": "второй пост", "files": [{"fullname": "456.png", "path": "//2ch.hk/b/src/456.png"}]},
                ]
            }
        ]
    }

    thread = parse_thread_json(payload, base_url="https://2ch.hk/b/res/123456.html")

    assert thread.texts == ["первый пост", "второй пост"]
    assert thread.image_urls == ["https://2ch.hk/b/src/123.jpg", "https://2ch.hk/b/src/456.png"]


async def test_fetch_twoch_import_imports_discovered_board_threads(monkeypatch):
    class FakeResponse:
        text = '<a href="/b/res/111.html">one</a><a href="/b/res/222.html">two</a>'

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            assert url == "https://2ch.hk/b/"
            return FakeResponse()

    async def fake_fetch_thread(url):
        if url == "https://2ch.hk/b/":
            raise ValueError("expected thread URL")
        if url.endswith("111.html"):
            return SimpleNamespace(texts=["one"], image_urls=["https://2ch.hk/b/src/1.jpg"])
        return SimpleNamespace(texts=["two"], image_urls=[])

    monkeypatch.setattr("services.twoch.httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr("services.twoch.fetch_thread", fake_fetch_thread)

    result = await fetch_twoch_import("https://2ch.hk/b/")

    assert result.texts == ["one", "two"]
    assert result.image_urls == ["https://2ch.hk/b/src/1.jpg"]
    assert result.thread_count == 2
    assert result.failed_thread_count == 0


async def test_fetch_twoch_import_continues_after_thread_failure(monkeypatch):
    class FakeResponse:
        text = '<a href="/b/res/111.html">one</a><a href="/b/res/222.html">two</a>'

        def raise_for_status(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return FakeResponse()

    async def fake_fetch_thread(url):
        if url == "https://2ch.hk/b/":
            raise ValueError("expected thread URL")
        if url.endswith("111.html"):
            raise RuntimeError("thread unavailable")
        return SimpleNamespace(texts=["two"], image_urls=[])

    monkeypatch.setattr("services.twoch.httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr("services.twoch.fetch_thread", fake_fetch_thread)

    result = await fetch_twoch_import("https://2ch.hk/b/")

    assert result.texts == ["two"]
    assert result.thread_count == 1
    assert result.failed_thread_count == 1
