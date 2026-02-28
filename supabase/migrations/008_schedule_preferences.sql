-- 008_schedule_preferences.sql
-- Add per-user schedule preference columns to tenants table.
-- Defaults match current hardcoded values (backward compatible).

ALTER TABLE tenants ADD COLUMN morning_hour SMALLINT NOT NULL DEFAULT 7;
ALTER TABLE tenants ADD COLUMN morning_minute SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE tenants ADD COLUMN review_day SMALLINT NOT NULL DEFAULT 0;  -- 0=Sunday, 1=Monday, ..., 6=Saturday

-- Constraints: valid hour/minute/day ranges
ALTER TABLE tenants ADD CONSTRAINT chk_morning_hour CHECK (morning_hour BETWEEN 0 AND 23);
ALTER TABLE tenants ADD CONSTRAINT chk_morning_minute CHECK (morning_minute BETWEEN 0 AND 59);
ALTER TABLE tenants ADD CONSTRAINT chk_review_day CHECK (review_day BETWEEN 0 AND 6);
