-- ============================================================
-- Migration 004: Telegram, Trial Management, Events, JSONB Logs
-- ============================================================

-- 1. Add Telegram and trial fields to tenants
ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE,
  ADD COLUMN IF NOT EXISTS onboarding_status TEXT NOT NULL DEFAULT 'signed_up'
    CHECK (onboarding_status IN (
      'signed_up', 'goal_set', 'plan_approved',
      'tg_connected', 'active', 'trial_expiring', 'churned', 'paying'
    )),
  ADD COLUMN IF NOT EXISTS trial_start_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_tenants_telegram ON tenants(telegram_id);
CREATE INDEX IF NOT EXISTS idx_tenants_onboarding ON tenants(onboarding_status);

-- 2. Add JSONB metrics column to tracker_entries
-- Keeps existing fixed columns for backward compatibility, adds flexible metrics
ALTER TABLE tracker_entries
  ADD COLUMN IF NOT EXISTS metrics JSONB DEFAULT '{}';

-- 3. Quarterly plans table
CREATE TABLE IF NOT EXISTS quarterly_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
  year INTEGER NOT NULL,
  milestones JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (goal_id, quarter, year)
);

-- 4. Monthly plans table
CREATE TABLE IF NOT EXISTS monthly_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  quarterly_plan_id UUID REFERENCES quarterly_plans(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
  year INTEGER NOT NULL,
  targets JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, month, year)
);

-- 5. Weekly plans table (parent for tasks)
CREATE TABLE IF NOT EXISTS weekly_plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  monthly_plan_id UUID REFERENCES monthly_plans(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, week_start)
);

-- 6. User events (PostHog backup + funnel tracking)
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  event_name TEXT NOT NULL,
  properties JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_tenant_time ON events(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(event_name);

-- 7. Stripe event idempotency
CREATE TABLE IF NOT EXISTS stripe_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_event_id TEXT UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. RLS for new tables
ALTER TABLE quarterly_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_quarterly ON quarterly_plans
  FOR ALL USING (goal_id IN (
    SELECT id FROM goals WHERE tenant_id IN (
      SELECT id FROM tenants WHERE user_id = auth.uid()
    )
  ));

CREATE POLICY tenant_isolation_monthly ON monthly_plans
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_weekly ON weekly_plans
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_events ON events
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- stripe_events: service role only (no user access)
CREATE POLICY service_only_stripe ON stripe_events
  FOR ALL USING (false);
