from __future__ import annotations

from typing import Any

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository

_database: Any | None = None


def set_database(database: Any | None) -> None:
    global _database
    _database = database


def _require_database() -> Any:
    if _database is None:
        raise RuntimeError("Database is not configured")
    return _database


async def createTable() -> None:
    return None


async def _ensure_chat(connection: Any, chat_id: int) -> None:
    await ChatRepository(connection).upsert_chat(
        chat_id=chat_id,
        title=None,
        chat_type="unknown",
        default_mode="absurd",
    )


async def insertMessage(chat_id, message):
    database = _require_database()
    async with database.acquire() as connection:
        await _ensure_chat(connection, chat_id)
        await MessageRepository(connection).insert_message(
            chat_id=chat_id,
            telegram_message_id=None,
            user_id=None,
            text=message,
            normalized_text=message,
            source="message",
            forwarded_from=None,
        )


async def insertMessages(chat_id, messages_list):
    database = _require_database()
    async with database.acquire() as connection:
        await _ensure_chat(connection, chat_id)
        await MessageRepository(connection).insert_messages_bulk(
            chat_id=chat_id,
            messages=messages_list,
            source="import",
        )


async def insertPhoto(chat_id, file_id):
    database = _require_database()
    async with database.acquire() as connection:
        await _ensure_chat(connection, chat_id)
        await MessageRepository(connection).insert_photo(
            chat_id=chat_id,
            telegram_message_id=None,
            file_id=file_id,
        )


async def getRandomPhoto(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        return await MessageRepository(connection).get_random_photo(chat_id=chat_id)


async def getRandomMessage(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        return await MessageRepository(connection).get_random_message(chat_id=chat_id)


async def getAllMessages(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        return await MessageRepository(connection).get_messages(chat_id=chat_id)


async def getMessagesCount(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        stats = await MessageRepository(connection).get_stats(chat_id=chat_id)
    return stats["total"]


async def getPhotosCount(chat_id):
    database = _require_database()
    async with database.acquire() as connection:
        stats = await MessageRepository(connection).get_stats(chat_id=chat_id)
    return stats["photos"]


async def setChatMode(chat_id, mode):
    database = _require_database()
    async with database.acquire() as connection:
        await ChatRepository(connection).set_default_mode(chat_id=chat_id, mode=mode)
