# 2ch Thread Import Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `/rt2ch` so admins can import 2ch thread text and external image URLs into the current chat corpus.

**Architecture:** Add a small parser service, external photo persistence, and a command handler. Demotivator image selection becomes source-aware: Telegram `file_id` or external URL downloaded on demand.

**Tech Stack:** Python 3.11, aiogram 3, asyncpg, httpx, BeautifulSoup, uv, pytest.

---

## File Structure

- `services/twoch.py`: parse 2ch thread URLs and HTML/API payloads into post texts and image URLs.
- `services/media.py`: download external image URLs into `BytesIO`.
- `repositories/messages.py`: persist and select external photos.
- `migrations/003_external_photos.sql`: add `external_photos` table.
- `handlers/twoch.py`: admin-only `/rt2ch` and `/readtread2ch` command.
- `handlers/generation.py`: demotivator can use external image URLs.
- `handlers/common.py`, `bot.py`, `README.md`: register and document the command.
- `tests/test_twoch_service.py`, `tests/test_twoch_handler.py`, `tests/test_repositories_unit.py`, `tests/test_handler_helpers.py`: regression coverage.

---

### Task 1: Parser And Migration

- [ ] Write failing tests for `parse_thread_url`, HTML text extraction, and image URL extraction.
- [ ] Add `beautifulsoup4` and `httpx` dependencies through `uv`.
- [ ] Implement `services/twoch.py` with URL parsing, HTML fallback parser, and async fetch function.
- [ ] Add `migrations/003_external_photos.sql` with `external_photos(chat_id, source, external_url, post_url, created_at)` and chat index.
- [ ] Verify with `uv run pytest tests/test_twoch_service.py tests/test_migration_sql.py -q` and `uv run ruff check .`.

### Task 2: Repository And Handler

- [ ] Write failing repository tests for `insert_external_photos_bulk` and `get_random_external_photo`.
- [ ] Write failing handler tests for `/rt2ch` argument validation and import summary.
- [ ] Implement repository methods in `repositories/messages.py`.
- [ ] Implement admin-only `handlers/twoch.py` command using `fetch_thread`, `ChatRepository.upsert_chat`, `insert_messages_bulk`, and `insert_external_photos_bulk`.
- [ ] Register router in `bot.py` and document command in help/README.
- [ ] Verify with targeted tests, full `uv run pytest -q`, and `uv run ruff check .`.

### Task 3: Demotivator External Images

- [ ] Write failing tests proving demotivator can choose an external URL when Telegram photos are absent.
- [ ] Add `services/media.py` external image downloader.
- [ ] Extend repository selection to return source-aware random photo.
- [ ] Update `handlers/generation.py` to download external URL or Telegram file depending on source.
- [ ] Verify with targeted tests, full `uv run pytest -q`, `uv run ruff check .`, `docker compose config`.

## Self-Review

- Spec coverage: command restore, admin-only, text import, external image URL storage, demotivator URL support, tests, and uv workflow are covered.
- Placeholder scan: no deferred placeholders.
- Type consistency: parser returns `TwochThread`, repository stores strings, handler reports inserted counts.
