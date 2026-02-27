"use client";

import { useState } from "react";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BOT_USERNAME = process.env.NEXT_PUBLIC_TELEGRAM_BOT || "CascadeCoachBot";

const STEPS = ["signup", "goal", "plan", "telegram"];

export default function OnboardingFlow() {
  const [step, setStep] = useState("signup");
  const [user, setUser] = useState(null);
  const [tenantId, setTenantId] = useState(null);
  const [goalId, setGoalId] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [telegramToken, setTelegramToken] = useState(null);
  const [error, setError] = useState(null);

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [goal, setGoal] = useState({
    title: "",
    description: "",
    success_criteria: "",
    target_date: "",
    current_state: "",
    core_hours: 10,
    flex_hours: 4,
  });

  async function handleSignup(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });
      if (authError) throw authError;
      setUser(data.user);
      setStep("goal");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoalSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/onboard/goal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id, ...goal }),
      });
      const data = await res.json();
      setTenantId(data.tenant_id);
      setGoalId(data.goal_id);

      // Generate cascade plan
      const planRes = await fetch(`${API_URL}/api/onboard/generate-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_id: data.tenant_id,
          goal_id: data.goal_id,
          api_key: "",
        }),
      });
      const planData = await planRes.json();
      setPlan(planData.plan);
      setStep("plan");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handlePlanApproved() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/onboard/generate-telegram-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id }),
      });
      const data = await res.json();
      setTelegramToken(data.token);
      setStep("telegram");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const telegramLink = telegramToken
    ? `https://t.me/${BOT_USERNAME}?start=${telegramToken}`
    : "#";

  return (
    <div className="max-w-xl mx-auto px-6 py-16">
      {/* Progress bar */}
      <div className="flex gap-2 mb-12">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded ${STEPS.indexOf(step) >= i ? "bg-red-500" : "bg-zinc-800"}`}
          />
        ))}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Step 1: Sign Up */}
      {step === "signup" && (
        <form onSubmit={handleSignup}>
          <h1 className="text-3xl font-bold mb-2">Create your account</h1>
          <p className="text-zinc-400 mb-8">
            Free to start. No credit card needed.
          </p>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-4 text-white"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            required
            minLength={8}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-6 text-white"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded transition-colors disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Get Started"}
          </button>
        </form>
      )}

      {/* Step 2: Define Goal */}
      {step === "goal" && (
        <form onSubmit={handleGoalSubmit}>
          <h1 className="text-3xl font-bold mb-2">Define your goal</h1>
          <p className="text-zinc-400 mb-8">
            Be specific. &quot;Run a marathon by October&quot; is better than
            &quot;get fit.&quot;
          </p>

          <label className="block text-sm text-zinc-400 mb-1">
            What&apos;s your main goal?
          </label>
          <input
            type="text"
            value={goal.title}
            onChange={(e) => setGoal({ ...goal, title: e.target.value })}
            placeholder="e.g. Launch my SaaS and hit $500 MRR"
            required
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-4 text-white"
          />

          <label className="block text-sm text-zinc-400 mb-1">
            What does success look like?
          </label>
          <input
            type="text"
            value={goal.success_criteria}
            onChange={(e) =>
              setGoal({ ...goal, success_criteria: e.target.value })
            }
            placeholder="e.g. 13 paying customers at $39/mo"
            required
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-4 text-white"
          />

          <label className="block text-sm text-zinc-400 mb-1">
            Where are you starting from?
          </label>
          <textarea
            value={goal.current_state}
            onChange={(e) =>
              setGoal({ ...goal, current_state: e.target.value })
            }
            placeholder="Be honest — Cascade plans better with real data."
            required
            rows={2}
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-4 text-white"
          />

          <label className="block text-sm text-zinc-400 mb-1">
            Target date
          </label>
          <input
            type="date"
            value={goal.target_date}
            onChange={(e) =>
              setGoal({ ...goal, target_date: e.target.value })
            }
            required
            className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 mb-4 text-white"
          />

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <label className="block text-sm text-zinc-400 mb-1">
                Core hours/week
              </label>
              <p className="text-xs text-zinc-500 mb-2">
                The floor. Your plan succeeds on Core alone.
              </p>
              <input
                type="number"
                value={goal.core_hours}
                onChange={(e) =>
                  setGoal({ ...goal, core_hours: parseInt(e.target.value) })
                }
                min={1}
                max={60}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1">
                Flex hours/week
              </label>
              <p className="text-xs text-zinc-500 mb-2">
                Bonus. Reach for these when energy allows.
              </p>
              <input
                type="number"
                value={goal.flex_hours}
                onChange={(e) =>
                  setGoal({ ...goal, flex_hours: parseInt(e.target.value) })
                }
                min={0}
                max={40}
                className="w-full bg-zinc-900 border border-zinc-700 rounded px-4 py-3 text-white"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded transition-colors disabled:opacity-50"
          >
            {loading ? "Generating your plan..." : "Generate My Plan"}
          </button>
        </form>
      )}

      {/* Step 3: Review Plan */}
      {step === "plan" && plan && (
        <div>
          <h1 className="text-3xl font-bold mb-2">Your Cascade Plan</h1>
          <p className="text-zinc-400 mb-8">
            Review your plan. This is your starting point — it adapts as you go.
          </p>

          <div className="bg-zinc-900 border border-zinc-700 rounded p-6 mb-6">
            <h3 className="text-sm text-zinc-400 uppercase tracking-wider mb-2">
              Year Overview
            </h3>
            <p className="text-white">{plan.year_plan}</p>
          </div>

          {plan.quarterly_milestones?.length > 0 && (
            <div className="bg-zinc-900 border border-zinc-700 rounded p-6 mb-6">
              <h3 className="text-sm text-zinc-400 uppercase tracking-wider mb-3">
                Quarterly Milestones
              </h3>
              {plan.quarterly_milestones.map((q, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <p className="text-white font-medium">
                    Q{q.quarter}: {q.description}
                  </p>
                </div>
              ))}
            </div>
          )}

          {plan.weekly_tasks && (
            <div className="bg-zinc-900 border border-zinc-700 rounded p-6 mb-6">
              <h3 className="text-sm text-zinc-400 uppercase tracking-wider mb-3">
                This Week
              </h3>
              <p className="text-xs text-zinc-500 mb-3">
                Core tasks — the plan. Flex tasks — acceleration.
              </p>
              {plan.weekly_tasks.core?.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 py-2 border-b border-zinc-800 last:border-0"
                >
                  <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">
                    Core
                  </span>
                  <span className="text-white">{t.title}</span>
                </div>
              ))}
              {plan.weekly_tasks.flex?.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 py-2 border-b border-zinc-800 last:border-0"
                >
                  <span className="text-xs bg-zinc-700 text-zinc-400 px-2 py-0.5 rounded">
                    Flex
                  </span>
                  <span className="text-zinc-300">{t.title}</span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handlePlanApproved}
            disabled={loading}
            className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-3 rounded transition-colors disabled:opacity-50"
          >
            {loading ? "Generating secure link..." : "Approve Plan & Connect Telegram"}
          </button>
        </div>
      )}

      {/* Step 4: Connect Telegram */}
      {step === "telegram" && (
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-2">Connect Telegram</h1>
          <p className="text-zinc-400 mb-8">
            Tap the button below to connect your Telegram. NanoClaw will send
            your first tasks tomorrow morning.
          </p>

          <a
            href={telegramLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-[#0088cc] hover:bg-[#006da3] text-white font-semibold py-4 px-8 rounded-lg text-lg transition-colors mb-8"
          >
            Open in Telegram
          </a>

          <div className="bg-zinc-900 border border-zinc-700 rounded p-6 text-left">
            <h3 className="text-sm text-zinc-400 uppercase tracking-wider mb-3">
              What happens next
            </h3>
            <ul className="space-y-2 text-zinc-300">
              <li>Every morning: your Core tasks for the day</li>
              <li>
                Every evening: &quot;How&apos;d today go?&quot; — reply to log
                progress
              </li>
              <li>Sundays: weekly review with stats and coaching</li>
              <li>Text anytime to log progress or check status</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
