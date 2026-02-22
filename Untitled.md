Claude Code Prompt: Cascade Landing Page - Next.js Setup

Context

I have a React component (`CascadeDemoWidget.jsx`) that is a fully styled chat widget for Cascade, an AI-powered goal execution platform. It uses inline styles, Google Fonts imports via CSS, and CSS keyframe animations. The component is a self-contained JSX file with hooks (useState, useRef, useEffect, useCallback). It currently runs in demo mode with simulated streaming responses.

Task

Create a Next.js 14+ app (App Router) that serves this widget as part of a landing page. Do NOT lose any styling, animations, or functionality from the original component.

Requirements

Project Setup

- Initialize with `npx create-next-app@latest cascade-landing` using App Router, Tailwind CSS, and TypeScript disabled (this is a JS project)
    
- Install no additional UI libraries unless strictly necessary
    

Component Migration

- Place the widget component at `components/CascadeDemoWidget.jsx`
    
- The component uses `useState`, `useRef`, `useEffect`, `useCallback` from React -- these must work in a Client Component
    
- Add `"use client"` directive at the top of the component file
    
- Preserve ALL inline styles exactly as they are. Do not convert them to Tailwind classes or CSS modules. The inline styles are intentional and tested.
    
- Preserve ALL CSS keyframe animations (`cascadeFadeUp`, `cascadeBlink`, `cascadeDot`, `cascadeGlow`, `cascadeSlideUp`) -- move them to `app/globals.css` instead of the `<style>` tag inside the component
    
- Preserve ALL CSS class styles (`.cascade-widget`, `.cascade-suggestion`, `.cascade-send`, `.cascade-input-field`) -- move these to `app/globals.css` as well
    
- Keep the Google Fonts import (`DM Mono`, `DM Sans`, `Space Grotesk`) -- load them via `next/font/google` or keep the CSS import in globals.css
    

Landing Page (`app/page.js`)

- Dark background matching the widget aesthetic (`#0a0a14` or similar deep navy/black)
    
- Center the widget vertically and horizontally on the page
    
- Above the widget: headline and subheadline text for Cascade
    
- Keep the page minimal -- the widget IS the demo, let it breathe
    
- This page should be a Server Component that imports the Client Component widget
    

Important: Do NOT

- Do not refactor, rename, or restructure the component internals
    
- Do not convert inline styles to Tailwind or CSS modules
    
- Do not remove the demo mode functionality or simulated responses
    
- Do not add a navbar, footer, or extra sections yet -- just the hero + widget
    
- Do not change any colors, font sizes, border radii, or animation timings
    

File Structure Expected

```
cascade-landing/
  app/
    layout.js
    page.js
    globals.css
  components/
    CascadeDemoWidget.jsx
  public/
```

Verification

After setup, run `npm run dev` and confirm:

1. Widget renders with dark theme, purple gradient accents
    
2. Typing indicator animation works (three bouncing dots)
    
3. Suggestion chips appear and are clickable
    
4. Sending a message triggers the simulated streaming response
    
5. Breakdown cards render with phased layout (Discovery, Foundation, Execution Sprint)
    
6. Rate limit counter displays and decrements
    
7. All fonts load correctly (DM Sans for body, Space Grotesk for headings, DM Mono for monospace elements)
    
8. All animations are smooth (fade up, blink cursor, slide up)
    

Here is the component source code:

[import { useState, useRef, useEffect, useCallback } from "react";

// ============================================================
// CASCADE DEMO CHAT WIDGET
// ============================================================
// Configuration: Set your LangGraph backend URL below.
// This widget connects to your LangGraph API endpoint
// and streams goal breakdowns in real-time.
//
// SETUP:
// 1. Set LANGGRAPH_API_URL to your deployed LangGraph endpoint
// 2. Adjust RATE_LIMIT_MAX and RATE_LIMIT_WINDOW as needed
// 3. Customize the SYSTEM_PROMPT for Cascade's personality
// 4. Embed this component in your landing page
// ============================================================

const CONFIG = {
  LANGGRAPH_API_URL: "https://your-langgraph-api.langchain.app/runs/stream",
  ASSISTANT_ID: "your-assistant-id",
  RATE_LIMIT_MAX: 5,
  RATE_LIMIT_WINDOW_MS: 60 * 60 * 1000, // 1 hour
  DEMO_MODE: true, // Set false when backend is connected
};

// Simulated Cascade responses for demo mode
const DEMO_RESPONSES = {
  default: (goal) => ({
    thinking: "Analyzing your goal...",
    breakdown: [
      {
        phase: "Discovery",
        description: `Research and validate the core assumptions behind "${goal}"`,
        timeframe: "Week 1",
        tasks: [
          "Identify 3 key assumptions to validate",
          "Find 5 comparable examples or competitors",
          "Draft a one-page validation plan",
        ],
      },
      {
        phase: "Foundation",
        description: "Build the minimum viable structure to support execution",
        timeframe: "Week 2-3",
        tasks: [
          "Define success metrics and KPIs",
          "Set up tracking and accountability system",
          "Create your first milestone checkpoint",
        ],
      },
      {
        phase: "Execution Sprint",
        description: "Ship the first tangible output",
        timeframe: "Week 3-4",
        tasks: [
          "Complete the highest-leverage task first",
          "Get feedback from 3 people in your target audience",
          "Iterate based on real signals, not assumptions",
        ],
      },
    ],
    nudge:
      "This is a simplified breakdown. The full Cascade agent adapts in real-time based on your progress, blockers, and changing priorities.",
  }),
};

// Rate limiter
function useRateLimit(max, windowMs) {
  const [remaining, setRemaining] = useState(max);
  const timestamps = useRef([]);

  const checkLimit = useCallback(() => {
    const now = Date.now();
    timestamps.current = timestamps.current.filter(
      (t) => now - t < windowMs
    );
    if (timestamps.current.length >= max) {
      return false;
    }
    timestamps.current.push(now);
    setRemaining(max - timestamps.current.length);
    return true;
  }, [max, windowMs]);

  return { remaining, checkLimit };
}

// Streaming text hook
function useStreamText(text, speed = 18) {
  const [displayed, setDisplayed] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    if (!text) return;
    setIsStreaming(true);
    setDisplayed("");
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else {
        setIsStreaming(false);
        clearInterval(interval);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return { displayed, isStreaming };
}

// Message bubble component
function Message({ message, isLast }) {
  const isUser = message.role === "user";
  const isBreakdown = message.type === "breakdown";

  if (isBreakdown) {
    return (
      <div
        style={{
          padding: "0 4px",
          marginBottom: 16,
          animation: isLast ? "cascadeFadeUp 0.4s ease both" : "none",
        }}
      >
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {message.phases.map((phase, i) => (
            <div
              key={i}
              style={{
                padding: "16px 20px",
                borderBottom:
                  i < message.phases.length - 1
                    ? "1px solid rgba(255,255,255,0.05)"
                    : "none",
                animation: isLast
                  ? `cascadeFadeUp 0.3s ease ${0.1 * (i + 1)}s both`
                  : "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    background: PHASE_COLORS[i] || "#6366f1",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    padding: "3px 8px",
                    borderRadius: 4,
                    fontFamily: "'DM Mono', monospace",
                  }}
                >
                  {phase.timeframe}
                </span>
                <span
                  style={{
                    color: "#e2e8f0",
                    fontSize: 14,
                    fontWeight: 600,
                    fontFamily: "'Space Grotesk', sans-serif",
                  }}
                >
                  {phase.phase}
                </span>
              </div>
              <p
                style={{
                  color: "#94a3b8",
                  fontSize: 13,
                  lineHeight: 1.5,
                  margin: "0 0 10px 0",
                  fontFamily: "'DM Sans', sans-serif",
                }}
              >
                {phase.description}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {phase.tasks.map((task, j) => (
                  <div
                    key={j}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 8,
                    }}
                  >
                    <span
                      style={{
                        color: PHASE_COLORS[i] || "#6366f1",
                        fontSize: 10,
                        marginTop: 4,
                        flexShrink: 0,
                      }}
                    >
                      ▸
                    </span>
                    <span
                      style={{
                        color: "#cbd5e1",
                        fontSize: 12.5,
                        lineHeight: 1.5,
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      {task}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 12,
        padding: "0 4px",
        animation: isLast ? "cascadeFadeUp 0.3s ease both" : "none",
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "10px 16px",
          borderRadius: isUser ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
          background: isUser
            ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
            : "rgba(255,255,255,0.05)",
          border: isUser ? "none" : "1px solid rgba(255,255,255,0.06)",
          color: isUser ? "#fff" : "#e2e8f0",
          fontSize: 13.5,
          lineHeight: 1.55,
          fontFamily: "'DM Sans', sans-serif",
        }}
      >
        {message.content}
        {message.isStreaming && (
          <span
            style={{
              display: "inline-block",
              width: 5,
              height: 14,
              background: "#6366f1",
              marginLeft: 2,
              animation: "cascadeBlink 0.8s infinite",
              verticalAlign: "text-bottom",
            }}
          />
        )}
      </div>
    </div>
  );
}

const PHASE_COLORS = ["#6366f1", "#06b6d4", "#10b981"];

// Typing indicator
function TypingIndicator() {
  return (
    <div
      style={{
        display: "flex",
        gap: 5,
        padding: "12px 16px",
        marginBottom: 12,
      }}
    >
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#6366f1",
            opacity: 0.5,
            animation: `cascadeDot 1.2s ease ${i * 0.15}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

// Main widget
export default function CascadeDemoWidget() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: "assistant",
      content:
        "Tell me a goal you're working toward. I'll break it into an actionable execution plan.",
      type: "text",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [isOpen, setIsOpen] = useState(true);
  const { remaining, checkLimit } = useRateLimit(
    CONFIG.RATE_LIMIT_MAX,
    CONFIG.RATE_LIMIT_WINDOW_MS
  );
  const [limitReached, setLimitReached] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingText, isLoading]);

  // Connect to LangGraph backend (real mode)
  async function sendToLangGraph(userMessage) {
    try {
      const response = await fetch(CONFIG.LANGGRAPH_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          assistant_id: CONFIG.ASSISTANT_ID,
          input: { messages: [{ role: "user", content: userMessage }] },
          stream_mode: ["messages"],
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        // Parse SSE events from LangGraph
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) {
                fullText += data.content;
                setStreamingText(fullText);
              }
            } catch (e) {
              // skip malformed chunks
            }
          }
        }
      }
      return fullText;
    } catch (error) {
      console.error("LangGraph API error:", error);
      return "Connection error. Please check the API configuration.";
    }
  }

  // Demo mode: simulate streaming response
  async function simulateResponse(userMessage) {
    const demo = DEMO_RESPONSES.default(userMessage);

    // Stream the thinking phase
    const thinkingMsg = demo.thinking;
    let streamed = "";
    for (let i = 0; i < thinkingMsg.length; i++) {
      streamed += thinkingMsg[i];
      setStreamingText(streamed);
      await new Promise((r) => setTimeout(r, 25));
    }

    // Add thinking as message
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        role: "assistant",
        content: thinkingMsg,
        type: "text",
      },
    ]);
    setStreamingText("");

    await new Promise((r) => setTimeout(r, 400));

    // Add breakdown card
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 1,
        role: "assistant",
        type: "breakdown",
        phases: demo.breakdown,
      },
    ]);

    await new Promise((r) => setTimeout(r, 600));

    // Stream the nudge
    let nudgeStreamed = "";
    for (let i = 0; i < demo.nudge.length; i++) {
      nudgeStreamed += demo.nudge[i];
      setStreamingText(nudgeStreamed);
      await new Promise((r) => setTimeout(r, 14));
    }

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 2,
        role: "assistant",
        content: demo.nudge,
        type: "text",
      },
    ]);
    setStreamingText("");
  }

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    if (!checkLimit()) {
      setLimitReached(true);
      return;
    }

    const userMsg = {
      id: Date.now(),
      role: "user",
      content: trimmed,
      type: "text",
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    if (CONFIG.DEMO_MODE) {
      await simulateResponse(trimmed);
    } else {
      const response = await sendToLangGraph(trimmed);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "assistant",
          content: response,
          type: "text",
        },
      ]);
      setStreamingText("");
    }

    setIsLoading(false);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const SUGGESTIONS = [
    "Launch a SaaS in 30 days",
    "Get my first 100 users",
    "Build a content flywheel",
  ];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:ital,wght@0,400;0,500;0,600;0,700&family=Space+Grotesk:wght@500;600;700&display=swap');
        
        @keyframes cascadeFadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes cascadeBlink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
        @keyframes cascadeDot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
          30% { transform: translateY(-6px); opacity: 0.8; }
        }
        @keyframes cascadeGlow {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.7; }
        }
        @keyframes cascadeSlideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .cascade-widget * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        .cascade-widget ::-webkit-scrollbar {
          width: 4px;
        }
        .cascade-widget ::-webkit-scrollbar-track {
          background: transparent;
        }
        .cascade-widget ::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 4px;
        }
        .cascade-suggestion {
          cursor: pointer;
          transition: all 0.2s ease;
          border: 1px solid rgba(99, 102, 241, 0.25);
          background: rgba(99, 102, 241, 0.06);
        }
        .cascade-suggestion:hover {
          border-color: rgba(99, 102, 241, 0.5);
          background: rgba(99, 102, 241, 0.12);
          transform: translateY(-1px);
        }
        .cascade-send {
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .cascade-send:hover:not(:disabled) {
          transform: scale(1.05);
        }
        .cascade-send:active:not(:disabled) {
          transform: scale(0.95);
        }
        .cascade-input-field {
          outline: none;
          border: none;
          background: transparent;
          color: #e2e8f0;
          font-size: 14px;
          font-family: 'DM Sans', sans-serif;
          width: 100%;
          resize: none;
        }
        .cascade-input-field::placeholder {
          color: #475569;
        }
      `}</style>

      <div
        className="cascade-widget"
        style={{
          width: "100%",
          maxWidth: 440,
          margin: "0 auto",
          fontFamily: "'DM Sans', sans-serif",
          animation: "cascadeSlideUp 0.5s ease both",
        }}
      >
        {/* Header */}
        <div
          style={{
            background: "linear-gradient(180deg, #0f0f1a 0%, #0c0c18 100%)",
            borderRadius: "16px 16px 0 0",
            border: "1px solid rgba(255,255,255,0.06)",
            borderBottom: "none",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {/* Logo mark */}
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(135deg, transparent 40%, rgba(255,255,255,0.15))",
                }}
              />
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                style={{ position: "relative", zIndex: 1 }}
              >
                <path
                  d="M8 2L4 6L8 10L12 6L8 2Z"
                  fill="white"
                  fillOpacity="0.9"
                />
                <path
                  d="M4 8L8 12L12 8"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity="0.6"
                />
              </svg>
            </div>
            <div>
              <div
                style={{
                  color: "#f1f5f9",
                  fontSize: 15,
                  fontWeight: 600,
                  fontFamily: "'Space Grotesk', sans-serif",
                  letterSpacing: "-0.01em",
                }}
              >
                Cascade
              </div>
              <div
                style={{
                  color: "#64748b",
                  fontSize: 11,
                  fontFamily: "'DM Mono', monospace",
                  letterSpacing: "0.02em",
                }}
              >
                goal execution engine
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "4px 10px",
                borderRadius: 20,
                background: limitReached
                  ? "rgba(239,68,68,0.1)"
                  : "rgba(99,102,241,0.08)",
                border: `1px solid ${limitReached ? "rgba(239,68,68,0.2)" : "rgba(99,102,241,0.15)"}`,
              }}
            >
              <div
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  background: limitReached ? "#ef4444" : "#6366f1",
                  animation: "cascadeGlow 2s ease infinite",
                }}
              />
              <span
                style={{
                  fontSize: 11,
                  color: limitReached ? "#ef4444" : "#6366f1",
                  fontFamily: "'DM Mono', monospace",
                  fontWeight: 500,
                }}
              >
                {remaining}/{CONFIG.RATE_LIMIT_MAX}
              </span>
            </div>
          </div>
        </div>

        {/* Chat body */}
        <div
          ref={scrollRef}
          style={{
            background: "#0c0c18",
            borderLeft: "1px solid rgba(255,255,255,0.06)",
            borderRight: "1px solid rgba(255,255,255,0.06)",
            height: 420,
            overflowY: "auto",
            padding: "16px 12px",
            position: "relative",
          }}
        >
          {/* Subtle grid bg */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: `
                linear-gradient(rgba(99,102,241,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(99,102,241,0.03) 1px, transparent 1px)
              `,
              backgroundSize: "32px 32px",
              pointerEvents: "none",
            }}
          />

          <div style={{ position: "relative", zIndex: 1 }}>
            {messages.map((msg, i) => (
              <Message
                key={msg.id}
                message={msg}
                isLast={i === messages.length - 1}
              />
            ))}

            {/* Streaming text */}
            {streamingText && (
              <Message
                message={{
                  id: "streaming",
                  role: "assistant",
                  content: streamingText,
                  type: "text",
                  isStreaming: true,
                }}
                isLast={true}
              />
            )}

            {isLoading && !streamingText && <TypingIndicator />}

            {/* Suggestion chips (only show at start) */}
            {messages.length === 1 && !isLoading && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  padding: "8px 4px",
                  animation: "cascadeFadeUp 0.4s ease 0.3s both",
                }}
              >
                <span
                  style={{
                    color: "#475569",
                    fontSize: 11,
                    fontFamily: "'DM Mono', monospace",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: 4,
                  }}
                >
                  Try one of these
                </span>
                {SUGGESTIONS.map((s, i) => (
                  <div
                    key={i}
                    className="cascade-suggestion"
                    onClick={() => {
                      setInput(s);
                      setTimeout(() => inputRef.current?.focus(), 50);
                    }}
                    style={{
                      padding: "8px 14px",
                      borderRadius: 10,
                      color: "#a5b4fc",
                      fontSize: 13,
                      fontFamily: "'DM Sans', sans-serif",
                      animation: `cascadeFadeUp 0.3s ease ${0.4 + i * 0.08}s both`,
                    }}
                  >
                    {s}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Rate limit banner */}
        {limitReached && (
          <div
            style={{
              background: "linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1))",
              borderLeft: "1px solid rgba(255,255,255,0.06)",
              borderRight: "1px solid rgba(255,255,255,0.06)",
              padding: "14px 20px",
              textAlign: "center",
              animation: "cascadeFadeUp 0.3s ease both",
            }}
          >
            <p
              style={{
                color: "#c7d2fe",
                fontSize: 13,
                fontWeight: 500,
                marginBottom: 8,
              }}
            >
              You've used all {CONFIG.RATE_LIMIT_MAX} free messages
            </p>
            <a
              href="#signup"
              style={{
                display: "inline-block",
                padding: "8px 24px",
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                color: "#fff",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
                fontFamily: "'Space Grotesk', sans-serif",
                letterSpacing: "-0.01em",
              }}
            >
              Get full access to Cascade
            </a>
          </div>
        )}

        {/* Input area */}
        <div
          style={{
            background: "#0c0c18",
            borderRadius: "0 0 16px 16px",
            border: "1px solid rgba(255,255,255,0.06)",
            borderTop: "1px solid rgba(255,255,255,0.04)",
            padding: "12px 16px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "rgba(255,255,255,0.03)",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.06)",
              padding: "10px 14px",
              transition: "border-color 0.2s",
            }}
          >
            <input
              ref={inputRef}
              className="cascade-input-field"
              type="text"
              placeholder={
                limitReached
                  ? "Sign up for unlimited access..."
                  : "Type a goal you want to crush..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading || limitReached}
              style={{
                flex: 1,
                opacity: limitReached ? 0.4 : 1,
              }}
            />
            <button
              className="cascade-send"
              onClick={handleSend}
              disabled={!input.trim() || isLoading || limitReached}
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                border: "none",
                background:
                  input.trim() && !isLoading && !limitReached
                    ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                    : "rgba(255,255,255,0.04)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                style={{
                  opacity:
                    input.trim() && !isLoading && !limitReached ? 1 : 0.2,
                }}
              >
                <path
                  d="M14 2L7 9M14 2L9.5 14L7 9M14 2L2 6.5L7 9"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              paddingTop: 10,
            }}
          >
            <span
              style={{
                color: "#334155",
                fontSize: 10,
                fontFamily: "'DM Mono', monospace",
                letterSpacing: "0.04em",
              }}
            >
              powered by cascade ai
            </span>
          </div>
        </div>
      </div>
    </>
  );
}]