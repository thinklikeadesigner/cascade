import { logger } from "../logger.js";

interface Session {
  threadId: string;
  chatJid: string;
  startedAt: Date;
  lastActivity: Date;
}

const SESSION_EXPIRY_MS = 24 * 60 * 60 * 1000; // 24 hours

/** In-memory session store. Will be replaced with Supabase in Phase 3. */
const sessions = new Map<string, Session>();

export function createSession(
  threadId: string,
  chatJid: string,
): Session {
  // Check for existing active session for this chatJid
  const existing = getSessionByChatJid(chatJid);
  if (existing) {
    throw new Error(
      `Active session already exists for ${chatJid}: ${existing.threadId}. ` +
        `Cancel it first or wait for it to complete.`,
    );
  }

  const session: Session = {
    threadId,
    chatJid,
    startedAt: new Date(),
    lastActivity: new Date(),
  };

  sessions.set(threadId, session);
  logger.info({ threadId, chatJid }, "Session created");
  return session;
}

export function getSession(threadId: string): Session | undefined {
  const session = sessions.get(threadId);
  if (session && isExpired(session)) {
    sessions.delete(threadId);
    logger.info({ threadId }, "Session expired");
    return undefined;
  }
  return session;
}

export function getSessionByChatJid(chatJid: string): Session | undefined {
  for (const session of sessions.values()) {
    if (session.chatJid === chatJid && !isExpired(session)) {
      return session;
    }
  }
  return undefined;
}

export function touchSession(threadId: string): void {
  const session = sessions.get(threadId);
  if (session) {
    session.lastActivity = new Date();
  }
}

export function deleteSession(threadId: string): void {
  sessions.delete(threadId);
  logger.info({ threadId }, "Session deleted");
}

function isExpired(session: Session): boolean {
  return Date.now() - session.lastActivity.getTime() > SESSION_EXPIRY_MS;
}
