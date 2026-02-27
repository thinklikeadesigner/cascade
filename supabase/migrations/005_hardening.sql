-- ============================================================
-- Migration 005: Hardening
-- Idempotent message deliveries, deep-link tokens,
-- computed is_active, expanded onboarding_status
-- ============================================================

-- 1. MESSAGE DELIVERIES — prevents double-sends of scheduled messages
CREATE TABLE message_deliveries (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  message_type TEXT NOT NULL CHECK (message_type IN (
    'morning', 'evening', 'weekly_review', 'weekly_kickoff',
    'trial_reminder', 'trial_expired'
  )),
  scheduled_for DATE NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, message_type, scheduled_for)
);

CREATE INDEX idx_deliveries_tenant_date ON message_deliveries(tenant_id, scheduled_for);

-- 2. DEEP LINK TOKENS — secure Telegram connection
CREATE TABLE deep_link_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  token_hash TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tokens_hash ON deep_link_tokens(token_hash);

-- 3. REPLACE is_active STORED COLUMN WITH COMPUTED FUNCTION
ALTER TABLE tenants DROP COLUMN IF EXISTS is_active;

CREATE OR REPLACE FUNCTION is_tenant_active(t tenants) RETURNS BOOLEAN AS $$
BEGIN
  IF t.subscription_status = 'active' THEN RETURN TRUE; END IF;
  IF t.trial_start_date IS NOT NULL
     AND (t.trial_start_date + INTERVAL '30 days') > NOW()
  THEN RETURN TRUE; END IF;
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- 4. ADD plan_drafted TO onboarding_status
ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_onboarding_status_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_onboarding_status_check CHECK (
  onboarding_status IN (
    'signed_up', 'goal_set', 'plan_drafted', 'plan_approved',
    'tg_connected', 'active', 'trial_expiring', 'churned', 'paying'
  )
);

-- 5. RLS ON NEW TABLES
ALTER TABLE message_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_link_tokens ENABLE ROW LEVEL SECURITY;

-- message_deliveries: tenant isolation (same pattern as tracker_entries, etc.)
CREATE POLICY tenant_isolation_deliveries ON message_deliveries
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- deep_link_tokens: service role only (backend manages these, no direct user access)
CREATE POLICY service_only_tokens ON deep_link_tokens
  FOR ALL USING (false);
