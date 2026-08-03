-- Project Sherlock — initial schema
-- Run once against a fresh database: psql $DATABASE_URL -f migrations/001_init.sql

CREATE TYPE clue_media_type AS ENUM ('text', 'image', 'audio', 'video', 'qr', 'location');
CREATE TYPE progress_status AS ENUM ('LOCKED', 'AVAILABLE', 'SOLVED', 'FAILED');

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(64),
    full_name VARCHAR(128) NOT NULL,
    language VARCHAR(2),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE seasons (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    submissions_locked BOOLEAN NOT NULL DEFAULT FALSE,
    start_date TIMESTAMPTZ,
    finale_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE clues (
    id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    day_number INT NOT NULL,
    title VARCHAR(128) NOT NULL,
    clue_text TEXT NOT NULL,
    media_type clue_media_type NOT NULL DEFAULT 'text',
    media_url VARCHAR(512),
    hint TEXT,
    correct_answers JSONB NOT NULL DEFAULT '[]',
    release_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (season_id, day_number)
);

CREATE TABLE journal_entries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    clue_id BIGINT NOT NULL REFERENCES clues(id) ON DELETE CASCADE,
    status progress_status NOT NULL DEFAULT 'LOCKED',
    attempts_used INT NOT NULL DEFAULT 0,
    points_earned INT NOT NULL DEFAULT 0,
    hint_used BOOLEAN NOT NULL DEFAULT FALSE,
    last_submitted_answer VARCHAR(256),
    notes TEXT,
    completed_at TIMESTAMPTZ,
    UNIQUE (user_id, clue_id)
);

CREATE TABLE attempts (
    id BIGSERIAL PRIMARY KEY,
    journal_entry_id BIGINT NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    attempt_number INT NOT NULL,
    submitted_answer VARCHAR(256) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    points_awarded INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL,
    message TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE admin_logs (
    id BIGSERIAL PRIMARY KEY,
    admin_telegram_id BIGINT NOT NULL,
    action VARCHAR(64) NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Leaderboard: computed via view, not a stored table, so it's always live.
CREATE VIEW season_leaderboard AS
SELECT
    u.id AS user_id,
    u.full_name,
    u.username,
    c.season_id,
    SUM(j.points_earned) AS total_points,
    MAX(j.completed_at) AS last_completed_at
FROM journal_entries j
JOIN users u ON u.id = j.user_id
JOIN clues c ON c.id = j.clue_id
WHERE j.status = 'SOLVED'
GROUP BY u.id, u.full_name, u.username, c.season_id
ORDER BY total_points DESC, last_completed_at ASC;

CREATE INDEX idx_clues_season_day ON clues (season_id, day_number);
CREATE INDEX idx_journal_user ON journal_entries (user_id);
CREATE INDEX idx_attempts_journal ON attempts (journal_entry_id);
