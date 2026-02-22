import { Annotation } from "@langchain/langgraph";
import type { CascadeLevel } from "../cascade/level-utils.js";

export interface FileChange {
  level: CascadeLevel;
  filePath: string;
  originalContent: string;
  newContent: string;
  summary: string;
}

export interface Analysis {
  level: CascadeLevel;
  impactSummary: string;
  proposedContent: string;
  requiresPropagation: boolean;
}

export interface ApprovalResponse {
  decision: "approve" | "reject" | "stop" | "modify";
  feedback?: string;
}

export const ReverseCascadeAnnotation = Annotation.Root({
  // Input
  userRequest: Annotation<string>,
  dataDir: Annotation<string>,
  chatJid: Annotation<string>,
  apiKey: Annotation<string>,

  // Level tracking
  originLevel: Annotation<CascadeLevel>,
  currentLevel: Annotation<CascadeLevel>,

  // File state
  cascadeFiles: Annotation<
    Partial<Record<CascadeLevel, { path: string; content: string }>>
  >,

  // Analysis at current level
  currentAnalysis: Annotation<Analysis | null>,

  // Accumulated changes (reducer: append new changes)
  appliedChanges: Annotation<FileChange[]>({
    reducer: (current, update) => [...current, ...update],
    default: () => [],
  }),

  // Approval flow
  lastApprovalResponse: Annotation<ApprovalResponse | null>,

  // Control flags
  propagationStopped: Annotation<boolean>,

  // Message to send to user (for checkpoint)
  checkpointMessage: Annotation<string>,
});

export type ReverseCascadeState = typeof ReverseCascadeAnnotation.State;
