"use client";

import { useState } from "react";

const CARD_CONFIGS = {
  goal_summary: {
    title: "Goal Summary",
    color: "#EF4444",
  },
  year_plan: {
    title: "Year Plan",
    color: "#EF4444",
  },
  quarter_plan: {
    title: "Quarterly Milestones",
    color: "#F87171",
  },
  month_plan: {
    title: "Monthly Targets",
    color: "#FB923C",
  },
  week_plan: {
    title: "Week Plan",
    color: "#F59E0B",
  },
};

function GoalSummaryContent({ data }) {
  if (!data) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div>
        <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Goal</div>
        <div style={{ color: "#F8FAFC", fontSize: 15, fontWeight: 600 }}>{data.title || "Untitled"}</div>
      </div>
      {data.success_criteria && (
        <div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Success Criteria</div>
          <div style={{ color: "#F8FAFC", fontSize: 13 }}>{data.success_criteria}</div>
        </div>
      )}
      {data.current_state && (
        <div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Starting From</div>
          <div style={{ color: "#94A3B8", fontSize: 13 }}>{data.current_state}</div>
        </div>
      )}
      <div style={{ display: "flex", gap: 16 }}>
        {data.target_date && (
          <div>
            <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Target Date</div>
            <div style={{ color: "#F8FAFC", fontSize: 13 }}>{data.target_date}</div>
          </div>
        )}
        {(data.core_hours != null || data.flex_hours != null) && (
          <div>
            <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Core / Flex</div>
            <div style={{ color: "#F8FAFC", fontSize: 13 }}>{data.core_hours ?? 0}h / {data.flex_hours ?? 0}h per week</div>
          </div>
        )}
      </div>
      {data.feasibility_notes && (
        <div style={{ background: "rgba(248,113,113,0.06)", border: "1px solid rgba(248,113,113,0.15)", borderRadius: 8, padding: "10px 14px" }}>
          <div style={{ color: "#F87171", fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Feasibility</div>
          <div style={{ color: "#94A3B8", fontSize: 12, lineHeight: 1.5 }}>{data.feasibility_notes}</div>
        </div>
      )}
    </div>
  );
}

function YearPlanContent({ data }) {
  if (!data) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.success_criteria && (
        <div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>Success Criteria</div>
          <div style={{ color: "#F8FAFC", fontSize: 13 }}>{data.success_criteria}</div>
        </div>
      )}
      {data.quarterly_arc?.map((q, i) => (
        <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 0", borderBottom: i < (data.quarterly_arc?.length ?? 0) - 1 ? "1px solid #2A1F22" : "none" }}>
          <span style={{ background: "#EF4444", color: "#fff", fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 4, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{q.quarter}</span>
          <div>
            <div style={{ color: "#F8FAFC", fontSize: 13, fontWeight: 600 }}>{q.focus}</div>
            <div style={{ color: "#94A3B8", fontSize: 12, marginTop: 2 }}>{q.milestone}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function QuarterPlanContent({ data }) {
  if (!data) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {data.quarters?.map((q, i) => (
        <div key={i} style={{ borderBottom: i < (data.quarters?.length ?? 0) - 1 ? "1px solid #2A1F22" : "none", paddingBottom: i < (data.quarters?.length ?? 0) - 1 ? 16 : 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <span style={{ background: "#F87171", color: "#fff", fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 4, fontFamily: "'JetBrains Mono', monospace" }}>{q.quarter}</span>
            <span style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>{q.months}</span>
          </div>
          {q.milestones?.map((m, j) => (
            <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 4 }}>
              <span style={{ color: "#F87171", fontSize: 10, marginTop: 4, flexShrink: 0 }}>▸</span>
              <span style={{ color: "#F8FAFC", fontSize: 12.5, lineHeight: 1.5 }}>{m}</span>
            </div>
          ))}
          {q.success_criteria && (
            <div style={{ color: "#8E9DB0", fontSize: 11, fontStyle: "italic", marginTop: 6 }}>Done when: {q.success_criteria}</div>
          )}
        </div>
      ))}
    </div>
  );
}

function MonthPlanContent({ data }) {
  if (!data) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ color: "#F8FAFC", fontSize: 14, fontWeight: 600 }}>{data.month || "This Month"}{data.year ? ` ${data.year}` : ""}</div>
      {data.targets?.map((t, i) => (
        <div key={i} style={{ background: "rgba(248,113,113,0.03)", border: "1px solid #2A1F22", borderRadius: 8, padding: "12px 14px" }}>
          <div style={{ color: "#F8FAFC", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{t.target}</div>
          {t.metric && <div style={{ color: "#8E9DB0", fontSize: 11 }}>Metric: {t.metric}</div>}
          {t.definition_of_done && <div style={{ color: "#94A3B8", fontSize: 11, marginTop: 2 }}>Done when: {t.definition_of_done}</div>}
        </div>
      ))}
    </div>
  );
}

function WeekPlanContent({ data }) {
  if (!data) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {data.week_of && <div style={{ color: "#F8FAFC", fontSize: 14, fontWeight: 600 }}>Week of {data.week_of}</div>}
      {data.core_tasks?.length > 0 && (
        <div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Core Tasks</div>
          {data.core_tasks.map((t, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "1px solid rgba(42,31,34,0.5)" }}>
              <span style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444", fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>Core</span>
              <span style={{ color: "#F8FAFC", fontSize: 12.5, flex: 1 }}>{t.title}</span>
              {t.duration_hours != null && <span style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{t.duration_hours}h</span>}
              {t.day && <span style={{ color: "#8E9DB0", fontSize: 10, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{t.day}</span>}
            </div>
          ))}
        </div>
      )}
      {data.flex_tasks?.length > 0 && (
        <div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Flex Tasks</div>
          {data.flex_tasks.map((t, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "1px solid rgba(42,31,34,0.3)" }}>
              <span style={{ background: "rgba(142,157,176,0.1)", color: "#8E9DB0", fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>Flex</span>
              <span style={{ color: "#94A3B8", fontSize: 12.5, flex: 1 }}>{t.title}</span>
              {t.duration_hours != null && <span style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>{t.duration_hours}h</span>}
            </div>
          ))}
        </div>
      )}
      {(data.total_core_hours != null || data.total_flex_hours != null) && (
        <div style={{ display: "flex", gap: 16, marginTop: 4 }}>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>Core: {data.total_core_hours ?? 0}h</div>
          <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>Flex: {data.total_flex_hours ?? 0}h</div>
        </div>
      )}
    </div>
  );
}

const CONTENT_RENDERERS = {
  goal_summary: GoalSummaryContent,
  year_plan: YearPlanContent,
  quarter_plan: QuarterPlanContent,
  month_plan: MonthPlanContent,
  week_plan: WeekPlanContent,
};

export default function CascadePlanCard({ cardType, data, active, approved, onApprove, onRequestChanges }) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");
  const config = CARD_CONFIGS[cardType] || CARD_CONFIGS.goal_summary;
  const ContentRenderer = CONTENT_RENDERERS[cardType];

  return (
    <div
      style={{
        padding: "0 4px",
        marginBottom: 16,
        opacity: approved && !active ? 0.5 : 1,
        transition: "opacity 0.3s ease",
        animation: active ? "cascadeFadeUp 0.4s ease both" : "none",
      }}
    >
      <div
        style={{
          background: "rgba(248,113,113,0.03)",
          border: `1px solid ${active ? config.color + "40" : "#2A1F22"}`,
          borderRadius: 12,
          overflow: "hidden",
          transition: "border-color 0.3s ease",
        }}
      >
        {/* Header */}
        <div style={{ padding: "12px 20px", borderBottom: "1px solid #2A1F22", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ background: config.color, color: "#fff", fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", padding: "3px 8px", borderRadius: 4, fontFamily: "'JetBrains Mono', monospace" }}>
              {config.title}
            </span>
            {approved && (
              <span style={{ color: "#4ADE80", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>Approved</span>
            )}
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: "16px 20px" }}>
          {ContentRenderer && <ContentRenderer data={data} />}
        </div>

        {/* Action buttons — only show when active and not yet approved */}
        {active && !approved && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid #2A1F22" }}>
            {!showFeedback ? (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={() => onApprove?.(cardType, data)}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "none",
                    background: "#EF4444",
                    color: "#fff",
                    fontSize: 13,
                    fontWeight: 600,
                    fontFamily: "'Outfit', sans-serif",
                    cursor: "pointer",
                  }}
                >
                  Approve
                </button>
                <button
                  onClick={() => setShowFeedback(true)}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "1px solid #2A1F22",
                    background: "transparent",
                    color: "#8E9DB0",
                    fontSize: 13,
                    fontWeight: 500,
                    fontFamily: "'Outfit', sans-serif",
                    cursor: "pointer",
                  }}
                >
                  Request Changes
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="What would you like to change?"
                  rows={2}
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: 8,
                    border: "1px solid #2A1F22",
                    background: "#1A1215",
                    color: "#F8FAFC",
                    fontSize: 13,
                    fontFamily: "'Outfit', sans-serif",
                    resize: "none",
                    outline: "none",
                  }}
                  autoFocus
                />
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => {
                      if (feedback.trim()) {
                        onRequestChanges?.(cardType, feedback.trim());
                        setFeedback("");
                        setShowFeedback(false);
                      }
                    }}
                    disabled={!feedback.trim()}
                    style={{
                      flex: 1,
                      padding: "8px 14px",
                      borderRadius: 8,
                      border: "none",
                      background: feedback.trim() ? "#EF4444" : "rgba(239,68,68,0.2)",
                      color: "#fff",
                      fontSize: 13,
                      fontWeight: 600,
                      fontFamily: "'Outfit', sans-serif",
                      cursor: feedback.trim() ? "pointer" : "default",
                    }}
                  >
                    Send Feedback
                  </button>
                  <button
                    onClick={() => { setShowFeedback(false); setFeedback(""); }}
                    style={{
                      padding: "8px 14px",
                      borderRadius: 8,
                      border: "1px solid #2A1F22",
                      background: "transparent",
                      color: "#8E9DB0",
                      fontSize: 13,
                      fontFamily: "'Outfit', sans-serif",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
