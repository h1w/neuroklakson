from __future__ import annotations

import random
from io import BytesIO

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from config import Settings
from demotivate import generateDemotivator, generateQuote
from markchain import makeShortSentence
from repositories.database import Database
from repositories.messages import MessageRepository
from utils import normalizeStringForDemotivator
from voiceover import textVoiceover

router = Router()

NEED_MORE_MATERIAL_MESSAGE = "Я ещё очень тупой, нужно немного подождать"


def _message_text(message: Message) -> str | None:
    return message.text or message.caption


async def _chat_messages_text(database: Database, chat_id: int) -> str:
    async with database.acquire() as connection:
        messages = await MessageRepository(connection).get_messages(chat_id=chat_id)
    return "\n".join(messages)


@router.message(Command("createdemotivator", "crdem", "cd"))
async def create_demotivator_handler(message: Message, settings: Settings) -> None:
    command_text = _message_text(message)
    if command_text is None:
        await message.answer("Еблан, мне не из чего делать демотиватор, пошел нахуй!")
        return

    args = command_text.split(maxsplit=1)[1] if len(command_text.split(maxsplit=1)) > 1 else ""
    first_line, separator, second_line = args.partition("|")
    if not separator:
        second_line = ""

    source_message = message.reply_to_message or message
    if not source_message.photo:
        await message.answer("Еблан, мне не из чего делать демотиватор, пошел нахуй!")
        return

    photo_bytes = BytesIO()
    await message.bot.download(source_message.photo[-1].file_id, destination=photo_bytes)
    photo_bytes.seek(0)
    demotivator_image = await generateDemotivator(
        photo_bytes,
        first_line,
        second_line,
        settings.bredo_demotivator_watermark,
        settings.bredo_demotivator_text_font,
    )

    output = BytesIO()
    demotivator_image.save(output, format="PNG")
    await message.answer_photo(types.BufferedInputFile(output.getvalue(), "aboba.png"))


@router.message(Command("createquote", "cq", "q"))
async def create_quote_handler(message: Message, settings: Settings) -> None:
    if message.reply_to_message is None:
        await message.answer("Придурок, на что мне делать цитату? Образумься")
        return

    replied = message.reply_to_message
    quote_text = _message_text(replied)
    if quote_text is None or replied.from_user is None:
        await message.answer("Придурок, на что мне делать цитату? Образумься")
        return

    profile_photos = await message.bot.get_user_profile_photos(replied.from_user.id)
    if not profile_photos.photos:
        await message.answer("Придурок, у автора нет аватарки для цитаты")
        return

    author_photo = BytesIO()
    await message.bot.download(profile_photos.photos[0][-1].file_id, destination=author_photo)
    author_photo.seek(0)
    quote_image = await generateQuote(
        author_photo,
        replied.from_user.username or replied.from_user.full_name,
        await normalizeStringForDemotivator(quote_text),
        settings.bredo_quote_headline_text,
        settings.bredo_quote_headline_text_font,
        settings.bredo_quote_author_name_text_font,
        settings.bredo_quote_quote_text_font,
    )

    output = BytesIO()
    quote_image.save(output, format="PNG")
    await message.answer_photo(types.BufferedInputFile(output.getvalue(), "aboba.png"))


@router.message(Command("generatebugurt", "genbug", "b"))
async def generate_bugurt_handler(message: Message, database: Database, settings: Settings) -> None:
    messages_text = await _chat_messages_text(database, message.chat.id)
    line_count = random.randint(
        settings.bredo_bugurt_message_min_lines,
        settings.bredo_bugurt_message_max_lines,
    )
    lines: list[str] = []
    for _ in range(line_count):
        line = await makeShortSentence(
            messages_text,
            min_words=settings.bredo_bugurt_message_min_words_per_line,
            target_words=(
                settings.bredo_bugurt_message_min_words_per_line
                + settings.bredo_bugurt_message_max_words_per_line
                + 1
            )
            // 2,
            max_words=settings.bredo_bugurt_message_max_words_per_line,
        )
        if line is not None:
            lines.append(await normalizeStringForDemotivator(line))

    if not lines:
        await message.answer(NEED_MORE_MATERIAL_MESSAGE)
        return
    await message.answer("\n@\n".join(lines))


@router.message(Command("voiceover", "v"))
async def voiceover_handler(message: Message) -> None:
    text = _message_text(message.reply_to_message) if message.reply_to_message else None
    if text is None and message.text is not None:
        text = message.text.split(maxsplit=1)[1] if len(message.text.split(maxsplit=1)) > 1 else None

    if text is None:
        await message.answer("Что мне озвучивать ебалай? Пошел нахуй конченый пидарас")
        return

    await message.answer_voice(types.BufferedInputFile(await textVoiceover(text), "aboba"))
