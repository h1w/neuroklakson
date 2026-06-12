import pytest

from services.twoch import parse_thread_html, parse_thread_json, parse_thread_url


def test_parse_thread_url_extracts_board_and_thread_id():
    parsed = parse_thread_url("https://2ch.hk/b/res/123456.html")

    assert parsed.board == "b"
    assert parsed.thread_id == "123456"
    assert parsed.normalized_url == "https://2ch.hk/b/res/123456.html"


def test_parse_thread_url_rejects_non_thread_urls():
    with pytest.raises(ValueError, match="2ch thread"):
        parse_thread_url("https://2ch.hk/b/")


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
