# neuroklakson

neuroklakson is a Telegram bot that learns each chat separately and generates absurd Markov-chain messages, demotivators, quotes, and voiceovers from that chat's own text.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker and Docker Compose, recommended for normal runs
- Telegram bot token from [BotFather](https://t.me/BotFather)

## Setup

Create a local environment file and set your Telegram bot token:

```sh
cp .env.example .env
```

Edit `.env` and replace `BOT_TOKEN` with your real token.

## Run With Docker Compose

Build and start the Compose services:

```sh
docker compose up --build
```

On a fresh database, apply migrations before using the bot. The bot should not start polling or handle messages until the schema exists.

If the bot is already running, stop it after Postgres has started, then apply migrations from the Compose environment:

```sh
docker compose run --rm bot uv run python migrations/apply.py
```

If you are already inside the bot container, run the same migration script directly:

```sh
uv run python migrations/apply.py
```

After migrations complete, start or restart the bot with Docker Compose:

```sh
docker compose up --build
```

## Local Development

Install dependencies, including development tools:

```sh
uv sync --extra dev
```

Run tests:

```sh
uv run pytest
```

Run linting:

```sh
uv run ruff check .
```

## Bot Commands

- `/gm [mode]` - generate a Markov message. The optional mode is `normal`, `absurd`, or `chaos`.
- `/demgen [mode]` - generate a demotivator. The optional mode is `normal`, `absurd`, or `chaos`.
- `/learn_forwarded` - admin-only; reply to a message to learn it into the current chat. Forwarded messages are supported, but any replied message can be learned.
- `/learn_history` - admin-only; import and learn from exported chat history in an attached or replied-to text document.
- `/set_mode <mode>` - admin-only; set the chat's default generation mode.
- `/stats` - show learning and generation statistics for the chat.
- `/help` - show bot help.
- `/createdemotivator` - legacy demotivator command.
- `/createquote` - legacy quote command.
- `/generatebugurt` - legacy generated-message command.
- `/voiceover` - legacy voiceover command.

## Generation Modes

- `normal` - closest to the learned chat style.
- `absurd` - stronger mutations for stranger output.
- `chaos` - maximum distortion for the most unhinged results.

## Telegram History Limitation

Telegram Bot API bots cannot read messages from before they joined a chat. To teach neuroklakson older history, export the chat history and use file import through `/learn_history`.
