from pathlib import Path


def _compact_sql(sql: str) -> str:
    return " ".join(sql.split())


def test_initial_migration_contains_required_tables_indexes_and_checks():
    migration_sql = Path("migrations/001_initial_schema.sql").read_text()

    required_fragments = [
        "CREATE TABLE IF NOT EXISTS chats",
        "CREATE TABLE IF NOT EXISTS messages",
        "CREATE TABLE IF NOT EXISTS photos",
        "CREATE TABLE IF NOT EXISTS imports",
        "CREATE INDEX IF NOT EXISTS idx_messages_chat_id",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_message_id",
        "CHECK (default_generation_mode IN ('normal', 'absurd', 'chaos'))",
        "CREATE INDEX IF NOT EXISTS idx_messages_chat_created_at",
    ]

    for fragment in required_fragments:
        assert fragment in migration_sql


def test_initial_migration_requires_message_text_fields():
    migration_sql = Path("migrations/001_initial_schema.sql").read_text()

    assert "text TEXT NOT NULL" in migration_sql
    assert "normalized_text TEXT NOT NULL" in migration_sql


def test_initial_migration_allows_duplicate_normalized_texts():
    migration_sql = _compact_sql(Path("migrations/001_initial_schema.sql").read_text())

    assert "idx_messages_chat_normalized_text" not in migration_sql
    assert "ON messages(chat_id, normalized_text)" not in migration_sql


def test_external_photos_migration_adds_external_media_table():
    migration_sql = Path("migrations/003_external_photos.sql").read_text()

    assert "CREATE TABLE IF NOT EXISTS external_photos" in migration_sql
    assert "external_url TEXT NOT NULL" in migration_sql
    assert "CREATE INDEX IF NOT EXISTS idx_external_photos_chat_id" in migration_sql
