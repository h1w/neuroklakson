import inspect

from repositories.chats import ChatRepository
from repositories.messages import MessageRepository


class FakeConnection:
    def __init__(
        self,
        *,
        execute_results=None,
        fetch_rows=None,
        fetchrow_row=None,
        fetchval_value=None,
    ):
        self.execute_calls = []
        self.fetch_calls = []
        self.fetchrow_calls = []
        self.fetchval_calls = []
        self._execute_results = list(execute_results or [])
        self._fetch_rows = fetch_rows or []
        self._fetchrow_row = fetchrow_row
        self._fetchval_value = fetchval_value

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))
        if self._execute_results:
            return self._execute_results.pop(0)
        return "INSERT 0 1"

    async def fetch(self, query, *args):
        self.fetch_calls.append((query, args))
        return self._fetch_rows

    async def fetchrow(self, query, *args):
        self.fetchrow_calls.append((query, args))
        return self._fetchrow_row

    async def fetchval(self, query, *args):
        self.fetchval_calls.append((query, args))
        return self._fetchval_value


async def test_chat_repository_upsert_chat_inserts_chat_without_overwriting_default_mode():
    connection = FakeConnection()
    repository = ChatRepository(connection)

    await repository.upsert_chat(
        chat_id=100,
        title="test",
        chat_type="supergroup",
        default_mode="absurd",
    )

    query, args = connection.execute_calls[0]
    assert "INSERT INTO chats" in query
    assert "default_generation_mode" in query
    assert "ON CONFLICT" in query
    assert "default_generation_mode =" not in query.partition("DO UPDATE SET")[2]
    assert args == (100, "test", "supergroup", "absurd")


async def test_chat_repository_get_default_mode_fetches_value():
    connection = FakeConnection(fetchval_value="chaos")
    repository = ChatRepository(connection)

    mode = await repository.get_default_mode(100)

    query, args = connection.fetchval_calls[0]
    assert mode == "chaos"
    assert "SELECT default_generation_mode" in query
    assert args == (100,)


async def test_chat_repository_set_default_mode_updates_value_and_timestamp():
    connection = FakeConnection()
    repository = ChatRepository(connection)

    await repository.set_default_mode(100, "normal")

    query, args = connection.execute_calls[0]
    assert "UPDATE chats" in query
    assert "default_generation_mode" in query
    assert "updated_at" in query
    assert args == (100, "normal")


async def test_message_repository_insert_message_ignores_conflicts():
    connection = FakeConnection()
    repository = MessageRepository(connection)

    await repository.insert_message(
        chat_id=100,
        telegram_message_id=10,
        user_id=55,
        text="сырный автобус",
        normalized_text="сырный автобус",
        source="message",
        forwarded_from=None,
    )

    query, args = connection.execute_calls[0]
    assert "INSERT INTO messages" in query
    assert "ON CONFLICT DO NOTHING" in query
    assert args == (100, 10, 55, "сырный автобус", "сырный автобус", "message", None)


async def test_message_repository_insert_messages_bulk_returns_accepted_count():
    connection = FakeConnection(execute_results=["INSERT 0 1", "INSERT 0 1", "INSERT 0 1"])
    repository = MessageRepository(connection)

    count = await repository.insert_messages_bulk(
        chat_id=100,
        messages=["same", "same", "same"],
        source="import",
    )

    assert count == 3
    assert len(connection.execute_calls) == 3
    for query, args in connection.execute_calls:
        assert "INSERT INTO messages" in query
        assert "ON CONFLICT DO NOTHING" in query
        assert args[0] == 100
        assert args[1:3] == (None, None)
        assert args[3] == args[4]
        assert args[5:] == ("import", None)


async def test_message_repository_create_import_records_started_import_and_returns_id():
    connection = FakeConnection(fetchval_value=42)
    repository = MessageRepository(connection)

    import_id = await repository.create_import(
        chat_id=100,
        admin_user_id=55,
        filename="history.txt",
    )

    query, args = connection.fetchval_calls[0]
    assert import_id == 42
    assert "INSERT INTO imports" in query
    assert "status" in query
    assert "RETURNING id" in query
    assert args == (100, 55, "history.txt", "started")


async def test_message_repository_finish_import_marks_completed_with_counts():
    connection = FakeConnection()
    repository = MessageRepository(connection)

    await repository.finish_import(import_id=42, accepted_count=7, rejected_count=3)

    query, args = connection.execute_calls[0]
    assert "UPDATE imports" in query
    assert "status = 'completed'" in query
    assert "accepted_count" in query
    assert "rejected_count" in query
    assert "updated_at = NOW()" in query
    assert args == (42, 7, 3)


async def test_message_repository_fail_import_marks_failed_and_truncates_error_text():
    connection = FakeConnection()
    repository = MessageRepository(connection)
    long_error = "x" * 501

    await repository.fail_import(import_id=42, error_text=long_error)

    query, args = connection.execute_calls[0]
    assert "UPDATE imports" in query
    assert "status = 'failed'" in query
    assert "error_text" in query
    assert "updated_at = NOW()" in query
    assert args == (42, "x" * 500)


async def test_message_repository_insert_photo_records_file_id():
    connection = FakeConnection()
    repository = MessageRepository(connection)

    await repository.insert_photo(chat_id=100, telegram_message_id=10, file_id="photo-file")

    query, args = connection.execute_calls[0]
    assert "INSERT INTO photos" in query
    assert args == (100, 10, "photo-file")


async def test_message_repository_get_messages_returns_normalized_text_strings():
    connection = FakeConnection(
        fetch_rows=[{"normalized_text": "first"}, {"normalized_text": "second"}]
    )
    repository = MessageRepository(connection)

    messages = await repository.get_messages(chat_id=100)

    query, args = connection.fetch_calls[0]
    assert messages == ["first", "second"]
    assert "SELECT normalized_text" in query
    assert "ORDER BY created_at" in query
    assert args == (100,)


async def test_message_repository_get_random_photo_returns_file_id():
    connection = FakeConnection(fetchrow_row={"file_id": "photo-file"})
    repository = MessageRepository(connection)

    file_id = await repository.get_random_photo(chat_id=100)

    query, args = connection.fetchrow_calls[0]
    assert file_id == "photo-file"
    assert "SELECT file_id" in query
    assert "ORDER BY RANDOM()" in query
    assert args == (100,)


async def test_message_repository_get_random_photo_returns_none_without_row():
    connection = FakeConnection(fetchrow_row=None)
    repository = MessageRepository(connection)

    file_id = await repository.get_random_photo(chat_id=100)

    assert file_id is None


async def test_message_repository_get_stats_returns_count_dict():
    connection = FakeConnection(
        fetchrow_row={
            "total": 5,
            "message": 2,
            "forwarded": 1,
            "import": 2,
        },
        fetchval_value=3,
    )
    repository = MessageRepository(connection)

    stats = await repository.get_stats(chat_id=100)

    message_query, message_args = connection.fetchrow_calls[0]
    photo_query, photo_args = connection.fetchval_calls[0]
    assert stats == {"total": 5, "message": 2, "forwarded": 1, "import": 2, "photos": 3}
    assert "COUNT(*)::int AS total" in message_query
    assert "FILTER (WHERE source = 'message')" in message_query
    assert "photos" not in message_query
    assert "FROM photos" in photo_query
    assert message_args == (100,)
    assert photo_args == (100,)


async def test_message_repository_get_stats_returns_zero_fallbacks():
    connection = FakeConnection(fetchrow_row=None, fetchval_value=None)
    repository = MessageRepository(connection)

    stats = await repository.get_stats(chat_id=100)

    assert stats == {"total": 0, "message": 0, "forwarded": 0, "import": 0, "photos": 0}


async def test_message_repository_get_latest_import_returns_latest_import_summary():
    import_row = {
        "status": "failed",
        "accepted_count": 7,
        "rejected_count": 2,
        "error_text": "bad row",
        "filename": "history.txt",
        "created_at": "2026-06-12 10:00:00",
    }
    connection = FakeConnection(fetchrow_row=import_row)
    repository = MessageRepository(connection)

    latest_import = await repository.get_latest_import(chat_id=100)

    query, args = connection.fetchrow_calls[0]
    assert latest_import == import_row
    assert "SELECT" in query
    assert "status" in query
    assert "accepted_count" in query
    assert "rejected_count" in query
    assert "error_text" in query
    assert "filename" in query
    assert "created_at" in query
    assert "FROM imports" in query
    assert "ORDER BY created_at DESC" in query
    assert "LIMIT 1" in query
    assert args == (100,)


async def test_message_repository_get_latest_import_returns_none_without_imports():
    connection = FakeConnection(fetchrow_row=None)
    repository = MessageRepository(connection)

    latest_import = await repository.get_latest_import(chat_id=100)

    assert latest_import is None


def test_repository_public_write_and_read_methods_use_keyword_only_parameters():
    methods = [
        ChatRepository.upsert_chat,
        MessageRepository.insert_message,
        MessageRepository.insert_messages_bulk,
        MessageRepository.create_import,
        MessageRepository.finish_import,
        MessageRepository.fail_import,
        MessageRepository.insert_photo,
        MessageRepository.get_messages,
        MessageRepository.get_random_message,
        MessageRepository.get_random_photo,
        MessageRepository.get_stats,
        MessageRepository.get_latest_import,
    ]

    for method in methods:
        parameters = list(inspect.signature(method).parameters.values())[1:]
        assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters)
