import type { ReverseCascadeState } from "../state.js";
import type { Analysis } from "../state.js";
import type { CascadeLevel } from "../../cascade/level-utils.js";
import { ask } from "../../llm/client.js";
import {
  ANALYZE_IMPACT_SYSTEM,
  buildAnalyzeImpactPrompt,
} from "../../llm/prompts.js";
import { logger } from "../../logger.js";

export async function analyzeImpact(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  const level = state.currentLevel;
  const fileInfo = state.cascadeFiles[level];

  if (!fileInfo) {
    logger.warn({ level }, "No file found for level, skipping analysis");
    return {
      currentAnalysis: {
        level,
        impactSummary: `No file found for ${level} level`,
        proposedContent: "",
        requiresPropagation: false,
      },
    };
  }

  logger.info({ level, file: fileInfo.path }, "Analyzing impact");

  const changesContext = state.appliedChanges.map((c) => ({
    level: c.level,
    summary: c.summary,
    content: c.newContent,
  }));

  const prompt = buildAnalyzeImpactPrompt(
    state.userRequest,
    level,
    fileInfo.content,
    changesContext,
  );

  const raw = await ask(ANALYZE_IMPACT_SYSTEM, prompt, state.apiKey);

  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`Failed to parse impact analysis response: ${raw}`);
  }

  const parsed = JSON.parse(jsonMatch[0]) as {
    impactSummary: string;
    proposedContent: string;
    requiresPropagation: boolean;
    reasoning: string;
  };

  const analysis: Analysis = {
    level,
    impactSummary: parsed.impactSummary,
    proposedContent: parsed.proposedContent,
    requiresPropagation: parsed.requiresPropagation,
  };

  logger.info(
    {
      level,
      requiresPropagation: analysis.requiresPropagation,
      summary: analysis.impactSummary,
    },
    "Impact analysis complete",
  );

  // Build a human-readable checkpoint message
  const checkpointMessage = formatCheckpointMessage(level, analysis);

  return {
    currentAnalysis: analysis,
    checkpointMessage,
  };
}

function formatCheckpointMessage(
  level: CascadeLevel,
  analysis: Analysis,
): string {
  return [
    `*Reverse Cascade — ${level.toUpperCase()} level*`,
    "",
    `*Impact:* ${analysis.impactSummary}`,
    "",
    `*Proposed changes:*`,
    "```",
    analysis.proposedContent.slice(0, 1500) +
      (analysis.proposedContent.length > 1500 ? "\n..." : ""),
    "```",
    "",
    `Reply with:`,
    `• *approve* — accept and continue cascading up`,
    `• *reject* — discard changes, stop`,
    `• *stop* — accept changes but don't cascade further`,
    `• *modify: [your feedback]* — revise the proposal`,
  ].join("\n");
}
