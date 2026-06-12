# 2ch Thread Import Restore

Date: 2026-06-12

## Goal

Restore `/rt2ch` so an admin can import a 2ch thread into the current Telegram chat's training corpus.

## Behavior

- Commands: `/rt2ch <thread_url>` and `/readtread2ch <thread_url>`.
- Admin-only in group chats.
- The command parses a 2ch thread URL, imports post text into `messages`, and imports image URLs into external media storage.
- Imported text belongs to the current Telegram `chat_id` and uses `source = 'import'`.
- Imported images must not spam the Telegram chat.
- Demotivator generation can use either Telegram `file_id` photos or external image URLs.

## Parser

- Prefer JSON/API-style parsing when possible.
- Keep an HTML fallback compatible with the old removed parser: find `article.post__message`, remove links, and use cleaned text.
- Extract external image URLs from the thread page/API when available.
- Network errors, invalid links, and empty imports produce user-facing error messages.

## Database

Add an external media table instead of overloading `photos.file_id`:

- `external_photos`: id, `chat_id`, source, external_url, post_url, created_at.
- Index by `chat_id`.
- Avoid strict URL deduplication for now; imports should be allowed to preserve all visible media references.

## Generation Integration

Demotivator selection should support:

- existing Telegram `photos.file_id` rows;
- new external image URL rows.

When an external URL is selected, the bot downloads it into memory and passes it into the demotivator generator.

## Quality

- Use `uv` only for project commands.
- Add tests for URL parsing, HTML parsing, import service behavior, repository calls, and command argument validation.
- Do not reintroduce broad silent `except: pass` behavior from the old implementation.
