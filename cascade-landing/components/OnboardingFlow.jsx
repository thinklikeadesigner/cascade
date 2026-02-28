"use client";

import { useState } from "react";
import { createClient } from "@supabase/supabase-js";

let _supabase;
function getSupabase() {
  if (!_supabase) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) throw new Error("Supabase configuration missing");
    _supabase = createClient(url, key);
  }
  return _supabase;
}

const STEPS = ["signup"];

export default function OnboardingFlow() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSignup(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // Try signup first
      const { data, error: authError } = await getSupabase().auth.signUp({
        email,
        password,
      });

      // If signup returned a fake user (email already exists) or failed, try sign in
      if (authError || !data.user?.identities?.length) {
        const { data: signInData, error: signInError } =
          await getSupabase().auth.signInWithPassword({ email, password });
        if (signInError) throw signInError;
      }
      window.location.href = "/onboard/chat";
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl mx-auto px-6 py-16">
      {/* Progress bar */}
      <div className="flex gap-2 mb-12">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className="h-1 flex-1 rounded bg-red-500"
          />
        ))}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Step 1: Sign Up */}
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
    </div>
  );
}
