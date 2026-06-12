from __future__ import annotations

from typing import Any, cast

import config
from markchain import GenerationMode, generate_markov_text


async def resolve_generation_mode(
    chat_repository: Any,
    *,
    chat_id: int,
    override: str | None,
) -> GenerationMode:
    if override in config.GENERATION_MODES:
        return cast(GenerationMode, override)
    if override:
        valid_modes = ", ".join(sorted(config.GENERATION_MODES))
        raise ValueError(f"mode must be one of: {valid_modes}")

    default_mode = await chat_repository.get_default_mode(chat_id)
    if default_mode in config.GENERATION_MODES:
        return cast(GenerationMode, default_mode)

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
