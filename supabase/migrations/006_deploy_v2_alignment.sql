-- Migration 006: Deploy v2 schema alignment
-- Implements decisions 2, 3, 7, 11, 12 from design doc

-- 1. Add payment + trial columns to tenants
ALTER TABLE tenants ADD COLUMN completed_weekly_reviews INTEGER DEFAULT 0;
ALTER TABLE tenants ADD COLUMN paid_at TIMESTAMPTZ;
ALTER TABLE tenants ADD COLUMN subscription_status TEXT DEFAULT 'none'
  CHECK (subscription_status IN ('none', 'active', 'past_due', 'canceled'));
ALTER TABLE tenants ADD COLUMN past_due_since TIMESTAMPTZ;

-- 2. Drop WhatsApp columns (Telegram is the channel)
ALTER TABLE tenants DROP COLUMN IF EXISTS phone_number;
ALTER TABLE tenants DROP COLUMN IF EXISTS whatsapp_session_id;

-- 3. Narrow onboarding_status to funnel-only (Decision 7)
-- First migrate any rows using removed values
UPDATE tenants SET onboarding_status = 'tg_connected'
  WHERE onboarding_status IN ('active', 'paying');
UPDATE tenants SET onboarding_status = 'signed_up'
  WHERE onboarding_status IN ('trial_expiring', 'churned');

ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_onboarding_status_check;
ALTER TABLE tenants ADD CONSTRAINT tenants_onboarding_status_check
  CHECK (onboarding_status IN (
    'signed_up', 'goal_set', 'plan_drafted', 'plan_approved', 'tg_connected'
  ));

-- 4. Add columns to tasks (Decision 11)
ALTER TABLE tasks ADD COLUMN description TEXT;
ALTER TABLE tasks ADD COLUMN weekly_plan_id UUID REFERENCES weekly_plans(id);

-- 5. Replace is_tenant_active() (Decisions 3, 12)
CREATE OR REPLACE FUNCTION is_tenant_active(t tenants) RETURNS BOOLEAN AS $$
BEGIN
  -- Paying subscriber
  IF t.subscription_status = 'active' THEN RETURN TRUE; END IF;
  -- Still in trial (fewer than 2 completed weekly reviews)
  IF t.completed_weekly_reviews < 2 THEN RETURN TRUE; END IF;
  -- Grace period: 7 days after payment failure
  IF t.subscription_status = 'past_due'
     AND t.past_due_since + INTERVAL '7 days' > NOW()
  THEN RETURN TRUE; END IF;
  -- Otherwise inactive
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;
