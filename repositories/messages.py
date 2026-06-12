from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class MessageRepository:
    def __init__(self, connection: Any) -> None:
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
                chat_id,
                telegram_message_id,
                user_id,
                text,
                normalized_text,
                source,
                forwarded_from
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
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
        messages: Sequence[str],
        source: str,
    ) -> int:
        accepted_count = 0
        for message in messages:
            result = await self.connection.execute(
                """
                INSERT INTO messages (
                    chat_id,
                    telegram_message_id,
                    user_id,
                    text,
                    normalized_text,
                    source,
                    forwarded_from
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
                """,
                chat_id,
                None,
                None,
                message,
                message,
                source,
                None,
            )
            if result == "INSERT 0 1":
                accepted_count += 1
        return accepted_count

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
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            chat_id,
            admin_user_id,
            filename,
            "started",
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
            SET status = 'completed',
                accepted_count = $2,
                rejected_count = $3,
                updated_at = NOW()
            WHERE id = $1
            """,
            import_id,
            accepted_count,
            rejected_count,
        )

    async def fail_import(
        self,
        *,
        import_id: int,
        error_text: str,
    ) -> None:
        await self.connection.execute(
            """
            UPDATE imports
            SET status = 'failed',
                error_text = $2,
                updated_at = NOW()
            WHERE id = $1
            """,
            import_id,
            error_text[:500],
        )

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
            """
            SELECT normalized_text
            FROM messages
            WHERE chat_id = $1
            ORDER BY created_at
            """,
            chat_id,
        )
        return [row["normalized_text"] for row in rows]

    async def get_random_message(self, *, chat_id: int) -> str | None:
        row = await self.connection.fetchrow(
            """
            SELECT normalized_text
            FROM messages
            WHERE chat_id = $1
            ORDER BY RANDOM()
            LIMIT 1
            """,
            chat_id,
        )
        if row is None:
            return None
        return row["normalized_text"]

    async def get_random_photo(self, *, chat_id: int) -> str | None:
        row = await self.connection.fetchrow(
            """
            SELECT file_id
            FROM photos
            WHERE chat_id = $1
            ORDER BY RANDOM()
            LIMIT 1
            """,
            chat_id,
        )
        if row is None:
            return None
        return row["file_id"]

    async def get_stats(self, *, chat_id: int) -> dict[str, int]:
        row = await self.connection.fetchrow(
            """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE source = 'message')::int AS message,
                COUNT(*) FILTER (WHERE source = 'forwarded')::int AS forwarded,
                COUNT(*) FILTER (WHERE source = 'import')::int AS import
            FROM messages
            WHERE chat_id = $1
            """,
            chat_id,
        )
        photos = await self.connection.fetchval(
            """
            SELECT COUNT(*)::int
            FROM photos
            WHERE chat_id = $1
            """,
            chat_id,
        )
        return {
            "total": row["total"] if row else 0,
            "message": row["message"] if row else 0,
            "forwarded": row["forwarded"] if row else 0,
            "import": row["import"] if row else 0,
            "photos": photos or 0,
        }

    async def get_latest_import(self, *, chat_id: int) -> dict[str, Any] | None:
        row = await self.connection.fetchrow(
            """
            SELECT
                status,
                accepted_count,
                rejected_count,
                error_text,
                filename,
                created_at
            FROM imports
            WHERE chat_id = $1
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            chat_id,
        )
        if row is None:
            return None
        return dict(row)
