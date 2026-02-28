"use client";

import { useState, useEffect } from "react";
import { createClient } from "@supabase/supabase-js";
import { loadConversation, createConversation } from "@/lib/conversations";

let _supabase;
function getSupabase() {
  if (!_supabase) {
    _supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    );
  }
  return _supabase;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT || "CascadeCoachBot";

export default function OnboardChatPage() {
  const [user, setUser] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completed, setCompleted] = useState(false);
  const [telegramLink, setTelegramLink] = useState(null);
  const [OnboardingChat, setOnboardingChat] = useState(null);

  // Dynamically import OnboardingChat to avoid module-level Supabase init during SSR
  useEffect(() => {
    import("@/components/OnboardingChat").then((mod) => {
      setOnboardingChat(() => mod.default);
    });
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const { data: { user: authUser } } = await getSupabase().auth.getUser();

        if (!authUser) {
          window.location.href = "/onboard";
          return;
        }

        setUser(authUser);

        let conv = await loadConversation(getSupabase(), authUser.id);
        if (!conv) {
          conv = await createConversation(getSupabase(), authUser.id);
        }

        setConversation(conv);
      } catch (err) {
        console.error("Init error:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  async function handleComplete(planData) {
    setCompleted(true);

    try {
      // Send only fields the FastAPI endpoint expects — avoid Pydantic validation errors
      const goalPayload = {
        user_id: user.id,
        title: planData.goal_summary?.title || "",
        description: "",
        success_criteria: planData.goal_summary?.success_criteria || "",
        current_state: planData.goal_summary?.current_state || "",
        target_date: planData.goal_summary?.target_date || "",
        core_hours: planData.goal_summary?.core_hours || 10,
        flex_hours: planData.goal_summary?.flex_hours || 4,
      };

      const res = await fetch(`${API_URL}/api/onboard/goal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(goalPayload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Goal creation failed (${res.status})`);
      }

      const goalData = await res.json();

      // Generate plan with the full plan_data
      const planRes = await fetch(`${API_URL}/api/onboard/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: goalData.tenant_id,
          goal_id: goalData.goal_id,
          plan_data: planData,
          api_key: "",
        }),
      });

      if (!planRes.ok) {
        console.warn("Plan generation failed, continuing to Telegram setup");
      }

      // Generate Telegram link
      const linkRes = await fetch(`${API_URL}/api/onboard/generate-telegram-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id }),
      });

      if (!linkRes.ok) {
        throw new Error("Failed to generate Telegram link");
      }

      const linkData = await linkRes.json();
      setTelegramLink(`https://t.me/${BOT_USERNAME}?start=${linkData.token}`);
    } catch (err) {
      console.error("Completion error:", err);
      setError(err.message);
    }
  }

  if (loading || !OnboardingChat) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0D0B0E", color: "#8E9DB0", fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
        Loading your conversation...
      </div>
    );
  }

  if (error && !completed) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0D0B0E", padding: 20 }}>
        <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#F87171", padding: "16px 24px", borderRadius: 12, maxWidth: 400, textAlign: "center", fontFamily: "'Outfit', sans-serif", fontSize: 14 }}>
          <div style={{ marginBottom: 12 }}>{error}</div>
          <button
            onClick={() => window.location.reload()}
            style={{ background: "#EF4444", color: "#fff", border: "none", padding: "8px 20px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Telegram connect screen (after plan completion)
  if (completed && telegramLink) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0D0B0E", padding: 20 }}>
        <div style={{ maxWidth: 440, textAlign: "center", fontFamily: "'Outfit', sans-serif" }}>
          <h1 style={{ color: "#F8FAFC", fontSize: 28, fontWeight: 700, marginBottom: 8 }}>Connect Telegram</h1>
          <p style={{ color: "#8E9DB0", fontSize: 15, marginBottom: 32 }}>
            Tap the button below to connect your Telegram. NanoClaw will send your first tasks tomorrow morning.
          </p>
          <a
            href={telegramLink}
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: "inline-block", background: "#0088cc", color: "#fff", fontWeight: 600, padding: "16px 32px", borderRadius: 12, fontSize: 16, textDecoration: "none", fontFamily: "'Outfit', sans-serif", marginBottom: 32 }}
          >
            Open in Telegram
          </a>
          <div style={{ background: "#1A1215", border: "1px solid #2A1F22", borderRadius: 12, padding: 24, textAlign: "left" }}>
            <h3 style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
              What happens next
            </h3>
            <ul style={{ color: "#94A3B8", fontSize: 14, lineHeight: 2, listStyle: "none", padding: 0, margin: 0 }}>
              <li>Every morning: your Core tasks for the day</li>
              <li>Every evening: &quot;How&apos;d today go?&quot; — reply to log progress</li>
              <li>Sundays: weekly review with stats and coaching</li>
              <li>Text anytime to log progress or check status</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  if (completed && !telegramLink) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0D0B0E" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#8E9DB0", fontFamily: "'JetBrains Mono', monospace", fontSize: 13, marginBottom: 8 }}>
            Setting up your account...
          </div>
          {error && (
            <div style={{ color: "#F87171", fontSize: 13, marginTop: 12 }}>{error}</div>
          )}
        </div>
      </div>
    );
  }

  if (!conversation) return null;

  return (
    <div style={{ height: "100vh", background: "#0D0B0E" }}>
      <OnboardingChat
        conversation={conversation}
        onComplete={handleComplete}
      />
    </div>
  );
}
