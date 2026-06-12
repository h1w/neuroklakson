from __future__ import annotations

from typing import Any


class ChatRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    async def upsert_chat(
        self,
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
                updated_at = NOW()
            """,
            chat_id,
            title,
            chat_type,
            default_mode,
        )

    async def get_default_mode(self, chat_id: int) -> str | None:
        return await self.connection.fetchval(
            """
            SELECT default_generation_mode
            FROM chats
            WHERE chat_id = $1
            """,
            chat_id,
        )

    async def set_default_mode(self, chat_id: int, mode: str) -> None:
        await self.connection.execute(
            """
            UPDATE chats
            SET default_generation_mode = $2,
                updated_at = NOW()
            WHERE chat_id = $1
            """,
            chat_id,
            mode,
        )
