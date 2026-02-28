import Anthropic from "@anthropic-ai/sdk";
import { startActiveObservation, startObservation, updateActiveTrace } from "@langfuse/tracing";
import { getLangfuseSpanProcessor } from "@/instrumentation";

export const dynamic = "force-dynamic";
export const maxDuration = 60; // Node.js runtime (default) — Edge has 30s limit which is too short for multi-tool loops

const client = new Anthropic();

// Tool names that represent cascade plan cards
const PLAN_TOOL_NAMES = [
  "present_goal_summary",
  "present_year_plan",
  "present_quarter_plan",
  "present_month_plan",
  "present_week_plan",
  "present_schedule_summary",
];

// Map tool names to card types for the frontend
const TOOL_TO_CARD_TYPE = {
  present_goal_summary: "goal_summary",
  present_year_plan: "year_plan",
  present_quarter_plan: "quarter_plan",
  present_month_plan: "month_plan",
  present_week_plan: "week_plan",
  present_schedule_summary: "schedule_summary",
};

// Rate limiting: per-user, in-memory
const rateLimitMap = new Map();

function checkRateLimit(userId) {
  const now = Date.now();
  const WINDOW = 3600000; // 1 hour
  const MAX = 30; // 30 requests/hour for onboarding (more generous than demo)

  // Clean stale entries
  for (const [key, timestamps] of rateLimitMap) {
    const valid = timestamps.filter((t) => now - t < WINDOW);
    if (valid.length === 0) rateLimitMap.delete(key);
    else rateLimitMap.set(key, valid);
  }

  // Safety valve
  if (rateLimitMap.size > 10000) rateLimitMap.clear();

  const timestamps = rateLimitMap.get(userId) || [];
  if (timestamps.length >= MAX) return false;
  timestamps.push(now);
  rateLimitMap.set(userId, timestamps);
  return true;
}

function buildSystemPrompt(cascadeState, planData, timezone) {
  let contextSection = "";

  if (planData && Object.keys(planData).length > 0) {
    contextSection = "\n\n## APPROVED PLANS (already reviewed and approved by the user)\n";
    if (planData.goal_summary) {
      contextSection += `\n### Goal\n- Title: ${planData.goal_summary.title}\n- Success Criteria: ${planData.goal_summary.success_criteria}\n- Current State: ${planData.goal_summary.current_state}\n- Target Date: ${planData.goal_summary.target_date}\n- Core Hours: ${planData.goal_summary.core_hours}/week\n- Flex Hours: ${planData.goal_summary.flex_hours}/week\n`;
    }
    if (planData.year_plan) {
      contextSection += `\n### Year Plan\n- Success Criteria: ${planData.year_plan.success_criteria}\n`;
      planData.year_plan.quarterly_arc?.forEach((q) => {
        contextSection += `- ${q.quarter}: ${q.focus} → ${q.milestone}\n`;
      });
    }
    if (planData.quarter_plan) {
      contextSection += `\n### Quarterly Milestones\n`;
      planData.quarter_plan.quarters?.forEach((q) => {
        contextSection += `- ${q.quarter} (${q.months}): ${q.milestones?.join(", ")}\n`;
      });
    }
    if (planData.month_plan) {
      contextSection += `\n### Monthly Targets (${planData.month_plan.month} ${planData.month_plan.year})\n`;
      planData.month_plan.targets?.forEach((t) => {
        contextSection += `- ${t.target}: ${t.definition_of_done}\n`;
      });
    }
  }

  const stateInstruction = {
    exploring: "You are in the goal exploration phase. Ask clarifying questions one at a time until you have: a specific goal, success criteria, current state, target date, and core/flex hours. When ready, call present_goal_summary.",
    goal: "The user approved their goal summary. Now present the year plan using present_year_plan.",
    year: "The user approved the year plan. Now present quarterly milestones using present_quarter_plan.",
    quarter: "The user approved the quarterly milestones. Now present this month's targets using present_month_plan.",
    month: "The user approved the monthly targets. Now present the first week's plan using present_week_plan.",
    week: "The user approved the week plan. Now ask them about their preferred schedule. Ask ONE question at a time:\n1. First ask: \"What time would you like your daily tasks sent?\" (e.g., 7am, 8:30am, 9am)\n2. After they answer, ask: \"What day do you want your weekly review included?\" (e.g., Sunday, Saturday)\n3. After both answers, call present_schedule_summary with the parsed values.\n\nParse natural language times into 24h format. '7am' = hour 7, '8:30pm' = hour 20 minute 30. Map day names to numbers: Sunday=0, Monday=1, ..., Saturday=6.\n\nMorning time should be between 4 AM and 12 PM. If they ask for a time outside that range, explain that the message works best as a morning briefing and suggest a time in range.",
    schedule: "The user approved their schedule. Congratulate them briefly. Their onboarding is complete.",
  }[cascadeState] || "You are in the goal exploration phase. Ask clarifying questions.";

  return `You are Cascade, a goal-execution engine that helps ambitious builders break down yearly goals into daily structure through cascading time horizons with human-in-the-loop checkpoints.

You are onboarding a new user. Guide them through defining their goal and building their first cascade plan.

## METHODOLOGY

### Gravity
Plans cascade down (year → quarter → month → week → day). Reality flows up. Today's results reshape tomorrow's targets.

### Core/Flex
Core hours are the floor. Your plan must succeed on Core alone. If a plan needs Flex hours to hit targets, it's overcommitted. Reduce scope or extend timeline.

Core is not the minimum. Core is the plan. Flex is acceleration.

### Checkpoints
Human approval at each time horizon is non-negotiable. Present each level, then STOP and wait for approval or feedback. Do NOT present the next level until the current one is approved.

## COACHING TONE

1. Observe, inform, give agency. Never lecture.
2. Be honest about numbers. "At 10 hours/week, this needs 6 months, not 3."
3. Respect autonomy. Present options, let them decide.
4. Never fake enthusiasm. Don't say "Great job!" for vague goals.
5. Never shame. A vague goal is a starting point, not a failure.
6. Trust data over intentions.
7. Tasks must be specific. "Talk to customers" is bad. "Interview 5 users this week" is good.

## CONVERSATION RULES

1. Ask ONE question at a time. Never ask multiple questions in one message.
2. Probe vague goals until they're specific, measurable, and time-bound. "What does 'get fit' mean to you? Give me a number and a date."
3. If the user says "I don't know" to approach or timeline questions, use web search to research realistic timelines and approaches.
4. Assess current state honestly. "Where are you starting from? Be honest — I plan better with real data."
5. Run a feasibility check: Can available time + approach realistically achieve the goal? If not, say so.
6. Set Core and Flex hours explicitly.
7. When you have enough information, present each cascade level using the corresponding tool.
8. After presenting a level, ask the user to review it. Wait for their response before proceeding.
9. If the user requests changes (their message will start with "[REVISION:"), regenerate ONLY that level with their feedback incorporated.
10. Keep messages concise. You're a system, not an essayist.

## CURRENT STATE

Today's date: ${new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
Phase: ${cascadeState}
${stateInstruction}
${contextSection}

IMPORTANT: All plans must account for today's date. Never schedule milestones or tasks in the past. If the current quarter is partially over, start planning from today forward. For example, if it's late February, Q1 milestones should only include what can be done in the remaining time — don't set deadlines in January or early February.

## TOOL USAGE

- present_goal_summary: Call when you've gathered enough info about the goal (title, success criteria, current state, target date, hours)
- present_year_plan: Call after goal is approved. Present year overview with quarterly arc.
- present_quarter_plan: Call after year plan is approved. Present all four quarters with milestones.
- present_month_plan: Call after quarter plan is approved. Present the current month's concrete targets.
- present_week_plan: Call after month plan is approved. Present week 1 with Core/Flex task split and daily blocks.
- present_schedule_summary: Call after week plan is approved and user has provided their preferred morning time and review day. Present their notification schedule for approval.
- web_search: Use when you need to research market data, realistic timelines, competitor info, or validate assumptions. The user has enabled this for market research.

IMPORTANT: Only call ONE plan tool per response. When you call a plan tool, the structured data will be displayed as a card to the user. After calling the tool, write a brief follow-up message asking the user to review — something like "Take a look at the plan above. Does this match what you had in mind, or would you change anything?"
${timezone ? `\n\nUser's timezone (auto-detected): ${timezone}. Include this in the schedule summary.` : ""}`;
}

const ONBOARDING_TOOLS = [
  {
    name: "present_goal_summary",
    description: "Present the user's goal summary for approval. Call this when you've gathered enough information about their goal.",
    input_schema: {
      type: "object",
      properties: {
        title: { type: "string", description: "The main goal title" },
        success_criteria: { type: "string", description: "How success will be measured" },
        current_state: { type: "string", description: "Where the user is starting from" },
        target_date: { type: "string", description: "When they want to achieve this by, in YYYY-MM-DD format (e.g. 2026-10-01)" },
        core_hours: { type: "number", description: "Weekly core hours commitment" },
        flex_hours: { type: "number", description: "Weekly flex hours (bonus)" },
        feasibility_notes: { type: "string", description: "Brief feasibility assessment" },
      },
      required: ["title", "success_criteria", "current_state", "target_date", "core_hours", "flex_hours"],
    },
  },
  {
    name: "present_year_plan",
    description: "Present the year plan with success criteria and quarterly arc. Call after goal is approved.",
    input_schema: {
      type: "object",
      properties: {
        success_criteria: { type: "string", description: "Year-level success criteria" },
        quarterly_arc: {
          type: "array",
          items: {
            type: "object",
            properties: {
              quarter: { type: "string", description: "e.g. Q1, Q2" },
              focus: { type: "string", description: "Main focus for this quarter" },
              milestone: { type: "string", description: "Key milestone to hit" },
            },
            required: ["quarter", "focus", "milestone"],
          },
        },
      },
      required: ["success_criteria", "quarterly_arc"],
    },
  },
  {
    name: "present_quarter_plan",
    description: "Present quarterly milestones. Call after year plan is approved.",
    input_schema: {
      type: "object",
      properties: {
        quarters: {
          type: "array",
          items: {
            type: "object",
            properties: {
              quarter: { type: "string" },
              months: { type: "string", description: "e.g. Jan-Mar" },
              milestones: { type: "array", items: { type: "string" } },
              success_criteria: { type: "string" },
            },
            required: ["quarter", "months", "milestones"],
          },
        },
      },
      required: ["quarters"],
    },
  },
  {
    name: "present_month_plan",
    description: "Present the current month's concrete targets. Call after quarter plan is approved.",
    input_schema: {
      type: "object",
      properties: {
        month: { type: "string", description: "Month name" },
        year: { type: "number" },
        targets: {
          type: "array",
          items: {
            type: "object",
            properties: {
              target: { type: "string" },
              metric: { type: "string" },
              definition_of_done: { type: "string" },
            },
            required: ["target", "definition_of_done"],
          },
        },
      },
      required: ["month", "year", "targets"],
    },
  },
  {
    name: "present_week_plan",
    description: "Present the first week's plan with Core/Flex task separation. Call after month plan is approved.",
    input_schema: {
      type: "object",
      properties: {
        week_of: { type: "string", description: "Week starting date" },
        core_tasks: {
          type: "array",
          items: {
            type: "object",
            properties: {
              title: { type: "string" },
              duration_hours: { type: "number" },
              day: { type: "string", description: "Which day of the week" },
            },
            required: ["title", "duration_hours", "day"],
          },
        },
        flex_tasks: {
          type: "array",
          items: {
            type: "object",
            properties: {
              title: { type: "string" },
              duration_hours: { type: "number" },
            },
            required: ["title", "duration_hours"],
          },
        },
        total_core_hours: { type: "number" },
        total_flex_hours: { type: "number" },
      },
      required: ["week_of", "core_tasks", "flex_tasks", "total_core_hours", "total_flex_hours"],
    },
  },
  {
    name: "present_schedule_summary",
    description: "Present the user's notification schedule for approval. Call after collecting preferred morning time and weekly review day.",
    input_schema: {
      type: "object",
      properties: {
        morning_hour: { type: "number", description: "Preferred morning hour (0-23)" },
        morning_minute: { type: "number", description: "Preferred morning minute (0-59)" },
        review_day: { type: "string", description: "Day name for weekly review (e.g., Sunday, Saturday)" },
        timezone: { type: "string", description: "User's timezone (e.g., America/New_York)" },
      },
      required: ["morning_hour", "morning_minute", "review_day"],
    },
  },
  {
    name: "web_search",
    description: "Search the web for market data, realistic timelines, competitor info, or to validate assumptions. Use when the user says 'I don't know' or needs research.",
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string", description: "The search query" },
      },
      required: ["query"],
    },
  },
];

export async function POST(request) {
  // Origin check (same as demo route)
  const origin = request.headers.get("origin");
  const allowedOrigins = [
    process.env.ALLOWED_ORIGIN,
    "https://cascade-flame.vercel.app",
    "https://cascade-landing-beige.vercel.app",
    process.env.NODE_ENV === "development" && "http://localhost:3000",
  ].filter(Boolean);
  const isVercelPreview = origin && origin.endsWith(".vercel.app") && origin.includes("cascade-landing");
  if (origin && !allowedOrigins.includes(origin) && !isVercelPreview) {
    return new Response("Forbidden", { status: 403 });
  }

  const body = await request.json().catch(() => null);
  if (!body) return new Response("Bad request", { status: 400 });

  const { messages: clientMessages, cascade_state = "exploring", plan_data = {}, user_id, timezone } = body;

  // Rate limit by user_id (fall back to IP if no user_id)
  const rateLimitKey = user_id || request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (!checkRateLimit(rateLimitKey)) {
    return new Response("Rate limit exceeded", { status: 429 });
  }

  if (!Array.isArray(clientMessages) || clientMessages.length === 0) {
    return new Response("Invalid messages", { status: 400 });
  }

  // Sanitize messages — keep last 40 turns for onboarding (longer conversations)
  const sanitizedMessages = clientMessages.slice(-40).reduce((acc, msg) => {
    if (
      (msg.role === "user" || msg.role === "assistant") &&
      typeof msg.content === "string" &&
      msg.content.trim().length > 0 &&
      msg.content.length <= 4000
    ) {
      acc.push({ role: msg.role, content: msg.content.trim() });
    }
    return acc;
  }, []);

  if (sanitizedMessages.length === 0 || sanitizedMessages[sanitizedMessages.length - 1].role !== "user") {
    return new Response("Invalid messages", { status: 400 });
  }

  const systemPrompt = buildSystemPrompt(cascade_state, plan_data, timezone);

  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder();

      function send(data) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      }

      try {
        await startActiveObservation("onboarding-chat", async (trace) => {
          updateActiveTrace({
            name: "onboarding-chat",
            userId: user_id || rateLimitKey,
            input: sanitizedMessages,
            metadata: { cascade_state },
          });

          const tools = ONBOARDING_TOOLS;

          // Claude call — may loop if tool calls need handling
          let currentMessages = [...sanitizedMessages];
          let loopCount = 0;
          const MAX_LOOPS = 4; // Safety: prevent infinite tool loops

          while (loopCount < MAX_LOOPS) {
            loopCount++;

            const generation = startObservation(
              `claude-call-${loopCount}`,
              {
                model: "claude-sonnet-4-6",
                input: currentMessages,
                metadata: { loop: loopCount, cascade_state },
              },
              { asType: "generation" }
            );

            const stream1 = client.messages.stream({
              model: "claude-sonnet-4-6",
              max_tokens: 4000,
              system: systemPrompt,
              messages: currentMessages,
              tools,
              tool_choice: { type: "auto" },
            });

            // Stream text deltas
            stream1.on("text", (delta) => {
              send({ type: "text_delta", text: delta });
            });

            const finalMessage = await stream1.finalMessage();

            generation.update({
              output: finalMessage.content,
              usageDetails: {
                input: finalMessage.usage?.input_tokens,
                output: finalMessage.usage?.output_tokens,
              },
            }).end();

            // If no tool use or end of turn, we're done
            if (finalMessage.stop_reason === "end_turn") {
              break;
            }

            // Collect ALL tool_use blocks (not just the first)
            const toolBlocks = finalMessage.content.filter(
              (block) => block.type === "tool_use"
            );

            if (toolBlocks.length === 0) {
              break;
            }

            // Build tool results for all tool calls
            const toolResults = [];

            for (const toolBlock of toolBlocks) {
              if (PLAN_TOOL_NAMES.includes(toolBlock.name)) {
                // Plan tool — send card to browser
                send({
                  type: "plan_card",
                  card_type: TOOL_TO_CARD_TYPE[toolBlock.name],
                  data: toolBlock.input,
                });

                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolBlock.id,
                  content: "Plan card displayed to user. They will now review it. Write a brief message asking them to review the plan above and let you know if they want to change anything.",
                });
              } else if (toolBlock.name === "web_search") {
                // Execute web search server-side
                let searchResult = "No results found.";
                try {
                  const searchRes = await fetch(
                    `https://api.search.brave.com/res/v1/web/search?q=${encodeURIComponent(toolBlock.input.query)}&count=5`,
                    { headers: { "X-Subscription-Token": process.env.BRAVE_SEARCH_API_KEY } }
                  );
                  if (searchRes.ok) {
                    const searchData = await searchRes.json();
                    searchResult = (searchData.web?.results || [])
                      .slice(0, 5)
                      .map((r) => `- ${r.title}: ${r.description} (${r.url})`)
                      .join("\n");
                  }
                } catch (searchErr) {
                  console.error("Web search failed:", searchErr);
                  searchResult = "Web search unavailable. Please continue with available information.";
                }
                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolBlock.id,
                  content: searchResult,
                });
              } else {
                // Unknown tool — should not happen, but handle gracefully
                toolResults.push({
                  type: "tool_result",
                  tool_use_id: toolBlock.id,
                  content: "Unknown tool. Continuing without result.",
                });
              }
            }

            // Send tool results back to Claude and continue
            currentMessages = [
              ...currentMessages,
              { role: "assistant", content: finalMessage.content },
              { role: "user", content: toolResults },
            ];
          }

          trace.update({ output: "completed" });
        });

        // Flush spans to Langfuse before the serverless function terminates
        await getLangfuseSpanProcessor()?.forceFlush();

        send({ type: "done" });
        controller.close();
      } catch (error) {
        console.error("Onboarding chat error:", error);
        await getLangfuseSpanProcessor()?.forceFlush().catch(() => {});
        send({ type: "error", message: "Something went wrong. Please try again." });
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
