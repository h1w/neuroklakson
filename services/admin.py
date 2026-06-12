from __future__ import annotations

from typing import Any

ADMIN_STATUSES = {"creator", "administrator"}


async def is_chat_admin(bot: Any, *, chat_id: int, user_id: int | None) -> bool:
    if user_id is None:
        return False

    chat_member = await bot.get_chat_member(chat_id, user_id)
    status = getattr(chat_member.status, "value", chat_member.status)
    return str(status).lower() in ADMIN_STATUSES
