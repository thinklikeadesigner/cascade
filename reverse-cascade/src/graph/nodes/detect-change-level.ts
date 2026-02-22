import type { ReverseCascadeState } from "../state.js";
import { readCascadeFiles } from "../../cascade/file-reader.js";
import type { CascadeLevel } from "../../cascade/level-utils.js";
import { ask } from "../../llm/client.js";
import {
  DETECT_LEVEL_SYSTEM,
  buildDetectLevelPrompt,
} from "../../llm/prompts.js";
import { logger } from "../../logger.js";

export async function detectChangeLevel(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  logger.info(
    { userRequest: state.userRequest, dataDir: state.dataDir },
    "Detecting change level",
  );

  const cascadeFiles = readCascadeFiles(state.dataDir);

  const prompt = buildDetectLevelPrompt(state.userRequest, cascadeFiles);
  const raw = await ask(DETECT_LEVEL_SYSTEM, prompt, state.apiKey);

  // Parse JSON response from Claude
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`Failed to parse level detection response: ${raw}`);
  }

  const parsed = JSON.parse(jsonMatch[0]) as {
    level: CascadeLevel;
    reasoning: string;
  };

  logger.info(
    { level: parsed.level, reasoning: parsed.reasoning },
    "Change level detected",
  );

  return {
    originLevel: parsed.level,
    currentLevel: parsed.level,
    cascadeFiles,
  };
}
