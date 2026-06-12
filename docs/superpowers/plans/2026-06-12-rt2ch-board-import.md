# /rt2ch Board Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `/rt2ch` import either one 2ch thread or up to 50 threads discovered from a 2ch board URL.

**Architecture:** Keep 2ch parsing/import orchestration in `services/twoch.py`. Add a board URL type, board HTML link extraction, and an aggregate import result. Update `handlers/twoch.py` to call the unified importer and persist aggregate texts/images through existing repositories.

**Tech Stack:** Python 3.12, aiogram, httpx, BeautifulSoup, pytest via `uv run pytest`, ruff via `uv run ruff`.

---

## Files

- Modify: `services/twoch.py` for board URL parsing, thread-link extraction, and aggregate import.
- Modify: `handlers/twoch.py` to call the unified importer and report aggregate counts.
- Modify: `tests/test_twoch_service.py` for board parser and aggregator tests.
- Modify: `tests/test_twoch_handler.py` for board handler persistence and response tests.
- No database migration required.

## Task 1: Board URL Parsing And Link Extraction

**Files:**
- Modify: `tests/test_twoch_service.py`
- Modify: `services/twoch.py`

- [ ] **Step 1: Add failing service tests**

Add these imports in `tests/test_twoch_service.py`:

```python
from services.twoch import extract_thread_urls_from_board_html, parse_board_url
```

Add these tests:

```python
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
```

- [ ] **Step 2: Run failing tests**

Run: `uv run pytest tests/test_twoch_service.py::test_parse_board_url_extracts_board_and_normalizes_url tests/test_twoch_service.py::test_extract_thread_urls_from_board_html_deduplicates_in_page_order -q`

Expected: FAIL because `parse_board_url` and `extract_thread_urls_from_board_html` are not defined.

- [ ] **Step 3: Implement board parser and extractor**

In `services/twoch.py`, add:

```python
BOARD_RE = re.compile(r"^/(?P<board>[^/]+)/?$")


@dataclass(frozen=True)
class TwochBoardUrl:
    board: str
    normalized_url: str
```

Add functions:

```python
def parse_board_url(url: str) -> TwochBoardUrl:
    parsed = urlparse(url.strip())
    match = BOARD_RE.match(parsed.path)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or match is None:
        raise ValueError("expected 2ch board URL like https://2ch.hk/b/")

    board = match.group("board")
    return TwochBoardUrl(board=board, normalized_url=f"https://{parsed.netloc}/{board}/")


def extract_thread_urls_from_board_html(html: str, *, board: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    thread_pattern = re.compile(rf"^/{re.escape(board)}/res/(\d+)(?:\.html)?")

    for tag in soup.find_all("a", href=True):
        absolute_url = urljoin(base_url, str(tag["href"]))
        parsed = urlparse(absolute_url)
        match = thread_pattern.match(parsed.path)
        if match is None:
            continue
        normalized_url = f"https://{parsed.netloc}/{board}/res/{match.group(1)}.html"
        if normalized_url not in seen:
            seen.add(normalized_url)
            urls.append(normalized_url)

    return urls
```

- [ ] **Step 4: Run service tests**

Run: `uv run pytest tests/test_twoch_service.py -q`

Expected: PASS.

## Task 2: Unified 2ch Import Aggregation

**Files:**
- Modify: `tests/test_twoch_service.py`
- Modify: `services/twoch.py`

- [ ] **Step 1: Add failing aggregation test**

Add import:

```python
from services.twoch import fetch_twoch_import
```

Add test:

```python
async def test_fetch_twoch_import_imports_discovered_board_threads(monkeypatch):
    class FakeResponse:
        status_code = 200
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
```

Also add `from types import SimpleNamespace` at the top of the file.

- [ ] **Step 2: Run failing aggregation test**

Run: `uv run pytest tests/test_twoch_service.py::test_fetch_twoch_import_imports_discovered_board_threads -q`

Expected: FAIL because `fetch_twoch_import` is not defined.

- [ ] **Step 3: Implement aggregate import result and unified fetch**

In `services/twoch.py`, add:

```python
BOARD_THREAD_LIMIT = 50


@dataclass(frozen=True)
class TwochImport:
    texts: list[str]
    image_urls: list[str]
    thread_count: int
    failed_thread_count: int = 0
```

Add functions:

```python
async def fetch_board(url: str, *, limit: int = BOARD_THREAD_LIMIT) -> TwochImport:
    parsed = parse_board_url(url)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(parsed.normalized_url)
    response.raise_for_status()

    thread_urls = extract_thread_urls_from_board_html(
        response.text,
        board=parsed.board,
        base_url=parsed.normalized_url,
    )[:limit]
    texts: list[str] = []
    image_urls: list[str] = []
    imported_threads = 0
    failed_threads = 0

    for thread_url in thread_urls:
        try:
            thread = await fetch_thread(thread_url)
        except Exception:
            failed_threads += 1
            continue
        imported_threads += 1
        texts.extend(thread.texts)
        image_urls.extend(thread.image_urls)

    return TwochImport(
        texts=texts,
        image_urls=list(dict.fromkeys(image_urls)),
        thread_count=imported_threads,
        failed_thread_count=failed_threads,
    )


async def fetch_twoch_import(url: str) -> TwochImport:
    try:
        thread = await fetch_thread(url)
    except ValueError:
        return await fetch_board(url)
    return TwochImport(texts=thread.texts, image_urls=thread.image_urls, thread_count=1)
```

- [ ] **Step 4: Add partial-failure aggregation test**

Add test:

```python
async def test_fetch_twoch_import_continues_after_thread_failure(monkeypatch):
    class FakeResponse:
        status_code = 200
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
        if url.endswith("111.html"):
            raise RuntimeError("thread unavailable")
        return SimpleNamespace(texts=["two"], image_urls=[])

    monkeypatch.setattr("services.twoch.httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr("services.twoch.fetch_thread", fake_fetch_thread)

    result = await fetch_twoch_import("https://2ch.hk/b/")

    assert result.texts == ["two"]
    assert result.thread_count == 1
    assert result.failed_thread_count == 1
```

- [ ] **Step 5: Run service tests**

Run: `uv run pytest tests/test_twoch_service.py -q`

Expected: PASS.

## Task 3: Handler Uses Unified Import Result

**Files:**
- Modify: `tests/test_twoch_handler.py`
- Modify: `handlers/twoch.py`

- [ ] **Step 1: Update existing handler test to patch unified importer**

In `tests/test_twoch_handler.py`, rename `fake_fetch_thread` to `fake_fetch_twoch_import`, return `thread_count=1` and `failed_thread_count=0`, and patch `handlers.twoch.fetch_twoch_import` instead of `handlers.twoch.fetch_thread`:

```python
async def fake_fetch_twoch_import(url):
    calls["fetch_url"] = url
    return SimpleNamespace(
        texts=["пост один", "пост два"],
        image_urls=["https://2ch.hk/b/src/1.jpg"],
        thread_count=1,
        failed_thread_count=0,
    )
```

- [ ] **Step 2: Add board handler test**

Add test:

```python
async def test_rt2ch_handler_reports_board_import_with_partial_failures(monkeypatch):
    calls = {}
    connection = object()

    async def fake_is_chat_admin(bot, *, chat_id, user_id):
        return True

    async def fake_fetch_twoch_import(url):
        calls["fetch_url"] = url
        return SimpleNamespace(
            texts=["пост один", "пост два", "пост три"],
            image_urls=["https://2ch.hk/b/src/1.jpg", "https://2ch.hk/b/src/2.jpg"],
            thread_count=31,
            failed_thread_count=6,
        )

    class FakeChatRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

        async def upsert_chat(self, **kwargs):
            calls["chat"] = kwargs

    class FakeMessageRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

        async def insert_messages_bulk(self, **kwargs):
            calls["messages"] = kwargs
            return len(kwargs["messages"])
        async def insert_external_photos_bulk(self, **kwargs):
            calls["photos"] = kwargs
            return len(kwargs["urls"])

    monkeypatch.setattr("handlers.twoch.is_chat_admin", fake_is_chat_admin)
    monkeypatch.setattr("handlers.twoch.fetch_twoch_import", fake_fetch_twoch_import)
    monkeypatch.setattr("handlers.twoch.ChatRepository", FakeChatRepository)
    monkeypatch.setattr("handlers.twoch.MessageRepository", FakeMessageRepository)

    message = SimpleNamespace(
        text="/rt2ch https://2ch.hk/b/",
        caption=None,
        bot=object(),
        from_user=SimpleNamespace(id=55),
        chat=SimpleNamespace(id=100, title="chat", full_name=None, type="supergroup"),
        answers=[],
    )

    async def answer(text):
        message.answers.append(text)

    message.answer = answer

    await twoch_handler.rt2ch_handler(
        message,
        FakeDatabase(connection),
        SimpleNamespace(default_generation_mode="absurd"),
    )

    assert calls["fetch_url"] == "https://2ch.hk/b/"
    assert calls["messages"]["messages"] == ["пост один", "пост два", "пост три"]
    assert calls["photos"]["urls"] == ["https://2ch.hk/b/src/1.jpg", "https://2ch.hk/b/src/2.jpg"]
    assert message.answers == ["Импортировано из 2ch: 31 тредов, 3 постов, 2 картинок. Ошибок: 6."]
```

- [ ] **Step 3: Run failing handler tests**

Run: `uv run pytest tests/test_twoch_handler.py -q`

Expected: FAIL because handler still imports and calls `fetch_thread`.

- [ ] **Step 4: Update handler implementation**

In `handlers/twoch.py`, change import:

```python
from services.twoch import fetch_twoch_import
```

Change missing URL response:

```python
await message.answer("Напиши ссылку на тред или доску: /rt2ch https://2ch.hk/b/res/123.html")
```

Change fetch block:

```python
try:
    imported = await fetch_twoch_import(url)
except Exception:
    await message.answer("Не смог прочитать ссылку 2ch")
    return
```

Change repository calls to use `imported.texts` and `imported.image_urls`.

Change final answer:

```python
answer = f"Импортировано из 2ch: {imported.thread_count} тредов, {message_count} постов, {photo_count} картинок."
if imported.failed_thread_count:
    answer += f" Ошибок: {imported.failed_thread_count}."
await message.answer(answer)
```

- [ ] **Step 5: Run handler tests**

Run: `uv run pytest tests/test_twoch_handler.py -q`

Expected: PASS.

## Task 4: Final Verification

**Files:**
- Modify only files already listed above.

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run linter**

Run: `uv run ruff check .`

Expected: no lint errors.

- [ ] **Step 3: Validate compose config**

Run: `docker compose config --quiet`

Expected: exits successfully. Do not print config because `.env` may contain secrets.

- [ ] **Step 4: Inspect changed files**

Run: `git diff -- services/twoch.py handlers/twoch.py tests/test_twoch_service.py tests/test_twoch_handler.py docs/superpowers/specs/2026-06-12-rt2ch-board-import-design.md docs/superpowers/plans/2026-06-12-rt2ch-board-import.md`

Expected: diff only contains board import implementation, tests, and docs.

## Notes

- Do not commit unless the user explicitly asks for a commit.
- Use `uv run ...` for Python test/lint commands.
- Preserve existing `/rt2ch <thread_url>` behavior except for the response including `1 тредов`.
