from __future__ import annotations

from typing import Any

import config
from markchain import generate_markov_text


async def resolve_generation_mode(
    chat_repository: Any,
    *,
    chat_id: int,
    override: str | None,
) -> str:
    if override in config.GENERATION_MODES:
        return override

    default_mode = await chat_repository.get_default_mode(chat_id)
    if default_mode in config.GENERATION_MODES:
        return default_mode

    return "absurd"


class GenerationService:
    def __init__(self, message_repository: Any, chat_repository: Any) -> None:
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
