-- ============================================================
-- 009: Memory System — core_memories, memories, memory_links
-- ============================================================

-- ============================================================
-- 1. CORE MEMORIES (always-in-context user profile doc)
-- ============================================================

CREATE TABLE core_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content TEXT NOT NULL DEFAULT '',
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One core memory doc per tenant
CREATE UNIQUE INDEX idx_core_memories_tenant ON core_memories(tenant_id);

ALTER TABLE core_memories ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_core_memories ON core_memories
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- ============================================================
-- 2. MEMORIES (archival Zettelkasten notes)
-- ============================================================

CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  memory_type TEXT NOT NULL DEFAULT 'fact'
    CHECK (memory_type IN ('fact', 'preference', 'pattern', 'goal_context', 'contradiction')),
  tags TEXT[] DEFAULT '{}',
  confidence REAL NOT NULL DEFAULT 1.0,
  decay_score REAL NOT NULL DEFAULT 1.0,
  source_conversation_id BIGINT REFERENCES conversations(id) ON DELETE SET NULL,
  embedding VECTOR(768),
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'pending_review', 'archived', 'forgotten')),
  superseded_by UUID REFERENCES memories(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_confirmed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memories_tenant ON memories(tenant_id, status);
CREATE INDEX idx_memories_tenant_type ON memories(tenant_id, memory_type)
  WHERE status = 'active';
CREATE INDEX idx_memories_vector ON memories
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_memories ON memories
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- ============================================================
-- 3. MEMORY LINKS (Zettelkasten connections)
-- ============================================================

CREATE TABLE memory_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  source_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  target_memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  link_type TEXT NOT NULL
    CHECK (link_type IN ('related', 'supports', 'contradicts', 'supersedes', 'part_of')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (source_memory_id, target_memory_id, link_type)
);

CREATE INDEX idx_memory_links_tenant ON memory_links(tenant_id);
CREATE INDEX idx_memory_links_source ON memory_links(source_memory_id);
CREATE INDEX idx_memory_links_target ON memory_links(target_memory_id);

ALTER TABLE memory_links ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_memory_links ON memory_links
  FOR ALL USING (tenant_id IN (SELECT id FROM tenants WHERE user_id = auth.uid()));

-- ============================================================
-- 4. SEMANTIC SEARCH FUNCTION for memories
-- ============================================================

CREATE OR REPLACE FUNCTION match_memories(
  query_embedding VECTOR(768),
  match_tenant_id UUID,
  match_count INTEGER DEFAULT 5,
  match_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  memory_type TEXT,
  tags TEXT[],
  confidence REAL,
  decay_score REAL,
  similarity FLOAT,
  created_at TIMESTAMPTZ,
  last_confirmed_at TIMESTAMPTZ
)
LANGUAGE sql STABLE
AS $$
  SELECT
    m.id,
    m.content,
    m.memory_type,
    m.tags,
    m.confidence,
    m.decay_score,
    1 - (m.embedding <=> query_embedding) AS similarity,
    m.created_at,
    m.last_confirmed_at
  FROM memories m
  WHERE m.tenant_id = match_tenant_id
    AND m.status = 'active'
    AND m.embedding IS NOT NULL
    AND 1 - (m.embedding <=> query_embedding) > match_threshold
  ORDER BY
    (1 - (m.embedding <=> query_embedding)) * m.decay_score * m.confidence DESC
  LIMIT match_count;
$$;

-- ============================================================
-- 5. DECAY SCORING FUNCTION (runs in Postgres, no cross-tenant risk)
-- ============================================================

CREATE OR REPLACE FUNCTION update_memory_decay_scores()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  updated_count INTEGER;
BEGIN
  UPDATE memories
  SET decay_score = ROUND(
    POWER(0.95, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400)::numeric,
    4
  )
  WHERE status = 'active'
    AND ABS(
      decay_score - POWER(0.95, EXTRACT(EPOCH FROM (NOW() - last_accessed_at)) / 86400)
    ) > 0.01;

  GET DIAGNOSTICS updated_count = ROW_COUNT;
  RETURN updated_count;
END;
$$;
