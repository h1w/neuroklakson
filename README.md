# neuroklakson

neuroklakson is a Telegram bot for group chats. It learns text and photos per chat, then uses that chat's own corpus for Markov-chain text generation and generated demotivators. It also has manual demotivator, quote, voiceover, Telegram-history import, and 2ch import commands.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL
- Docker and Docker Compose, recommended for normal runs
- Telegram bot token from [BotFather](https://t.me/BotFather)

## Configuration

Create a local environment file and set the real token before running the bot:

```sh
cp .env.example .env
```

Required variables:

- `BOT_TOKEN` - Telegram bot token.
- `DATABASE_URL` - PostgreSQL connection string. In Docker Compose, the example value points at the `postgres` service.

Important optional variables:

- `DEFAULT_GENERATION_MODE` - initial per-chat mode for new chats; one of `normal`, `absurd`, `chaos`; default `absurd`.
- `BREDO_GENERATION_PROBABILITY` - legacy compatibility value, integer `0..100`; default `3`.
- `BREDO_MESSAGE_VOICEOVER_PROBABILITY` - legacy compatibility value, integer `0..100`; default `1`.
- `BREDO_DEMOTIVATOR_WATERMARK` - watermark text for generated demotivators; default `neuroklakson`.
- `BREDO_*_FONT` and `BREDO_QUOTE_HEADLINE_TEXT` - fonts/text used by manual demotivator and quote rendering.

`.env.example` contains a starter Docker Compose configuration. `config.py` contains the authoritative list of supported environment variables and defaults.

## Run With Docker Compose

For the first run on a fresh database, start PostgreSQL without starting the bot:

```sh
docker compose up -d postgres
```

Build the bot image used by the migration container:

```sh
docker compose build bot
```

Apply database migrations before the bot starts polling or handles messages:

```sh
docker compose run --rm bot uv run python migrations/apply.py
```

After migrations complete, start the bot:

```sh
docker compose up -d bot
```

For later runs after migrations have already been applied, rebuild and start the stack:

```sh
docker compose up --build
```

Migrations are not wired into the Compose startup command; run `uv run python migrations/apply.py` again whenever new files appear in `migrations/`.

## Local Development

Install dependencies, including development tools:

```sh
uv sync --extra dev
```

Use a reachable PostgreSQL database in `DATABASE_URL`, then apply migrations:

```sh
uv run python migrations/apply.py
```

Run the bot locally:

```sh
uv run python bot.py
```

Run tests:

```sh
uv run pytest
```

Run linting:

```sh
uv run ruff check .
```

## Learning Model

- The bot passively learns text, captions, and Telegram photo file IDs only in group and supergroup chats.
- Normal messages, forwarded messages, and imported history are stored separately; generation weights direct chat messages highest, forwarded messages next, imports lowest.
- Text starting with `/` is ignored by the learner, so bot commands do not train the corpus.
- Telegram Bot API bots cannot read messages sent before they joined a chat. To teach older history, export the chat as a text document and import it with `/learn_history`.
- 2ch imports store post text and external image URLs. Generated demotivators prefer stored Telegram photos and fall back to imported external images only when the chat has no Telegram photos.

## Bot Commands

The command list below mirrors the handlers registered in `handlers/`.

| Command | Admin only | Arguments | Behavior |
| --- | --- | --- | --- |
| `/start` | No | none | Greeting command. |
| `/help`, `/h` | No | none | Show the bot help text. |
| `/generatemessage`, `/genmsg`, `/gm` | No | optional `normal`, `absurd`, or `chaos` | Generate a Markov-chain message from the current chat corpus. Without an argument, uses the chat default mode. |
| `/demotivatorgeneration`, `/demgen`, `/d` | No | optional `normal`, `absurd`, or `chaos` | Generate demotivator text from the current chat corpus and render it over a stored Telegram photo or imported external image. |
| `/generatebugurt`, `/genbug`, `/b` | No | none | Generate a multi-line legacy “bugurt” text from the current chat corpus. |
| `/createdemotivator`, `/crdem`, `/cd` | No | optional `<top>|<bottom>` | Create a demotivator from a photo attached to the command or from a replied-to photo. |
| `/createquote`, `/cq`, `/q` | No | reply to a message | Create a quote image from the replied-to message and the author's Telegram profile photo. |
| `/learn_history` | Yes | attached document with exported text or reply to one | Import exported Telegram chat history into the current chat corpus. |
| `/readtread2ch`, `/rt2ch` | Yes | 2ch thread or board URL | Import post text and image URLs from one 2ch thread or from a board page. Board imports try up to 50 thread links. |
| `/set_mode` | Yes | `normal`, `absurd`, or `chaos` | Set the current chat's default generation mode. |
| `/stats`, `/s` | No | none | Show message, import, Telegram-photo, mode, and latest-import stats for the current chat. |
| `/voiceover`, `/v` | No | text argument or reply to a text message | Generate a voice message for the supplied text. |

### Generation Modes

- `normal` - closest to learned chat style.
- `absurd` - stranger output; also the default mode unless changed by `DEFAULT_GENERATION_MODE` or `/set_mode`.
- `chaos` - shortest and most distorted output.

More command usage notes are in [`docs/bot-commands.md`](docs/bot-commands.md).
