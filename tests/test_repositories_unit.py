from repositories.chats import ChatRepository
from repositories.messages import MessageRepository


class FakeConnection:
    def __init__(self, *, fetch_rows=None, fetchrow_row=None, fetchval_value=None):
        self.execute_calls = []
        self.fetch_calls = []
        self.fetchrow_calls = []
        self.fetchval_calls = []
        self._fetch_rows = fetch_rows or []
        self._fetchrow_row = fetchrow_row
        self._fetchval_value = fetchval_value

    async def execute(self, query, *args):
        self.execute_calls.append((query, args))
        return "EXECUTE"

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

    await repository.upsert_chat(100, "test", "supergroup", "absurd")

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
        100,
        10,
        55,
        "сырный автобус",
        "сырный автобус",
        "message",
        None,
    )

    query, args = connection.execute_calls[0]
    assert "INSERT INTO messages" in query
    assert "ON CONFLICT DO NOTHING" in query
    assert args == (100, 10, 55, "сырный автобус", "сырный автобус", "message", None)


async def test_message_repository_insert_messages_bulk_returns_accepted_count():
    connection = FakeConnection()
    repository = MessageRepository(connection)

    count = await repository.insert_messages_bulk(100, ["one", "two"], "import")

    assert count == 2
    assert len(connection.execute_calls) == 2
    for query, args in connection.execute_calls:
        assert "INSERT INTO messages" in query
        assert "ON CONFLICT DO NOTHING" in query
        assert args[0] == 100
        assert args[1:3] == (None, None)
        assert args[3] == args[4]
        assert args[5:] == ("import", None)


async def test_message_repository_insert_photo_records_file_id():
    connection = FakeConnection()
    repository = MessageRepository(connection)

    await repository.insert_photo(100, 10, "photo-file")

    query, args = connection.execute_calls[0]
    assert "INSERT INTO photos" in query
    assert args == (100, 10, "photo-file")


async def test_message_repository_get_messages_returns_normalized_text_strings():
    connection = FakeConnection(
        fetch_rows=[{"normalized_text": "first"}, {"normalized_text": "second"}]
    )
    repository = MessageRepository(connection)

    messages = await repository.get_messages(100)

    query, args = connection.fetch_calls[0]
    assert messages == ["first", "second"]
    assert "SELECT normalized_text" in query
    assert "ORDER BY created_at" in query
    assert args == (100,)


async def test_message_repository_get_random_photo_returns_file_id():
    connection = FakeConnection(fetchval_value="photo-file")
    repository = MessageRepository(connection)

    file_id = await repository.get_random_photo(100)

    query, args = connection.fetchval_calls[0]
    assert file_id == "photo-file"
    assert "SELECT file_id" in query
    assert "ORDER BY RANDOM()" in query
    assert args == (100,)


async def test_message_repository_get_stats_returns_count_dict():
    connection = FakeConnection(
        fetchrow_row={
            "total": 5,
            "message": 2,
            "forwarded": 1,
            "import": 2,
            "photos": 3,
        }
    )
    repository = MessageRepository(connection)

    stats = await repository.get_stats(100)

    query, args = connection.fetchrow_calls[0]
    assert stats == {"total": 5, "message": 2, "forwarded": 1, "import": 2, "photos": 3}
    assert "COUNT" in query
    assert "photos" in query
    assert args == (100,)
