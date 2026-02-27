-- ============================================================
-- Cascade: Initial Schema
-- Extensions, tenants, tracker, sessions, plans, embeddings
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- 1. TENANTS
-- ============================================================

CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  phone_number TEXT UNIQUE,
  whatsapp_session_id TEXT,
  timezone TEXT NOT NULL DEFAULT 'America/New_York',
  morning_time TIME NOT NULL DEFAULT '07:30',
  evening_time TIME NOT NULL DEFAULT '20:00',
  core_hours INTEGER NOT NULL DEFAULT 10,
  flex_hours INTEGER NOT NULL DEFAULT 4,
  subscription_tier TEXT NOT NULL DEFAULT 'free' CHECK (subscription_tier IN ('free', 'core', 'pro', 'team')),
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  api_key_encrypted TEXT,  -- BYOK users
  onboarded_at TIMESTAMPTZ,
  last_active_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_user_id ON tenants(user_id);
CREATE INDEX idx_tenants_phone ON tenants(phone_number);
CREATE INDEX idx_tenants_stripe ON tenants(stripe_customer_id);

-- ============================================================
-- 2. TRACKER ENTRIES (replaces tracker.csv)
-- ============================================================

CREATE TABLE tracker_entries (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  outreach_sent INTEGER DEFAULT 0,
  conversations INTEGER DEFAULT 0,
  new_clients INTEGER DEFAULT 0,
  features_shipped INTEGER DEFAULT 0,
  content_published INTEGER DEFAULT 0,
  mrr NUMERIC(10,2) DEFAULT 0,
  energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 5),
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (tenant_id, date)
);

CREATE INDEX idx_tracker_tenant_date ON tracker_entries(tenant_id, date DESC);

-- ============================================================
-- 3. GOALS
-- ============================================================

CREATE TABLE goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  success_criteria TEXT,
  target_date DATE,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'abandoned')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_goals_tenant ON goals(tenant_id);

-- ============================================================
-- 4. TASKS (weekly plan tasks — replaces checkboxes in week-*.md)
-- ============================================================

CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
  week_start DATE NOT NULL,           -- Monday of the week this task belongs to
  scheduled_day DATE,                 -- specific day within the week
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'core' CHECK (category IN ('core', 'flex')),
  estimated_minutes INTEGER,
  completed BOOLEAN NOT NULL DEFAULT FALSE,
  completed_at TIMESTAMPTZ,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_tenant_week ON tasks(tenant_id, week_start);
CREATE INDEX idx_tasks_tenant_day ON tasks(tenant_id, scheduled_day);

-- ============================================================
-- 5. ADAPTATIONS (patterns Cascade learns about the user)
-- ============================================================

CREATE TABLE adaptations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  pattern_type TEXT NOT NULL,         -- 'velocity', 'energy', 'day_pattern', 'rest_debt', 'scope'
  description TEXT NOT NULL,
  approved BOOLEAN NOT NULL DEFAULT FALSE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  approved_at TIMESTAMPTZ
);

CREATE INDEX idx_adaptations_tenant ON adaptations(tenant_id, active);

-- ============================================================
-- 6. SESSIONS (replaces in-memory session store)
-- ============================================================

CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  chat_jid TEXT NOT NULL,             -- WhatsApp chat JID
  thread_id TEXT,                     -- LangGraph thread ID
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_sessions_tenant ON sessions(tenant_id);
CREATE INDEX idx_sessions_jid ON sessions(chat_jid);

-- ============================================================
-- 7. MESSAGE LOG (audit trail for WhatsApp interactions)
-- ============================================================

CREATE TABLE messages (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  message_type TEXT NOT NULL DEFAULT 'session' CHECK (message_type IN ('session', 'template', 'scheduled')),
  content TEXT NOT NULL,
  parsed_intent TEXT,                 -- 'log', 'status', 'task_complete', 'reschedule', 'unknown'
  whatsapp_message_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_tenant_time ON messages(tenant_id, created_at DESC);

-- ============================================================
-- 8. EMBEDDINGS (pgvector — semantic search over user context)
-- ============================================================

CREATE TABLE embeddings (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,          -- 'goal', 'task', 'tracker_note', 'adaptation', 'message'
  source_id TEXT NOT NULL,            -- ID of the source record
  content TEXT NOT NULL,              -- the text that was embedded
  embedding VECTOR(1536) NOT NULL,    -- OpenAI text-embedding-3-small dimension
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embeddings_tenant ON embeddings(tenant_id);

-- HNSW index for fast similarity search
CREATE INDEX idx_embeddings_vector ON embeddings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 9. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracker_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE adaptations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Tenants can only access their own data
CREATE POLICY tenant_isolation_tenants ON tenants
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY tenant_isolation_tracker ON tracker_entries
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_goals ON goals
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_tasks ON tasks
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_adaptations ON adaptations
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_sessions ON sessions
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_messages ON messages
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

CREATE POLICY tenant_isolation_embeddings ON embeddings
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- Service role bypasses RLS (for NanoClaw backend)
-- Supabase service_role key already bypasses RLS by default

-- ============================================================
-- 10. HELPER FUNCTIONS
-- ============================================================

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_updated_at
  BEFORE UPDATE ON tenants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER goals_updated_at
  BEFORE UPDATE ON goals
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Semantic search function
CREATE OR REPLACE FUNCTION match_embeddings(
  query_embedding VECTOR(1536),
  match_tenant_id UUID,
  match_count INTEGER DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  id BIGINT,
  source_type TEXT,
  source_id TEXT,
  content TEXT,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    e.id,
    e.source_type,
    e.source_id,
    e.content,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM embeddings e
  WHERE e.tenant_id = match_tenant_id
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Weekly velocity calculation
CREATE OR REPLACE FUNCTION get_weekly_velocity(
  p_tenant_id UUID,
  p_weeks INTEGER DEFAULT 4
)
RETURNS TABLE (
  week_start DATE,
  core_completed BIGINT,
  core_total BIGINT,
  flex_completed BIGINT,
  flex_total BIGINT,
  completion_rate NUMERIC
)
LANGUAGE sql STABLE
AS $$
  SELECT
    t.week_start,
    COUNT(*) FILTER (WHERE t.category = 'core' AND t.completed) AS core_completed,
    COUNT(*) FILTER (WHERE t.category = 'core') AS core_total,
    COUNT(*) FILTER (WHERE t.category = 'flex' AND t.completed) AS flex_completed,
    COUNT(*) FILTER (WHERE t.category = 'flex') AS flex_total,
    ROUND(
      COUNT(*) FILTER (WHERE t.category = 'core' AND t.completed)::NUMERIC /
      NULLIF(COUNT(*) FILTER (WHERE t.category = 'core'), 0) * 100,
      1
    ) AS completion_rate
  FROM tasks t
  WHERE t.tenant_id = p_tenant_id
  GROUP BY t.week_start
  ORDER BY t.week_start DESC
  LIMIT p_weeks;
$$;
