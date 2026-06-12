from types import SimpleNamespace

import handlers.twoch as twoch_handler


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeDatabase:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


async def test_rt2ch_handler_imports_texts_and_external_photos(monkeypatch):
    calls = {}
    connection = object()

    async def fake_is_chat_admin(bot, *, chat_id, user_id):
        return True

    async def fake_fetch_thread(url):
        calls["fetch_url"] = url
        return SimpleNamespace(
            texts=["пост один", "пост два"],
            image_urls=["https://2ch.hk/b/src/1.jpg"],
        )

    class FakeChatRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection
        async def upsert_chat(self, **kwargs):
            calls["chat"] = kwargs

    class FakeMessageRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection
        async def insert_messages_bulk(self, **kwargs):
            calls["messages"] = kwargs
            return len(kwargs["messages"])
        async def insert_external_photos_bulk(self, **kwargs):
            calls["photos"] = kwargs
            return len(kwargs["urls"])

    monkeypatch.setattr("handlers.twoch.is_chat_admin", fake_is_chat_admin)
    monkeypatch.setattr("handlers.twoch.fetch_thread", fake_fetch_thread)
    monkeypatch.setattr("handlers.twoch.ChatRepository", FakeChatRepository)
    monkeypatch.setattr("handlers.twoch.MessageRepository", FakeMessageRepository)

    message = SimpleNamespace(
        text="/rt2ch https://2ch.hk/b/res/123.html",
        caption=None,
        bot=object(),
        from_user=SimpleNamespace(id=55),
        chat=SimpleNamespace(id=100, title="chat", full_name=None, type="supergroup"),
        answers=[],
    )
    async def answer(text):
        message.answers.append(text)
    message.answer = answer

    await twoch_handler.rt2ch_handler(
        message,
        FakeDatabase(connection),
        SimpleNamespace(default_generation_mode="absurd"),
    )

    assert calls["fetch_url"] == "https://2ch.hk/b/res/123.html"
    assert calls["messages"]["messages"] == ["пост один", "пост два"]
    assert calls["messages"]["source"] == "import"
    assert calls["photos"]["urls"] == ["https://2ch.hk/b/src/1.jpg"]
    assert message.answers == ["Импортировано из 2ch: 2 постов, 1 картинок."]


async def test_rt2ch_handler_rejects_non_admin(monkeypatch):
    async def fake_is_chat_admin(bot, *, chat_id, user_id):
        return False
    monkeypatch.setattr("handlers.twoch.is_chat_admin", fake_is_chat_admin)
    message = SimpleNamespace(
        text="/rt2ch https://2ch.hk/b/res/123.html",
        caption=None,
        bot=object(),
        from_user=SimpleNamespace(id=55),
        chat=SimpleNamespace(id=100),
        answers=[],
    )
    async def answer(text):
        message.answers.append(text)
    message.answer = answer

    await twoch_handler.rt2ch_handler(message, FakeDatabase(object()), SimpleNamespace())

    assert message.answers == ["Эта команда только для админов чата"]
