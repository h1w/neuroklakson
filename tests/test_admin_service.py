from types import SimpleNamespace

from services.admin import is_chat_admin


class FakeBot:
    def __init__(self, status: str) -> None:
        self.status = status
        self.calls = []

    async def get_chat_member(self, chat_id: int, user_id: int):
        self.calls.append((chat_id, user_id))
        return SimpleNamespace(status=self.status)


async def test_is_chat_admin_accepts_creator():
    bot = FakeBot("creator")

    assert await is_chat_admin(bot, chat_id=100, user_id=10) is True
    assert bot.calls == [(100, 10)]


async def test_is_chat_admin_accepts_administrator():
    bot = FakeBot("administrator")

    assert await is_chat_admin(bot, chat_id=100, user_id=10) is True


async def test_is_chat_admin_rejects_member():
    bot = FakeBot("member")

    assert await is_chat_admin(bot, chat_id=100, user_id=10) is False


async def test_is_chat_admin_rejects_missing_user_without_bot_call():
    bot = FakeBot("creator")

    assert await is_chat_admin(bot, chat_id=100, user_id=None) is False
    assert bot.calls == []
