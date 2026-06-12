from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import GENERATION_MODES
from repositories.chats import ChatRepository
from repositories.database import Database
from repositories.messages import MessageRepository
from services.generation import GenerationService

router = Router()

NEED_MORE_MATERIAL_MESSAGE = "Я ещё очень тупой, нужно немного подождать"


def parse_mode_argument(text: str | None) -> str | None:
    parts = (text or "").split(maxsplit=1)
    if len(parts) == 1:
        return None

    mode = parts[1].strip().lower()
    if mode in GENERATION_MODES:
        return mode

    valid_modes = ", ".join(sorted(GENERATION_MODES))
    raise ValueError(f"mode must be one of: {valid_modes}")


@router.message(Command("generatemessage", "genmsg", "gm"))
async def generate_message_handler(message: Message, database: Database) -> None:
    try:
        mode = parse_mode_argument(message.text or message.caption)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    async with database.acquire() as connection:
        service = GenerationService(
            MessageRepository(connection),
            ChatRepository(connection),
        )
        generated_text = await service.generate_message(
            chat_id=message.chat.id,
            mode_override=mode,
            max_words=30,
        )

    await message.answer(generated_text or NEED_MORE_MATERIAL_MESSAGE)
