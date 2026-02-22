import type { ReverseCascadeState } from "../state.js";
import { restoreBackups } from "../../cascade/file-writer.js";
import { logger } from "../../logger.js";

/**
 * Handle a rejected change — restore backups and stop.
 */
export async function handleRejection(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  const threadId = state.chatJid;

  logger.info(
    { level: state.currentLevel, threadId },
    "Change rejected, restoring backups",
  );

  const restored = restoreBackups(threadId);
  if (restored.length > 0) {
    logger.info({ count: restored.length }, "Backups restored");
  }

  return {
    propagationStopped: true,
    checkpointMessage: `Changes at ${state.currentLevel} level rejected. All changes rolled back.`,
  };
}
