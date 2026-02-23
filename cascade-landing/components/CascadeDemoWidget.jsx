"use client";

import { useState, useRef, useEffect, useCallback } from "react";

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
            background: "rgba(248,113,113,0.03)",
            border: "1px solid #2A1F22",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          {message.phases.map((phase, i) => (
            <div
              key={i}
              className="cascade-phase-card"
              style={{
                padding: "16px 20px",
                borderBottom:
                  i < message.phases.length - 1
                    ? "1px solid #2A1F22"
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
                    background: PHASE_COLORS[i] || "#EF4444",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    padding: "3px 8px",
                    borderRadius: 4,
                    fontFamily: "'JetBrains Mono', monospace",
                  }}
                >
                  {phase.timeframe}
                </span>
                <span
                  style={{
                    color: "#F8FAFC",
                    fontSize: 14,
                    fontWeight: 600,
                    fontFamily: "'Outfit', sans-serif",
                  }}
                >
                  {phase.phase}
                </span>
              </div>
              <p
                style={{
                  color: "#94A3B8",
                  fontSize: 13,
                  lineHeight: 1.5,
                  margin: "0 0 10px 0",
                  fontFamily: "'Outfit', sans-serif",
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
                        color: PHASE_COLORS[i] || "#EF4444",
                        fontSize: 10,
                        marginTop: 4,
                        flexShrink: 0,
                      }}
                    >
                      ▸
                    </span>
                    <span
                      style={{
                        color: "#F8FAFC",
                        fontSize: 12.5,
                        lineHeight: 1.5,
                        fontFamily: "'Outfit', sans-serif",
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
            ? "#EF4444"
            : "#1A1215",
          border: isUser ? "none" : "1px solid #2A1F22",
          color: "#F8FAFC",
          fontSize: 13.5,
          lineHeight: 1.55,
          fontFamily: "'Outfit', sans-serif",
          overflowWrap: "break-word",
          wordBreak: "break-word",
        }}
      >
        {message.content}
        {message.isStreaming && (
          <span
            style={{
              display: "inline-block",
              width: 5,
              height: 14,
              background: "#EF4444",
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

const PHASE_COLORS = ["#EF4444", "#F87171", "#FB923C"];

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
            background: "#EF4444",
            opacity: 0.5,
            animation: `cascadeDot 1.2s ease ${i * 0.15}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

// Main widget
export default function CascadeDemoWidget({ fullScreen = false }) {
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
    <div
      className={`cascade-widget ${fullScreen ? "cascade-widget--full" : ""}`}
      style={{
        width: "100%",
        ...(!fullScreen && { maxWidth: 440 }),
        margin: "0 auto",
        fontFamily: "'Outfit', sans-serif",
        ...(fullScreen
          ? { display: "flex", flexDirection: "column", height: "100%" }
          : { animation: "cascadeSlideUp 0.5s ease both" }),
      }}
    >
      {/* Header */}
      <div
        className="cascade-widget-header"
        style={{
          background: "#1A1215",
          ...(!fullScreen && {
            borderRadius: "16px 16px 0 0",
            border: "1px solid #2A1F22",
          }),
          borderBottom: fullScreen ? "1px solid #2A1F22" : "none",
          padding: "16px 20px",
          ...(fullScreen && { paddingTop: "max(16px, env(safe-area-inset-top))" }),
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Back link in full-screen mode */}
          {fullScreen && (
            <a
              href="/"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 44,
                height: 44,
                marginLeft: -10,
                color: "#8E9DB0",
                textDecoration: "none",
                flexShrink: 0,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                <path
                  d="M10 3L5 8L10 13"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </a>
          )}
          {/* Logo mark */}
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "rgba(239, 68, 68, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              style={{ position: "relative", zIndex: 1 }}
            >
              <path
                d="M3 4L8 6.5L13 4"
                stroke="#EF4444"
                strokeWidth="1.5"
                fill="none"
                strokeLinecap="round"
              />
              <path
                d="M5 8L8 9.5L11 8"
                stroke="#EF4444"
                strokeWidth="1.2"
                fill="none"
                strokeLinecap="round"
                opacity="0.6"
              />
              <path
                d="M6.5 11.5L8 12.5L9.5 11.5"
                stroke="#EF4444"
                strokeWidth="1"
                fill="none"
                strokeLinecap="round"
                opacity="0.3"
              />
            </svg>
          </div>
          <div>
            <div
              style={{
                color: "#F8FAFC",
                fontSize: 15,
                fontWeight: 600,
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: "-0.01em",
              }}
            >
              Cascade
            </div>
            <div
              style={{
                color: "#8E9DB0",
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
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
                : "rgba(239,68,68,0.06)",
              border: `1px solid ${limitReached ? "rgba(239,68,68,0.3)" : "rgba(239,68,68,0.15)"}`,
            }}
          >
            <div
              style={{
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: "#EF4444",
                animation: "cascadeGlow 2s ease infinite",
              }}
            />
            <span
              style={{
                fontSize: 11,
                color: limitReached ? "#EF4444" : "#F87171",
                fontFamily: "'JetBrains Mono', monospace",
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
        className="cascade-widget-body"
        style={{
          background: "#0D0B0E",
          ...(!fullScreen && {
            borderLeft: "1px solid #2A1F22",
            borderRight: "1px solid #2A1F22",
          }),
          overflowY: "auto",
          padding: "16px 12px",
          position: "relative",
          ...(fullScreen && { flex: 1, minHeight: 0 }),
        }}
      >
        {/* Subtle grid bg */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `
              linear-gradient(rgba(248,113,113,0.02) 1px, transparent 1px),
              linear-gradient(90deg, rgba(248,113,113,0.02) 1px, transparent 1px)
            `,
            backgroundSize: "32px 32px",
            pointerEvents: "none",
          }}
        />

        <div style={{ position: "relative", zIndex: 1, maxWidth: 600, margin: "0 auto" }}>
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
                  color: "#8E9DB0",
                  fontSize: 11,
                  fontFamily: "'JetBrains Mono', monospace",
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
                    padding: "10px 14px",
                    borderRadius: 10,
                    color: "#F87171",
                    fontSize: 13,
                    fontFamily: "'Outfit', sans-serif",
                    minHeight: 44,
                    display: "flex",
                    alignItems: "center",
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
            background: "rgba(239, 68, 68, 0.06)",
            ...(!fullScreen && {
              borderLeft: "1px solid #2A1F22",
              borderRight: "1px solid #2A1F22",
            }),
            padding: "14px 20px",
            textAlign: "center",
            animation: "cascadeFadeUp 0.3s ease both",
            flexShrink: 0,
          }}
        >
          <p
            style={{
              color: "#F8FAFC",
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
              background: "#EF4444",
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              textDecoration: "none",
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: "-0.01em",
              boxShadow: "0 0 20px rgba(239, 68, 68, 0.25)",
            }}
          >
            Get full access to Cascade
          </a>
        </div>
      )}

      {/* Input area */}
      <div
        className="cascade-widget-input-area"
        style={{
          background: "#0D0B0E",
          ...(!fullScreen && {
            borderRadius: "0 0 16px 16px",
            border: "1px solid #2A1F22",
          }),
          borderTop: "1px solid rgba(248,113,113,0.06)",
          padding: fullScreen ? "12px 16px env(safe-area-inset-bottom, 12px) 16px" : "12px 16px",
          paddingBottom: fullScreen ? "max(12px, env(safe-area-inset-bottom))" : 12,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            background: "#1A1215",
            borderRadius: 12,
            border: "1px solid #2A1F22",
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
              width: 44,
              height: 44,
              borderRadius: 8,
              border: "none",
              background:
                input.trim() && !isLoading && !limitReached
                  ? "#EF4444"
                  : "rgba(248,113,113,0.06)",
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

        {!fullScreen && (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              paddingTop: 10,
            }}
          >
            <span
              style={{
                color: "#8E9DB0",
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: "0.04em",
              }}
            >
              powered by cascade ai
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
