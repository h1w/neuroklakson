from pathlib import Path
from types import SimpleNamespace

import pytest

import handlers.common as common
import handlers.generation as generation
from handlers.generation import parse_mode_argument
from handlers.learning import _learn_imported_text, select_history_document


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        self.connection.events.append("transaction:start")

    async def __aexit__(self, exc_type, exc, tb):
        self.connection.events.append("transaction:rollback" if exc_type else "transaction:commit")


class FakeImportConnection:
    def __init__(self, *, execute_results):
        self.events = []
        self._execute_results = list(execute_results)

    def transaction(self):
        return FakeTransaction(self)

    async def execute(self, query, *args):
        compact_query = " ".join(query.split())
        if "INSERT INTO chats" in query:
            self.events.append("upsert_chat")
            return "INSERT 0 1"
        if "INSERT INTO messages" in query:
            self.events.append(f"insert_message:{args[3]}")
            result = self._execute_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        if "UPDATE imports" in query:
            self.events.append(f"update_import:{compact_query}")
            return "UPDATE 1"
        raise AssertionError(compact_query)

    async def fetchval(self, query, *args):
        assert "INSERT INTO imports" in query
        self.events.append("create_import")
        return 42


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


def test_parse_mode_argument_returns_none_without_mode():
    assert parse_mode_argument("/gm") is None
    assert parse_mode_argument("/demgen") is None


def test_parse_mode_argument_returns_valid_mode():
    assert parse_mode_argument("/demgen chaos") == "chaos"


def test_parse_mode_argument_rejects_invalid_mode_with_valid_modes():
    with pytest.raises(ValueError, match="normal.*absurd.*chaos|normal.*chaos.*absurd|absurd.*normal.*chaos|absurd.*chaos.*normal|chaos.*normal.*absurd|chaos.*absurd.*normal"):
        parse_mode_argument("/gm cursed")


async def test_generate_demotivator_uses_default_mode_and_random_photo(monkeypatch):
    calls = {"generated": []}
    connection = object()

    class FakeBot:
        async def download(self, file_id, destination):
            calls["download_file_id"] = file_id
            destination.write(b"photo-bytes")

    class FakeMessageRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

        async def get_random_photo(self, *, chat_id):
            calls["random_photo_chat_id"] = chat_id
            return "photo-file-id"

    class FakeChatRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

    class FakeGenerationService:
        def __init__(self, message_repository, chat_repository):
            assert isinstance(message_repository, FakeMessageRepository)
            assert isinstance(chat_repository, FakeChatRepository)

        async def generate_message(self, *, chat_id, mode_override, max_words):
            calls["generated"].append(
                {"chat_id": chat_id, "mode_override": mode_override, "max_words": max_words}
            )
            return "first line" if max_words == 8 else "second line"

    class FakeImage:
        def save(self, output, format):
            calls["saved_format"] = format
            output.write(b"demotivator-png")

    async def fake_generate_demotivator(image, top_text, bottom_text, watermark, font):
        calls["image_bytes"] = image.getvalue()
        calls["demotivator_args"] = (top_text, bottom_text, watermark, font)
        return FakeImage()

    monkeypatch.setattr("handlers.generation.MessageRepository", FakeMessageRepository)
    monkeypatch.setattr("handlers.generation.ChatRepository", FakeChatRepository)
    monkeypatch.setattr("handlers.generation.GenerationService", FakeGenerationService)
    monkeypatch.setattr("handlers.generation.generateDemotivator", fake_generate_demotivator)

    message = SimpleNamespace(
        text="/demgen",
        caption=None,
        chat=SimpleNamespace(id=100),
        bot=FakeBot(),
        sent_photos=[],
    )

    async def answer_photo(photo):
        message.sent_photos.append(photo)

    message.answer_photo = answer_photo

    await generation.generate_demotivator_handler(
        message,
        FakeDatabase(connection),
        SimpleNamespace(bredo_demotivator_watermark="wm", bredo_demotivator_text_font="font.ttf"),
    )

    assert calls["random_photo_chat_id"] == 100
    assert calls["download_file_id"] == "photo-file-id"
    assert calls["generated"] == [
        {"chat_id": 100, "mode_override": None, "max_words": 8},
        {"chat_id": 100, "mode_override": None, "max_words": 12},
    ]
    assert calls["image_bytes"] == b"photo-bytes"
    assert calls["demotivator_args"] == ("first line", "second line", "wm", "font.ttf")
    assert calls["saved_format"] == "PNG"
    assert len(message.sent_photos) == 1


async def test_generate_demotivator_passes_mode_override(monkeypatch):
    mode_overrides = []

    class FakeMessageRepository:
        def __init__(self, repository_connection):
            pass

        async def get_random_photo(self, *, chat_id):
            return None

    class FakeGenerationService:
        def __init__(self, message_repository, chat_repository):
            pass

        async def generate_message(self, *, chat_id, mode_override, max_words):
            mode_overrides.append(mode_override)
            return None

    monkeypatch.setattr("handlers.generation.MessageRepository", FakeMessageRepository)
    monkeypatch.setattr("handlers.generation.GenerationService", FakeGenerationService)

    message = SimpleNamespace(
        text="/demgen chaos",
        caption=None,
        chat=SimpleNamespace(id=100),
        answers=[],
    )

    async def answer(text):
        message.answers.append(text)

    message.answer = answer

    await generation.generate_demotivator_handler(
        message,
        FakeDatabase(object()),
        SimpleNamespace(bredo_demotivator_watermark="wm", bredo_demotivator_text_font="font.ttf"),
    )

    assert mode_overrides == ["chaos", "chaos"]
    assert message.answers == ["Я ещё очень тупой, нужно немного подождать"]


async def test_stats_handler_includes_latest_import_summary(monkeypatch):
    connection = object()
    calls = {}

    class FakeChatRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

        async def get_default_mode(self, chat_id):
            calls["mode_chat_id"] = chat_id
            return "normal"

    class FakeMessageRepository:
        def __init__(self, repository_connection):
            assert repository_connection is connection

        async def get_stats(self, *, chat_id):
            calls["stats_chat_id"] = chat_id
            return {"total": 10, "message": 7, "forwarded": 1, "import": 2, "photos": 3}

        async def get_latest_import(self, *, chat_id):
            calls["latest_import_chat_id"] = chat_id
            return {
                "status": "failed",
                "accepted_count": 10,
                "rejected_count": 2,
                "error_text": "parse error",
                "filename": "history.txt",
                "created_at": "2026-06-12 10:00:00",
            }

    monkeypatch.setattr("handlers.common.ChatRepository", FakeChatRepository)
    monkeypatch.setattr("handlers.common.MessageRepository", FakeMessageRepository)

    message = SimpleNamespace(chat=SimpleNamespace(id=100), answers=[])

    async def answer(text):
        message.answers.append(text)

    message.answer = answer

    await common.stats_handler(message, FakeDatabase(connection))

    assert calls == {"mode_chat_id": 100, "stats_chat_id": 100, "latest_import_chat_id": 100}
    assert len(message.answers) == 1
    assert "Последний импорт: failed, принято 10, отброшено 2" in message.answers[0]
    assert "Ошибка: parse error" in message.answers[0]


def test_runtime_code_does_not_use_bot_mapping_access():
    project_root = Path(__file__).resolve().parents[1]
    paths = [project_root / "bot.py", *sorted((project_root / "handlers").glob("*.py"))]
    runtime_source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert 'bot["' not in runtime_source
    assert "bot['" not in runtime_source
    assert "message.bot[" not in runtime_source


def test_select_history_document_prefers_attached_document_over_caption_text():
    document = SimpleNamespace(file_id="attached-file")
    message = SimpleNamespace(
        document=document,
        caption="/learn_history this caption is not the import source",
        text=None,
        reply_to_message=None,
    )

    assert select_history_document(message) is document


def test_select_history_document_uses_replied_document():
    document = SimpleNamespace(file_id="replied-file")
    message = SimpleNamespace(
        document=None,
        reply_to_message=SimpleNamespace(document=document),
    )

    assert select_history_document(message) is document


async def test_learn_imported_text_wraps_message_insert_and_finish_in_transaction():
    connection = FakeImportConnection(execute_results=["INSERT 0 1"])
    message = SimpleNamespace(
        chat=SimpleNamespace(id=100, title="chat", full_name=None, type="supergroup"),
        answer=lambda text: None,
    )

    async def answer(text):
        message.answer_text = text

    message.answer = answer

    await _learn_imported_text(
        message,
        "hello world",
        FakeDatabase(connection),
        SimpleNamespace(default_generation_mode="absurd"),
        admin_user_id=55,
        filename="history.txt",
    )

    assert connection.events == [
        "upsert_chat",
        "create_import",
        "transaction:start",
        "insert_message:hello world",
        "update_import:UPDATE imports SET status = 'completed', accepted_count = $2, rejected_count = $3, updated_at = NOW() WHERE id = $1",
        "transaction:commit",
    ]


async def test_learn_imported_text_marks_import_failed_after_transaction_rollback():
    connection = FakeImportConnection(execute_results=[RuntimeError("boom")])
    message = SimpleNamespace(
        chat=SimpleNamespace(id=100, title="chat", full_name=None, type="supergroup"),
        answer=lambda text: None,
    )

    with pytest.raises(RuntimeError, match="boom"):
        await _learn_imported_text(
            message,
            "hello world",
            FakeDatabase(connection),
            SimpleNamespace(default_generation_mode="absurd"),
            admin_user_id=55,
            filename="history.txt",
        )

    assert connection.events == [
        "upsert_chat",
        "create_import",
        "transaction:start",
        "insert_message:hello world",
        "transaction:rollback",
        "update_import:UPDATE imports SET status = 'failed', error_text = $2, updated_at = NOW() WHERE id = $1",
    ]
