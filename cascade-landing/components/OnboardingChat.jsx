"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import CascadePlanCard from "./CascadePlanCard";
import { saveConversation } from "@/lib/conversations";
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

// State progression: which cascade_state follows approval of each card type
const STATE_AFTER_APPROVAL = {
  goal_summary: "goal",
  year_plan: "year",
  quarter_plan: "quarter",
  month_plan: "month",
  week_plan: "week",
  schedule_summary: "schedule",
};

// Message bubble (reused from CascadeDemoWidget with minor tweaks)
function Message({ message }) {
  const isUser = message.role === "user";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        marginBottom: 12,
        padding: "0 4px",
      }}
    >
      <div
        style={{
          maxWidth: "85%",
          padding: "10px 16px",
          borderRadius: isUser ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
          background: isUser ? "#EF4444" : "#1A1215",
          border: isUser ? "none" : "1px solid #2A1F22",
          color: "#F8FAFC",
          fontSize: 13.5,
          lineHeight: 1.6,
          fontFamily: "'Outfit', sans-serif",
          overflowWrap: "break-word",
          wordBreak: "break-word",
        }}
      >
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
              strong: ({ children }) => <strong style={{ color: "#F8FAFC", fontWeight: 600 }}>{children}</strong>,
              em: ({ children }) => <em style={{ color: "#CBD5E1" }}>{children}</em>,
              ul: ({ children }) => <ul style={{ margin: "4px 0 8px 0", paddingLeft: 16, listStyleType: "disc" }}>{children}</ul>,
              ol: ({ children }) => <ol style={{ margin: "4px 0 8px 0", paddingLeft: 16 }}>{children}</ol>,
              li: ({ children }) => <li style={{ marginBottom: 2, color: "#F8FAFC" }}>{children}</li>,
              code: ({ children }) => (
                <code style={{ background: "rgba(248,113,113,0.1)", color: "#F87171", padding: "1px 5px", borderRadius: 4, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                  {children}
                </code>
              ),
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#F87171", textDecoration: "underline" }}>
                  {children}
                </a>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
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

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 5, padding: "12px 16px", marginBottom: 12 }}>
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

export default function OnboardingChat({ conversation, onComplete }) {
  const [messages, setMessages] = useState(conversation.messages || []);
  const [planCards, setPlanCards] = useState(conversation.plan_cards || []);
  const [cascadeState, setCascadeState] = useState(conversation.cascade_state || "exploring");
  const [planData, setPlanData] = useState(conversation.plan_data || {});
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const conversationId = conversation.id;

  // Refs to track latest state during async streaming (avoids closure bugs)
  const messagesRef = useRef(messages);
  const planCardsRef = useRef(planCards);
  const cascadeStateRef = useRef(cascadeState);
  const planDataRef = useRef(planData);

  // Keep refs in sync with state
  useEffect(() => { messagesRef.current = messages; }, [messages]);
  useEffect(() => { planCardsRef.current = planCards; }, [planCards]);
  useEffect(() => { cascadeStateRef.current = cascadeState; }, [cascadeState]);
  useEffect(() => { planDataRef.current = planData; }, [planData]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, planCards, streamingText, isLoading]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Save to Supabase
  const persistConversation = useCallback(
    async (newMessages, newCascadeState, newPlanData, newPlanCards) => {
      try {
        await saveConversation(getSupabase(), conversationId, {
          messages: newMessages,
          cascadeState: newCascadeState,
          planData: newPlanData,
          planCards: newPlanCards,
        });
      } catch (err) {
        console.error("Failed to save conversation:", err);
      }
    },
    [conversationId]
  );

  // Build the display list: interleave messages and plan cards by insertion order
  function buildDisplayItems() {
    const items = [];
    let cardIndex = 0;

    for (const msg of messages) {
      items.push({ type: "message", data: msg });

      // Insert any plan cards that were placed after this message
      while (cardIndex < planCards.length && planCards[cardIndex].afterMessageId === msg.id) {
        items.push({ type: "card", data: planCards[cardIndex] });
        cardIndex++;
      }
    }

    // Any remaining cards (fallback for cards with no matching afterMessageId)
    while (cardIndex < planCards.length) {
      items.push({ type: "card", data: planCards[cardIndex] });
      cardIndex++;
    }

    return items;
  }

  async function sendMessage(text) {
    if (!text.trim() || isLoading) return;

    const userMsg = {
      id: Date.now(),
      role: "user",
      content: text.trim(),
      type: "text",
    };

    // Use functional update to avoid stale state
    const newMessages = [...messagesRef.current, userMsg];
    messagesRef.current = newMessages;
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);
    setStreamingText("");

    try {
      // Build simple text messages for the API
      const apiMessages = newMessages
        .filter((m) => m.type === "text" && m.content)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch("/api/chat/onboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: apiMessages,
          cascade_state: cascadeStateRef.current,
          plan_data: planDataRef.current,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulatedText = "";
      let lastAssistantMsgId = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let parsed;
          try {
            parsed = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          switch (parsed.type) {
            case "text_delta":
              accumulatedText += parsed.text;
              setStreamingText(accumulatedText);
              break;

            case "plan_card": {
              // Finalize any accumulated text as a message
              if (accumulatedText) {
                lastAssistantMsgId = Date.now();
                const textMsg = {
                  id: lastAssistantMsgId,
                  role: "assistant",
                  content: accumulatedText,
                  type: "text",
                };
                const updated = [...messagesRef.current, textMsg];
                messagesRef.current = updated;
                setMessages(updated);
                setStreamingText("");
                accumulatedText = "";
              }

              // Add the plan card
              const anchorId = lastAssistantMsgId || messagesRef.current[messagesRef.current.length - 1]?.id || "last";
              const card = {
                id: Date.now() + 1,
                cardType: parsed.card_type,
                data: parsed.data,
                approved: false,
                afterMessageId: anchorId,
              };
              const updatedCards = [...planCardsRef.current, card];
              planCardsRef.current = updatedCards;
              setPlanCards(updatedCards);

              await new Promise((r) => setTimeout(r, 300));
              break;
            }

            case "done":
              break;

            case "error":
              setStreamingText("");
              const errMsg = {
                id: Date.now(),
                role: "assistant",
                content: parsed.message || "Something went wrong.",
                type: "text",
              };
              const errUpdated = [...messagesRef.current, errMsg];
              messagesRef.current = errUpdated;
              setMessages(errUpdated);
              setIsLoading(false);
              return;
          }
        }
      }

      // Finalize any remaining text
      if (accumulatedText) {
        const finalMsg = {
          id: Date.now() + 2,
          role: "assistant",
          content: accumulatedText,
          type: "text",
        };
        const finalUpdated = [...messagesRef.current, finalMsg];
        messagesRef.current = finalUpdated;
        setMessages(finalUpdated);
      }
      setStreamingText("");

      // Persist
      await persistConversation(messagesRef.current, cascadeStateRef.current, planDataRef.current, planCardsRef.current);
    } catch (error) {
      console.error("Chat error:", error);
      const connErrMsg = {
        id: Date.now(),
        role: "assistant",
        content: "Connection error. Please try again.",
        type: "text",
      };
      const connUpdated = [...messagesRef.current, connErrMsg];
      messagesRef.current = connUpdated;
      setMessages(connUpdated);
      setStreamingText("");
    } finally {
      setIsLoading(false);
    }
  }

  function handleApprove(cardType, data) {
    const newPlanData = { ...planData, [cardType]: data };
    const newCascadeState = STATE_AFTER_APPROVAL[cardType] || cascadeState;

    // Mark the card as approved
    const newPlanCards = planCardsRef.current.map((c) =>
      c.cardType === cardType && !c.approved ? { ...c, approved: true } : c
    );

    // Update refs synchronously BEFORE sendMessage reads them
    planCardsRef.current = newPlanCards;
    cascadeStateRef.current = newCascadeState;
    planDataRef.current = newPlanData;

    setPlanData(newPlanData);
    setCascadeState(newCascadeState);
    setPlanCards(newPlanCards);

    // Check if onboarding is complete
    if (cardType === "schedule_summary") {
      const completedState = "completed";
      setCascadeState(completedState);
      persistConversation(messagesRef.current, completedState, newPlanData, newPlanCards);
      onComplete?.(newPlanData);
      return;
    }

    // Persist then send approval message to continue the conversation
    persistConversation(messagesRef.current, newCascadeState, newPlanData, newPlanCards);
    sendMessage("Approved. Let's move on.");
  }

  function handleRequestChanges(cardType, feedback) {
    // Remove the unapproved card so Claude regenerates it
    const newPlanCards = planCardsRef.current.filter(
      (c) => !(c.cardType === cardType && !c.approved)
    );
    planCardsRef.current = newPlanCards;
    setPlanCards(newPlanCards);

    // Prefix feedback so Claude unambiguously knows this is a revision request
    const prefixedFeedback = `[REVISION: ${cardType}] ${feedback}`;
    sendMessage(prefixedFeedback);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  const displayItems = buildDisplayItems();
  const activeCardType = planCards.find((c) => !c.approved)?.cardType;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        fontFamily: "'Outfit', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          background: "#1A1215",
          borderBottom: "1px solid #2A1F22",
          padding: "16px 20px",
          paddingTop: "max(16px, env(safe-area-inset-top))",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <a
            href="/onboard"
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
              <path d="M10 3L5 8L10 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </a>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "rgba(239, 68, 68, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 4L8 6.5L13 4" stroke="#EF4444" strokeWidth="1.5" fill="none" strokeLinecap="round" />
              <path d="M5 8L8 9.5L11 8" stroke="#EF4444" strokeWidth="1.2" fill="none" strokeLinecap="round" opacity="0.6" />
              <path d="M6.5 11.5L8 12.5L9.5 11.5" stroke="#EF4444" strokeWidth="1" fill="none" strokeLinecap="round" opacity="0.3" />
            </svg>
          </div>
          <div>
            <div style={{ color: "#F8FAFC", fontSize: 15, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.01em" }}>
              Cascade
            </div>
            <div style={{ color: "#8E9DB0", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.02em" }}>
              setting up your plan
            </div>
          </div>
        </div>

        {/* Progress indicator */}
        <div style={{ display: "flex", gap: 4 }}>
          {["exploring", "goal", "year", "quarter", "month", "week", "schedule"].map((state, i) => (
            <div
              key={state}
              style={{
                width: 20,
                height: 3,
                borderRadius: 2,
                background:
                  ["exploring", "goal", "year", "quarter", "month", "week", "schedule"].indexOf(cascadeState) >= i
                    ? "#EF4444"
                    : "#2A1F22",
                transition: "background 0.3s ease",
              }}
            />
          ))}
        </div>
      </div>

      {/* Chat body */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          padding: "16px 12px",
          background: "#0D0B0E",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `linear-gradient(rgba(248,113,113,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(248,113,113,0.02) 1px, transparent 1px)`,
            backgroundSize: "32px 32px",
            pointerEvents: "none",
          }}
        />

        <div style={{ position: "relative", zIndex: 1, maxWidth: 600, margin: "0 auto" }}>
          {displayItems.map((item) => {
            if (item.type === "message") {
              return <Message key={item.data.id} message={item.data} />;
            }
            if (item.type === "card") {
              return (
                <CascadePlanCard
                  key={item.data.id}
                  cardType={item.data.cardType}
                  data={item.data.data}
                  active={item.data.cardType === activeCardType}
                  approved={item.data.approved}
                  onApprove={handleApprove}
                  onRequestChanges={handleRequestChanges}
                />
              );
            }
            return null;
          })}

          {streamingText && (
            <Message
              message={{
                id: "streaming",
                role: "assistant",
                content: streamingText,
                type: "text",
                isStreaming: true,
              }}
            />
          )}

          {isLoading && !streamingText && <TypingIndicator />}
        </div>
      </div>

      {/* Input area */}
      <div
        style={{
          background: "#0D0B0E",
          borderTop: "1px solid rgba(248,113,113,0.06)",
          padding: "12px 16px",
          paddingBottom: "max(12px, env(safe-area-inset-bottom))",
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
            maxWidth: 600,
            margin: "0 auto",
          }}
        >
          <input
            ref={inputRef}
            className="cascade-input-field"
            type="text"
            placeholder={cascadeState === "completed" ? "Onboarding complete!" : "Type your answer..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading || cascadeState === "completed"}
            style={{ flex: 1, opacity: cascadeState === "completed" ? 0.4 : 1 }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isLoading || cascadeState === "completed"}
            style={{
              width: 44,
              height: 44,
              borderRadius: 8,
              border: "none",
              background: input.trim() && !isLoading ? "#EF4444" : "rgba(248,113,113,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              cursor: input.trim() && !isLoading ? "pointer" : "default",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              style={{ opacity: input.trim() && !isLoading ? 1 : 0.2 }}
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
      </div>
    </div>
  );
}
