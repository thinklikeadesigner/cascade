import Anthropic from "@anthropic-ai/sdk";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

const client = new Anthropic();

const SYSTEM_PROMPT = `You are Cascade, a goal-execution engine that helps ambitious builders break down goals into actionable structure through cascading time horizons.

You are not a planner. You are a system. Plans are cheap — everyone has a plan on January 1st. Cascade exists because plans fail without structure, accountability, and honest feedback.

## METHODOLOGY

### Gravity
Plans cascade down (year → quarter → month → week → day). Reality flows up. Today's results reshape tomorrow's targets — not the other way around.

### Core/Flex
Core hours are the floor. Your plan must succeed on Core alone. Flex hours are bonus — reach for them when energy allows. If a plan needs Flex hours to hit targets, the plan is overcommitted.

## COACHING TONE

You are not a cheerleader. You are not a drill sergeant. You observe, inform, and give agency.

1. Observe, inform, give agency. Never lecture.
2. Be honest about numbers. "At 10 hours/week, this needs 6 months, not 3."
3. Respect autonomy. Present options, let them decide.
4. Never fake enthusiasm.
5. Never shame. A bad plan is data, not failure.
6. Trust data over intentions. If a timeline is unrealistic, say so.
7. Tasks must be specific. "Talk to customers" is bad. "Interview 5 users this week" is good.

## CRITICAL BEHAVIOR RULES

**ALWAYS call the create_goal_breakdown tool when the user shares anything resembling a goal.** This is your primary function. Do not ask clarifying questions instead of producing a breakdown. If details are missing, make reasonable assumptions and note them in your analysis text.

When a user shares a goal:
1. Write 1-2 sentences of analysis. Be honest about feasibility. Note any assumptions you're making.
2. IMMEDIATELY call create_goal_breakdown with 3 phases. Each phase: name, description, timeframe, 3 specific tasks. Do NOT skip this step to ask questions.
3. After the tool result, give a 1-2 sentence coaching nudge. Tell them what to do first.

If the user provides more context in follow-up messages, call the tool again with a refined breakdown. Every goal-related message should produce a breakdown.

Only skip the tool for pure non-goal messages (greetings, "what is Cascade?", etc.). When in doubt, produce a breakdown.

This is a demo widget — users expect to see a structured breakdown, not an interview. Act first, refine later.`;

const TOOL = {
  name: "create_goal_breakdown",
  description:
    "Create a structured goal breakdown with phases, descriptions, timeframes, and tasks",
  input_schema: {
    type: "object",
    properties: {
      phases: {
        type: "array",
        items: {
          type: "object",
          properties: {
            phase: { type: "string" },
            description: { type: "string" },
            timeframe: { type: "string" },
            tasks: { type: "array", items: { type: "string" } },
          },
          required: ["phase", "description", "timeframe", "tasks"],
        },
      },
    },
    required: ["phases"],
  },
};

// Rate limiting: IP-based, in-memory, per-request cleanup
const rateLimitMap = new Map();

function checkRateLimit(ip) {
  const now = Date.now();
  const WINDOW = 3600000; // 1 hour
  const MAX = 12;

  // Clean stale entries
  for (const [key, timestamps] of rateLimitMap) {
    const valid = timestamps.filter((t) => now - t < WINDOW);
    if (valid.length === 0) rateLimitMap.delete(key);
    else rateLimitMap.set(key, valid);
  }

  // DoS safety valve
  if (rateLimitMap.size > 10000) rateLimitMap.clear();

  const timestamps = rateLimitMap.get(ip) || [];
  if (timestamps.length >= MAX) return false;
  timestamps.push(now);
  rateLimitMap.set(ip, timestamps);
  return true;
}

export async function POST(request) {
  // Origin check
  const origin = request.headers.get("origin");
  const allowedOrigins = [
    process.env.ALLOWED_ORIGIN,
    "https://cascade-flame.vercel.app",
    "https://cascade-landing-beige.vercel.app",
    process.env.NODE_ENV === "development" && "http://localhost:3000",
  ].filter(Boolean);

  // Also allow Vercel preview deployments
  const isVercelPreview = origin && origin.endsWith(".vercel.app") && origin.includes("cascade-landing");

  if (origin && !allowedOrigins.includes(origin) && !isVercelPreview) {
    return new Response("Forbidden", { status: 403 });
  }

  // Rate limit
  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (!checkRateLimit(ip)) {
    return new Response("Rate limit exceeded", { status: 429 });
  }

  // Input validation
  const body = await request.json().catch(() => null);
  if (!body) return new Response("Bad request", { status: 400 });

  const { messages: clientMessages } = body;
  if (!Array.isArray(clientMessages) || clientMessages.length === 0) {
    return new Response("Invalid messages", { status: 400 });
  }

  // Validate and sanitize messages, limit to last 20 turns
  const sanitizedMessages = clientMessages.slice(-20).reduce((acc, msg) => {
    if (
      (msg.role === "user" || msg.role === "assistant") &&
      typeof msg.content === "string" &&
      msg.content.trim().length > 0 &&
      msg.content.length <= 2000
    ) {
      acc.push({ role: msg.role, content: msg.content.trim() });
    }
    return acc;
  }, []);

  if (sanitizedMessages.length === 0 || sanitizedMessages[sanitizedMessages.length - 1].role !== "user") {
    return new Response("Invalid messages", { status: 400 });
  }

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      function send(data) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      }

      try {
        // Call 1: Claude analyzes goal and may call tool
        const stream1 = client.messages.stream({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 1000,
          system: SYSTEM_PROMPT,
          messages: sanitizedMessages,
          tools: [TOOL],
          tool_choice: { type: "auto" },
        });

        // Stream text deltas in real-time
        stream1.on("text", (delta) => {
          send({ type: "text_delta", text: delta });
        });

        const finalMessage = await stream1.finalMessage();

        // If no tool use, we're done (text-only response)
        if (finalMessage.stop_reason === "end_turn") {
          send({ type: "done" });
          controller.close();
          return;
        }

        // Extract tool_use block
        const toolBlock = finalMessage.content.find(
          (block) => block.type === "tool_use"
        );

        if (!toolBlock) {
          send({ type: "done" });
          controller.close();
          return;
        }

        // Send breakdown to client
        send({ type: "breakdown", phases: toolBlock.input.phases });

        // Call 2: Send tool_result back to Claude for the nudge
        const stream2 = client.messages.stream({
          model: "claude-haiku-4-5-20251001",
          max_tokens: 300,
          system: SYSTEM_PROMPT,
          messages: [
            ...sanitizedMessages,
            { role: "assistant", content: finalMessage.content },
            {
              role: "user",
              content: [
                {
                  type: "tool_result",
                  tool_use_id: toolBlock.id,
                  content: "Breakdown displayed to user. Now give a brief coaching nudge.",
                },
              ],
            },
          ],
          tools: [TOOL],
          tool_choice: { type: "none" },
        });

        stream2.on("text", (delta) => {
          send({ type: "text_delta", text: delta });
        });

        await stream2.finalMessage();

        send({ type: "done" });
        controller.close();
      } catch (error) {
        console.error("Chat API error:", error);
        send({
          type: "error",
          message: "Something went wrong. Please try again.",
        });
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Encoding": "none",
    },
  });
}
