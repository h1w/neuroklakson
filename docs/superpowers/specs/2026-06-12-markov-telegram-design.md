# Markov Telegram Bot Redesign

Date: 2026-06-12

## Goal

Bring the project into a maintainable state and redesign the Markov-chain generation system so the bot can serve many Telegram group chats independently. Each chat must have its own learning corpus, generation settings, photos, statistics, and imported training data. The generator should support increasingly absurd humor while still being based on the chat's own content.

## Current Context

The project is a small Python 3 Telegram bot built with `aiogram`. It currently stores messages and photos in SQLite tables keyed by `chat_id`, but most logic lives in `bot.py`. The Markov chain is rebuilt from all chat messages on each generation request, the database layer is a thin SQLite helper, and the project has almost no setup documentation beyond Python and pip versions.

The redesign should preserve the useful existing behavior: automatic message learning, random generated messages, demotivator generation, quotes, voiceover, and chat statistics.

## Scope

This phase includes:

- PostgreSQL database with Docker Compose.
- Service-oriented Python project structure.
- Per-chat corpora and settings.
- Improved Markov generator with `normal`, `absurd`, and `chaos` modes.
- Training from normal messages, forwarded messages, and uploaded history files.
- Admin-only commands for training imports and default mode changes.
- README, environment example, dependency manifest, migrations, tests, formatter, and linter.

This phase does not include MTProto/userbot access. A normal Telegram bot cannot read chat history from before it was added. Full old-history learning is supported through file import in this phase; direct Telegram history reading can be a future phase.

## Architecture

Keep the project simple, but split responsibilities into clear modules:

- `bot.py`: application entry point, bot startup, dispatcher setup, lifecycle hooks.
- `config.py`: environment-based configuration for Telegram token, database URL, generation defaults, and feature probabilities.
- `handlers/`: Telegram-facing command and message handlers.
- `services/`: application logic for learning, generation, history import, demotivators, stats, and admin checks.
- `repositories/`: PostgreSQL queries and persistence boundaries.
- `markov.py`: pure text generation logic with no Telegram or database dependencies.
- `migrations/`: database schema migrations.
- `tests/`: unit tests and repository/import tests.

The existing large `bot.py` should be reduced to orchestration. Handlers should call services, services should call repositories, and the Markov generator should receive plain text inputs and return plain text outputs.

## Database

Use PostgreSQL as the target database and run it through Docker Compose with the bot service.

Core tables:

- `chats`: `chat_id`, title, chat type, default generation mode, timestamps.
- `messages`: id, `chat_id`, Telegram message id when available, user id when available, original text, normalized text, source, forwarded metadata, timestamps.
- `photos`: id, `chat_id`, Telegram message id when available, file id, timestamps.
- `imports`: id, `chat_id`, admin user id, filename, status, accepted count, rejected count, error text, timestamps.

Indexes:

- `messages(chat_id)` for per-chat corpus reads.
- `messages(chat_id, telegram_message_id)` for deduplication of Telegram messages.
- `messages(chat_id, created_at)` for stats and future time-based sampling.
- `photos(chat_id)` for random demotivator photo selection.
- `imports(chat_id, created_at)` for import history.

All learning and generation queries must filter by `chat_id`. Content from one chat must never be used for another chat unless explicitly forwarded or imported into that target chat.

## Learning

The bot learns from three sources:

- `message`: ordinary group messages and captions seen after the bot is added.
- `forwarded`: forwarded messages or captions saved into the current chat's corpus.
- `import`: lines parsed from an uploaded history file.

The learning service should normalize and filter text before storage:

- Ignore bot commands.
- Strip links while preserving surrounding text.
- Reject empty strings and very short noise.
- Trim extreme word lengths.
- Collapse repeated whitespace.
- Avoid duplicate Telegram message ids per chat.
- Avoid obvious duplicate normalized texts where practical.

Forwarded content is intentionally saved under the current `chat_id`, because users are using it to teach the current chat's bot personality. The source should still be stored as `forwarded` for stats and future tuning.

History import is admin-only. The admin sends or replies to a `.txt`-like file and runs `/learn_history`. The importer reads the file, extracts candidate text lines, applies the same normalization rules, stores accepted lines in batches, and records an `imports` row with accepted/rejected counts.

## Commands

Generation commands:

- `/gm`: generate a message using the chat's default mode.
- `/gm normal|absurd|chaos`: generate a message with a one-off mode override.
- `/demgen`: generate a demotivator using the chat's default mode for text.
- `/demgen normal|absurd|chaos`: generate a demotivator with a one-off mode override.

Training and settings commands:

- `/learn_history`: admin-only command that imports a replied or attached text history file into the current chat's corpus.
- `/set_mode normal|absurd|chaos`: admin-only command that changes the chat's default generation mode.
- `/stats`: shows message count, photo count, counts by learning source, default mode, and latest import summary.
- `/help`: documents the updated commands.

New chats default to `absurd` mode.

## Generator

Replace the current single-path Markov implementation with a pure generator that supports controlled absurdity.

Modes:

- `normal`: uses a higher order chain, favors coherent transitions, and stays closer to chat style.
- `absurd`: default mode. Mixes seed fragments, occasionally resets context, and gives more weight to unusual transitions.
- `chaos`: uses a lower order chain, resets context more often, permits sharper topic jumps, and allows stranger endings.

Generator behavior:

- Build a model from messages for one chat only.
- Support chain order 2 for coherence and order 1 for chaos.
- Select varied seeds rather than always starting from a random chain key.
- Avoid empty results and endless repetition.
- Clean generated text after generation: collapse repeated words, trim oversized words, normalize spacing and punctuation, and enforce word limits.
- Return a clear "need more training data" response when the corpus is too small.

Absurd humor should come from controlled degradation of coherence, not from fully random word salad. The output should still feel like it came from the chat, but with more surprising collisions between topics and phrases.

## Error Handling

Replace broad silent `except ... pass` blocks with logging and user-facing fallback messages where appropriate. Repository errors should be logged with context and surfaced to handlers as controlled failures. Import errors should update the `imports` record with `failed` status and an error summary.

## Configuration And Deployment

Use environment variables instead of relying on `credentials.cfg` only. Provide `.env.example` with safe placeholder values.

Docker Compose should define:

- `bot`: Python bot service.
- `postgres`: PostgreSQL service with persistent volume.

The README should explain:

- Local setup.
- Docker Compose startup.
- Required environment variables.
- Database migration command.
- Test command.
- Main bot commands.

## Quality Bar

Add project hygiene as part of this phase:

- Dependency manifest with pinned or bounded dependencies.
- Migration tooling or a simple repeatable migration runner.
- Formatter and linter configuration.
- Tests for text normalization, Markov generation modes, history import parsing, and repository behavior.
- No unrelated feature rewrites beyond what is needed for the architecture and generator redesign.

## Acceptance Criteria

- The bot starts through Docker Compose with PostgreSQL.
- A new chat receives an `absurd` default mode.
- Ordinary messages are saved only to their own chat corpus.
- Forwarded text can be learned into the current chat by an admin command.
- A text history file can be imported by an admin command with accepted/rejected counts.
- `/gm` and `/demgen` use the default mode when no mode argument is provided.
- `/gm normal|absurd|chaos` and `/demgen normal|absurd|chaos` override the mode for one call.
- `/set_mode` changes the chat default mode.
- `/stats` reports per-chat counts and settings.
- Generation never mixes corpora between chats unless content was explicitly forwarded/imported into that chat.
- Tests cover the generator, normalization/import logic, and repository basics.
- README, `.env.example`, migrations, and dependency files exist.

## Future Work

- Optional MTProto/userbot integration for direct old-history reading, if the operational risk and account requirements are acceptable.
- Cached or materialized Markov models per chat if generation becomes slow on large corpora.
- Per-chat tuning of auto-reply probability and default text length.
- Admin command for pruning or resetting a chat corpus.
