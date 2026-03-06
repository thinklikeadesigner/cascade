import { createClient } from "@supabase/supabase-js";

export const dynamic = "force-dynamic";

const LANGFUSE_BASE = process.env.LANGFUSE_BASE_URL || "https://us.cloud.langfuse.com";
const LANGFUSE_PK = process.env.LANGFUSE_PUBLIC_KEY;
const LANGFUSE_SK = process.env.LANGFUSE_SECRET_KEY;

function authHeader() {
  return "Basic " + Buffer.from(`${LANGFUSE_PK}:${LANGFUSE_SK}`).toString("base64");
}

async function fetchLangfuse(path) {
  const res = await fetch(`${LANGFUSE_BASE}${path}`, {
    headers: { Authorization: authHeader() },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    console.error(`Langfuse ${path}: ${res.status}`, body);
    throw new Error(`Langfuse ${path}: ${res.status} — ${body}`);
  }
  return res.json();
}

async function fetchAllTraces(limit = 300) {
  const pages = [];
  let page = 1;
  while (pages.length < limit) {
    const data = await fetchLangfuse(`/api/public/traces?limit=100&page=${page}`);
    const items = data.data || [];
    pages.push(...items);
    if (items.length < 100) break;
    page++;
  }
  return pages.slice(0, limit);
}

const CASCADE_STATES = ["exploring", "goal", "year", "quarter", "month", "week", "schedule", "completed"];

export async function GET() {
  if (process.env.NODE_ENV !== "development") {
    return new Response("Not found", { status: 404 });
  }
  if (!LANGFUSE_PK || !LANGFUSE_SK) {
    return Response.json({ error: "Missing LANGFUSE keys in .env.local" }, { status: 500 });
  }

  try {
    const [traces, observations] = await Promise.all([
      fetchAllTraces(300),
      fetchLangfuse("/api/public/observations?limit=100"),
    ]);

    const obs = observations.data || [];
    const now = new Date();
    const day = 24 * 60 * 60 * 1000;

    // --- Split traces by endpoint ---
    const onboardTraces = traces.filter((t) => t.name === "onboarding-chat");
    const demoTraces = traces.filter((t) => t.name === "demo-chat");
    const otherTraces = traces.filter((t) => t.name !== "onboarding-chat" && t.name !== "demo-chat");

    // ============================================
    // DEMO ANALYTICS
    // ============================================

    // Group demo traces by IP (userId on demo traces)
    const demoSessions = {};
    for (const t of demoTraces) {
      const ip = t.userId || "unknown";
      if (!demoSessions[ip]) demoSessions[ip] = [];
      demoSessions[ip].push(t);
    }

    const demoUniqueVisitors = Object.keys(demoSessions).length;
    const demoTotalCalls = demoTraces.length;

    // How many demos showed a breakdown (tool_fired)?
    let demoBreakdownsShown = 0;
    const demoGoals = [];
    for (const t of demoTraces) {
      const toolFired = t.metadata?.tool_fired || t.output === "breakdown_shown";
      if (toolFired) demoBreakdownsShown++;
      const goal = t.metadata?.goal_text;
      if (goal && t.metadata?.turn_number === 1) {
        demoGoals.push(goal);
      }
    }
    const demoBreakdownRate = demoTotalCalls > 0
      ? Math.round((demoBreakdownsShown / demoTotalCalls) * 100)
      : 0;

    // ============================================
    // ONBOARDING FUNNEL
    // ============================================

    const userStates = {};
    const userRevisions = {}; // userId -> { target: count }
    const userTraceCount = {}; // userId -> number of traces

    for (const t of onboardTraces) {
      const uid = t.userId || "anonymous";
      const state = t.metadata?.cascade_state;

      // Track max state per user
      if (state) {
        const stateIdx = CASCADE_STATES.indexOf(state);
        if (!userStates[uid] || stateIdx > CASCADE_STATES.indexOf(userStates[uid])) {
          userStates[uid] = state;
        }
      }

      // Count traces per user
      userTraceCount[uid] = (userTraceCount[uid] || 0) + 1;

      // Count revisions per user per target
      if (t.metadata?.is_revision) {
        const target = t.metadata?.revision_target || "unknown";
        if (!userRevisions[uid]) userRevisions[uid] = {};
        userRevisions[uid][target] = (userRevisions[uid][target] || 0) + 1;
      }
    }

    // Funnel: users who reached at least this state
    const funnel = CASCADE_STATES.map((state) => {
      const stateIdx = CASCADE_STATES.indexOf(state);
      const count = Object.values(userStates).filter(
        (s) => CASCADE_STATES.indexOf(s) >= stateIdx
      ).length;
      return { state, count };
    });

    // Dropoff: users whose max state is exactly this stage
    const dropoff = CASCADE_STATES.map((state) => ({
      state,
      count: Object.values(userStates).filter((s) => s === state).length,
    }));

    // Completion
    const totalUsers = Object.keys(userStates).length;
    const completedUsers = Object.values(userStates).filter(
      (s) => s === "schedule" || s === "completed"
    ).length;
    const completionRate = totalUsers > 0 ? Math.round((completedUsers / totalUsers) * 100) : 0;

    // ============================================
    // REVISIONS — which plan levels get revised most?
    // ============================================

    const revisionsByLevel = {};
    let totalRevisions = 0;
    for (const targets of Object.values(userRevisions)) {
      for (const [target, count] of Object.entries(targets)) {
        revisionsByLevel[target] = (revisionsByLevel[target] || 0) + count;
        totalRevisions += count;
      }
    }

    // ============================================
    // COST
    // ============================================

    let onboardCost = 0;
    let demoCost = 0;
    for (const t of onboardTraces) onboardCost += t.totalCost || 0;
    for (const t of demoTraces) demoCost += t.totalCost || 0;

    const costPerOnboard = completedUsers > 0
      ? Math.round((onboardCost / completedUsers) * 10000) / 10000
      : 0;
    const costPerDemo = demoUniqueVisitors > 0
      ? Math.round((demoCost / demoUniqueVisitors) * 10000) / 10000
      : 0;

    // Avg calls per completed onboard
    const completedUserIds = Object.entries(userStates)
      .filter(([, s]) => s === "schedule" || s === "completed")
      .map(([uid]) => uid);

    let totalCallsForCompleted = 0;
    for (const uid of completedUserIds) {
      totalCallsForCompleted += userTraceCount[uid] || 0;
    }
    const avgCallsPerOnboard = completedUsers > 0
      ? Math.round((totalCallsForCompleted / completedUsers) * 10) / 10
      : 0;

    // ============================================
    // DAILY COST (7 days)
    // ============================================

    const dailyCosts = [];
    for (let i = 6; i >= 0; i--) {
      const start = new Date(now - (i + 1) * day);
      const end = new Date(now - i * day);
      const dayTraces = traces.filter((t) => {
        const ts = new Date(t.timestamp);
        return ts >= start && ts < end;
      });
      const cost = dayTraces.reduce((s, t) => s + (t.totalCost || 0), 0);
      const onboard = dayTraces.filter((t) => t.name === "onboarding-chat").length;
      const demo = dayTraces.filter((t) => t.name === "demo-chat").length;
      dailyCosts.push({
        date: end.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
        cost: Math.round(cost * 10000) / 10000,
        onboard,
        demo,
      });
    }

    // ============================================
    // MODEL BREAKDOWN
    // ============================================

    const models = {};
    let totalTokensIn = 0;
    let totalTokensOut = 0;
    for (const o of obs) {
      const model = o.model || "unknown";
      models[model] = (models[model] || 0) + 1;
      totalTokensIn += o.usage?.input || o.promptTokens || 0;
      totalTokensOut += o.usage?.output || o.completionTokens || 0;
    }

    // ============================================
    // RECENT TRACES (both types)
    // ============================================

    const recentOnboards = onboardTraces.slice(0, 15).map((t) => ({
      id: t.id,
      userId: t.userId || "anon",
      timestamp: t.timestamp,
      cascadeState: t.metadata?.cascade_state || "-",
      isRevision: t.metadata?.is_revision || false,
      revisionTarget: t.metadata?.revision_target || null,
      cost: Math.round((t.totalCost || 0) * 10000) / 10000,
      latency: t.latency,
    }));

    const recentDemos = demoTraces.slice(0, 10).map((t) => ({
      id: t.id,
      ip: (t.userId || "unknown").slice(0, 12),
      timestamp: t.timestamp,
      goalText: t.metadata?.goal_text || null,
      toolFired: t.metadata?.tool_fired || t.output === "breakdown_shown",
      turnNumber: t.metadata?.turn_number || 1,
      cost: Math.round((t.totalCost || 0) * 10000) / 10000,
    }));

    // ============================================
    // USERS (from Supabase)
    // ============================================

    let users = [];
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

    if (supabaseUrl && supabaseServiceKey) {
      try {
        const supabase = createClient(supabaseUrl, supabaseServiceKey, {
          auth: { autoRefreshToken: false, persistSession: false },
        });
        const { data: authUsers } = await supabase.auth.admin.listUsers();

        // Also fetch onboarding conversations to get cascade_state per user
        const { data: conversations } = await supabase
          .from("onboarding_conversations")
          .select("user_id, cascade_state, created_at, updated_at")
          .order("updated_at", { ascending: false });

        const convByUser = {};
        for (const c of (conversations || [])) {
          // Keep the most recent conversation per user
          if (!convByUser[c.user_id]) convByUser[c.user_id] = c;
        }

        users = (authUsers?.users || []).map((u) => {
          const conv = convByUser[u.id];
          return {
            id: u.id,
            email: u.email,
            created_at: u.created_at,
            last_sign_in: u.last_sign_in_at,
            provider: u.app_metadata?.provider || "email",
            cascadeState: conv?.cascade_state || null,
            onboardStarted: conv?.created_at || null,
            onboardUpdated: conv?.updated_at || null,
          };
        });
      } catch (err) {
        console.error("Supabase users fetch failed:", err.message);
      }
    }

    return Response.json({
      // Onboarding
      funnel,
      dropoff,
      totalUsers,
      completedUsers,
      completionRate,
      avgCallsPerOnboard,
      revisionsByLevel,
      totalRevisions,
      // Demo
      demo: {
        uniqueVisitors: demoUniqueVisitors,
        totalCalls: demoTotalCalls,
        breakdownsShown: demoBreakdownsShown,
        breakdownRate: demoBreakdownRate,
        costPerVisitor: costPerDemo,
        recentGoals: demoGoals.slice(0, 20),
      },
      // Cost
      costByEndpoint: {
        onboard: Math.round(onboardCost * 10000) / 10000,
        demo: Math.round(demoCost * 10000) / 10000,
        total: Math.round((onboardCost + demoCost) * 10000) / 10000,
      },
      costPerOnboard,
      dailyCosts,
      // Usage
      models,
      tokens: { in: totalTokensIn, out: totalTokensOut },
      traceCounts: {
        onboard: onboardTraces.length,
        demo: demoTraces.length,
        other: otherTraces.length,
        total: traces.length,
      },
      // Tables
      recentOnboards,
      recentDemos,
      users,
    });
  } catch (err) {
    console.error("Dashboard API error:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
