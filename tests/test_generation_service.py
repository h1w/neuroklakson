import pytest

from services.generation import GenerationService, resolve_generation_mode


class FakeChats:
    def __init__(self, default_mode=None):
        self.default_mode = default_mode
        self.requests = []

    async def get_default_mode(self, chat_id):
        self.requests.append(chat_id)
        return self.default_mode


class FakeMessages:
    def __init__(self, messages):
        self.messages = messages
        self.requests = []
        self.generation_requests = []

    async def get_messages(self, *, chat_id):
        self.requests.append(chat_id)
        return self.messages

    async def get_generation_messages(self, *, chat_id):
        self.generation_requests.append(chat_id)
        return self.messages


async def test_resolve_generation_mode_uses_valid_override():
    chats = FakeChats(default_mode="normal")

    mode = await resolve_generation_mode(chats, chat_id=100, override="chaos")

    assert mode == "chaos"
    assert chats.requests == []


async def test_resolve_generation_mode_uses_valid_chat_default():
    chats = FakeChats(default_mode="normal")

    mode = await resolve_generation_mode(chats, chat_id=100, override=None)

    assert mode == "normal"
    assert chats.requests == [100]


async def test_resolve_generation_mode_rejects_invalid_override():
    chats = FakeChats(default_mode="invalid")

    with pytest.raises(ValueError, match="mode"):
        await resolve_generation_mode(chats, chat_id=100, override="invalid")

    assert chats.requests == []


async def test_resolve_generation_mode_falls_back_to_absurd_for_invalid_chat_default():
    chats = FakeChats(default_mode="invalid")

    mode = await resolve_generation_mode(chats, chat_id=100, override=None)

    assert mode == "absurd"


async def test_generate_message_returns_text_within_max_words():
    messages = FakeMessages(
        [
            "кабачок спорит с автобусом около подъезда",
            "автобус ругает чайник около подъезда",
            "чайник кусает кабачок около модема",
        ]
    )
    chats = FakeChats(default_mode="normal")
    service = GenerationService(messages, chats)

    generated = await service.generate_message(chat_id=100, mode_override=None, max_words=4)

    assert generated is not None
    assert len(generated.split()) <= 4
    assert messages.generation_requests == [100]
    assert messages.requests == []
    assert chats.requests == [100]
