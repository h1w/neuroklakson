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


def test_initial_migration_has_unconditional_unique_normalized_text_index():
    migration_sql = _compact_sql(Path("migrations/001_initial_schema.sql").read_text())

    expected_index = (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_normalized_text "
        "ON messages(chat_id, normalized_text);"
    )

    assert expected_index in migration_sql
