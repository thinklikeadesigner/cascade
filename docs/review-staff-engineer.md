# Staff Engineer Review: NanoClaw Media Implementation Plan

**Reviewer:** Staff Engineer
**Date:** February 19, 2026
**Document:** `docs/nanoclaw-media-plan.md`
**Verdict:** Mostly sound architecture. Several inaccuracies vs. actual codebase, one critical container lifecycle issue, and a few gaps that need addressing before implementation.

---

## Finding 1: Channel Interface Has No `sendImage` — But Also No Common Pattern For It

**Severity:** Medium
**Plan Reference:** Section 1 — "Extend Channel interface"

The plan correctly identifies that `Channel` in `src/types.ts` (line 82) lacks `sendImage`. The proposed addition is straightforward. However, the plan shows:

```typescript
interface Channel {
  sendMessage(jid: string, text: string): Promise<void>;
  sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void>;
  // ... existing methods
}
```

The actual interface is:

```typescript
export interface Channel {
  name: string;
  connect(): Promise<void>;
  sendMessage(jid: string, text: string): Promise<void>;
  isConnected(): boolean;
  ownsJid(jid: string): boolean;
  disconnect(): Promise<void>;
  setTyping?(jid: string, isTyping: boolean): Promise<void>;
}
```

**Issue:** `setTyping` is optional (`setTyping?`). Should `sendImage` be optional too? If only some channels support images, making it optional avoids forcing a no-op implementation on channels that can't send images. But both WhatsApp and Telegram support it, so making it required is fine for now.

**Recommendation:** Make it required. Both target channels support it. If a future channel doesn't, refactor then.

---

## Finding 2: WhatsApp `sendImage` Skips the Outgoing Queue and Prefix Logic

**Severity:** High
**Plan Reference:** Section 2 — "WhatsApp image sending"

The plan proposes:

```typescript
async sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void> {
  await this.sock.sendMessage(jid, {
    image: buffer,
    caption: caption || undefined,
  });
}
```

The actual `sendMessage` in `whatsapp.ts` (lines 226-248) does two critical things the plan omits:

1. **Prefixes bot messages** with `ASSISTANT_NAME` when using a shared phone number (lines 231-233). Captions should receive the same prefix for consistency.
2. **Queues messages when disconnected** (lines 235-238). If `this.connected` is false, messages are pushed to `outgoingQueue` and flushed on reconnect. The plan's `sendImage` would throw if called while disconnected.

**Fix:**
```typescript
async sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void> {
  const prefixedCaption = caption
    ? (ASSISTANT_HAS_OWN_NUMBER ? caption : `${ASSISTANT_NAME}: ${caption}`)
    : undefined;

  if (!this.connected) {
    // Cannot queue binary data in the current text-only queue.
    // Log a warning and drop the image. Alternatively, extend the queue
    // to support image payloads.
    logger.warn({ jid }, 'Cannot send image while disconnected (not queued)');
    return;
  }

  await this.sock.sendMessage(jid, {
    image: buffer,
    caption: prefixedCaption,
  });
}
```

The outgoing queue only supports `{ jid: string; text: string }`. Queuing images requires either extending the queue type or accepting that images sent while disconnected are dropped (with a log). The plan doesn't acknowledge this.

---

## Finding 3: Telegram `sendImage` Uses `this.bot` Directly — But Pool Bots Exist

**Severity:** Medium
**Plan Reference:** Section 3 — "Telegram image sending"

The plan proposes:

```typescript
async sendImage(chatId: string, buffer: Buffer, caption?: string): Promise<void> {
  await this.bot.api.sendDocument(chatId, new InputFile(buffer, 'cascade-status.png'), {
    caption: caption || undefined,
  });
}
```

But `telegram.ts` has a **bot pool system** (`sendPoolMessage` at line 53) used for agent team messages. When a message has a `sender` field and the target is Telegram, IPC routes through `sendPoolMessage` instead of `channel.sendMessage`. The plan's `sendImage` uses the main bot only.

**Issue:** If the agent team architecture is used and images should come from the same bot identity as text messages, the pool system needs `sendDocument` support too.

**Recommendation:** For v1, using the main bot for images is fine — status cards are system-level messages, not individual agent responses. Document this decision so future implementers know pool bot images aren't supported yet.

Also, `this.bot` can be `null` (line 100). Add a null guard like `sendMessage` does (line 270).

---

## Finding 4: IPC Handler Doesn't Handle `type: "image"` — Correct, But the Integration Point is Wrong

**Severity:** High
**Plan Reference:** Section 4 — "IPC image message handler"

The plan proposes adding `case 'image'` to `ipc.ts`. But the actual IPC handler in `ipc.ts` (line 75) checks for `data.type === 'message'` inside the existing message processing loop. The plan's proposed code:

```typescript
case 'image': {
  const imageBuffer = fs.readFileSync(msg.imagePath);
  await channel.sendImage(msg.chatJid, imageBuffer, msg.caption);
  fs.unlinkSync(msg.imagePath);
  break;
}
```

**Issues:**

1. **There is no `switch` statement in the message handler.** The messages dir handler uses `if (data.type === 'message')`. You'd need to add an `else if (data.type === 'image')` — not a `case`.

2. **The handler calls `deps.sendMessage()`** (line 90), not `channel.sendImage()`. The IPC handler doesn't have direct channel access — it uses `deps.sendMessage` from `IpcDeps` (line 19). You'd need to add a `sendImage` method to `IpcDeps`:

```typescript
export interface IpcDeps {
  sendMessage: (jid: string, text: string) => Promise<void>;
  sendImage: (jid: string, buffer: Buffer, caption?: string) => Promise<void>;  // NEW
  // ...
}
```

3. **Authorization check is needed.** The existing message handler checks authorization (lines 77-81): `isMain || (targetGroup && targetGroup.folder === sourceGroup)`. The image handler must do the same.

4. **The `imagePath` points to a file inside the container's IPC mount.** Since the IPC dir is a Docker bind mount, the path `/workspace/ipc/media/weekly-progress.png` maps to `DATA_DIR/ipc/{groupFolder}/media/weekly-progress.png` on the host. The plan correctly relies on bind mounts, but the host code should read from the host-side path, not the container path. The IPC JSON should use a **relative path** (e.g., `media/weekly-progress.png`) that the host resolves against its own IPC directory.

**Fix:** The IPC message schema should use a relative `imagePath`, and the host resolves it:

```typescript
const absolutePath = path.join(ipcBaseDir, sourceGroup, data.imagePath);
const imageBuffer = fs.readFileSync(absolutePath);
```

---

## Finding 5: Container Lifecycle vs. Long-Lived Puppeteer Browser — Critical Mismatch

**Severity:** Critical
**Plan Reference:** Section 7 — "Browser initialization"

The plan proposes:

> "Puppeteer with a long-lived browser process inside the Docker container."

And initializes it at "container startup":

```typescript
let browser: puppeteer.Browser;
async function initBrowser() {
  browser = await puppeteer.launch({ ... });
}
```

**The container is NOT long-lived.** Looking at `container-runner.ts` (line 262), containers are spawned per conversation turn:

```typescript
const container = spawn('docker', containerArgs, { stdio: ['pipe', 'pipe', 'pipe'] });
```

The container runs, processes the query, and exits. It's kept alive between turns via the IPC `waitForIpcMessage` loop (in `index.ts` line 565), but once idle timeout hits, it's killed via `docker stop` (line 369 of `container-runner.ts`). The `IDLE_TIMEOUT` triggers a `_close` sentinel that terminates the process.

**Implications:**

1. **Puppeteer launch cost is paid per conversation**, not once. The "warm path 200-800ms" claim only holds for the second+ renders within a single conversation turn. The first render includes browser launch (~1-3 seconds).
2. **Browser cleanup is implicit** (container exits, process dies). This is actually fine — no orphan browser processes. But the plan should acknowledge this.
3. **For scheduled tasks** (where the container runs, sends a message, and exits), the browser launch + render + exit cycle is: ~2s (browser launch) + ~500ms (render) + cleanup. Not terrible, but the plan's 200-800ms estimate is misleading for the scheduled task use case, which is the primary use case for image generation.

**Recommendation:**

- The approach still works, just with different performance characteristics. Acknowledge that browser launch is per-container, not per-process lifetime.
- Consider lazy initialization: only launch Puppeteer when `render_image` is first called, so conversations that don't generate images don't pay the startup cost.
- For the MCP server (`ipc-mcp-stdio.ts`), Puppeteer is initialized in the **MCP server process**, which is separate from the agent-runner process. The MCP server is spawned by the Claude Code SDK as a child process. Browser initialization here means: MCP server starts -> launches Chromium -> waits for tool calls. This is fine, but the browser lifecycle is tied to the MCP server process, not the container.

---

## Finding 6: `render_image` MCP Tool — Output Path Assumes `media/` Dir Exists

**Severity:** Medium
**Plan Reference:** Section 7 — `render_image` tool

The tool writes to `/workspace/ipc/media/${filename}`. But the plan says to create this directory in `container-runner.ts` (Section 5). Looking at the actual `buildVolumeMounts` in `container-runner.ts` (lines 152-160):

```typescript
const groupIpcDir = path.join(DATA_DIR, 'ipc', group.folder);
fs.mkdirSync(path.join(groupIpcDir, 'messages'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'tasks'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'input'), { recursive: true });
```

The `media/` subdirectory is NOT created. The plan's fix is correct — add `fs.mkdirSync(path.join(groupIpcDir, 'media'), { recursive: true })`. But the MCP tool should also `fs.mkdirSync` defensively inside the container, since the directory creation in `container-runner.ts` might not have run yet (race condition on first ever container spawn).

**Recommendation:** Add `fs.mkdirSync('/workspace/ipc/media', { recursive: true })` inside the `render_image` handler before writing the file.

---

## Finding 7: `send_image` MCP Tool — `currentChatJid` and `currentGroupFolder` Don't Exist

**Severity:** High
**Plan Reference:** Section 7 — `send_image` tool

The plan's `send_image` handler uses:

```typescript
chatJid: currentChatJid,
groupFolder: currentGroupFolder,
```

But looking at the actual MCP server (`ipc-mcp-stdio.ts`), these values come from environment variables (lines 19-21):

```typescript
const chatJid = process.env.NANOCLAW_CHAT_JID!;
const groupFolder = process.env.NANOCLAW_GROUP_FOLDER!;
```

The variables are named `chatJid` and `groupFolder`, not `currentChatJid` and `currentGroupFolder`. This is a minor naming error in the plan, but it matters because copy-pasting the plan's code would produce a `ReferenceError`.

**Fix:** Use `chatJid` and `groupFolder` (the existing module-level constants).

---

## Finding 8: Dockerfile — `puppeteer` vs `puppeteer-core` Inconsistency

**Severity:** Medium
**Plan Reference:** Section 7 — "Container Dockerfile addition" and Dependencies section

The plan's Dockerfile section says:

```dockerfile
RUN npm install puppeteer
```

But the Dependencies section says:

> Use `puppeteer-core` instead of `puppeteer` since Chromium is already installed in the container. No Chromium download.

These contradict each other. `puppeteer` (without `-core`) downloads its own Chromium (~300MB) even with `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true` in newer versions (the env var behavior has changed over time). `puppeteer-core` never downloads Chromium.

**Recommendation:** Use `puppeteer-core` consistently. The Dockerfile should be:

```dockerfile
RUN npm install puppeteer-core
```

And the import should be `import puppeteer from 'puppeteer-core'`.

Also, this should go in the **agent-runner** `package.json`, not a global `npm install` in the Dockerfile. The current build process copies `agent-runner/package*.json` and runs `npm install` (Dockerfile lines 39-42). Adding `puppeteer-core` to `container/agent-runner/package.json` is the correct approach.

---

## Finding 9: Router Needs `routeOutboundImage` — Plan Understates This

**Severity:** Medium
**Plan Reference:** Section 6 — "Router update"

The plan says:

> "If the router handles outbound message formatting, ensure it can pass through image-type messages without stripping them as text."

The router (`src/router.ts`) has `routeOutbound` (line 36):

```typescript
export function routeOutbound(
  channels: Channel[],
  jid: string,
  text: string,
): Promise<void> {
  const channel = channels.find((c) => c.ownsJid(jid) && c.isConnected());
  if (!channel) throw new Error(`No channel for JID: ${jid}`);
  return channel.sendMessage(jid, text);
}
```

This only handles text. You need a new function:

```typescript
export function routeOutboundImage(
  channels: Channel[],
  jid: string,
  buffer: Buffer,
  caption?: string,
): Promise<void> {
  const channel = channels.find((c) => c.ownsJid(jid) && c.isConnected());
  if (!channel) throw new Error(`No channel for JID: ${jid}`);
  return channel.sendImage(jid, buffer, caption);
}
```

The IPC handler should call this instead of directly calling `channel.sendImage`. This keeps the routing logic centralized.

---

## Finding 10: `task-scheduler.ts` Integration is Vague

**Severity:** Medium
**Plan Reference:** Section 10 — "Scheduled task integration"

The plan says:

> "Update the scheduled task handlers to: 1. Generate status card HTML from data, 2. Render to PNG via the container, 3. Send image + text summary"

Looking at `task-scheduler.ts`, scheduled tasks run by spawning a full container with a prompt (lines 105-128 in `runTask`). The scheduled task system doesn't directly generate images — it tells the agent to do something, and the agent uses MCP tools.

**This means:** The "update" is actually just updating the scheduled task **prompt** to include instructions like "generate and send a visual weekly review card." The agent inside the container then uses `render_image` and `send_image` MCP tools. No code changes to `task-scheduler.ts` are needed.

The plan conflates "updating the scheduled task handler" with "updating the scheduled task prompt." This should be clarified — it's a prompt/skill change, not a code change.

---

## Finding 11: WhatsApp 24-Hour Session Window Section is Misleading

**Severity:** Low
**Plan Reference:** "WhatsApp-Specific Considerations"

The plan discusses the WhatsApp 24-hour session window and template pre-approval via Meta Business Manager. But NanoClaw uses **Baileys** (WhatsApp Web protocol), not the **Meta Cloud API** (Business API). Baileys operates as a WhatsApp Web client, which does NOT have the 24-hour session window restriction. That restriction applies to the Business API only.

The plan's "Recommended API Path" section even says:

> "Start with direct Meta Cloud API (not Twilio)" ... "Baileys wraps the WhatsApp Web protocol"

These are contradictory. Baileys IS the WhatsApp Web protocol. The Meta Cloud API is a different thing entirely.

**Bottom line:** The 24-hour window discussion and template pre-approval section are irrelevant for Baileys-based implementations. Remove or mark as "future consideration if migrating to Business API."

---

## Finding 12: No Graceful Fallback if Puppeteer Fails to Launch

**Severity:** Medium
**Plan Reference:** Section 7

If Chromium fails to launch inside the container (OOM, missing libs after an apt update, sandbox issues), the `render_image` MCP tool will throw an unhandled error. The MCP SDK will return an error to the agent, but the plan's skill definition says:

> "If rendering fails, fall back to text-only output"

This fallback logic lives in the **skill prompt**, meaning it depends on the agent correctly interpreting the error and deciding to send text instead. This is fragile — LLMs can loop on errors.

**Recommendation:** Add explicit error handling in the `render_image` tool that returns a structured error:

```typescript
try {
  // ... render logic
} catch (err) {
  return {
    content: [{ type: 'text', text: `Rendering failed: ${err.message}. Send text-only instead.` }],
    isError: true,
  };
}
```

---

## Finding 13: Templates in Cascade Repo, Not in Container

**Severity:** Low
**Plan Reference:** Section 8 — "Status card HTML templates"

Templates are proposed at `cascade/templates/cards/`. But the container's access to Cascade data is via an additional mount (configured per-group in `containerConfig.additionalMounts`). The templates need to be accessible inside the container.

Two options:
1. Mount `cascade/templates/` as an additional read-only volume
2. Embed templates in the skill definition (as the plan partially suggests in the skill markdown)

The plan's skill definition includes "[Include condensed versions of each template with data injection points]" — this suggests embedding templates in the skill. If so, the separate template files in `cascade/templates/cards/` become development/preview artifacts, not runtime dependencies. This is fine but should be clarified.

**Recommendation:** Embed templates in the skill markdown. The agent reads the skill, has the template, generates HTML, renders it. No additional mount needed.

---

## Summary Table

| # | Finding | Severity | Type |
|---|---------|----------|------|
| 1 | Channel interface `sendImage` optionality | Medium | Design |
| 2 | WhatsApp `sendImage` skips queue + prefix logic | High | Bug Risk |
| 3 | Telegram pool bots lack image support | Medium | Gap |
| 4 | IPC handler integration point is wrong (no switch, no channel access, path resolution) | High | Incorrect |
| 5 | Container lifecycle vs. long-lived Puppeteer — containers are ephemeral | Critical | Architecture |
| 6 | `media/` directory not created in container-runner | Medium | Bug Risk |
| 7 | `currentChatJid`/`currentGroupFolder` don't exist — wrong variable names | High | Incorrect |
| 8 | Dockerfile says `puppeteer` but deps section says `puppeteer-core` | Medium | Inconsistency |
| 9 | Router needs `routeOutboundImage`, plan understates this | Medium | Gap |
| 10 | task-scheduler.ts doesn't need code changes, just prompt updates | Medium | Misleading |
| 11 | WhatsApp 24-hour window is irrelevant for Baileys | Low | Incorrect |
| 12 | No graceful Puppeteer failure handling | Medium | Gap |
| 13 | Template location ambiguity (cascade repo vs. embedded in skill) | Low | Clarity |

---

## Overall Assessment

The plan's architecture is fundamentally sound — the data flow (agent generates HTML -> Puppeteer renders PNG -> IPC sends to host -> channel delivers) is correct and leverages the existing IPC infrastructure well. The decision to render inside the container is the right call given Chromium is already there.

The critical issue is the container lifecycle misunderstanding. The plan assumes a long-lived browser process, but containers are ephemeral (per-conversation, killed after idle timeout). This doesn't break the design — it just changes the performance profile. Lazy browser initialization in the MCP server process is the right mitigation.

The high-severity findings are implementation details that would cause bugs if the plan's code snippets were copied verbatim. The IPC handler integration (Finding 4) needs the most rework — the plan's code doesn't match the actual code structure.

**Recommended implementation order (revised):**

1. Add `sendImage` to Channel interface (`types.ts`)
2. Implement in WhatsApp channel (with queue/prefix considerations) and Telegram channel (with null guard)
3. Add `sendImage` to `IpcDeps` and handle `type: "image"` in IPC watcher (with auth + correct path resolution)
4. Add `routeOutboundImage` to router
5. Add `puppeteer-core` to agent-runner `package.json`
6. Add `render_image` and `send_image` MCP tools with lazy browser init and error handling
7. Create `media/` dir in `container-runner.ts`
8. Build templates and embed in skill definition
9. Test end-to-end
