# /rt2ch Board Import Design

## Goal

Extend `/rt2ch` so it accepts both a specific 2ch thread URL and a board URL such as `https://2ch.hk/b/`. For a board URL, the bot imports visible board threads by discovering thread links and reusing the existing thread importer.

## Scope

- Keep `/rt2ch` and `/readtread2ch` admin-only.
- Preserve existing single-thread behavior.
- Add board URL parsing for `https://2ch.hk/<board>/` and equivalent trailing-slash forms.
- Import up to 50 discovered threads per board command invocation.
- Continue storing post text in `messages` with `source="import"`.
- Continue storing external 2ch image URLs in `external_photos`, without posting images to the chat.

## Approach

The service layer will distinguish thread URLs from board URLs. Thread URLs continue through `fetch_thread`. Board URLs fetch the board page, extract `/board/res/thread.html` links from HTML, deduplicate them while preserving page order, cap the list at 50, then import each thread through `fetch_thread`.

JSON endpoints such as `/b/catalog.json` are not relied on because they returned HTML during verification from this environment. They can be added later as an optimization, but the first implementation will use HTML discovery for reliability against the observed behavior.

## Data Flow

1. Handler receives `/rt2ch <url>`.
2. Service parses URL as either thread or board.
3. For a thread, service returns one imported thread result.
4. For a board, service fetches the board page, discovers thread URLs, imports each thread, and aggregates counts.
5. Handler inserts all imported texts and external image URLs into repositories.
6. Handler replies with counts for threads, posts, images, and partial failures if any.

## Error Handling

- Invalid URLs return the existing user-facing import failure message, updated to mention thread or board URLs.
- If board page fetching fails, the command fails without DB writes.
- If individual thread imports fail during a board import, the importer skips that thread and continues.
- If no thread links are discovered, the command reports that nothing was imported.

## Testing

- Unit tests for board URL parsing.
- Unit tests for HTML thread-link extraction and deduplication.
- Unit tests for board aggregation with successful and failed thread fetches.
- Handler tests for board import persistence and response counts.
- Existing thread import tests must continue to pass.

## Out Of Scope

- Telegram chat history import changes.
- Posting imported 2ch images directly to Telegram.
- Persisting imported thread IDs to avoid future re-imports.
- User-configurable import limits.
