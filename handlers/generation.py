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
MESSAGE_SHAPES = {
    "normal": {"min_words": 10, "target_words": 20, "max_words": 33},
    "absurd": {"min_words": 7, "target_words": 14, "max_words": 22},
    "chaos": {"min_words": 5, "target_words": 10, "max_words": 15},
}
DEMOTIVATOR_TOP_SHAPE = {"min_words": 2, "target_words": 5, "max_words": 8}
DEMOTIVATOR_BOTTOM_SHAPE = {"min_words": 3, "target_words": 8, "max_words": 12}


def parse_mode_argument(text: str | None) -> str | None:
    parts = (text or "").split(maxsplit=1)
    if len(parts) == 1:
        return None

    mode = parts[1].strip().lower()
    if mode in GENERATION_MODES:
        return mode

    valid_modes = ", ".join(sorted(GENERATION_MODES))
    raise ValueError(f"mode must be one of: {valid_modes}")


def generation_shape_for_mode(mode: str | None) -> dict[str, int]:
    return MESSAGE_SHAPES.get(mode or "absurd", MESSAGE_SHAPES["absurd"])


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
            **generation_shape_for_mode(mode),
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
            **DEMOTIVATOR_TOP_SHAPE,
        )
        second_line = await service.generate_message(
            chat_id=message.chat.id,
            mode_override=mode,
            **DEMOTIVATOR_BOTTOM_SHAPE,
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
