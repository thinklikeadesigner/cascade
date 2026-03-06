"use client";

import { useState, useEffect } from "react";
import "./dashboard.css";

const IS_DEV = process.env.NODE_ENV === "development";

function Stat({ label, value, sub, accent }) {
  return (
    <div className="dash-stat">
      <span className={`dash-stat-value ${accent ? "dash-accent" : ""}`}>{value}</span>
      <span className="dash-stat-label">{label}</span>
      {sub && <span className="dash-stat-sub">{sub}</span>}
    </div>
  );
}

function FunnelBar({ state, count, maxCount, dropped }) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
  return (
    <div className="dash-funnel-row">
      <span className="dash-funnel-label">{state}</span>
      <div className="dash-funnel-track">
        <div className="dash-funnel-fill" style={{ width: `${Math.max(pct, 3)}%` }} />
      </div>
      <span className="dash-funnel-count">{count}</span>
      {dropped > 0 && <span className="dash-funnel-drop">-{dropped}</span>}
    </div>
  );
}

function CostBar({ data, maxCost }) {
  const height = maxCost > 0 ? (data.cost / maxCost) * 100 : 0;
  return (
    <div className="dash-bar-col">
      <span className="dash-bar-val">{data.cost > 0 ? `$${data.cost}` : ""}</span>
      <div className="dash-bar-track">
        <div className="dash-bar-fill" style={{ height: `${Math.max(height, 2)}%` }} />
      </div>
      <span className="dash-bar-label">{data.date}</span>
      <span className="dash-bar-sub">{data.onboard}o {data.demo}d</span>
    </div>
  );
}

function TabBar({ active, onSwitch }) {
  return (
    <div className="dash-tabs">
      {["llm", "analytics"].map((tab) => (
        <button
          key={tab}
          className={`dash-tab ${active === tab ? "dash-tab-active" : ""}`}
          onClick={() => onSwitch(tab)}
        >
          {tab === "llm" ? "LLM / Users" : "PostHog"}
        </button>
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [phData, setPhData] = useState(null);
  const [error, setError] = useState(null);
  const [phError, setPhError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [phLoading, setPhLoading] = useState(true);
  const [tab, setTab] = useState("llm");

  useEffect(() => {
    if (!IS_DEV) return;
    fetch("/api/dashboard")
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    fetch("/api/dashboard/posthog")
      .then((r) => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(setPhData)
      .catch((e) => setPhError(e.message))
      .finally(() => setPhLoading(false));
  }, []);

  if (!IS_DEV) {
    return <div className="dash-container"><p className="dash-error">Not available.</p></div>;
  }

  return (
    <div className="dash-container">
      <header className="dash-header">
        <h1>Cascade</h1>
        <span className="dash-tag">dev dashboard</span>
        <TabBar active={tab} onSwitch={setTab} />
      </header>

      {tab === "analytics" && (
        <PostHogDashboard data={phData} loading={phLoading} error={phError} />
      )}

      {tab === "llm" && <LLMDashboard data={data} loading={loading} error={error} />}
    </div>
  );
}

function LLMDashboard({ data, loading, error }) {
  if (loading) {
    return <div className="dash-loading"><div className="dash-spinner" /><span>Pulling from Langfuse...</span></div>;
  }
  if (error) {
    return <p className="dash-error">Error: {error}</p>;
  }
  if (!data) return null;

  const maxFunnel = data.funnel[0]?.count || 1;
  const maxCost = Math.max(...data.dailyCosts.map((d) => d.cost), 0.001);
  const dropoffMap = {};
  for (const d of data.dropoff) dropoffMap[d.state] = d.count;

  return (
    <>

      {/* ---- USERS ---- */}
      {data.users.length > 0 && (
        <div className="dash-section" style={{ marginBottom: 24 }}>
          <h2>Users ({data.users.length})</h2>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Signed up</th>
                  <th>Onboard state</th>
                  <th>Last activity</th>
                  <th>Provider</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td className="dash-mono">{formatTime(u.created_at)}</td>
                    <td>
                      {u.cascadeState
                        ? <span className={`dash-state dash-state-${u.cascadeState}`}>{u.cascadeState}</span>
                        : <span className="dash-muted">no onboard</span>
                      }
                    </td>
                    <td className="dash-mono">{formatTime(u.onboardUpdated || u.last_sign_in)}</td>
                    <td className="dash-mono">{u.provider}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---- TOP KPIs ---- */}
      <div className="dash-cards">
        <div className="dash-card">
          <h2>Demo (top of funnel)</h2>
          <div className="dash-card-stats">
            <Stat label="visitors" value={data.demo.uniqueVisitors} />
            <Stat label="calls" value={data.demo.totalCalls} />
            <Stat label="breakdowns shown" value={`${data.demo.breakdownRate}%`} accent sub={`${data.demo.breakdownsShown} of ${data.demo.totalCalls}`} />
            <Stat label="cost/visitor" value={`$${data.demo.costPerVisitor}`} />
          </div>
        </div>
        <div className="dash-card">
          <h2>Onboarding</h2>
          <div className="dash-card-stats">
            <Stat label="users" value={data.totalUsers} />
            <Stat label="completed" value={data.completedUsers} />
            <Stat label="completion" value={`${data.completionRate}%`} accent />
            <Stat label="avg calls" value={data.avgCallsPerOnboard} />
          </div>
        </div>
        <div className="dash-card">
          <h2>Cost</h2>
          <div className="dash-card-stats">
            <Stat label="total" value={`$${data.costByEndpoint.total}`} />
            <Stat label="onboard" value={`$${data.costByEndpoint.onboard}`} />
            <Stat label="demo" value={`$${data.costByEndpoint.demo}`} />
            <Stat label="per completed" value={`$${data.costPerOnboard}`} accent />
          </div>
        </div>
      </div>

      {/* ---- FUNNEL ---- */}
      <div className="dash-section">
        <h2>Onboarding funnel</h2>
        <p className="dash-section-sub">Users who reached each cascade state (left = dropoff at that stage)</p>
        <div className="dash-funnel">
          {data.funnel.map((f) => (
            <FunnelBar
              key={f.state}
              state={f.state}
              count={f.count}
              maxCount={maxFunnel}
              dropped={dropoffMap[f.state] || 0}
            />
          ))}
        </div>
      </div>

      {/* ---- REVISIONS ---- */}
      {data.totalRevisions > 0 && (
        <div className="dash-section">
          <h2>Revisions by plan level</h2>
          <p className="dash-section-sub">{data.totalRevisions} total revisions — which levels need rework?</p>
          <div className="dash-models">
            {Object.entries(data.revisionsByLevel)
              .sort(([, a], [, b]) => b - a)
              .map(([level, count]) => (
                <span key={level} className="dash-model">
                  {level} <span className="dash-model-count">{count}</span>
                </span>
              ))}
          </div>
        </div>
      )}

      {/* ---- DAILY COST ---- */}
      <div className="dash-section">
        <h2>Daily cost (7d)</h2>
        <p className="dash-section-sub">o = onboard, d = demo</p>
        <div className="dash-bar-chart">
          {data.dailyCosts.map((d) => (
            <CostBar key={d.date} data={d} maxCost={maxCost} />
          ))}
        </div>
      </div>

      {/* ---- DEMO GOALS (market signal) ---- */}
      {data.demo.recentGoals.length > 0 && (
        <div className="dash-section">
          <h2>What people type into the demo</h2>
          <p className="dash-section-sub">First messages — raw market signal</p>
          <div className="dash-goals">
            {data.demo.recentGoals.map((goal, i) => (
              <div key={i} className="dash-goal">{goal}</div>
            ))}
          </div>
        </div>
      )}

      <div className="dash-two-col">
        <div className="dash-section">
          <h2>Models</h2>
          <div className="dash-models">
            {Object.entries(data.models).map(([model, count]) => (
              <span key={model} className="dash-model">
                {model} <span className="dash-model-count">{count}</span>
              </span>
            ))}
            {Object.keys(data.models).length === 0 && <span className="dash-muted">No data yet</span>}
          </div>
        </div>
        <div className="dash-section">
          <h2>Tokens (recent 100 obs)</h2>
          <div className="dash-card-stats" style={{ gap: 24 }}>
            <Stat label="in" value={formatTokens(data.tokens.in)} />
            <Stat label="out" value={formatTokens(data.tokens.out)} />
            <Stat label="total" value={formatTokens(data.tokens.in + data.tokens.out)} />
          </div>
        </div>
      </div>

      {/* ---- RECENT DEMO TRACES ---- */}
      {data.recentDemos.length > 0 && (
        <div className="dash-section">
          <h2>Recent demo traces</h2>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Goal</th>
                  <th>Breakdown?</th>
                  <th>Turn</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {data.recentDemos.map((t) => (
                  <tr key={t.id}>
                    <td className="dash-mono">{formatTime(t.timestamp)}</td>
                    <td className="dash-goal-cell">{t.goalText || <span className="dash-muted">-</span>}</td>
                    <td>{t.toolFired ? <span className="dash-state dash-state-completed">yes</span> : <span className="dash-state dash-state-exploring">no</span>}</td>
                    <td className="dash-mono">{t.turnNumber}</td>
                    <td className="dash-mono">${t.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---- RECENT ONBOARD TRACES ---- */}
      <div className="dash-section">
        <h2>Recent onboard traces</h2>
        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>State</th>
                <th>Type</th>
                <th>Cost</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {data.recentOnboards.map((t) => (
                <tr key={t.id}>
                  <td className="dash-mono">{formatTime(t.timestamp)}</td>
                  <td className="dash-mono">{t.userId.slice(0, 8)}</td>
                  <td><span className={`dash-state dash-state-${t.cascadeState}`}>{t.cascadeState}</span></td>
                  <td>
                    {t.isRevision
                      ? <span className="dash-state dash-state-revision">rev:{t.revisionTarget}</span>
                      : <span className="dash-muted">normal</span>
                    }
                  </td>
                  <td className="dash-mono">${t.cost}</td>
                  <td className="dash-mono">{t.latency ? `${t.latency}ms` : "-"}</td>
                </tr>
              ))}
              {data.recentOnboards.length === 0 && (
                <tr><td colSpan={6} className="dash-muted">No traces yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function PostHogDashboard({ data, loading, error }) {
  if (loading) {
    return <div className="dash-loading"><div className="dash-spinner" /><span>Pulling from PostHog...</span></div>;
  }
  if (error) {
    return <p className="dash-error">PostHog error: {error}</p>;
  }
  if (!data) return null;

  return (
    <>
      {/* Overview */}
      <div className="dash-cards">
        <div className="dash-card">
          <h2>Events (recent 100)</h2>
          <div className="dash-card-stats">
            <Stat label="total" value={data.totalEvents} />
            <Stat label="custom" value={data.customEvents.length} />
          </div>
        </div>
        <div className="dash-card">
          <h2>Persons</h2>
          <div className="dash-card-stats">
            <Stat label="real" value={data.realPersons} accent />
            <Stat label="test/mock" value={data.testPersons} />
            <Stat label="total" value={data.totalPersons} />
          </div>
        </div>
      </div>

      {/* Event breakdown */}
      <div className="dash-section">
        <h2>Event types</h2>
        <div className="dash-models">
          {Object.entries(data.eventCounts)
            .sort(([, a], [, b]) => b - a)
            .map(([event, count]) => (
              <span key={event} className="dash-model">
                {event} <span className="dash-model-count">{count}</span>
              </span>
            ))}
        </div>
      </div>

      {/* Page breakdown */}
      {Object.keys(data.pageCounts).length > 0 && (
        <div className="dash-section">
          <h2>Pages visited</h2>
          <div className="dash-models">
            {Object.entries(data.pageCounts)
              .sort(([, a], [, b]) => b - a)
              .map(([page, count]) => (
                <span key={page} className="dash-model">
                  {page} <span className="dash-model-count">{count}</span>
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Custom events */}
      {data.customEvents.length > 0 && (
        <div className="dash-section">
          <h2>Custom events</h2>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event</th>
                  <th>Properties</th>
                  <th>Person</th>
                </tr>
              </thead>
              <tbody>
                {data.customEvents.map((e, i) => (
                  <tr key={i}>
                    <td className="dash-mono">{formatTime(e.timestamp)}</td>
                    <td><span className="dash-state dash-state-completed">{e.event}</span></td>
                    <td className="dash-goal-cell">{Object.keys(e.properties).length > 0 ? JSON.stringify(e.properties) : <span className="dash-muted">-</span>}</td>
                    <td className="dash-mono">{e.person}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Persons */}
      <div className="dash-section">
        <h2>Persons</h2>
        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Location</th>
                <th>OS / Browser</th>
                <th>First seen</th>
              </tr>
            </thead>
            <tbody>
              {data.users.map((u, i) => (
                <tr key={i}>
                  <td>{u.email || <span className="dash-mono">{String(u.distinctIds[0]).slice(0, 16)}</span>}</td>
                  <td>{u.email ? <span className="dash-muted">{String(u.distinctIds[0]).slice(0, 12)}</span> : <span className="dash-muted">anonymous</span>}</td>
                  <td>{[u.city, u.country].filter(Boolean).join(", ") || <span className="dash-muted">-</span>}</td>
                  <td className="dash-mono">{[u.os, u.browser].filter(Boolean).join(" / ") || "-"}</td>
                  <td className="dash-mono">{formatTime(u.createdAt)}</td>
                </tr>
              ))}
              {data.users.length === 0 && (
                <tr><td colSpan={5} className="dash-muted">No persons yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent pageviews */}
      <div className="dash-section">
        <h2>Recent pageviews</h2>
        <div className="dash-table-wrap">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Page</th>
                <th>Person</th>
              </tr>
            </thead>
            <tbody>
              {data.pageviews.map((pv, i) => (
                <tr key={i}>
                  <td className="dash-mono">{formatTime(pv.timestamp)}</td>
                  <td className="dash-goal-cell">{pv.url}</td>
                  <td className="dash-mono">{pv.person}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function formatTokens(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function formatTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;
  if (diff < 60_000) return "just now";
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
