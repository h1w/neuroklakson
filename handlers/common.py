from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import Settings
from handlers.generation import parse_mode_argument
from repositories.chats import ChatRepository
from repositories.database import Database
from repositories.messages import MessageRepository
from services.admin import is_chat_admin

router = Router()

ADMIN_ONLY_MESSAGE = "Эта команда только для админов чата"
HELP_TEXT = """Команды бота:
/start - пошел нахуй
/help, /h - помощь по командам
/generatemessage, /genmsg, /gm [normal|absurd|chaos] - сгенерировать сообщение
/demotivatorgeneration, /demgen, /d [normal|absurd|chaos] - сгенерировать демотиватор
/set_mode <normal|absurd|chaos> - установить режим генерации по умолчанию
/stats, /s - статистика чата
/learn_history - импортировать историю из ответа или txt-документа
/readtread2ch, /rt2ch <url> - импортировать тред 2ch
"""


def _chat_title(message: Message) -> str | None:
    return message.chat.title or message.chat.full_name


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    full_name = message.from_user.full_name if message.from_user else ""
    await message.answer(f"Пошел нахуй {full_name}!")


@router.message(Command("help", "h"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("set_mode"))
async def set_mode_handler(message: Message, database: Database, settings: Settings) -> None:
    if not await is_chat_admin(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
    ):
        await message.answer(ADMIN_ONLY_MESSAGE)
        return

    try:
        mode = parse_mode_argument(message.text or message.caption)
    except ValueError as exc:
        await message.answer(str(exc))
        return

    if mode is None:
        await message.answer("Укажи режим: normal, absurd или chaos")
        return

    async with database.acquire() as connection:
        repository = ChatRepository(connection)
        await repository.upsert_chat(
            chat_id=message.chat.id,
            title=_chat_title(message),
            chat_type=message.chat.type,
            default_mode=settings.default_generation_mode,
        )
        await repository.set_default_mode(message.chat.id, mode)

    await message.answer(f"Режим генерации установлен: {mode}")


@router.message(Command("stats", "s"))
async def stats_handler(message: Message, database: Database) -> None:
    async with database.acquire() as connection:
        chat_repository = ChatRepository(connection)
        message_repository = MessageRepository(connection)
        mode = await chat_repository.get_default_mode(message.chat.id) or "absurd"
        stats = await message_repository.get_stats(chat_id=message.chat.id)
        latest_import = await message_repository.get_latest_import(chat_id=message.chat.id)

    lines = [
        f"ID чата: {message.chat.id}",
        f"Режим: {mode}",
        f"Всего сообщений: {stats['total']}",
        f"Обычные: {stats['message']}",
        f"Forwarded: {stats['forwarded']}",
        f"Import: {stats['import']}",
        f"Фото: {stats['photos']}",
    ]
    if latest_import is not None:
        lines.append(
            "Последний импорт: "
            f"{latest_import['status']}, "
            f"принято {latest_import['accepted_count']}, "
            f"отброшено {latest_import['rejected_count']}"
        )
        if latest_import.get("status") == "failed" and latest_import.get("error_text"):
            lines.append(f"Ошибка: {latest_import['error_text']}")

    await message.answer("\n".join(lines))
