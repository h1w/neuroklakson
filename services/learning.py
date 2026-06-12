from __future__ import annotations

from typing import Any

from services.text import normalize_training_text


class LearningService:
    def __init__(self, message_repository: Any) -> None:
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
        normalized_text = normalize_training_text(text)
        if normalized_text is None:
            return False

        await self.message_repository.insert_message(
            chat_id=chat_id,
            telegram_message_id=telegram_message_id,
            user_id=user_id,
            text=text or "",
            normalized_text=normalized_text,
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
