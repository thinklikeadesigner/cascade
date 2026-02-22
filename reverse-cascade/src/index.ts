import express from "express";
import { MemorySaver } from "@langchain/langgraph";
import { buildGraph } from "./graph/graph.js";
import { createRouter } from "./api/routes.js";
import { logger } from "./logger.js";

const PORT = parseInt(process.env.PORT ?? "3456", 10);

async function main() {
  // Phase 1: In-memory checkpointer. Phase 3 will swap in Postgres.
  const checkpointer = new MemorySaver();
  const graph = buildGraph(checkpointer);

  const app = express();
  app.use(express.json());
  app.use(createRouter(graph));

  // Health check
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", service: "reverse-cascade" });
  });

  app.listen(PORT, () => {
    logger.info({ port: PORT }, "Reverse Cascade service started");
  });
}

main().catch((err) => {
  logger.error({ err }, "Failed to start service");
  process.exit(1);
});
