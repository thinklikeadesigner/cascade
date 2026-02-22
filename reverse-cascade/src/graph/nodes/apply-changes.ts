import type { ReverseCascadeState } from "../state.js";
import type { FileChange } from "../state.js";
import { writeCascadeFile } from "../../cascade/file-writer.js";
import { logger } from "../../logger.js";

/**
 * Writes the approved changes to disk and records them in appliedChanges.
 */
export async function applyChanges(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  const analysis = state.currentAnalysis;
  if (!analysis || !analysis.proposedContent) {
    logger.warn("No analysis to apply");
    return {};
  }

  const fileInfo = state.cascadeFiles[analysis.level];
  if (!fileInfo) {
    logger.warn({ level: analysis.level }, "No file found to write to");
    return {};
  }

  // Write file with backup (threadId is derived from the graph's thread_id config)
  // For now, use chatJid as a simple threadId proxy
  const threadId = state.chatJid;
  writeCascadeFile(fileInfo.path, analysis.proposedContent, threadId);

  logger.info(
    { level: analysis.level, path: fileInfo.path },
    "Changes applied to file",
  );

  const change: FileChange = {
    level: analysis.level,
    filePath: fileInfo.path,
    originalContent: fileInfo.content,
    newContent: analysis.proposedContent,
    summary: analysis.impactSummary,
  };

  // Update cascadeFiles with the new content so subsequent analysis uses it
  const updatedFiles = { ...state.cascadeFiles };
  updatedFiles[analysis.level] = {
    path: fileInfo.path,
    content: analysis.proposedContent,
  };

  return {
    appliedChanges: [change], // Reducer will append
    cascadeFiles: updatedFiles,
  };
}
