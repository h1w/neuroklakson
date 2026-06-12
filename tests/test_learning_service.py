from services.learning import LearningService


class FakeMessages:
    def __init__(self):
        self.saved = []
        self.photos = []

    async def insert_message(self, **kwargs):
        self.saved.append(kwargs)

    async def insert_photo(self, **kwargs):
        self.photos.append(kwargs)


async def test_learn_text_normalizes_and_saves_message_source():
    messages = FakeMessages()
    service = LearningService(messages)

    learned = await service.learn_text(
        chat_id=100,
        telegram_message_id=10,
        user_id=55,
        text="  смотри https://example.com  вот кабачок  ",
        source="message",
    )

    assert learned is True
    assert messages.saved == [
        {
            "chat_id": 100,
            "telegram_message_id": 10,
            "user_id": 55,
            "text": "  смотри https://example.com  вот кабачок  ",
            "normalized_text": "смотри вот кабачок",
            "source": "message",
            "forwarded_from": None,
        }
    ]


async def test_learn_text_rejects_commands_without_saving():
    messages = FakeMessages()
    service = LearningService(messages)

    learned = await service.learn_text(
        chat_id=100,
        telegram_message_id=10,
        user_id=55,
        text="/start кабачок",
        source="message",
    )

    assert learned is False
    assert messages.saved == []


async def test_learn_photo_rejects_missing_file_id_without_saving():
    messages = FakeMessages()
    service = LearningService(messages)

    learned = await service.learn_photo(chat_id=100, telegram_message_id=10, file_id="")

    assert learned is False
    assert messages.photos == []


async def test_learn_photo_saves_file_id():
    messages = FakeMessages()
    service = LearningService(messages)

    learned = await service.learn_photo(chat_id=100, telegram_message_id=10, file_id="photo-file")

    assert learned is True
    assert messages.photos == [
        {"chat_id": 100, "telegram_message_id": 10, "file_id": "photo-file"}
    ]
