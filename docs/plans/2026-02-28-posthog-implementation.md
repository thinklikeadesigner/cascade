# PostHog Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire PostHog analytics into Cascade's frontend (Next.js) and finish the partially-started backend (FastAPI) integration.

**Architecture:** Frontend uses `posthog-js` loaded lazily via a React provider. Backend already has `posthog_client.py` with `track_event()` — we add missing events and proper shutdown. Both sides share the same PostHog project, linked by `user_id` as `distinct_id`.

**Tech Stack:** posthog-js (frontend), posthog Python SDK (backend, already installed), Next.js App Router, FastAPI

---

### Task 1: Install posthog-js and add env var

**Files:**
- Modify: `cascade-landing/package.json`
- Modify: `cascade-landing/.env.example`

**Step 1: Install posthog-js**

Run: `cd /Users/k2/Desktop/moltathon/cascade/cascade-landing && npm install posthog-js`

**Step 2: Add env var to .env.example**

Add to `cascade-landing/.env.example`:
```
# PostHog (client-side analytics)
NEXT_PUBLIC_POSTHOG_KEY=phc_...
```

**Step 3: Add the actual key to .env.local**

Run: `echo "NEXT_PUBLIC_POSTHOG_KEY=<your-key>" >> cascade-landing/.env.local`

(User must provide their actual key)

**Step 4: Commit**

```bash
git add cascade-landing/package.json cascade-landing/package-lock.json cascade-landing/.env.example
git commit -m "feat: add posthog-js dependency and env var"
```

---

### Task 2: Create PostHogProvider component

**Files:**
- Create: `cascade-landing/components/PostHogProvider.jsx`

**Step 1: Create the provider**

```jsx
"use client";

import { useEffect } from "react";
import posthog from "posthog-js";
import { usePathname, useSearchParams } from "next/navigation";

export default function PostHogProvider({ children }) {
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) return;

    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
      api_host: "https://us.i.posthog.com",
      capture_pageview: false, // we handle SPA page views manually
      capture_pageleave: true,
      persistence: "localStorage",
    });
  }, []);

  // Track SPA page views on route change
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!pathname || !posthog.__loaded) return;
    const url = searchParams.toString()
      ? `${pathname}?${searchParams.toString()}`
      : pathname;
    posthog.capture("$pageview", { $current_url: url });
  }, [pathname, searchParams]);

  return children;
}
```

**Step 2: Commit**

```bash
git add cascade-landing/components/PostHogProvider.jsx
git commit -m "feat: add PostHog provider with SPA page view tracking"
```

---

### Task 3: Add PostHogProvider to layout.js

**Files:**
- Modify: `cascade-landing/app/layout.js`

**Step 1: Wrap children in PostHogProvider**

The layout is a server component. We need to wrap children in a Suspense boundary (required because PostHogProvider uses `useSearchParams`).

```jsx
import "./globals.css";
import { Suspense } from "react";
import PostHogProvider from "@/components/PostHogProvider";

export const viewport = {
  viewportFit: "cover",
};

export const metadata = {
  title: "Cascade | Your yearly goals die by March. Make them survive.",
  description:
    "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
  openGraph: {
    title: "Cascade | Your yearly goals die by March. Make them survive.",
    description:
      "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
    type: "website",
    url: "https://cascade-flame.vercel.app/",
    images: ["/cascade-og-image.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Cascade | Your yearly goals die by March. Make them survive.",
    description:
      "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
    images: ["/cascade-twitter-card.png"],
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body>
        <Suspense fallback={null}>
          <PostHogProvider>{children}</PostHogProvider>
        </Suspense>
      </body>
    </html>
  );
}
```

**Step 2: Verify dev server starts**

Run: `cd /Users/k2/Desktop/moltathon/cascade/cascade-landing && npm run build`
Expected: Builds without errors.

**Step 3: Commit**

```bash
git add cascade-landing/app/layout.js
git commit -m "feat: wrap app in PostHog provider"
```

---

### Task 4: Add event tracking to WaitlistForm

**Files:**
- Modify: `cascade-landing/components/WaitlistForm.jsx:33-48`

**Step 1: Add posthog import and capture call**

Add import at top of file:
```jsx
import posthog from "posthog-js";
```

Inside `handleSubmit`, after the success path (line 45, after `setSuccess({ duplicate: false })`), add:
```jsx
posthog.capture("waitlist_joined", { source: id });
```

For the duplicate case (line 40, after `setSuccess({ duplicate: true })`), add:
```jsx
posthog.capture("waitlist_joined", { source: id, duplicate: true });
```

**Step 2: Commit**

```bash
git add cascade-landing/components/WaitlistForm.jsx
git commit -m "feat: track waitlist_joined event in PostHog"
```

---

### Task 5: Add event tracking to CascadeDemoWidget

**Files:**
- Modify: `cascade-landing/components/CascadeDemoWidget.jsx:632-658`

**Step 1: Add posthog import**

Add at top of file:
```jsx
import posthog from "posthog-js";
```

**Step 2: Track demo_goal_submitted in handleSend**

Inside `handleSend()`, after the user message is added to messages (line 647, after `setMessages(prev => [...prev, userMsg])`), add:
```jsx
posthog.capture("demo_goal_submitted", { goal_text: trimmed });
```

**Step 3: Commit**

```bash
git add cascade-landing/components/CascadeDemoWidget.jsx
git commit -m "feat: track demo_goal_submitted event in PostHog"
```

---

### Task 6: Add identify + events to onboard chat page

**Files:**
- Modify: `cascade-landing/app/onboard/chat/page.js:37-64` (init useEffect)
- Modify: `cascade-landing/app/onboard/chat/page.js:79-141` (handleComplete)
- Modify: `cascade-landing/app/onboard/chat/page.js:168-197` (telegram link)

**Step 1: Add posthog import**

Add at top of file:
```jsx
import posthog from "posthog-js";
```

**Step 2: Identify user on auth**

In the `init()` function, after `setUser(authUser)` (line 47), add:
```jsx
posthog.identify(authUser.id, { email: authUser.email });
```

**Step 3: Track onboard_completed**

In `handleComplete`, after `setCompleted(true)` (line 80), add:
```jsx
posthog.capture("onboard_completed", {
  goal_title: planData.goal_summary?.title,
});
```

**Step 4: Track telegram_link_clicked**

On the Telegram link `<a>` element (around line 176), add an onClick handler:
```jsx
onClick={() => posthog.capture("telegram_link_clicked")}
```

**Step 5: Commit**

```bash
git add cascade-landing/app/onboard/chat/page.js
git commit -m "feat: identify user and track onboard events in PostHog"
```

---

### Task 7: Add event tracking to payment page

**Files:**
- Modify: `cascade-landing/app/payment/page.js:13-21`

**Step 1: Add posthog import**

Add at top of file (inside the "use client" section):
```jsx
import posthog from "posthog-js";
```

**Step 2: Track checkout_started**

In `handleCheckout`, after `setLoading(true)` (line 14), add:
```jsx
posthog.capture("checkout_started", { plan });
```

**Step 3: Commit**

```bash
git add cascade-landing/app/payment/page.js
git commit -m "feat: track checkout_started event in PostHog"
```

---

### Task 8: Add PostHog shutdown to backend lifespan

**Files:**
- Modify: `cascade-api/cascade_api/main.py:36-69`

**Step 1: Import posthog client**

Add import:
```python
from cascade_api.observability.posthog_client import get_posthog
```

**Step 2: Add shutdown flush**

In the `lifespan` function, after the `yield` (line 60), before the bot cleanup, add:
```python
    ph = get_posthog()
    if ph:
        ph.flush()
        ph.shutdown()
```

**Step 3: Commit**

```bash
git add cascade-api/cascade_api/main.py
git commit -m "feat: flush PostHog on shutdown"
```

---

### Task 9: Add identify_user to backend PostHog client

**Files:**
- Modify: `cascade-api/cascade_api/observability/posthog_client.py`

**Step 1: Add identify_user function**

Add after `track_event`:
```python
def identify_user(
    user_id: str,
    properties: dict | None = None,
) -> None:
    """Set user properties in PostHog. No-op if not configured."""
    ph = get_posthog()
    if not ph:
        return
    ph.identify(
        distinct_id=user_id,
        properties=properties or {},
    )
```

**Step 2: Commit**

```bash
git add cascade-api/cascade_api/observability/posthog_client.py
git commit -m "feat: add identify_user to PostHog client"
```

---

### Task 10: Add missing backend events

**Files:**
- Modify: `cascade-api/cascade_api/api/payment.py:23-42`
- Modify: `cascade-api/cascade_api/api/telegram_webhook.py:70-87`
- Modify: `cascade-api/cascade_api/api/cron.py:42-84`

**Step 1: Track stripe_checkout_created in payment.py**

Add import:
```python
from cascade_api.observability.posthog_client import track_event
```

In `create_checkout`, after the Stripe session is created (after line 39), add:
```python
    track_event(req.tenant_id, "stripe_checkout_created", {"plan": req.plan})
```

**Step 2: Track telegram_message_received in telegram_webhook.py**

Add import:
```python
from cascade_api.observability.posthog_client import track_event
```

In `telegram_webhook`, after `update = Update.de_json(body, bot_app.bot)` (line 84), add:
```python
    user_id = str(update.effective_user.id) if update.effective_user else "unknown"
    track_event(user_id, "telegram_message_received", {
        "chat_type": update.effective_chat.type if update.effective_chat else None,
    })
```

**Step 3: Track cron events in cron.py**

Add import:
```python
from cascade_api.observability.posthog_client import track_event
```

In `cron_morning`, after `result = await send_morning_messages(bot)`, add:
```python
    track_event("system", "cron_morning_sent", result)
```

In `cron_evening`, after `result = await send_evening_messages(bot)`, add:
```python
    track_event("system", "cron_evening_sent", result)
```

In `cron_sunday_review`, after `result = await send_sunday_review_messages(bot)`, add:
```python
    track_event("system", "cron_sunday_review_sent", result)
```

In `cron_monday_kickoff`, after `result = await send_monday_kickoff_messages(bot)`, add:
```python
    track_event("system", "cron_monday_kickoff_sent", result)
```

**Step 4: Commit**

```bash
git add cascade-api/cascade_api/api/payment.py cascade-api/cascade_api/api/telegram_webhook.py cascade-api/cascade_api/api/cron.py
git commit -m "feat: add PostHog tracking to payment, telegram, and cron endpoints"
```

---

### Task 11: Verify frontend builds and backend imports

**Step 1: Build frontend**

Run: `cd /Users/k2/Desktop/moltathon/cascade/cascade-landing && npm run build`
Expected: Clean build, no errors.

**Step 2: Check backend imports**

Run: `cd /Users/k2/Desktop/moltathon/cascade/cascade-api && python -c "from cascade_api.observability.posthog_client import track_event, identify_user; print('OK')"`
Expected: `OK`

**Step 3: Final commit if any fixes needed**
