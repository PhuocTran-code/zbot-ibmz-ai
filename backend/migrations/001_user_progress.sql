-- Migration 001: user progress table
-- Run once in your Supabase SQL editor (or via CLI: supabase db push)

CREATE TABLE IF NOT EXISTS user_progress (
    user_id    TEXT        NOT NULL,
    badge_id   TEXT        NOT NULL,
    status     TEXT        NOT NULL DEFAULT 'not_started'
                           CHECK (status IN ('not_started', 'in_progress', 'completed')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, badge_id)
);

-- Auto-update updated_at on row changes
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER user_progress_updated_at
    BEFORE UPDATE ON user_progress
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Optional: RLS (enable if you add Supabase Auth later)
-- ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can manage their own progress"
--     ON user_progress FOR ALL
--     USING (auth.uid()::text = user_id);
