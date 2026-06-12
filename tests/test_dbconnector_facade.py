import pytest

import dbconnector


class FakeAcquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeDatabase:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


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


def teardown_function():
    dbconnector.set_database(None)


async def test_get_all_messages_uses_configured_database():
    connection = FakeConnection(fetch_rows=[{"normalized_text": "кот"}])
    dbconnector.set_database(FakeDatabase(connection))

    messages = await dbconnector.getAllMessages(100)

    assert messages == ["кот"]
    assert connection.fetch_calls[0][1] == (100,)


async def test_get_all_messages_requires_configured_database():
    dbconnector.set_database(None)

    with pytest.raises(RuntimeError, match="Database is not configured"):
        await dbconnector.getAllMessages(100)


async def test_insert_message_delegates_to_message_repository():
    connection = FakeConnection()
    dbconnector.set_database(FakeDatabase(connection))

    await dbconnector.insertMessage(100, "сырный автобус")

    chat_query, chat_args = connection.execute_calls[0]
    message_query, message_args = connection.execute_calls[1]
    assert "INSERT INTO chats" in chat_query
    assert chat_args == (100, None, "unknown", "absurd")
    assert "INSERT INTO messages" in message_query
    assert message_args == (100, None, None, "сырный автобус", "сырный автобус", "message", None)


async def test_get_random_message_uses_random_message_query():
    connection = FakeConnection(fetchrow_row={"normalized_text": "рандом"})
    dbconnector.set_database(FakeDatabase(connection))

    message = await dbconnector.getRandomMessage(100)

    query, args = connection.fetchrow_calls[0]
    assert message == "рандом"
    assert "SELECT normalized_text" in query
    assert "ORDER BY RANDOM()" in query
    assert "LIMIT 1" in query
    assert args == (100,)


async def test_get_random_message_returns_none_without_row():
    connection = FakeConnection(fetchrow_row=None)
    dbconnector.set_database(FakeDatabase(connection))

    message = await dbconnector.getRandomMessage(100)

    assert message is None
