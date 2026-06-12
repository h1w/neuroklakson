from __future__ import annotations

from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository
from services.imports import parse_history_text
from services.learning import LearningService

router = Router()


def _message_text(message: Message) -> str | None:
    return message.text or message.caption


def _chat_title(message: Message) -> str | None:
    return message.chat.title or message.chat.full_name


def _forwarded_from(message: Message) -> str | None:
    forward_from = getattr(message, "forward_from", None)
    if forward_from is not None:
        return str(forward_from.id)
    forward_from_chat = getattr(message, "forward_from_chat", None)
    if forward_from_chat is not None:
        return str(forward_from_chat.id)
    return None


async def _learn_imported_text(message: Message, raw_text: str) -> None:
    parsed = parse_history_text(raw_text)
    database = message.bot["database"]
    async with database.acquire() as connection:
        inserted = await MessageRepository(connection).insert_messages_bulk(
            chat_id=message.chat.id,
            messages=parsed.accepted,
            source="import",
        )

    await message.answer(
        f"Импортировано: {inserted}. Отклонено: {parsed.rejected_count}."
    )


@router.message(Command("learn_forwarded"))
async def learn_forwarded_handler(message: Message) -> None:
    if message.reply_to_message is None:
        await message.answer("Ответь командой на сообщение, которое нужно выучить.")
        return

    replied = message.reply_to_message
    database = message.bot["database"]
    async with database.acquire() as connection:
        learned = await LearningService(MessageRepository(connection)).learn_text(
            chat_id=message.chat.id,
            telegram_message_id=replied.message_id,
            user_id=replied.from_user.id if replied.from_user else None,
            text=_message_text(replied),
            source="forwarded",
            forwarded_from=_forwarded_from(replied),
        )

    await message.answer("Выучил forwarded-сообщение." if learned else "Там нечего учить.")


@router.message(Command("learn_history"))
async def learn_history_handler(message: Message) -> None:
    source_message = message.reply_to_message or message
    raw_text = _message_text(source_message)
    if raw_text is not None:
        await _learn_imported_text(message, raw_text)
        return

    document = source_message.document
    if document is None:
        await message.answer("Ответь на текст истории или приложи txt-документ.")
        return

    buffer = BytesIO()
    await message.bot.download(document.file_id, destination=buffer)
    await _learn_imported_text(message, buffer.getvalue().decode("utf-8", errors="ignore"))


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def passive_learning_handler(message: Message) -> None:
    database = message.bot["database"]
    settings = message.bot["settings"]
    async with database.acquire() as connection:
        chat_repository = ChatRepository(connection)
        message_repository = MessageRepository(connection)
        await chat_repository.upsert_chat(
            chat_id=message.chat.id,
            title=_chat_title(message),
            chat_type=message.chat.type,
            default_mode=settings.default_generation_mode,
        )

        learning_service = LearningService(message_repository)
        await learning_service.learn_text(
            chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            user_id=message.from_user.id if message.from_user else None,
            text=_message_text(message),
            source="message",
        )
        if message.photo:
            await learning_service.learn_photo(
                chat_id=message.chat.id,
                telegram_message_id=message.message_id,
                file_id=message.photo[-1].file_id,
            )
