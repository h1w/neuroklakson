from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import Settings
from repositories.chats import ChatRepository
from repositories.database import Database
from repositories.messages import MessageRepository
from services.admin import is_chat_admin
from services.twoch import fetch_thread

router = Router()
ADMIN_ONLY_MESSAGE = "Эта команда только для админов чата"


def _chat_title(message: Message) -> str | None:
    return message.chat.title or message.chat.full_name


def _command_arg(message: Message) -> str | None:
    parts = (message.text or message.caption or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else None


@router.message(Command("readtread2ch", "rt2ch"))
async def rt2ch_handler(message: Message, database: Database, settings: Settings) -> None:
    if not await is_chat_admin(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
    ):
        await message.answer(ADMIN_ONLY_MESSAGE)
        return

    url = _command_arg(message)
    if not url:
        await message.answer("Напиши ссылку на тред: /rt2ch https://2ch.hk/b/res/123.html")
        return

    try:
        thread = await fetch_thread(url)
    except Exception:
        await message.answer("Не смог прочитать тред 2ch")
        return

    async with database.acquire() as connection:
        await ChatRepository(connection).upsert_chat(
            chat_id=message.chat.id,
            title=_chat_title(message),
            chat_type=message.chat.type,
            default_mode=settings.default_generation_mode,
        )
        repository = MessageRepository(connection)
        message_count = await repository.insert_messages_bulk(
            chat_id=message.chat.id,
            messages=thread.texts,
            source="import",
        )
        photo_count = await repository.insert_external_photos_bulk(
            chat_id=message.chat.id,
            urls=thread.image_urls,
            source="2ch",
            post_url=url,
        )

    await message.answer(f"Импортировано из 2ch: {message_count} постов, {photo_count} картинок.")
