from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

MIGRATIONS_DIR = Path(__file__).resolve().parent


def migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))


async def apply_migrations(database_url: str) -> None:
    connection = await asyncpg.connect(database_url)
    try:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        for migration_file in migration_files():
            version = migration_file.stem
            already_applied = await connection.fetchval(
                "SELECT 1 FROM schema_migrations WHERE version = $1",
                version,
            )
            if already_applied:
                continue

            async with connection.transaction():
                await connection.execute(migration_file.read_text())
                await connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    version,
                )
    finally:
        await connection.close()


async def main() -> None:
    from config import load_settings

    settings = load_settings()
    await apply_migrations(settings.database_url)


if __name__ == "__main__":
    asyncio.run(main())
