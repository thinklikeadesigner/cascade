-- ============================================================
-- Expert Graph, User Skills, Leading Indicators, Conversations
-- ============================================================

-- Expert Graph: weighted skill requirements for a goal
CREATE TABLE expert_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  skill_name TEXT NOT NULL,
  weight NUMERIC(3,2) NOT NULL CHECK (weight BETWEEN 0 AND 1),
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_expert_skills_goal ON expert_skills(goal_id);

-- User Skill Graph: current capabilities, updated on indicator completion
CREATE TABLE user_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  skill_name TEXT NOT NULL,
  proficiency NUMERIC(3,2) DEFAULT 0 CHECK (proficiency BETWEEN 0 AND 1),
  last_practiced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, skill_name)
);

-- Goal Decomposition Tree: North Star → OKR → Leading Indicators
CREATE TABLE leading_indicators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  target_value INTEGER NOT NULL,
  current_value INTEGER DEFAULT 0,
  unit TEXT,
  skill_name TEXT,
  due_date DATE,
  completed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_indicators_goal ON leading_indicators(goal_id);

-- Raw conversations: training data for Graphiti v2
CREATE TABLE conversations (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  raw_text TEXT NOT NULL,
  source TEXT DEFAULT 'whatsapp',
  extracted_entities JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id, created_at DESC);

-- RLS
ALTER TABLE expert_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE leading_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_iso_expert ON expert_skills
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));
CREATE POLICY tenant_iso_skills ON user_skills
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));
CREATE POLICY tenant_iso_indicators ON leading_indicators
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));
CREATE POLICY tenant_iso_conversations ON conversations
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- updated_at trigger for user_skills
CREATE TRIGGER user_skills_updated_at
  BEFORE UPDATE ON user_skills
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
