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

export default function OnboardingFlow() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSignup(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data, error: authError } = await getSupabase().auth.signUp({
        email,
        password,
      });

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
    <div className="onboard-wrap">
      <h1>Create your account</h1>
      <p className="onboard-sub">
        Free to start. No credit card needed.
      </p>

      {error && <div className="onboard-error">{error}</div>}

      <form onSubmit={handleSignup}>
        <div className="onboard-field">
          <label className="onboard-label" htmlFor="onboard-email">
            Email
          </label>
          <input
            id="onboard-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            className="onboard-input"
          />
        </div>

        <div className="onboard-field">
          <label className="onboard-label" htmlFor="onboard-password">
            Password
          </label>
          <input
            id="onboard-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="8+ characters"
            required
            minLength={8}
            className="onboard-input"
          />
        </div>

        <button type="submit" disabled={loading} className="onboard-btn">
          {loading ? (
            <>
              <span className="onboard-spinner" />
              Creating account...
            </>
          ) : (
            "Get Started"
          )}
        </button>
      </form>

      <p className="onboard-footer">
        Already have an account? Enter your credentials above.
      </p>
    </div>
  );
}
