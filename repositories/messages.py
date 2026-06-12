from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class MessageRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    async def insert_message(
        self,
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
            if result != "INSERT 0 0":
                accepted_count += 1
        return accepted_count

    async def insert_photo(
        self,
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

    async def get_messages(self, chat_id: int) -> list[str]:
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

    async def get_random_photo(self, chat_id: int) -> str | None:
        return await self.connection.fetchval(
            """
            SELECT file_id
            FROM photos
            WHERE chat_id = $1
            ORDER BY RANDOM()
            LIMIT 1
            """,
            chat_id,
        )

    async def get_stats(self, chat_id: int) -> dict[str, int]:
        row = await self.connection.fetchrow(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE source = 'message') AS message,
                COUNT(*) FILTER (WHERE source = 'forwarded') AS forwarded,
                COUNT(*) FILTER (WHERE source = 'import') AS import,
                (
                    SELECT COUNT(*)
                    FROM photos
                    WHERE photos.chat_id = $1
                ) AS photos
            FROM messages
            WHERE chat_id = $1
            """,
            chat_id,
        )
        return {
            "total": row["total"],
            "message": row["message"],
            "forwarded": row["forwarded"],
            "import": row["import"],
            "photos": row["photos"],
        }
