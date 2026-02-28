"use client";

import { useState } from "react";
import posthog from "posthog-js";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  "https://gwqvkbxrrvswyczhqkdb.supabase.co",
  "sb_publishable_-TbjuoH7I4z1jl3FOULdJQ_nioKng7r"
);

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function WaitlistForm({ id = "hero", children }) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = email.trim();

    if (!isValidEmail(trimmed)) {
      setError("Enter a valid email address.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const { error: sbError } = await supabase
        .from("waitlist")
        .insert({ email: trimmed, source: "landing" });

      if (sbError) {
        if (sbError.code === "23505") {
          setSuccess({ duplicate: true });
          posthog.capture("waitlist_joined", { source: id, duplicate: true });
          return;
        }
        throw new Error(sbError.message);
      }
      setSuccess({ duplicate: false });
      posthog.capture("waitlist_joined", { source: id });
    } catch (err) {
      setLoading(false);
      setError("Something went wrong. Try again.");
    }
  }

  if (success) {
    return (
      <div className="success-msg">
        <h3>
          {success.duplicate
            ? "You\u2019re already on the list."
            : "You\u2019re on the list."}
        </h3>
        <p>
          {success.duplicate
            ? "We\u2019ve got your email. We\u2019ll reach out when it\u2019s time."
            : "We\u2019ll reach out when Cascade is ready. Talk soon."}
        </p>
      </div>
    );
  }

  return (
    <>
      <form
        className="waitlist-form"
        onSubmit={handleSubmit}
        aria-label={
          id === "hero" ? "Get early access" : "Join the waitlist"
        }
      >
        <label htmlFor={`${id}-email`} className="sr-only">
          Email address
        </label>
        <input
          type="email"
          id={`${id}-email`}
          name="email"
          placeholder="you@example.com"
          required
          autoComplete="email"
          className={error ? "error" : ""}
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setError("");
          }}
        />
        <button
          type="submit"
          className={`btn${loading ? " btn-loading" : ""}`}
          disabled={loading}
        >
          <span className="btn-text">Get early access</span>
          <span className="btn-spinner" aria-hidden="true"></span>
        </button>
        <span
          className={`form-error${error ? " show" : ""}`}
          role="alert"
        >
          {error}
        </span>
      </form>
      {children}
    </>
  );
}
