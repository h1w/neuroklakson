# Markov Telegram Bot Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the bot into a maintainable PostgreSQL-backed Telegram bot with per-chat learning corpora, improved absurd Markov generation, admin training imports, and project hygiene.

**Architecture:** Keep the app as a simple Python project, but split Telegram handlers, services, repositories, configuration, and pure Markov generation. PostgreSQL is accessed through `asyncpg`, migrations are plain SQL applied by a small runner, and `bot.py` becomes startup wiring only.

**Tech Stack:** Python 3.11+, aiogram 3, asyncpg, PostgreSQL 16, Docker Compose, pytest, pytest-asyncio, ruff.

---

## File Structure

- Create `pyproject.toml`: dependency manifest, pytest config, ruff config.
- Create `.env.example`: safe runtime configuration sample.
- Create `Dockerfile`: bot image.
- Create `docker-compose.yml`: bot and PostgreSQL services.
- Create `config.py`: environment parsing and typed settings.
- Create `migrations/001_initial_schema.sql`: PostgreSQL tables and indexes.
- Create `migrations/apply.py`: idempotent migration runner.
- Replace `dbconnector.py`: compatibility facade backed by repositories during migration.
- Create `repositories/database.py`: asyncpg pool lifecycle.
- Create `repositories/chats.py`: chat metadata and settings queries.
- Create `repositories/messages.py`: message/photo/import queries.
- Create `services/text.py`: normalization, link stripping, command filtering, generated text cleanup.
- Create `services/imports.py`: history text parsing and batch import logic.
- Create `services/admin.py`: Telegram chat admin check.
- Create `services/generation.py`: corpus loading and Markov mode selection.
- Create `handlers/common.py`: `/help`, `/stats`, `/set_mode`.
- Create `handlers/generation.py`: `/gm`, `/demgen`.
- Create `handlers/learning.py`: `/learn_forwarded`, `/learn_history`, passive message learning.
- Modify `markchain.py`: replace old generator with pure mode-aware generator while keeping `makeShortSentence` compatibility until handlers move.
- Modify `bot.py`: wire settings, database pool, routers, startup/shutdown.
- Modify `README.md`: setup, Docker, migrations, tests, commands.
- Create `tests/`: unit and async repository tests.

---

### Task 1: Project Tooling And Runtime Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config tests**

Create `tests/test_config.py`:

```python
import pytest

from config import Settings, load_settings


def test_load_settings_from_environment(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    monkeypatch.setenv("DEFAULT_GENERATION_MODE", "chaos")
    monkeypatch.setenv("BREDO_GENERATION_PROBABILITY", "17")

    settings = load_settings()

    assert settings.bot_token == "123:test"
    assert settings.database_url == "postgresql://bot:bot@postgres:5432/neuroklakson"
    assert settings.default_generation_mode == "chaos"
    assert settings.bredo_generation_probability == 17


def test_default_generation_mode_must_be_valid(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    monkeypatch.setenv("DEFAULT_GENERATION_MODE", "goblin")

    with pytest.raises(ValueError, match="DEFAULT_GENERATION_MODE"):
        load_settings()


def test_probability_must_be_between_zero_and_one_hundred():
    with pytest.raises(ValueError, match="BREDO_GENERATION_PROBABILITY"):
        Settings(
            bot_token="123:test",
            database_url="postgresql://bot:bot@postgres:5432/neuroklakson",
            default_generation_mode="absurd",
            bredo_generation_probability=101,
            bredo_message_voiceover_probability=0,
        )
```

- [ ] **Step 2: Run the tests and verify they fail because config does not exist**

Run: `pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 3: Add dependency and tool configuration**

Create `pyproject.toml`:

```toml
[project]
name = "neuroklakson"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "aiogram>=3.4,<4",
    "asyncpg>=0.29,<1",
    "pillow>=10,<11",
    "gtts>=2.5,<3",
]

[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "pytest-asyncio>=0.23,<1",
    "ruff>=0.5,<1",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
```

- [ ] **Step 4: Add environment configuration**

Create `.env.example`:

```dotenv
BOT_TOKEN=123456:replace_me
DATABASE_URL=postgresql://neuroklakson:neuroklakson@postgres:5432/neuroklakson
DEFAULT_GENERATION_MODE=absurd
BREDO_GENERATION_PROBABILITY=3
BREDO_MESSAGE_VOICEOVER_PROBABILITY=1
BREDO_DEMOTIVATOR_WATERMARK=neuroklakson
BREDO_DEMOTIVATOR_TEXT_FONT=fonts/OpenSans-Bold.ttf
BREDO_QUOTE_HEADLINE_TEXT=Great minds of Telegram
BREDO_QUOTE_HEADLINE_TEXT_FONT=fonts/OpenSans-Bold.ttf
BREDO_QUOTE_AUTHOR_NAME_TEXT_FONT=fonts/OpenSans-Regular.ttf
BREDO_QUOTE_QUOTE_TEXT_FONT=fonts/OpenSans-Italic.ttf
```

- [ ] **Step 5: Add Docker runtime files**

Create `Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --extra dev --frozen --no-cache

COPY . .

CMD ["uv", "run", "python", "bot.py"]
```

Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: neuroklakson
      POSTGRES_USER: neuroklakson
      POSTGRES_PASSWORD: neuroklakson
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neuroklakson -d neuroklakson"]
      interval: 5s
      timeout: 5s
      retries: 10

  bot:
    build: .
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres-data:
```

- [ ] **Step 6: Implement settings parsing**

Create `config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

GENERATION_MODES = {"normal", "absurd", "chaos"}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    default_generation_mode: str = "absurd"
    bredo_generation_probability: int = 3
    bredo_message_voiceover_probability: int = 1
    bredo_demotivator_watermark: str = "neuroklakson"
    bredo_demotivator_text_font: str = "fonts/OpenSans-Bold.ttf"
    bredo_quote_headline_text: str = "Great minds of Telegram"
    bredo_quote_headline_text_font: str = "fonts/OpenSans-Bold.ttf"
    bredo_quote_author_name_text_font: str = "fonts/OpenSans-Regular.ttf"
    bredo_quote_quote_text_font: str = "fonts/OpenSans-Italic.ttf"

    def __post_init__(self) -> None:
        if self.default_generation_mode not in GENERATION_MODES:
            raise ValueError(
                "DEFAULT_GENERATION_MODE must be one of: normal, absurd, chaos"
            )
        _validate_probability("BREDO_GENERATION_PROBABILITY", self.bredo_generation_probability)
        _validate_probability(
            "BREDO_MESSAGE_VOICEOVER_PROBABILITY",
            self.bredo_message_voiceover_probability,
        )


def _validate_probability(name: str, value: int) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_settings() -> Settings:
    return Settings(
        bot_token=_required_env("BOT_TOKEN"),
        database_url=_required_env("DATABASE_URL"),
        default_generation_mode=os.getenv("DEFAULT_GENERATION_MODE", "absurd"),
        bredo_generation_probability=_int_env("BREDO_GENERATION_PROBABILITY", 3),
        bredo_message_voiceover_probability=_int_env(
            "BREDO_MESSAGE_VOICEOVER_PROBABILITY", 1
        ),
        bredo_demotivator_watermark=os.getenv(
            "BREDO_DEMOTIVATOR_WATERMARK", "neuroklakson"
        ),
        bredo_demotivator_text_font=os.getenv(
            "BREDO_DEMOTIVATOR_TEXT_FONT", "fonts/OpenSans-Bold.ttf"
        ),
        bredo_quote_headline_text=os.getenv(
            "BREDO_QUOTE_HEADLINE_TEXT", "Great minds of Telegram"
        ),
        bredo_quote_headline_text_font=os.getenv(
            "BREDO_QUOTE_HEADLINE_TEXT_FONT", "fonts/OpenSans-Bold.ttf"
        ),
        bredo_quote_author_name_text_font=os.getenv(
            "BREDO_QUOTE_AUTHOR_NAME_TEXT_FONT", "fonts/OpenSans-Regular.ttf"
        ),
        bredo_quote_quote_text_font=os.getenv(
            "BREDO_QUOTE_QUOTE_TEXT_FONT", "fonts/OpenSans-Italic.ttf"
        ),
    )
```

- [ ] **Step 7: Run config tests and lint**

Run: `pytest tests/test_config.py -v`

Expected: PASS.

Run: `ruff check config.py tests/test_config.py`

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add pyproject.toml .env.example Dockerfile docker-compose.yml config.py tests/test_config.py
git commit -m "chore: add project runtime configuration"
```

Expected: commit succeeds.

---

### Task 2: PostgreSQL Migrations And Database Pool

**Files:**
- Create: `repositories/__init__.py`
- Create: `repositories/database.py`
- Create: `migrations/001_initial_schema.sql`
- Create: `migrations/apply.py`
- Test: `tests/test_migration_sql.py`

- [ ] **Step 1: Write migration structure tests**

Create `tests/test_migration_sql.py`:

```python
from pathlib import Path


def test_initial_migration_contains_required_tables_and_indexes():
    sql = Path("migrations/001_initial_schema.sql").read_text()

    assert "CREATE TABLE IF NOT EXISTS chats" in sql
    assert "CREATE TABLE IF NOT EXISTS messages" in sql
    assert "CREATE TABLE IF NOT EXISTS photos" in sql
    assert "CREATE TABLE IF NOT EXISTS imports" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_messages_chat_id" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_message_id" in sql
    assert "CHECK (default_generation_mode IN ('normal', 'absurd', 'chaos'))" in sql
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `pytest tests/test_migration_sql.py -v`

Expected: FAIL because `migrations/001_initial_schema.sql` does not exist.

- [ ] **Step 3: Add initial migration SQL**

Create `migrations/001_initial_schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    title TEXT,
    chat_type TEXT NOT NULL,
    default_generation_mode TEXT NOT NULL DEFAULT 'absurd',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (default_generation_mode IN ('normal', 'absurd', 'chaos'))
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    telegram_message_id BIGINT,
    user_id BIGINT,
    text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    source TEXT NOT NULL,
    forwarded_from TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (source IN ('message', 'forwarded', 'import'))
);

CREATE TABLE IF NOT EXISTS photos (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    telegram_message_id BIGINT,
    file_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS imports (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    admin_user_id BIGINT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status IN ('started', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_message_id
    ON messages(chat_id, telegram_message_id)
    WHERE telegram_message_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_chat_created_at ON messages(chat_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_normalized_text
    ON messages(chat_id, normalized_text);
CREATE INDEX IF NOT EXISTS idx_photos_chat_id ON photos(chat_id);
CREATE INDEX IF NOT EXISTS idx_imports_chat_created_at ON imports(chat_id, created_at);
```

- [ ] **Step 4: Add asyncpg pool wrapper**

Create `repositories/__init__.py`:

```python
"""Database repositories for neuroklakson."""
```

Create `repositories/database.py`:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(self.database_url)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        if self.pool is None:
            raise RuntimeError("Database pool is not connected")
        async with self.pool.acquire() as connection:
            yield connection
```

- [ ] **Step 5: Add migration runner**

Create `migrations/apply.py`:

```python
from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg

from config import load_settings


MIGRATIONS_DIR = Path(__file__).parent


async def apply_migrations(database_url: str) -> None:
    connection = await asyncpg.connect(database_url)
    try:
        for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = path.name
            already_applied = await connection.fetchval(
                "SELECT 1 FROM schema_migrations WHERE version = $1",
                version,
            )
            if already_applied:
                continue
            async with connection.transaction():
                await connection.execute(path.read_text())
                await connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES ($1)",
                    version,
                )
    finally:
        await connection.close()


async def main() -> None:
    settings = load_settings()
    await apply_migrations(settings.database_url)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: Run migration SQL tests and lint**

Run: `pytest tests/test_migration_sql.py -v`

Expected: PASS.

Run: `ruff check repositories migrations tests/test_migration_sql.py`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add repositories migrations tests/test_migration_sql.py
git commit -m "feat: add postgres migrations"
```

Expected: commit succeeds.

---

### Task 3: Text Normalization And Import Parsing

**Files:**
- Create: `services/__init__.py`
- Create: `services/text.py`
- Create: `services/imports.py`
- Test: `tests/test_text_services.py`
- Test: `tests/test_imports.py`

- [ ] **Step 1: Write failing text normalization tests**

Create `tests/test_text_services.py`:

```python
from services.text import clean_generated_text, normalize_training_text


def test_normalize_training_text_rejects_commands_and_empty_text():
    assert normalize_training_text("/gm chaos") is None
    assert normalize_training_text("   ") is None


def test_normalize_training_text_strips_links_and_collapses_spaces():
    assert normalize_training_text("смотри https://example.com  вот") == "смотри вот"


def test_normalize_training_text_rejects_too_short_noise():
    assert normalize_training_text("ок") is None


def test_normalize_training_text_trims_extreme_word_lengths():
    text = normalize_training_text("абсурд " + "а" * 80)
    assert text == "абсурд " + "а" * 32


def test_clean_generated_text_removes_repeated_words_and_spacing():
    assert clean_generated_text("кот кот кот ,  орет   .") == "кот, орет."
```

- [ ] **Step 2: Write failing import parsing tests**

Create `tests/test_imports.py`:

```python
from services.imports import parse_history_text


def test_parse_history_text_accepts_plain_lines_and_counts_rejections():
    result = parse_history_text("привет абсурдный мир\n/gm\nhttps://example.com\nмемный паровоз летит")

    assert result.accepted == ["привет абсурдный мир", "мемный паровоз летит"]
    assert result.rejected_count == 2


def test_parse_history_text_extracts_telegram_export_lines():
    raw = "[12.06.2026 10:00] Ivan: кабачок объявил войну чайнику\n[12.06.2026 10:01] Anna: да"

    result = parse_history_text(raw)

    assert result.accepted == ["кабачок объявил войну чайнику"]
    assert result.rejected_count == 1
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `pytest tests/test_text_services.py tests/test_imports.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services'`.

- [ ] **Step 4: Implement text services**

Create `services/__init__.py`:

```python
"""Application services for neuroklakson."""
```

Create `services/text.py`:

```python
from __future__ import annotations

import re

LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EXPORT_LINE_RE = re.compile(r"^\[[^\]]+\]\s+[^:]+:\s*(?P<text>.+)$")
WORD_RE = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)


def normalize_training_text(text: str | None, *, max_word_length: int = 32) -> str | None:
    if text is None:
        return None
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        return None

    stripped = LINK_RE.sub(" ", stripped)
    stripped = re.sub(r"[\x00-\x1f]+", " ", stripped)
    stripped = " ".join(stripped.split())
    if len(stripped) < 8:
        return None

    words = [word[:max_word_length] for word in stripped.split()]
    normalized = " ".join(words)
    if len(normalized) < 8:
        return None
    return normalized


def extract_export_text(line: str) -> str:
    match = EXPORT_LINE_RE.match(line.strip())
    if match:
        return match.group("text")
    return line


def clean_generated_text(text: str, *, max_word_length: int = 32) -> str:
    cleaned = " ".join(text.split())
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = WORD_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
    cleaned = re.sub(r"([,.!?;:])([^\s])", r"\1 \2", cleaned)
    cleaned = " ".join(word[:max_word_length] for word in cleaned.split())
    return cleaned.strip()
```

- [ ] **Step 5: Implement import parsing**

Create `services/imports.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from services.text import extract_export_text, normalize_training_text


@dataclass(frozen=True)
class ParsedHistory:
    accepted: list[str]
    rejected_count: int


def parse_history_text(raw_text: str) -> ParsedHistory:
    accepted: list[str] = []
    rejected_count = 0

    for raw_line in raw_text.splitlines():
        candidate = extract_export_text(raw_line)
        normalized = normalize_training_text(candidate)
        if normalized is None:
            rejected_count += 1
            continue
        accepted.append(normalized)

    return ParsedHistory(accepted=accepted, rejected_count=rejected_count)
```

- [ ] **Step 6: Run tests and lint**

Run: `pytest tests/test_text_services.py tests/test_imports.py -v`

Expected: PASS.

Run: `ruff check services tests/test_text_services.py tests/test_imports.py`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add services tests/test_text_services.py tests/test_imports.py
git commit -m "feat: add training text normalization"
```

Expected: commit succeeds.

---

### Task 4: Mode-Aware Markov Generator

**Files:**
- Modify: `markchain.py`
- Test: `tests/test_markchain.py`

- [ ] **Step 1: Write failing generator tests**

Create `tests/test_markchain.py`:

```python
import random

import pytest

from markchain import GenerationMode, generate_markov_text, makeShortSentence


CORPUS = [
    "кот украл у чайника паспорт",
    "чайник основал профсоюз голубей",
    "голуби требуют зарплату кабачками",
    "кабачок смотрит новости и кричит",
    "новости съели кота и заплакали",
]


def test_generate_markov_text_returns_none_for_small_corpus():
    assert generate_markov_text(["слишком мало"], mode="absurd", max_words=8) is None


@pytest.mark.parametrize("mode", ["normal", "absurd", "chaos"])
def test_generate_markov_text_supports_all_modes(mode):
    result = generate_markov_text(CORPUS, mode=mode, max_words=10, rng=random.Random(1))

    assert result is not None
    assert 1 <= len(result.split()) <= 10


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError, match="mode"):
        generate_markov_text(CORPUS, mode="boring", max_words=10)


@pytest.mark.asyncio
async def test_make_short_sentence_compatibility_wrapper():
    text = "\n".join(CORPUS)

    result = await makeShortSentence(text, max_words=7)

    assert result is not None
    assert len(result.split()) <= 7


def test_generation_mode_constants():
    assert set(GenerationMode.__args__) == {"normal", "absurd", "chaos"}
```

- [ ] **Step 2: Run tests and verify they fail against old generator**

Run: `pytest tests/test_markchain.py -v`

Expected: FAIL because `GenerationMode` and `generate_markov_text` do not exist.

- [ ] **Step 3: Replace generator implementation**

Replace `markchain.py` with:

```python
from __future__ import annotations

import random
from collections import defaultdict
from typing import Literal

from services.text import clean_generated_text, normalize_training_text

GenerationMode = Literal["normal", "absurd", "chaos"]
VALID_MODES = {"normal", "absurd", "chaos"}


def _tokenize_messages(messages: list[str]) -> list[list[str]]:
    tokenized: list[list[str]] = []
    for message in messages:
        normalized = normalize_training_text(message)
        if normalized is None:
            continue
        words = normalized.split()
        if len(words) >= 3:
            tokenized.append(words)
    return tokenized


def _build_chain(tokenized: list[list[str]], order: int) -> dict[tuple[str, ...], list[str]]:
    chain: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for words in tokenized:
        if len(words) <= order:
            continue
        for index in range(len(words) - order):
            key = tuple(words[index : index + order])
            chain[key].append(words[index + order])
    return dict(chain)


def _mode_settings(mode: GenerationMode) -> tuple[int, float]:
    if mode == "normal":
        return 2, 0.05
    if mode == "absurd":
        return 2, 0.22
    if mode == "chaos":
        return 1, 0.38
    raise ValueError("mode must be one of: normal, absurd, chaos")


def generate_markov_text(
    messages: list[str],
    *,
    mode: GenerationMode = "absurd",
    max_words: int = 30,
    rng: random.Random | None = None,
) -> str | None:
    if mode not in VALID_MODES:
        raise ValueError("mode must be one of: normal, absurd, chaos")

    rng = rng or random.Random()
    tokenized = _tokenize_messages(messages)
    if len(tokenized) < 3:
        return None

    order, reset_probability = _mode_settings(mode)
    chain = _build_chain(tokenized, order)
    if not chain:
        return None

    keys = list(chain.keys())
    current_key = rng.choice(keys)
    generated = list(current_key)

    while len(generated) < max_words:
        if rng.random() < reset_probability:
            current_key = rng.choice(keys)
            generated.extend(list(current_key))
            generated = generated[:max_words]
            continue

        options = chain.get(tuple(generated[-order:]))
        if not options:
            current_key = rng.choice(keys)
            generated.extend(list(current_key))
            generated = generated[:max_words]
            continue

        generated.append(rng.choice(options))

    result = clean_generated_text(" ".join(generated[:max_words]))
    return result or None


async def create_chain(text: str, chain_length: int = 2) -> dict[tuple[str, ...], list[str]]:
    messages = text.splitlines()
    return _build_chain(_tokenize_messages(messages), chain_length)


async def generate_text(
    chain: dict[tuple[str, ...], list[str]],
    chain_length: int = 2,
    max_words: int = 100,
) -> str | None:
    if not chain:
        return None
    rng = random.Random()
    key = rng.choice(list(chain.keys()))
    generated = list(key)
    while len(generated) < max_words:
        options = chain.get(tuple(generated[-chain_length:]))
        if not options:
            break
        generated.append(rng.choice(options))
    return clean_generated_text(" ".join(generated))


async def makeShortSentence(text: str, max_words: int = 100) -> str | None:
    return generate_markov_text(text.splitlines(), mode="absurd", max_words=max_words)


async def textCleaner(text: str) -> str:
    return normalize_training_text(text) or ""
```

- [ ] **Step 4: Run generator tests and lint**

Run: `pytest tests/test_markchain.py tests/test_text_services.py -v`

Expected: PASS.

Run: `ruff check markchain.py tests/test_markchain.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add markchain.py tests/test_markchain.py
git commit -m "feat: add absurd markov generation modes"
```

Expected: commit succeeds.

---

### Task 5: Chat And Message Repositories

**Files:**
- Create: `repositories/chats.py`
- Create: `repositories/messages.py`
- Test: `tests/test_repositories_unit.py`

- [ ] **Step 1: Write repository unit tests with fake connections**

Create `tests/test_repositories_unit.py`:

```python
import pytest

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.fetchval_result = None
        self.fetch_result = []
        self.fetchrow_result = None

    async def execute(self, query, *args):
        self.calls.append(("execute", query, args))
        return "OK"

    async def fetchval(self, query, *args):
        self.calls.append(("fetchval", query, args))
        return self.fetchval_result

    async def fetch(self, query, *args):
        self.calls.append(("fetch", query, args))
        return self.fetch_result

    async def fetchrow(self, query, *args):
        self.calls.append(("fetchrow", query, args))
        return self.fetchrow_result


@pytest.mark.asyncio
async def test_upsert_chat_uses_default_mode():
    connection = FakeConnection()
    repo = ChatRepository(connection)

    await repo.upsert_chat(chat_id=100, title="test", chat_type="supergroup", default_mode="absurd")

    method, query, args = connection.calls[0]
    assert method == "execute"
    assert "INSERT INTO chats" in query
    assert args == (100, "test", "supergroup", "absurd")


@pytest.mark.asyncio
async def test_insert_message_deduplicates_on_conflict():
    connection = FakeConnection()
    repo = MessageRepository(connection)

    await repo.insert_message(
        chat_id=100,
        telegram_message_id=10,
        user_id=55,
        text="сырный автобус",
        normalized_text="сырный автобус",
        source="message",
        forwarded_from=None,
    )

    method, query, args = connection.calls[0]
    assert method == "execute"
    assert "ON CONFLICT DO NOTHING" in query
    assert args == (100, 10, 55, "сырный автобус", "сырный автобус", "message", None)


@pytest.mark.asyncio
async def test_get_messages_returns_plain_strings():
    connection = FakeConnection()
    connection.fetch_result = [{"normalized_text": "кот"}, {"normalized_text": "чайник"}]
    repo = MessageRepository(connection)

    assert await repo.get_messages(chat_id=100) == ["кот", "чайник"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `pytest tests/test_repositories_unit.py -v`

Expected: FAIL because repository modules do not exist.

- [ ] **Step 3: Implement chat repository**

Create `repositories/chats.py`:

```python
from __future__ import annotations

import asyncpg


class ChatRepository:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self.connection = connection

    async def upsert_chat(
        self,
        *,
        chat_id: int,
        title: str | None,
        chat_type: str,
        default_mode: str,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO chats (chat_id, title, chat_type, default_generation_mode)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (chat_id) DO UPDATE SET
                title = EXCLUDED.title,
                chat_type = EXCLUDED.chat_type,
                updated_at = now()
            """,
            chat_id,
            title,
            chat_type,
            default_mode,
        )

    async def get_default_mode(self, chat_id: int) -> str | None:
        return await self.connection.fetchval(
            "SELECT default_generation_mode FROM chats WHERE chat_id = $1",
            chat_id,
        )

    async def set_default_mode(self, chat_id: int, mode: str) -> None:
        await self.connection.execute(
            """
            UPDATE chats
            SET default_generation_mode = $2, updated_at = now()
            WHERE chat_id = $1
            """,
            chat_id,
            mode,
        )
```

- [ ] **Step 4: Implement message repository**

Create `repositories/messages.py`:

```python
from __future__ import annotations

import asyncpg


class MessageRepository:
    def __init__(self, connection: asyncpg.Connection) -> None:
        self.connection = connection

    async def insert_message(
        self,
        *,
        chat_id: int,
        telegram_message_id: int | None,
        user_id: int | None,
        text: str,
        normalized_text: str,
        source: str,
        forwarded_from: str | None,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO messages (
                chat_id, telegram_message_id, user_id, text, normalized_text, source, forwarded_from
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT DO NOTHING
            """,
            chat_id,
            telegram_message_id,
            user_id,
            text,
            normalized_text,
            source,
            forwarded_from,
        )

    async def insert_messages_bulk(
        self,
        *,
        chat_id: int,
        messages: list[str],
        source: str,
    ) -> int:
        accepted = 0
        for message in messages:
            await self.insert_message(
                chat_id=chat_id,
                telegram_message_id=None,
                user_id=None,
                text=message,
                normalized_text=message,
                source=source,
                forwarded_from=None,
            )
            accepted += 1
        return accepted

    async def insert_photo(
        self,
        *,
        chat_id: int,
        telegram_message_id: int | None,
        file_id: str,
    ) -> None:
        await self.connection.execute(
            """
            INSERT INTO photos (chat_id, telegram_message_id, file_id)
            VALUES ($1, $2, $3)
            """,
            chat_id,
            telegram_message_id,
            file_id,
        )

    async def get_messages(self, *, chat_id: int) -> list[str]:
        rows = await self.connection.fetch(
            "SELECT normalized_text FROM messages WHERE chat_id = $1 ORDER BY created_at",
            chat_id,
        )
        return [row["normalized_text"] for row in rows]

    async def get_random_photo(self, *, chat_id: int) -> str | None:
        row = await self.connection.fetchrow(
            "SELECT file_id FROM photos WHERE chat_id = $1 ORDER BY random() LIMIT 1",
            chat_id,
        )
        if row is None:
            return None
        return row["file_id"]

    async def get_stats(self, *, chat_id: int) -> dict[str, int]:
        row = await self.connection.fetchrow(
            """
            SELECT
                count(*)::int AS total,
                count(*) FILTER (WHERE source = 'message')::int AS message,
                count(*) FILTER (WHERE source = 'forwarded')::int AS forwarded,
                count(*) FILTER (WHERE source = 'import')::int AS import
            FROM messages
            WHERE chat_id = $1
            """,
            chat_id,
        )
        photos = await self.connection.fetchval(
            "SELECT count(*)::int FROM photos WHERE chat_id = $1",
            chat_id,
        )
        return {
            "total": row["total"] if row else 0,
            "message": row["message"] if row else 0,
            "forwarded": row["forwarded"] if row else 0,
            "import": row["import"] if row else 0,
            "photos": photos or 0,
        }
```

- [ ] **Step 5: Run repository tests and lint**

Run: `pytest tests/test_repositories_unit.py -v`

Expected: PASS.

Run: `ruff check repositories tests/test_repositories_unit.py`

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add repositories tests/test_repositories_unit.py
git commit -m "feat: add postgres repositories"
```

Expected: commit succeeds.

---

### Task 6: Learning And Generation Services

**Files:**
- Create: `services/learning.py`
- Create: `services/generation.py`
- Test: `tests/test_learning_service.py`
- Test: `tests/test_generation_service.py`

- [ ] **Step 1: Write failing learning service tests**

Create `tests/test_learning_service.py`:

```python
import pytest

from services.learning import LearningService


class FakeMessages:
    def __init__(self):
        self.saved = []
        self.photos = []

    async def insert_message(self, **kwargs):
        self.saved.append(kwargs)

    async def insert_photo(self, **kwargs):
        self.photos.append(kwargs)


@pytest.mark.asyncio
async def test_learn_message_normalizes_and_saves():
    repo = FakeMessages()
    service = LearningService(repo)

    saved = await service.learn_text(
        chat_id=1,
        telegram_message_id=2,
        user_id=3,
        text="смешной https://example.com кабачок",
        source="message",
    )

    assert saved is True
    assert repo.saved[0]["normalized_text"] == "смешной кабачок"
    assert repo.saved[0]["source"] == "message"


@pytest.mark.asyncio
async def test_learn_message_rejects_commands():
    repo = FakeMessages()
    service = LearningService(repo)

    saved = await service.learn_text(
        chat_id=1,
        telegram_message_id=2,
        user_id=3,
        text="/gm chaos",
        source="message",
    )

    assert saved is False
    assert repo.saved == []
```

- [ ] **Step 2: Write failing generation service tests**

Create `tests/test_generation_service.py`:

```python
import pytest

from services.generation import GenerationService, resolve_generation_mode


class FakeMessages:
    async def get_messages(self, *, chat_id):
        return [
            "кот украл у чайника паспорт",
            "чайник основал профсоюз голубей",
            "голуби требуют зарплату кабачками",
            "кабачок смотрит новости и кричит",
        ]


class FakeChats:
    async def get_default_mode(self, chat_id):
        return "chaos"


@pytest.mark.asyncio
async def test_resolve_generation_mode_uses_override():
    assert await resolve_generation_mode(FakeChats(), chat_id=1, override="normal") == "normal"


@pytest.mark.asyncio
async def test_resolve_generation_mode_uses_chat_default():
    assert await resolve_generation_mode(FakeChats(), chat_id=1, override=None) == "chaos"


@pytest.mark.asyncio
async def test_generation_service_returns_text():
    service = GenerationService(FakeMessages(), FakeChats())

    text = await service.generate_message(chat_id=1, mode_override="absurd", max_words=8)

    assert text is not None
    assert len(text.split()) <= 8
```

- [ ] **Step 3: Run tests and verify they fail**

Run: `pytest tests/test_learning_service.py tests/test_generation_service.py -v`

Expected: FAIL because service modules do not exist.

- [ ] **Step 4: Implement learning service**

Create `services/learning.py`:

```python
from __future__ import annotations

from services.text import normalize_training_text


class LearningService:
    def __init__(self, message_repository) -> None:
        self.message_repository = message_repository

    async def learn_text(
        self,
        *,
        chat_id: int,
        telegram_message_id: int | None,
        user_id: int | None,
        text: str | None,
        source: str,
        forwarded_from: str | None = None,
    ) -> bool:
        normalized = normalize_training_text(text)
        if normalized is None:
            return False
        await self.message_repository.insert_message(
            chat_id=chat_id,
            telegram_message_id=telegram_message_id,
            user_id=user_id,
            text=text or "",
            normalized_text=normalized,
            source=source,
            forwarded_from=forwarded_from,
        )
        return True

    async def learn_photo(
        self,
        *,
        chat_id: int,
        telegram_message_id: int | None,
        file_id: str | None,
    ) -> bool:
        if not file_id:
            return False
        await self.message_repository.insert_photo(
            chat_id=chat_id,
            telegram_message_id=telegram_message_id,
            file_id=file_id,
        )
        return True
```

- [ ] **Step 5: Implement generation service**

Create `services/generation.py`:

```python
from __future__ import annotations

from config import GENERATION_MODES
from markchain import GenerationMode, generate_markov_text


async def resolve_generation_mode(chat_repository, *, chat_id: int, override: str | None) -> GenerationMode:
    if override:
        if override not in GENERATION_MODES:
            raise ValueError("mode must be one of: normal, absurd, chaos")
        return override  # type: ignore[return-value]
    default_mode = await chat_repository.get_default_mode(chat_id)
    if default_mode in GENERATION_MODES:
        return default_mode  # type: ignore[return-value]
    return "absurd"


class GenerationService:
    def __init__(self, message_repository, chat_repository) -> None:
        self.message_repository = message_repository
        self.chat_repository = chat_repository

    async def generate_message(
        self,
        *,
        chat_id: int,
        mode_override: str | None,
        max_words: int,
    ) -> str | None:
        mode = await resolve_generation_mode(
            self.chat_repository,
            chat_id=chat_id,
            override=mode_override,
        )
        messages = await self.message_repository.get_messages(chat_id=chat_id)
        return generate_markov_text(messages, mode=mode, max_words=max_words)
```

- [ ] **Step 6: Run service tests and lint**

Run: `pytest tests/test_learning_service.py tests/test_generation_service.py -v`

Expected: PASS.

Run: `ruff check services tests/test_learning_service.py tests/test_generation_service.py`

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add services tests/test_learning_service.py tests/test_generation_service.py
git commit -m "feat: add learning and generation services"
```

Expected: commit succeeds.

---

### Task 7: Compatibility Database Facade

**Files:**
- Replace: `dbconnector.py`
- Test: `tests/test_dbconnector_facade.py`

- [ ] **Step 1: Write failing facade tests**

Create `tests/test_dbconnector_facade.py`:

```python
import pytest

import dbconnector as dbc


class FakeDatabase:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return self

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.fetch_result = [{"normalized_text": "кот"}]
        self.fetchrow_result = {"file_id": "photo-1"}
        self.fetchval_result = 7
        self.calls = []

    async def execute(self, query, *args):
        self.calls.append(("execute", query, args))

    async def fetch(self, query, *args):
        self.calls.append(("fetch", query, args))
        return self.fetch_result

    async def fetchrow(self, query, *args):
        self.calls.append(("fetchrow", query, args))
        return self.fetchrow_result

    async def fetchval(self, query, *args):
        self.calls.append(("fetchval", query, args))
        return self.fetchval_result


@pytest.mark.asyncio
async def test_get_all_messages_uses_configured_database():
    dbc.set_database(FakeDatabase(FakeConnection()))

    assert await dbc.getAllMessages(1) == ["кот"]
```

- [ ] **Step 2: Run test and verify it fails against old SQLite facade**

Run: `pytest tests/test_dbconnector_facade.py -v`

Expected: FAIL because `set_database` does not exist.

- [ ] **Step 3: Replace dbconnector with asyncpg-backed compatibility functions**

Replace `dbconnector.py` with:

```python
from __future__ import annotations

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository

_database = None


def set_database(database) -> None:
    global _database
    _database = database


def _require_database():
    if _database is None:
        raise RuntimeError("Database is not configured")
    return _database


async def createTable():
    return None


async def insertMessage(chat_id, message):
    database = _require_database()
    async with database.acquire() as connection:
        await MessageRepository(connection).insert_message(
            chat_id=chat_id,
            telegram_message_id=None,
            user_id=None,
            text=message,
            normalized_text=message,
            source="message",
            forwarded_from=None,
        )


async def insertMessages(chat_id, messages_list):
    database = _require_database()
    async with database.acquire() as connection:
        await MessageRepository(connection).insert_messages_bulk(
            chat_id=chat_id,
            messages=messages_list,
            source="import",
        )


async def insertPhoto(chat_id, file_id):
    database = _require_database()
    async with database.acquire() as connection:
        await MessageRepository(connection).insert_photo(
            chat_id=chat_id,
            telegram_message_id=None,
            file_id=file_id,
        )


async def getRandomPhoto(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        return await MessageRepository(connection).get_random_photo(chat_id=chat_id)


async def getRandomMessage(chat_id):
    messages = await getAllMessages(chat_id)
    return messages[0] if messages else None


async def getAllMessages(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        return await MessageRepository(connection).get_messages(chat_id=chat_id)


async def getMessagesCount(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        stats = await MessageRepository(connection).get_stats(chat_id=chat_id)
        return stats["total"]


async def getPhotosCount(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        stats = await MessageRepository(connection).get_stats(chat_id=chat_id)
        return stats["photos"]


async def setChatMode(chat_id, mode):
    database = _require_database()
    async with database.acquire() as connection:
        await ChatRepository(connection).set_default_mode(chat_id, mode)
```

- [ ] **Step 4: Run facade tests and existing unit tests**

Run: `pytest tests/test_dbconnector_facade.py tests/test_repositories_unit.py -v`

Expected: PASS.

Run: `ruff check dbconnector.py tests/test_dbconnector_facade.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add dbconnector.py tests/test_dbconnector_facade.py
git commit -m "feat: switch db facade to postgres repositories"
```

Expected: commit succeeds.

---

### Task 8: Telegram Handlers And Bot Wiring

**Files:**
- Create: `handlers/__init__.py`
- Create: `handlers/common.py`
- Create: `handlers/generation.py`
- Create: `handlers/learning.py`
- Modify: `bot.py`
- Test: `tests/test_handler_helpers.py`

- [ ] **Step 1: Write helper tests for mode argument parsing**

Create `tests/test_handler_helpers.py`:

```python
import pytest

from handlers.generation import parse_mode_argument


def test_parse_mode_argument_returns_none_when_missing():
    assert parse_mode_argument("/gm") is None


def test_parse_mode_argument_accepts_valid_mode():
    assert parse_mode_argument("/demgen chaos") == "chaos"


def test_parse_mode_argument_rejects_invalid_mode():
    with pytest.raises(ValueError, match="normal, absurd, chaos"):
        parse_mode_argument("/gm potato")
```

- [ ] **Step 2: Run test and verify it fails**

Run: `pytest tests/test_handler_helpers.py -v`

Expected: FAIL because `handlers.generation` does not exist.

- [ ] **Step 3: Add handler package and generation helpers**

Create `handlers/__init__.py`:

```python
"""Telegram handlers for neuroklakson."""
```

Create `handlers/generation.py`:

```python
from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command

from config import GENERATION_MODES

router = Router()


def parse_mode_argument(text: str | None) -> str | None:
    if not text:
        return None
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return None
    mode = parts[1].strip().lower()
    if mode not in GENERATION_MODES:
        raise ValueError("mode must be one of: normal, absurd, chaos")
    return mode


@router.message(Command("generatemessage", "genmsg", "gm"))
async def generate_message_handler(message: types.Message) -> None:
    database = message.bot.get("database")
    async with database.acquire() as connection:
        from repositories.chats import ChatRepository
        from repositories.messages import MessageRepository
        from services.generation import GenerationService

        mode = parse_mode_argument(message.text)
        service = GenerationService(MessageRepository(connection), ChatRepository(connection))
        generated = await service.generate_message(
            chat_id=message.chat.id,
            mode_override=mode,
            max_words=30,
        )
    await message.answer(generated or "Я ещё очень тупой, нужно больше материала")
```

- [ ] **Step 4: Add common handlers**

Create `handlers/common.py`:

```python
from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command, CommandStart

from config import GENERATION_MODES
from repositories.chats import ChatRepository
from repositories.messages import MessageRepository

router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message) -> None:
    await message.answer(f"Пошел нахуй {message.from_user.full_name}!")


@router.message(Command("help", "h"))
async def help_handler(message: types.Message) -> None:
    await message.answer(
        "Команды бота:\n"
        "/gm [normal|absurd|chaos] - сгенерировать сообщение\n"
        "/demgen [normal|absurd|chaos] - сгенерировать демотиватор\n"
        "/learn_forwarded - выучить пересланное сообщение через reply\n"
        "/learn_history - импортировать историю из файла\n"
        "/set_mode normal|absurd|chaos - режим по умолчанию\n"
        "/stats - статистика чата\n"
        "/voiceover, /v - озвучка сообщения"
    )


@router.message(Command("set_mode"))
async def set_mode_handler(message: types.Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2 or parts[1] not in GENERATION_MODES:
        await message.answer("Режим должен быть normal, absurd или chaos")
        return
    database = message.bot.get("database")
    async with database.acquire() as connection:
        await ChatRepository(connection).set_default_mode(message.chat.id, parts[1])
    await message.answer(f"Режим по умолчанию: {parts[1]}")


@router.message(Command("stats", "s"))
async def stats_handler(message: types.Message) -> None:
    database = message.bot.get("database")
    async with database.acquire() as connection:
        chat_repo = ChatRepository(connection)
        message_repo = MessageRepository(connection)
        mode = await chat_repo.get_default_mode(message.chat.id) or "absurd"
        stats = await message_repo.get_stats(chat_id=message.chat.id)
    await message.answer(
        f"ID чата: {message.chat.id}\n"
        f"Режим: {mode}\n"
        f"Сообщений: {stats['total']}\n"
        f"Обычных: {stats['message']}\n"
        f"Пересланных: {stats['forwarded']}\n"
        f"Импортированных: {stats['import']}\n"
        f"Изображений: {stats['photos']}"
    )
```

- [ ] **Step 5: Add learning handlers**

Create `handlers/learning.py`:

```python
from __future__ import annotations

from aiogram import Router, types
from aiogram.filters import Command

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository
from services.imports import parse_history_text
from services.learning import LearningService

router = Router()


def _message_text(message: types.Message) -> str | None:
    return message.text or message.caption


@router.message(Command("learn_forwarded"))
async def learn_forwarded_handler(message: types.Message) -> None:
    if message.reply_to_message is None:
        await message.answer("Ответь командой на пересланное сообщение")
        return
    database = message.bot.get("database")
    async with database.acquire() as connection:
        service = LearningService(MessageRepository(connection))
        saved = await service.learn_text(
            chat_id=message.chat.id,
            telegram_message_id=message.reply_to_message.message_id,
            user_id=message.reply_to_message.from_user.id if message.reply_to_message.from_user else None,
            text=_message_text(message.reply_to_message),
            source="forwarded",
            forwarded_from=str(message.reply_to_message.forward_origin),
        )
    await message.answer("Впитал" if saved else "Там нечего впитывать")


@router.message(Command("learn_history"))
async def learn_history_handler(message: types.Message) -> None:
    document = message.document or (message.reply_to_message.document if message.reply_to_message else None)
    if document is None:
        await message.answer("Пришли файл с историей или ответь командой на файл")
        return
    bot = message.bot
    file = await bot.get_file(document.file_id)
    buffer = await bot.download_file(file.file_path)
    raw_text = buffer.read().decode("utf-8", errors="ignore")
    parsed = parse_history_text(raw_text)
    database = bot.get("database")
    async with database.acquire() as connection:
        await MessageRepository(connection).insert_messages_bulk(
            chat_id=message.chat.id,
            messages=parsed.accepted,
            source="import",
        )
    await message.answer(
        f"Импорт завершен: принято {len(parsed.accepted)}, отброшено {parsed.rejected_count}"
    )


@router.message()
async def passive_learning_handler(message: types.Message) -> None:
    if message.chat.type not in {"group", "supergroup"}:
        return
    database = message.bot.get("database")
    async with database.acquire() as connection:
        await ChatRepository(connection).upsert_chat(
            chat_id=message.chat.id,
            title=message.chat.title,
            chat_type=message.chat.type,
            default_mode="absurd",
        )
        service = LearningService(MessageRepository(connection))
        await service.learn_text(
            chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            user_id=message.from_user.id if message.from_user else None,
            text=_message_text(message),
            source="message",
        )
        if message.photo:
            await service.learn_photo(
                chat_id=message.chat.id,
                telegram_message_id=message.message_id,
                file_id=message.photo[-1].file_id,
            )
```

- [ ] **Step 6: Wire bot startup**

Replace `bot.py` with:

```python
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from config import load_settings
from handlers import common, generation, learning
from repositories.database import Database

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def main() -> None:
    settings = load_settings()
    bot = Bot(settings.bot_token)
    database = Database(settings.database_url)
    await database.connect()
    bot["database"] = database
    bot["settings"] = settings

    dispatcher = Dispatcher()
    dispatcher.include_router(common.router)
    dispatcher.include_router(generation.router)
    dispatcher.include_router(learning.router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Run handler tests and lint**

Run: `pytest tests/test_handler_helpers.py -v`

Expected: PASS.

Run: `ruff check bot.py handlers tests/test_handler_helpers.py`

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add bot.py handlers tests/test_handler_helpers.py
git commit -m "feat: add telegram handler structure"
```

Expected: commit succeeds.

---

### Task 9: Admin Checks And Import Tracking

**Files:**
- Create: `services/admin.py`
- Modify: `repositories/messages.py`
- Modify: `handlers/common.py`
- Modify: `handlers/learning.py`
- Test: `tests/test_admin_service.py`

- [ ] **Step 1: Write failing admin service tests**

Create `tests/test_admin_service.py`:

```python
import pytest

from services.admin import is_chat_admin


class FakeBot:
    def __init__(self, status):
        self.status = status

    async def get_chat_member(self, chat_id, user_id):
        return type("Member", (), {"status": self.status})()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["creator", "administrator"])
async def test_is_chat_admin_accepts_admin_statuses(status):
    assert await is_chat_admin(FakeBot(status), chat_id=1, user_id=2) is True


@pytest.mark.asyncio
async def test_is_chat_admin_rejects_members():
    assert await is_chat_admin(FakeBot("member"), chat_id=1, user_id=2) is False
```

- [ ] **Step 2: Run test and verify it fails**

Run: `pytest tests/test_admin_service.py -v`

Expected: FAIL because `services.admin` does not exist.

- [ ] **Step 3: Implement admin service**

Create `services/admin.py`:

```python
from __future__ import annotations

ADMIN_STATUSES = {"creator", "administrator"}


async def is_chat_admin(bot, *, chat_id: int, user_id: int | None) -> bool:
    if user_id is None:
        return False
    member = await bot.get_chat_member(chat_id, user_id)
    return str(member.status) in ADMIN_STATUSES
```

- [ ] **Step 4: Add import tracking repository methods**

Append these methods inside `MessageRepository` in `repositories/messages.py`:

```python
    async def create_import(
        self,
        *,
        chat_id: int,
        admin_user_id: int,
        filename: str,
    ) -> int:
        return await self.connection.fetchval(
            """
            INSERT INTO imports (chat_id, admin_user_id, filename, status)
            VALUES ($1, $2, $3, 'started')
            RETURNING id
            """,
            chat_id,
            admin_user_id,
            filename,
        )

    async def finish_import(
        self,
        *,
        import_id: int,
        accepted_count: int,
        rejected_count: int,
    ) -> None:
        await self.connection.execute(
            """
            UPDATE imports
            SET status = 'completed', accepted_count = $2, rejected_count = $3, updated_at = now()
            WHERE id = $1
            """,
            import_id,
            accepted_count,
            rejected_count,
        )

    async def fail_import(self, *, import_id: int, error_text: str) -> None:
        await self.connection.execute(
            """
            UPDATE imports
            SET status = 'failed', error_text = $2, updated_at = now()
            WHERE id = $1
            """,
            import_id,
            error_text[:500],
        )
```

- [ ] **Step 5: Protect admin-only handlers**

In `handlers/common.py`, import `is_chat_admin`:

```python
from services.admin import is_chat_admin
```

At the top of `set_mode_handler`, after parsing parts and before database writes, add:

```python
    if not await is_chat_admin(message.bot, chat_id=message.chat.id, user_id=message.from_user.id if message.from_user else None):
        await message.answer("Эта команда только для админов чата")
        return
```

In `handlers/learning.py`, import `is_chat_admin`:

```python
from services.admin import is_chat_admin
```

At the top of `learn_forwarded_handler` and `learn_history_handler`, add the same admin check:

```python
    if not await is_chat_admin(message.bot, chat_id=message.chat.id, user_id=message.from_user.id if message.from_user else None):
        await message.answer("Эта команда только для админов чата")
        return
```

- [ ] **Step 6: Track import completion and failure**

In `handlers/learning.py`, replace the database block in `learn_history_handler` with:

```python
    async with database.acquire() as connection:
        repo = MessageRepository(connection)
        import_id = await repo.create_import(
            chat_id=message.chat.id,
            admin_user_id=message.from_user.id if message.from_user else 0,
            filename=document.file_name or "history.txt",
        )
        try:
            await repo.insert_messages_bulk(
                chat_id=message.chat.id,
                messages=parsed.accepted,
                source="import",
            )
            await repo.finish_import(
                import_id=import_id,
                accepted_count=len(parsed.accepted),
                rejected_count=parsed.rejected_count,
            )
        except Exception as exc:
            await repo.fail_import(import_id=import_id, error_text=str(exc))
            raise
```

- [ ] **Step 7: Run admin tests and lint**

Run: `pytest tests/test_admin_service.py tests/test_repositories_unit.py -v`

Expected: PASS.

Run: `ruff check services/admin.py handlers repositories/messages.py tests/test_admin_service.py`

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
git add services/admin.py handlers repositories/messages.py tests/test_admin_service.py
git commit -m "feat: restrict training commands to admins"
```

Expected: commit succeeds.

---

### Task 10: Demotivator Mode Override

**Files:**
- Modify: `handlers/generation.py`
- Test: `tests/test_handler_helpers.py`

- [ ] **Step 1: Extend helper tests for demotivator command aliases**

Append to `tests/test_handler_helpers.py`:

```python
def test_parse_mode_argument_accepts_demgen_without_mode():
    assert parse_mode_argument("/demgen") is None
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_handler_helpers.py -v`

Expected: PASS because the parser already supports this.

- [ ] **Step 3: Add demotivator handler using the same mode rules**

Append to `handlers/generation.py`:

```python
from io import BytesIO

from demotivate import generateDemotivator


@router.message(Command("demotivatorgeneration", "demgen", "d"))
async def demotivator_handler(message: types.Message) -> None:
    database = message.bot.get("database")
    settings = message.bot.get("settings")
    async with database.acquire() as connection:
        from repositories.chats import ChatRepository
        from repositories.messages import MessageRepository
        from services.generation import GenerationService

        mode = parse_mode_argument(message.text)
        message_repo = MessageRepository(connection)
        service = GenerationService(message_repo, ChatRepository(connection))
        first_line = await service.generate_message(
            chat_id=message.chat.id,
            mode_override=mode,
            max_words=8,
        )
        second_line = await service.generate_message(
            chat_id=message.chat.id,
            mode_override=mode,
            max_words=12,
        )
        photo_file_id = await message_repo.get_random_photo(chat_id=message.chat.id)

    if not first_line or not photo_file_id:
        await message.answer("Я ещё очень тупой, нужно больше текста и хотя бы одна картинка")
        return

    photo_bytes = BytesIO()
    await message.bot.download(photo_file_id, photo_bytes)
    demotivator_image = await generateDemotivator(
        photo_bytes,
        first_line,
        second_line or "",
        settings.bredo_demotivator_watermark,
        settings.bredo_demotivator_text_font,
    )
    output = BytesIO()
    demotivator_image.save(output, format="PNG")
    output.seek(0)
    await message.answer_photo(types.BufferedInputFile(output.getvalue(), "demotivator.png"))
```

- [ ] **Step 4: Run handler tests and lint**

Run: `pytest tests/test_handler_helpers.py -v`

Expected: PASS.

Run: `ruff check handlers/generation.py tests/test_handler_helpers.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add handlers/generation.py tests/test_handler_helpers.py
git commit -m "feat: use generation modes for demotivators"
```

Expected: commit succeeds.

---

### Task 11: Documentation And Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with setup and command documentation**

Replace `README.md` with:

```markdown
# neuroklakson

Telegram bot that learns each group chat separately and generates absurd Markov-chain messages, demotivators, quotes, and voiceovers.

## Requirements

- Python 3.11+
- Docker and Docker Compose for the recommended setup
- Telegram bot token

## Setup

```bash
cp .env.example .env
```

Edit `.env` and set `BOT_TOKEN`.

## Run With Docker Compose

```bash
docker compose up --build
```

In another shell, apply migrations when needed:

```bash
docker compose run --rm bot python migrations/apply.py
```

## Local Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

## Commands

- `/gm` - generate a message using the chat default mode.
- `/gm normal|absurd|chaos` - generate with a one-off mode override.
- `/demgen` - generate a demotivator using the chat default mode.
- `/demgen normal|absurd|chaos` - generate a demotivator with a one-off mode override.
- `/learn_forwarded` - admin-only; reply to a forwarded message to teach the current chat.
- `/learn_history` - admin-only; import a text history file into the current chat.
- `/set_mode normal|absurd|chaos` - admin-only; set default mode for the chat.
- `/stats` - show per-chat corpus and media stats.
- `/help` - show command help.

## Generation Modes

- `normal`: more coherent and close to chat style.
- `absurd`: default mode for new chats; stranger transitions with readable fragments.
- `chaos`: maximum context resets and topic jumps.

## Notes

A normal Telegram bot cannot read messages from before it joined a chat. To train on old history, export the history to a text file and import it with `/learn_history`.
```

- [ ] **Step 2: Run all tests**

Run: `pytest -v`

Expected: PASS.

- [ ] **Step 3: Run lint**

Run: `ruff check .`

Expected: PASS.

- [ ] **Step 4: Check Docker Compose config**

Run: `docker compose config`

Expected: PASS and printed resolved compose config.

- [ ] **Step 5: Inspect git status**

Run: `git status --short`

Expected: only `README.md` modified.

- [ ] **Step 6: Commit documentation and final verification**

Run:

```bash
git add README.md
git commit -m "docs: update setup and bot commands"
```

Expected: commit succeeds.

---

## Final Verification Checklist

- [ ] `pytest -v` passes.
- [ ] `ruff check .` passes.
- [ ] `docker compose config` passes.
- [ ] `git status --short` is clean.
- [ ] The spec acceptance criteria in `docs/superpowers/specs/2026-06-12-markov-telegram-design.md` are covered by tasks 1-11.

## Plan Self-Review

- Spec coverage: PostgreSQL, Docker Compose, per-chat data, `normal`/`absurd`/`chaos`, forwarded learning, file import, admin-only settings/training, stats, README, `.env.example`, tests, lint, and migrations are mapped to tasks 1-11.
- Placeholder scan: no task uses deferred implementation language; each code-changing step names files and includes concrete code or exact insertion text.
- Type consistency: generation modes are consistently `normal`, `absurd`, and `chaos`; repository methods used by services and handlers are defined before use; compatibility names in `dbconnector.py` retain existing camelCase functions while new modules use snake_case.
