CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    title TEXT,
    chat_type TEXT NOT NULL,
    default_generation_mode TEXT NOT NULL DEFAULT 'absurd',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (default_generation_mode IN ('normal', 'absurd', 'chaos'))
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    telegram_message_id BIGINT,
    user_id BIGINT,
    text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    source TEXT NOT NULL,
    forwarded_from TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (source IN ('message', 'forwarded', 'import'))
);

CREATE TABLE IF NOT EXISTS photos (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    telegram_message_id BIGINT,
    file_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS imports (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    admin_user_id BIGINT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (status IN ('started', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_id
    ON messages(chat_id);

CREATE INDEX IF NOT EXISTS idx_messages_chat_created_at
    ON messages(chat_id, created_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_message_id
    ON messages(chat_id, telegram_message_id)
    WHERE telegram_message_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_chat_normalized_text
    ON messages(chat_id, normalized_text);

CREATE INDEX IF NOT EXISTS idx_photos_chat_id
    ON photos(chat_id);

CREATE INDEX IF NOT EXISTS idx_imports_chat_created_at
    ON imports(chat_id, created_at);
