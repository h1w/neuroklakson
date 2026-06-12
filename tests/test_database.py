from repositories import database as database_module
from repositories.database import Database


class FakePool:
    async def close(self):
        pass


async def test_database_connect_is_idempotent(monkeypatch):
    created_pools = []

    async def fake_create_pool(database_url):
        created_pools.append(database_url)
        return FakePool()

    monkeypatch.setattr(database_module.asyncpg, "create_pool", fake_create_pool)
    database = Database("postgresql://bot:bot@postgres:5432/neuroklakson")

    await database.connect()
    first_pool = database._pool
    await database.connect()

    assert database._pool is first_pool
    assert created_pools == ["postgresql://bot:bot@postgres:5432/neuroklakson"]
