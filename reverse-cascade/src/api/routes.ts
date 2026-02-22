import { Router, type Request, type Response } from "express";

type Params = { threadId: string };
import { randomUUID } from "node:crypto";
import { Command } from "@langchain/langgraph";
import type { ReverseCascadeGraph } from "../graph/graph.js";
import type { ApprovalResponse } from "../graph/state.js";
import {
  createSession,
  getSession,
  touchSession,
  deleteSession,
} from "../sessions/session-manager.js";
import { cleanupBackups } from "../cascade/file-writer.js";
import { logger } from "../logger.js";

export function createRouter(graph: ReverseCascadeGraph): Router {
  const router = Router();

  /**
   * POST /api/reprioritize
   * Start a new reverse cascade session.
   * Body: { chatJid, userRequest, dataDir }
   */
  router.post("/api/reprioritize", async (req: Request, res: Response) => {
    try {
      const { chatJid, userRequest, dataDir, apiKey } = req.body;

      if (!chatJid || !userRequest || !dataDir || !apiKey) {
        res.status(400).json({
          error: "Missing required fields: chatJid, userRequest, dataDir, apiKey",
        });
        return;
      }

      const threadId = randomUUID();

      createSession(threadId, chatJid);

      logger.info({ threadId, chatJid, userRequest }, "Starting reverse cascade (BYOK)");

      // Run graph until first interrupt (checkpoint_approval)
      const config = { configurable: { thread_id: threadId } };
      const result = await graph.invoke(
        {
          userRequest,
          dataDir,
          chatJid,
          apiKey,
          propagationStopped: false,
          appliedChanges: [],
          currentAnalysis: null,
          lastApprovalResponse: null,
          checkpointMessage: "",
          cascadeFiles: {},
        },
        config,
      );

      // Graph paused at interrupt — get the checkpoint message
      const state = await graph.getState(config);

      res.json({
        threadId,
        status: "awaiting_approval",
        checkpoint: {
          level: result.currentLevel,
          message: result.checkpointMessage,
        },
        // Include interrupt info if available
        next: state.next,
      });
    } catch (err: any) {
      logger.error({ err }, "Failed to start reverse cascade");
      res.status(500).json({ error: err.message });
    }
  });

  /**
   * POST /api/reprioritize/:threadId/respond
   * Send approval/rejection for current checkpoint.
   * Body: { decision: "approve"|"reject"|"stop"|"modify", feedback?: string }
   */
  router.post(
    "/api/reprioritize/:threadId/respond",
    async (req: Request<Params>, res: Response) => {
      try {
        const threadId = req.params.threadId;
        const { decision, feedback } = req.body as ApprovalResponse;

        if (!decision) {
          res.status(400).json({ error: "Missing required field: decision" });
          return;
        }

        const session = getSession(threadId);
        if (!session) {
          res.status(404).json({ error: "Session not found or expired" });
          return;
        }

        touchSession(threadId);

        logger.info({ threadId, decision, feedback }, "Resuming with user response");

        const config = { configurable: { thread_id: threadId } };

        // Resume the graph from the interrupt with the user's decision
        const response: ApprovalResponse = { decision, feedback };
        const result = await graph.invoke(
          new Command({ resume: response }),
          config,
        );

        const state = await graph.getState(config);
        const isComplete = !state.next || state.next.length === 0;

        if (isComplete) {
          deleteSession(threadId);
          res.json({
            threadId,
            status: "completed",
            appliedChanges: result.appliedChanges?.map(
              (c: { level: string; summary: string }) => ({
                level: c.level,
                summary: c.summary,
              }),
            ),
          });
        } else {
          res.json({
            threadId,
            status: "awaiting_approval",
            checkpoint: {
              level: result.currentLevel,
              message: result.checkpointMessage,
            },
            next: state.next,
          });
        }
      } catch (err: any) {
        logger.error({ err }, "Failed to process response");
        res.status(500).json({ error: err.message });
      }
    },
  );

  /**
   * GET /api/reprioritize/:threadId/status
   * Check session progress.
   */
  router.get(
    "/api/reprioritize/:threadId/status",
    async (req: Request<Params>, res: Response) => {
      try {
        const threadId = req.params.threadId;
        const session = getSession(threadId);

        if (!session) {
          res.status(404).json({ error: "Session not found or expired" });
          return;
        }

        const config = { configurable: { thread_id: threadId } };
        const state = await graph.getState(config);

        res.json({
          threadId,
          chatJid: session.chatJid,
          startedAt: session.startedAt,
          lastActivity: session.lastActivity,
          currentLevel: state.values?.currentLevel,
          appliedChanges: state.values?.appliedChanges?.length ?? 0,
          isWaiting: state.next && state.next.length > 0,
          next: state.next,
        });
      } catch (err: any) {
        logger.error({ err }, "Failed to get status");
        res.status(500).json({ error: err.message });
      }
    },
  );

  /**
   * DELETE /api/reprioritize/:threadId
   * Cancel session and rollback all changes.
   */
  router.delete(
    "/api/reprioritize/:threadId",
    async (req: Request<Params>, res: Response) => {
      try {
        const threadId = req.params.threadId;
        const session = getSession(threadId);

        if (!session) {
          res.status(404).json({ error: "Session not found or expired" });
          return;
        }

        // Restore backups
        cleanupBackups(threadId);
        deleteSession(threadId);

        logger.info({ threadId }, "Session cancelled and cleaned up");
        res.json({ threadId, status: "cancelled" });
      } catch (err: any) {
        logger.error({ err }, "Failed to cancel session");
        res.status(500).json({ error: err.message });
      }
    },
  );

  return router;
}
