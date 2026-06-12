CREATE TABLE IF NOT EXISTS external_photos (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    external_url TEXT NOT NULL,
    post_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_photos_chat_id
    ON external_photos(chat_id);
