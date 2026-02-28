# PostHog Integration Design

## Goal

Full product analytics for Cascade: funnel tracking (landing -> demo -> onboard -> payment -> Telegram) and feature usage (server-side events for Telegram, cron, Stripe).

## Decisions

- **Analytics only** — no session replay for now (can enable later with one config flag)
- **Approach 1**: PostHog JS SDK on frontend + Python SDK on backend
- **No proxy** — direct to PostHog. Add proxy later if ad blockers become a problem
- **Lazy loading** — PostHog loads after hydration via useEffect, not in initial bundle

## Frontend (cascade-landing)

### Setup

- Install `posthog-js`
- Create `PostHogProvider.jsx` — client component that lazy-loads PostHog in useEffect
- Wrap app in provider via `layout.js`
- Config: `autocapture: true`, `capture_pageview: false` (use Next.js router for SPA page views), no session replay
- Env var: `NEXT_PUBLIC_POSTHOG_KEY`

### Events

| Event | Where | Why |
|-------|-------|-----|
| `waitlist_joined` | WaitlistForm submit | Top of funnel |
| `demo_started` | /try page load | Interest signal |
| `demo_goal_submitted` | Demo widget submit | Engagement depth |
| `onboard_started` | /onboard/chat page load | Funnel progression |
| `onboard_completed` | handleComplete fires | Conversion |
| `payment_page_viewed` | /payment page load | Purchase intent |
| `checkout_started` | handleCheckout fires | Revenue signal |
| `telegram_link_clicked` | Telegram link click | Activation |

### User Identification

Call `posthog.identify(userId)` when user authenticates in onboard flow. Ties anonymous pre-auth activity to authenticated user.

### Files Changed

| File | Change |
|------|--------|
| `package.json` | Add `posthog-js` |
| `app/layout.js` | Wrap children in PostHogProvider |
| `components/PostHogProvider.jsx` | New — lazy-loads PostHog |
| `components/WaitlistForm.jsx` | capture waitlist_joined |
| `app/try/page.js` | capture demo_started |
| `app/onboard/chat/page.js` | identify + onboard events |
| `app/payment/page.js` | capture checkout_started |
| `.env.example` | Add NEXT_PUBLIC_POSTHOG_KEY |

## Backend (cascade-api)

### Setup

- Init PostHog client in `main.py` lifespan (start/shutdown)
- Create `observability/posthog.py` — thin wrapper with `track_event()` and `identify_user()`

### Events

| Event | Where | Why |
|-------|-------|-----|
| `goal_created` | `/api/onboard/goal` | Onboarding completed server-side |
| `plan_generated` | `/api/onboard/generate-plan` | Plan cascade worked |
| `telegram_linked` | `/api/onboard/generate-telegram-link` | Activation |
| `telegram_message_received` | Telegram webhook | Daily engagement |
| `stripe_checkout_created` | `/api/payment/create-checkout` | Revenue funnel |
| `stripe_payment_completed` | Stripe webhook | Conversion |
| `cron_review_sent` | Sunday cron | System health |
| `cron_kickoff_sent` | Monday cron | System health |

### User Identification

Server-side identify with properties: `plan`, `goal_title`, `signup_date` for segmentation in PostHog.

### Files Changed

| File | Change |
|------|--------|
| `main.py` | Init/shutdown PostHog in lifespan |
| `observability/posthog.py` | New — track_event, identify_user |
| `api/onboard.py` | Track goal_created, plan_generated, telegram_linked |
| `api/payment.py` | Track stripe_checkout_created |
| `api/stripe_webhook.py` | Track stripe_payment_completed |
| `api/telegram_webhook.py` | Track telegram_message_received |
| `api/cron.py` | Track cron events |

## What We're NOT Doing

- No session replay (enable later when needed)
- No proxy (add later if ad blockers are a problem)
- No custom middleware — direct capture calls at event sites
- No changes to landing page static HTML (autocapture handles it)
