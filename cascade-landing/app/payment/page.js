"use client";

import { useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import posthog from "posthog-js";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function PaymentContent() {
  const params = useSearchParams();
  const tenantId = params.get("tenant");
  const [loading, setLoading] = useState(false);

  async function handleCheckout(plan) {
    setLoading(true);
    posthog.capture("checkout_started", { plan });
    const res = await fetch(`${API_URL}/api/payment/create-checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_id: tenantId, plan }),
    });
    const data = await res.json();
    window.location.href = data.checkout_url;
  }

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        <h1 className="text-3xl font-bold mb-2">Keep using Cascade</h1>
        <p className="text-zinc-400 mb-8">
          Your free trial is ending. Pick a plan to continue.
        </p>

        <button
          onClick={() => handleCheckout("founding")}
          disabled={loading}
          className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold py-4 rounded-lg mb-4 transition-colors disabled:opacity-50"
        >
          <span className="text-lg">Founding Member — $29/mo</span>
          <span className="block text-sm text-red-200 mt-1">
            Locked in forever. Limited spots.
          </span>
        </button>

        <button
          onClick={() => handleCheckout("standard")}
          disabled={loading}
          className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-semibold py-4 rounded-lg transition-colors disabled:opacity-50"
        >
          <span className="text-lg">Standard — $49/mo</span>
        </button>
      </div>
    </div>
  );
}

export default function PaymentPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-black text-white flex items-center justify-center">
          Loading...
        </div>
      }
    >
      <PaymentContent />
    </Suspense>
  );
}
