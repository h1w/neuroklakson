from __future__ import annotations

from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from config import Settings
from repositories.chats import ChatRepository
from repositories.database import Database
from repositories.messages import MessageRepository
from services.admin import is_chat_admin
from services.imports import parse_history_text
from services.learning import LearningService

router = Router()

ADMIN_ONLY_MESSAGE = "Эта команда только для админов чата"


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


def select_history_document(message: Message):
    if message.document is not None:
        return message.document
    if message.reply_to_message is not None:
        return message.reply_to_message.document
    return None


async def _upsert_chat(connection, message: Message, settings: Settings) -> None:
    await ChatRepository(connection).upsert_chat(
        chat_id=message.chat.id,
        title=_chat_title(message),
        chat_type=message.chat.type,
        default_mode=settings.default_generation_mode,
    )


async def _learn_imported_text(
    message: Message,
    raw_text: str,
    database: Database,
    settings: Settings,
    *,
    admin_user_id: int,
    filename: str,
) -> None:
    async with database.acquire() as connection:
        await _upsert_chat(connection, message, settings)
        repository = MessageRepository(connection)
        import_id = await repository.create_import(
            chat_id=message.chat.id,
            admin_user_id=admin_user_id,
            filename=filename,
        )
        try:
            parsed = parse_history_text(raw_text)
            async with connection.transaction():
                inserted = await repository.insert_messages_bulk(
                    chat_id=message.chat.id,
                    messages=parsed.accepted,
                    source="import",
                )
                await repository.finish_import(
                    import_id=import_id,
                    accepted_count=inserted,
                    rejected_count=parsed.rejected_count,
                )
        except Exception as exc:
            await repository.fail_import(import_id=import_id, error_text=str(exc))
            raise

    await message.answer(
        f"Импортировано: {inserted}. Отклонено: {parsed.rejected_count}."
    )


@router.message(Command("learn_forwarded"))
async def learn_forwarded_handler(
    message: Message,
    database: Database,
    settings: Settings,
) -> None:
    if not await is_chat_admin(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
    ):
        await message.answer(ADMIN_ONLY_MESSAGE)
        return

    if message.reply_to_message is None:
        await message.answer("Ответь командой на сообщение, которое нужно выучить.")
        return

    replied = message.reply_to_message
    async with database.acquire() as connection:
        await _upsert_chat(connection, message, settings)
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
async def learn_history_handler(
    message: Message,
    database: Database,
    settings: Settings,
) -> None:
    admin_user_id = message.from_user.id if message.from_user else None
    if not await is_chat_admin(
        message.bot,
        chat_id=message.chat.id,
        user_id=admin_user_id,
    ):
        await message.answer(ADMIN_ONLY_MESSAGE)
        return

    document = select_history_document(message)
    if document is None:
        await message.answer("Ответь на txt-документ с историей или приложи его к команде.")
        return

    buffer = BytesIO()
    await message.bot.download(document.file_id, destination=buffer)
    await _learn_imported_text(
        message,
        buffer.getvalue().decode("utf-8", errors="ignore"),
        database,
        settings,
        admin_user_id=admin_user_id,
        filename=document.file_name or document.file_id,
    )


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def passive_learning_handler(
    message: Message,
    database: Database,
    settings: Settings,
) -> None:
    async with database.acquire() as connection:
        message_repository = MessageRepository(connection)
        await _upsert_chat(connection, message, settings)

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
