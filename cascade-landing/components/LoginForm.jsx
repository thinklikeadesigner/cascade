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

export default function LoginForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { error: signInError } =
        await getSupabase().auth.signInWithPassword({ email, password });
      if (signInError) {
        if (signInError.message === "Invalid login credentials") {
          throw new Error("Wrong email or password. Please try again.");
        }
        if (signInError.message === "Email not confirmed") {
          throw new Error("Please confirm your email before logging in. Check your inbox.");
        }
        throw signInError;
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
      <h1>Welcome back</h1>
      <p className="onboard-sub">
        Log in to continue your plan.
      </p>

      {error && <div className="onboard-error">{error}</div>}

      <form onSubmit={handleLogin}>
        <div className="onboard-field">
          <label className="onboard-label" htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            className="onboard-input"
          />
        </div>

        <div className="onboard-field">
          <label className="onboard-label" htmlFor="login-password">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Your password"
            required
            className="onboard-input"
          />
        </div>

        <button type="submit" disabled={loading} className="onboard-btn">
          {loading ? (
            <>
              <span className="onboard-spinner" />
              Logging in...
            </>
          ) : (
            "Log In"
          )}
        </button>
      </form>

      <p className="onboard-footer">
        Don&apos;t have an account?{" "}
        <a href="/onboard" className="onboard-link">Sign up</a>
      </p>
    </div>
  );
}
