# Bot Commands

This document records the current command surface from `handlers/`. Keep it in sync with `handlers/common.py::HELP_TEXT` and the registered `Command(...)` decorators.

## Configuration Variables

Required environment variables:

- `BOT_TOKEN` - Telegram bot token.
- `DATABASE_URL` - PostgreSQL connection string.

Supported optional environment variables and code defaults:

| Variable | Default |
| --- | --- |
| `DEFAULT_GENERATION_MODE` | `absurd` |
| `BREDO_GENERATION_PROBABILITY` | `3` |
| `BREDO_MESSAGE_VOICEOVER_PROBABILITY` | `1` |
| `BREDO_DEMOTIVATOR_WATERMARK` | `neuroklakson` |
| `BREDO_DEMOTIVATOR_TEXT_FONT` | `fonts/OpenSans-Bold.ttf` |
| `BREDO_QUOTE_HEADLINE_TEXT` | `Цитаты ебланойдов` |
| `BREDO_QUOTE_HEADLINE_TEXT_FONT` | `fonts/OpenSans-Bold.ttf` |
| `BREDO_QUOTE_AUTHOR_NAME_TEXT_FONT` | `fonts/OpenSans-Regular.ttf` |
| `BREDO_QUOTE_QUOTE_TEXT_FONT` | `fonts/OpenSans-Italic.ttf` |
| `BREDO_DEMOTIVATOR_MIN_WORD_SIZE` | `3` |
| `BREDO_DEMOTIVATOR_MAX_WORD_SIZE` | `8` |
| `BREDO_DEMOTIVATOR_SECOND_LINE_MIN_WORD_SIZE` | `3` |
| `BREDO_DEMOTIVATOR_SECOND_LINE_MAX_WORD_SIZE` | `12` |
| `BREDO_MESSAGE_MIN_WORD_SIZE` | `5` |
| `BREDO_MESSAGE_MAX_WORD_SIZE` | `30` |
| `BREDO_BUGURT_MESSAGE_MIN_WORD_SIZE` | `8` |
| `BREDO_BUGURT_MESSAGE_MAX_WORD_SIZE` | `40` |
| `BREDO_BUGURT_MESSAGE_MIN_WORDS_PER_LINE` | `2` |
| `BREDO_BUGURT_MESSAGE_MAX_WORDS_PER_LINE` | `8` |
| `BREDO_BUGURT_MESSAGE_MIN_LINES` | `2` |
| `BREDO_BUGURT_MESSAGE_MAX_LINES` | `8` |

`DEFAULT_GENERATION_MODE` must be `normal`, `absurd`, or `chaos`. Probability values must be integers from `0` to `100`.

## Command Matrix

| Command | Aliases | Admin only | Arguments | Current behavior |
| --- | --- | --- | --- | --- |
| `/start` | none | No | none | Replies with a greeting. |
| `/help` | `/h` | No | none | Sends the built-in help text from `handlers/common.py`. |
| `/generatemessage` | `/genmsg`, `/gm` | No | optional `normal`, `absurd`, or `chaos` | Generates one Markov-chain message from the current chat corpus. If the mode argument is omitted, generation uses the chat default mode. |
| `/demotivatorgeneration` | `/demgen`, `/d` | No | optional `normal`, `absurd`, or `chaos` | Generates top and bottom demotivator text from the current chat corpus and renders it over a stored Telegram photo or imported external image. |
| `/generatebugurt` | `/genbug`, `/b` | No | none | Generates a legacy multi-line “bugurt” text from the current chat corpus. It does not read `/set_mode`; the low-level Markov default is `absurd`. |
| `/createdemotivator` | `/crdem`, `/cd` | No | optional `<top>|<bottom>` | Creates a demotivator from a photo attached to the command message or from the replied-to photo. Text before `|` becomes the top line; text after `|` becomes the bottom line. |
| `/createquote` | `/cq`, `/q` | No | reply to a message | Creates a quote image from the replied-to message text or caption and the author's Telegram profile photo. |
| `/learn_history` | none | Yes | attached document or reply to a document | Imports text from an exported chat-history document into the current chat corpus. |
| `/readtread2ch` | `/rt2ch` | Yes | 2ch thread or board URL | Imports post text and image URLs from a 2ch thread or board. |
| `/set_mode` | none | Yes | `normal`, `absurd`, or `chaos` | Stores the current chat's default generation mode. |
| `/stats` | `/s` | No | none | Shows chat ID, current mode, learned message counts by source, Telegram-photo count, and latest import status. |
| `/voiceover` | `/v` | No | text argument or reply to text/caption | Generates a voice message from the supplied text. |

## Admin-Only Commands

The bot checks Telegram chat administrator status before running these commands:

- `/learn_history`
- `/readtread2ch`, `/rt2ch`
- `/set_mode`

Non-admin users receive the bot's admin-only error response and the handler returns without changing data.

## Generation Modes

The only accepted generation modes are:

- `normal`
- `absurd`
- `chaos`

`DEFAULT_GENERATION_MODE` controls the default mode assigned when a chat is first stored. The code default is `absurd`. `/set_mode <mode>` changes the stored default for the current chat.

When `/generatemessage` or `/demotivatorgeneration` receives an invalid mode argument, the handler replies with the valid mode list and does not generate output.

## Learning and Imports

- Passive learning runs only in group and supergroup chats.
- The learner stores message text/captions and Telegram photo file IDs for the current chat.
- Text that starts with `/` is ignored by learning, so bot commands are not added to the corpus.
- Generation reads only the current chat's stored corpus.
- Direct messages are not covered by the passive learner.
- Telegram Bot API does not give the bot pre-join chat history; use `/learn_history` for exported history.

`/learn_history`:

1. Requires a chat admin.
2. Reads a document attached to the command or a document in the replied-to message.
3. Parses each line as exported history text when it matches Telegram export format; otherwise it treats the line as raw text.
4. Imports normalized non-empty lines and reports accepted/rejected counts.

`/readtread2ch` and `/rt2ch`:

1. Require a chat admin.
2. Accept a thread URL such as `https://2ch.hk/b/res/123.html`.
3. Accept a board URL such as `https://2ch.hk/b/`.
4. For board imports, the service scans the board page and attempts up to 50 thread links.
5. Stores imported post text as import-source messages and stores image URLs in `external_photos`.

Generated demotivators choose a Telegram photo from the current chat first. If the chat has no stored Telegram photos, they can fall back to a stored external image URL imported from 2ch.

## Runtime Commands

Install development dependencies:

```sh
uv sync --extra dev
```

Apply migrations against the configured PostgreSQL database:

```sh
uv run python migrations/apply.py
```

Run the bot locally:

```sh
uv run python bot.py
```

Run the test suite:

```sh
uv run pytest
```

Run linting:

```sh
uv run ruff check .
```

For Docker Compose, `docker-compose.yml` defines `postgres` and `bot` services. Migrations are manual: run them before the bot starts on a fresh database and again whenever new SQL files are added under `migrations/`.
