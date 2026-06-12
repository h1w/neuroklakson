from pathlib import Path


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
    ]

    for fragment in required_fragments:
        assert fragment in migration_sql
