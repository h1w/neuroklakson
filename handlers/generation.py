from __future__ import annotations

from io import BytesIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from config import GENERATION_MODES, Settings
from demotivate import generateDemotivator
from repositories.chats import ChatRepository
from repositories.database import Database
from repositories.messages import MessageRepository
from services.generation import GenerationService
from services.media import download_external_image

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


@router.message(Command("demotivatorgeneration", "demgen", "d"))
async def generate_demotivator_handler(
    message: Message,
    database: Database,
    settings: Settings,
) -> None:
    try:
        mode = parse_mode_argument(message.text or message.caption)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    async with database.acquire() as connection:
        message_repository = MessageRepository(connection)
        service = GenerationService(
            message_repository,
            ChatRepository(connection),
        )
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
        photo_source = await message_repository.get_random_photo_source(chat_id=message.chat.id)

    if first_line is None or second_line is None or photo_source is None:
        await message.answer(NEED_MORE_MATERIAL_MESSAGE)
        return

    if photo_source["source"] == "telegram":
        photo_bytes = BytesIO()
        await message.bot.download(photo_source["value"], destination=photo_bytes)
        photo_bytes.seek(0)
    else:
        photo_bytes = await download_external_image(photo_source["value"])
    demotivator_image = await generateDemotivator(
        photo_bytes,
        first_line,
        second_line,
        settings.bredo_demotivator_watermark,
        settings.bredo_demotivator_text_font,
    )

    output = BytesIO()
    demotivator_image.save(output, format="PNG")
    await message.answer_photo(BufferedInputFile(output.getvalue(), "aboba.png"))
