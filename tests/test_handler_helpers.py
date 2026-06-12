from pathlib import Path
from types import SimpleNamespace

import pytest

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


def test_parse_mode_argument_returns_valid_mode():
    assert parse_mode_argument("/demgen chaos") == "chaos"


def test_parse_mode_argument_rejects_invalid_mode_with_valid_modes():
    with pytest.raises(ValueError, match="normal.*absurd.*chaos|normal.*chaos.*absurd|absurd.*normal.*chaos|absurd.*chaos.*normal|chaos.*normal.*absurd|chaos.*absurd.*normal"):
        parse_mode_argument("/gm cursed")


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
