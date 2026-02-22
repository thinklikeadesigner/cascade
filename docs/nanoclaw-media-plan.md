# NanoClaw Media: Image Generation & Sending Implementation Plan

**Date:** February 19, 2026
**Revised:** February 20, 2026 (post-review — incorporates findings from staff, security, and QA engineer reviews)
**Status:** Ready for implementation
**Scope:** Enable NanoClaw to generate HTML status cards, render them to PNG, and send images via WhatsApp and Telegram.

---

## Executive Summary

NanoClaw currently sends text-only messages. This plan adds:
1. **HTML-to-PNG rendering** inside the existing Docker container (Chromium is already installed)
2. **Image sending** via WhatsApp (Baileys) and Telegram (grammy) — both libraries already support it, just not wired up
3. **Status card templates** embedded in a skill definition for automated visual reports
4. **`render_image` and `send_image` MCP tools** so the Claude agent can trigger image generation and sending
5. **A `cascade-media` skill** teaching the agent when and how to generate visual cards

The gap is narrow — most of the infrastructure exists. This is a wiring job + templates.

---

## Architecture

### Data Flow

```
Agent reads Cascade data (tracker.csv, week-*.md, monthly targets)
  │
  ▼
Agent HTML-escapes all user data values
  │
  ▼
Agent generates HTML from template (token replacement with escaped values)
  │
  ▼
Agent calls render_image MCP tool
  → Puppeteer (lazy-initialized, JS disabled, network blocked)
  → Renders HTML to PNG buffer
  → Validates file size (< 4MB)
  │
  ▼
Agent calls send_image MCP tool
  → Validates path is within /workspace/ipc/media/
  → Writes IPC JSON via atomic writeIpcFile() helper
  │
  ▼
NanoClaw host (ipc.ts) picks up IPC file
  → Validates imagePath is within expected media dir (realpathSync)
  → Checks authorization (same pattern as text messages)
  → Reads PNG buffer
  │
  ▼
Host calls routeOutboundImage(channels, jid, buffer, caption)
  │
  ▼
Baileys (WhatsApp) or grammy (Telegram) delivers image to user
  → On failure: falls back to text-only caption
  → Always: cleans up PNG file in finally block
```

### Key Decision: Render Inside Container

**Puppeteer-core with lazy-initialized browser** inside the Docker container. The container already has Chromium installed. No new system dependencies.

**Container lifecycle reality:** Containers are ephemeral — spawned per conversation, killed after idle timeout. The browser is NOT long-lived across conversations. It is lazy-initialized on the first `render_image` call within a session, then reused for subsequent renders in the same session. When the container exits, the browser dies with it (no orphan cleanup needed).

**Performance characteristics:**
- **First render per session:** ~2-3s (browser launch + render + capture)
- **Subsequent renders in same session:** ~200-800ms (browser reused, new page per render)
- **Scheduled tasks (single render + exit):** ~2.5-3.5s total. Acceptable for async messaging.

**Security hardening:**
- `page.setJavaScriptEnabled(false)` — templates are pure CSS, no JS needed. Eliminates script injection.
- Network requests blocked via request interception — prevents data exfiltration from rendered HTML.
- `--no-sandbox` is required in Docker but acceptable because JS is disabled.

Fallback: if templates end up being simple Flexbox-only, evaluate Satori + resvg (~10-50ms, no browser, no Chromium attack surface) in a future iteration.

---

## Implementation: 11 Changes Across 2 Repos

### Phase 1: Plumbing (NanoClaw repo — 7 files)

#### 1. Extend Channel interface
**File:** `nanoclaw/src/types.ts`

Add `sendImage` as an **optional** method on the Channel interface. This avoids breaking any future channel implementations that don't support images.

```typescript
export interface Channel {
  name: string;
  connect(): Promise<void>;
  sendMessage(jid: string, text: string): Promise<void>;
  sendImage?(jid: string, buffer: Buffer, caption?: string): Promise<void>;  // NEW — optional
  isConnected(): boolean;
  ownsJid(jid: string): boolean;
  disconnect(): Promise<void>;
  setTyping?(jid: string, isTyping: boolean): Promise<void>;
}
```

#### 2. WhatsApp image sending
**File:** `nanoclaw/src/channels/whatsapp.ts`

Implement `sendImage` using Baileys. Must match the patterns of existing `sendMessage`: handle the `ASSISTANT_NAME` prefix for shared phone numbers, and handle disconnected state gracefully (images cannot be queued in the current text-only `outgoingQueue`).

```typescript
async sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void> {
  const prefixedCaption = caption
    ? (ASSISTANT_HAS_OWN_NUMBER ? caption : `${ASSISTANT_NAME}: ${caption}`)
    : undefined;

  if (!this.connected) {
    // Current outgoingQueue only supports text. Log and drop image.
    // User will still get the text caption via fallback in the IPC handler.
    logger.warn({ jid }, 'Cannot send image while disconnected (not queued)');
    return;
  }

  await this.sock.sendMessage(jid, {
    image: buffer,
    caption: prefixedCaption,
  });
}
```

**Note:** Baileys uses the WhatsApp Web protocol. There is no 24-hour session window or template pre-approval requirement. Those constraints apply only to the Meta Cloud API / Business API, which NanoClaw does not use.

#### 3. Telegram image sending
**File:** `nanoclaw/src/channels/telegram.ts`

Implement `sendImage` using grammy. Default to `sendPhoto` for inline display (better UX — image shows directly in chat). The Telegram JPEG compression is acceptable at phone screen resolution. Provide `sendDocument` as a fallback for when pixel-perfect quality is needed.

```typescript
import { InputFile } from 'grammy';

async sendImage(chatId: string, buffer: Buffer, caption?: string): Promise<void> {
  if (!this.bot) {
    logger.warn({ chatId }, 'Telegram bot not initialized, cannot send image');
    return;
  }

  await this.bot.api.sendPhoto(chatId, new InputFile(buffer, 'cascade-status.png'), {
    caption: caption || undefined,
  });
}
```

**UX rationale (revised from v1):** `sendDocument` preserves PNG quality but requires users to tap "Download" then open the file — 2-3 taps on mobile. `sendPhoto` displays inline in the chat (zero taps). For daily status cards that are part of the morning rhythm, inline display matters more than pixel-perfect quality. At phone resolution, JPEG compression artifacts on a dark-background status card are not visually noticeable.

**Note:** The bot pool system (`sendPoolMessage`) is text-only. Status card images are system-level messages sent via the main bot, not individual agent responses. Pool bot image support is out of scope for v1.

#### 4. IPC image message handler
**File:** `nanoclaw/src/ipc.ts`

Two changes:

**a) Add `sendImage` to `IpcDeps` interface:**

```typescript
export interface IpcDeps {
  sendMessage: (jid: string, text: string) => Promise<void>;
  sendImage: (jid: string, buffer: Buffer, caption?: string) => Promise<void>;  // NEW
  // ... existing methods
}
```

**b) Handle `type: "image"` in the IPC message processor.** The current code uses `if (data.type === 'message')` — add an `else if` for images. Must include:
- **Authorization check** (same `isMain || sourceGroup === targetFolder` pattern as text messages)
- **Path validation** (prevent path traversal — resolve with `realpathSync`, verify prefix)
- **try/finally cleanup** (always delete the PNG, even on send failure)
- **Fallback to text** (if `sendImage` fails or isn't supported, send caption as text)

```typescript
else if (data.type === 'image' && data.chatJid && data.imagePath) {
  // Authorization check — same as text messages
  const targetGroup = registeredGroups[data.chatJid];
  if (!isMain && (!targetGroup || targetGroup.folder !== sourceGroup)) {
    logger.warn({ chatJid: data.chatJid, sourceGroup }, 'Unauthorized IPC image attempt blocked');
    return;
  }

  // Path traversal prevention — resolve symlinks and verify prefix
  const expectedPrefix = path.join(DATA_DIR, 'ipc', sourceGroup, 'media');
  let resolvedPath: string;
  try {
    resolvedPath = fs.realpathSync(data.imagePath);
  } catch {
    logger.warn({ imagePath: data.imagePath }, 'Image path does not exist');
    return;
  }
  if (!resolvedPath.startsWith(expectedPrefix)) {
    logger.warn({ imagePath: data.imagePath, resolvedPath, expectedPrefix }, 'Path traversal attempt blocked');
    return;
  }

  // Send image with cleanup in finally
  try {
    const imageBuffer = fs.readFileSync(resolvedPath);
    await deps.sendImage(data.chatJid, imageBuffer, data.caption);
  } catch (err) {
    // Fallback to text-only caption
    logger.error({ err, chatJid: data.chatJid }, 'Image send failed, falling back to text');
    if (data.caption) {
      await deps.sendMessage(data.chatJid, data.caption);
    }
  } finally {
    // Always clean up the PNG file
    try { fs.unlinkSync(resolvedPath); } catch {}
  }
}
```

**IPC message schema** — uses **relative** path (container writes relative, host resolves against its own IPC dir):

```json
{
  "type": "image",
  "chatJid": "120363336345536173@g.us",
  "imagePath": "media/weekly-progress-1708345800000-a3f2c1.png",
  "caption": "Week 2 Progress — Core: 56%",
  "groupFolder": "main",
  "timestamp": "2026-02-19T15:30:00.000Z"
}
```

The host resolves the path: `path.join(DATA_DIR, 'ipc', sourceGroup, data.imagePath)`.

#### 5. Ensure media directory in IPC mount
**File:** `nanoclaw/src/container-runner.ts`

In `buildVolumeMounts()`, add `media/` alongside existing `messages/`, `tasks/`, `input/`:

```typescript
const groupIpcDir = path.join(DATA_DIR, 'ipc', group.folder);
fs.mkdirSync(path.join(groupIpcDir, 'messages'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'tasks'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'input'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'media'), { recursive: true });  // NEW
```

Also add to the Dockerfile:
```dockerfile
RUN mkdir -p /workspace/ipc/messages /workspace/ipc/tasks /workspace/ipc/input /workspace/ipc/media
```

#### 6. Router — add `routeOutboundImage`
**File:** `nanoclaw/src/router.ts`

Add a new routing function for images, parallel to existing `routeOutbound`:

```typescript
export async function routeOutboundImage(
  channels: Channel[],
  jid: string,
  buffer: Buffer,
  caption?: string,
): Promise<void> {
  const channel = channels.find((c) => c.ownsJid(jid) && c.isConnected());
  if (!channel) throw new Error(`No connected channel for JID: ${jid}`);

  if (typeof channel.sendImage === 'function') {
    await channel.sendImage(jid, buffer, caption);
  } else {
    // Channel doesn't support images — send text caption only
    await channel.sendMessage(jid, caption || '[Image not supported on this channel]');
  }
}
```

The IPC handler calls `routeOutboundImage` instead of `deps.sendImage` directly. This keeps routing logic centralized.

#### 7. Wire up `sendImage` in IpcDeps
**File:** Where `IpcDeps` is constructed (likely `src/index.ts` or wherever the IPC watcher is initialized)

```typescript
const ipcDeps: IpcDeps = {
  sendMessage: (jid, text) => routeOutbound(channels, jid, text),
  sendImage: (jid, buffer, caption) => routeOutboundImage(channels, jid, buffer, caption),  // NEW
  // ... existing deps
};
```

---

### Phase 2: Container MCP Tools (NanoClaw repo — 2 files)

#### 8. Add `render_image` and `send_image` MCP tools
**File:** `nanoclaw/container/agent-runner/src/ipc-mcp-stdio.ts`

Two new MCP tools. Key security/reliability measures baked in:

**Browser initialization — lazy, with cleanup:**

```typescript
import puppeteer from 'puppeteer-core';
import type { Browser, Page } from 'puppeteer-core';

let browser: Browser | null = null;

async function getBrowser(): Promise<Browser> {
  if (!browser || !browser.connected) {
    browser = await puppeteer.launch({
      headless: true,
      executablePath: '/usr/bin/chromium',
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    });
  }
  return browser;
}

// Cleanup on process exit — prevent orphan Chromium processes
process.on('exit', () => { try { browser?.close(); } catch {} });
process.on('SIGTERM', () => { try { browser?.close(); } catch {} process.exit(0); });
```

**Rate limiter:**

```typescript
const renderTimestamps: number[] = [];
const MAX_RENDERS_PER_MINUTE = 10;
const MAX_SENDS_PER_MINUTE = 5;
const sendTimestamps: number[] = [];

function checkRateLimit(timestamps: number[], max: number, label: string): string | null {
  const now = Date.now();
  // Prune old entries
  while (timestamps.length > 0 && timestamps[0] < now - 60000) timestamps.shift();
  if (timestamps.length >= max) {
    return `Rate limit: max ${max} ${label} per minute`;
  }
  timestamps.push(now);
  return null;
}
```

**`render_image`** — HTML string to PNG file:

```typescript
{
  name: 'render_image',
  description: 'Render an HTML string to a PNG image file. Returns the file path. All user data values in the HTML MUST be HTML-escaped before injection.',
  inputSchema: {
    type: 'object',
    properties: {
      html: { type: 'string', description: 'Full HTML document string to render. All dynamic values must be HTML-escaped.' },
      width: { type: 'number', description: 'Viewport width in pixels (100-2400)', default: 1200 },
      height: { type: 'number', description: 'Viewport height in pixels (100-2000)', default: 800 },
    },
    required: ['html'],
  },
  handler: async ({ html, width = 1200, height = 800 }) => {
    // Rate limit
    const rateLimitErr = checkRateLimit(renderTimestamps, MAX_RENDERS_PER_MINUTE, 'renders');
    if (rateLimitErr) return { content: [{ type: 'text', text: rateLimitErr }], isError: true };

    // Input validation — HTML size
    const MAX_HTML_SIZE = 512 * 1024; // 512 KB
    if (html.length > MAX_HTML_SIZE) {
      return { content: [{ type: 'text', text: `HTML too large: ${html.length} bytes (max ${MAX_HTML_SIZE})` }], isError: true };
    }

    // Input validation — viewport dimensions
    const clampedWidth = Math.min(Math.max(width, 100), 2400);
    const clampedHeight = Math.min(Math.max(height, 100), 2000);

    // Generate unique filename (prevents collisions and path injection)
    const safeFilename = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}.png`;
    const outputPath = `/workspace/ipc/media/${safeFilename}`;

    // Ensure media directory exists
    fs.mkdirSync('/workspace/ipc/media', { recursive: true });

    let page: Page | null = null;
    try {
      const b = await getBrowser();
      page = await b.newPage();
      await page.setViewport({ width: clampedWidth, height: clampedHeight, deviceScaleFactor: 2 });

      // SECURITY: Disable JavaScript — templates are pure CSS, no JS needed.
      // Prevents script injection via user data in templates.
      await page.setJavaScriptEnabled(false);

      // SECURITY: Block all network requests — prevents data exfiltration via
      // injected <img src="https://evil.com/..."> or @import url("https://evil.com/...")
      await page.setRequestInterception(true);
      page.on('request', (req) => {
        if (req.url().startsWith('data:')) {
          req.continue(); // Allow data: URIs (inline fonts, inline images)
        } else {
          req.abort();    // Block everything else (network, file://)
        }
      });

      await page.setContent(html, { waitUntil: 'domcontentloaded' });

      // Screenshot with timeout
      const RENDER_TIMEOUT = 10000; // 10 seconds
      const buffer = await Promise.race([
        page.screenshot({ path: outputPath, type: 'png', optimizeForSpeed: true }),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Render timeout (10s)')), RENDER_TIMEOUT)
        ),
      ]);

      // Validate output file size
      const stats = fs.statSync(outputPath);
      const MAX_FILE_SIZE = 4 * 1024 * 1024; // 4 MB (WhatsApp limit is 5 MB, leave margin)
      if (stats.size > MAX_FILE_SIZE) {
        // Re-render at deviceScaleFactor: 1 for smaller file
        await page.setViewport({ width: clampedWidth, height: clampedHeight, deviceScaleFactor: 1 });
        await page.setContent(html, { waitUntil: 'domcontentloaded' });
        await page.screenshot({ path: outputPath, type: 'png', optimizeForSpeed: true });
        const retryStats = fs.statSync(outputPath);
        if (retryStats.size > MAX_FILE_SIZE) {
          fs.unlinkSync(outputPath);
          return { content: [{ type: 'text', text: `Image too large (${retryStats.size} bytes) even at 1x scale. Simplify the template.` }], isError: true };
        }
      }

      // Return relative path (container-relative) for use with send_image
      return { content: [{ type: 'text', text: JSON.stringify({ path: `media/${safeFilename}` }) }] };

    } catch (err: any) {
      // Clean up on failure
      try { fs.unlinkSync(outputPath); } catch {}
      return { content: [{ type: 'text', text: `Rendering failed: ${err.message}. Send text-only instead.` }], isError: true };
    } finally {
      if (page) { try { await page.close(); } catch {} }
    }
  },
}
```

**`send_image`** — send a rendered PNG via IPC:

```typescript
{
  name: 'send_image',
  description: 'Send a rendered PNG image to the chat. Use render_image first to create the PNG.',
  inputSchema: {
    type: 'object',
    properties: {
      image_path: { type: 'string', description: 'Relative path from render_image (e.g., "media/1708345800000-a3f2c1.png")' },
      caption: { type: 'string', description: 'Caption text to send with the image. Keep under 100 words.' },
    },
    required: ['image_path'],
  },
  handler: async ({ image_path, caption }) => {
    // Rate limit
    const rateLimitErr = checkRateLimit(sendTimestamps, MAX_SENDS_PER_MINUTE, 'sends');
    if (rateLimitErr) return { content: [{ type: 'text', text: rateLimitErr }], isError: true };

    // SECURITY: Path validation — must be within /workspace/ipc/media/
    const fullPath = path.resolve('/workspace/ipc', image_path);
    if (!fullPath.startsWith('/workspace/ipc/media/')) {
      return { content: [{ type: 'text', text: 'image_path must be within media/ directory' }], isError: true };
    }

    // Verify file exists
    if (!fs.existsSync(fullPath)) {
      return { content: [{ type: 'text', text: `Image file not found: ${image_path}` }], isError: true };
    }

    // Write IPC file using atomic writeIpcFile helper
    const ipcMessage = {
      type: 'image',
      chatJid: chatJid,          // Module-level constant from process.env.NANOCLAW_CHAT_JID
      imagePath: image_path,     // Relative path — host resolves against its own IPC dir
      caption: caption || '',
      groupFolder: groupFolder,  // Module-level constant from process.env.NANOCLAW_GROUP_FOLDER
      timestamp: new Date().toISOString(),
    };
    writeIpcFile(MESSAGES_DIR, ipcMessage);  // Atomic write (temp file + rename)
    return { content: [{ type: 'text', text: 'Image queued for sending.' }] };
  },
}
```

#### 9. Container Dockerfile changes
**File:** `nanoclaw/container/Dockerfile`

```dockerfile
# Add to container/agent-runner/package.json (not global npm install):
# "puppeteer-core": "24.2.0"  (pin version, use system Chromium)
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Add media directory
RUN mkdir -p /workspace/ipc/media
```

Use `puppeteer-core` (NOT `puppeteer`). The `-core` variant never downloads Chromium, is ~3 MB, and requires explicit `executablePath` which we provide. Add it to `container/agent-runner/package.json` dependencies with a pinned version.

**Check:** Verify whether `agent-browser` (already in the container) bundles `puppeteer-core` internally. If so, consider reusing its installation instead of adding a duplicate. Run `npm ls puppeteer-core` inside the container to check.

---

### Phase 3: Skill Definition (NanoClaw repo — 1 new file)

#### 10. Cascade media skill with embedded templates
**New file:** `nanoclaw/container/skills/cascade-media/cascade-media.md`

Templates are **embedded in the skill definition**, not stored as separate files. This eliminates the need for additional volume mounts — the agent reads the skill prompt and has the templates inline.

Development/preview copies of templates can live in `cascade/templates/cards/` for local browser testing, but the runtime source of truth is the skill markdown.

```markdown
# Cascade Media Skill

You can generate and send visual status cards to the user as PNG images.

## When to Generate Images

- **Sunday weekly review**: Always send a visual weekly progress card alongside the text summary
- **Status requests**: When user texts "status" or "how am I doing", include a visual card
- **Monday kickoff**: Optionally send a visual card with the week's Core goals
- **Monthly milestones**: When a monthly target is hit or missed, send a visual card
- **On request**: When user asks for a chart, diagram, or visual

## How to Generate Images

1. Read the relevant data files from /workspace/extra/cascade-data/
2. HTML-escape ALL user data values before injecting into templates (see Escaping section)
3. Build an HTML string using the card templates below
4. Call the `render_image` MCP tool with the HTML string
5. Call the `send_image` MCP tool with the rendered PNG path and a caption
6. If `render_image` fails, send text-only output — never block a message because image gen failed

## CRITICAL: HTML Escaping

ALL values from tracker.csv, week files, and user input MUST be escaped before
injecting into HTML templates. This prevents HTML/CSS injection from user data.

Escape these characters:
- & → &amp;
- < → &lt;
- > → &gt;
- " → &quot;
- ' → &#39;

Example:
- Raw note: `sent email to <client> & reviewed "proposal"`
- Escaped: `sent email to &lt;client&gt; &amp; reviewed &quot;proposal&quot;`

NEVER inject raw user strings into HTML. Always escape first.

## Data Files (read-only for card generation)

Only read these files from /workspace/extra/cascade-data/:
- tracker.csv — progress data
- week-*.md — weekly plans with checkboxes
- {month}-{year}.md — monthly targets
- adaptations.md — learned patterns
- {year}-goals.md — year overview
- q{n}-*.md — quarterly milestones

Do NOT read any other files for card generation.

## Style Guide

Templates use inline fonts (no external @import). All CSS is inline in <style> tags.

- Dark background: #06060b
- Surface: #0d0d14
- Surface-2: #12121c
- Border: #1a1a2e
- Text: #e8e8f0
- Text dim: #5a5a72
- Text mid: #8888a0
- Green (done): #22c55e
- Amber (active): #f59e0b
- Dim (upcoming): #44445a
- Fonts: system monospace for labels/data, system sans-serif for body
  (container has Liberation Sans and Liberation Mono installed)
- Max width: 1200px, height: 800px

## Card Templates

### Weekly Progress Card

[Full HTML template with token placeholders — uses inline <style>,
system fonts, dark theme. Tokens: {{WEEK_NUMBER}}, {{WEEK_DATES}},
{{CORE_DONE}}, {{CORE_TOTAL}}, {{CORE_PCT}}, {{FLEX_DONE}},
{{FLEX_TOTAL}}, {{VELOCITY}}, {{HIGHLIGHTS}}, {{COACHING_LINE}}]

### Daily Summary Card

[Simpler template — just today's Core tasks in a scannable list.
Tokens: {{DAY_NAME}}, {{DATE}}, {{TASKS_HTML}}]

### Monthly Dashboard Card

[Timeline + targets layout. Tokens: {{MONTH}}, {{YEAR}},
{{MONTH_GOAL}}, {{WEEKS_HTML}}, {{TARGETS_HTML}}, {{PROGRESS_PCT}}]

### Goal Tracker Card

[Full goal overview. Tokens: {{GOAL}}, {{QUARTERLY_STATUS}},
{{MONTHLY_STATUS}}, {{VELOCITY}}, {{FORECAST}}]

## Handling Missing Data

- Empty tracker.csv (headers only): Show "No progress logged yet" state
- Missing week file: Show "No plan generated yet — run plan in Claude Code"
- Zero tasks: Show 0/0 (0%) — never divide by zero
- Long strings: Truncate task names to 80 characters with "..."
- Unicode: Pass through (system fonts support most scripts)

## Rules

- Always send a text caption WITH the image (not everyone can view images immediately)
- Keep captions under 100 words — the image is the detail, the caption is the summary
- If rendering fails, fall back to text-only output
- Don't send images for simple confirmations ("Logged for Feb 18" doesn't need an image)
- One image per message — don't send multiple images in rapid succession
- Maximum 5 image sends per minute (rate-limited by MCP tool)
```

#### 11. Scheduled task prompts
**File:** No code changes to `nanoclaw/src/task-scheduler.ts`

The scheduled task system works by spawning containers with specific prompts. Image generation is triggered by **updating the scheduled task prompts** (not by changing task-scheduler.ts code):

- **Sunday review prompt:** Add "Generate and send a visual weekly review card alongside the text summary."
- **Monday kickoff prompt:** Add "If a visual card would help, generate and send a weekly goals card."

The agent inside the container uses the `cascade-media` skill + MCP tools to handle the rest.

---

## Telegram-Specific Considerations

### sendPhoto (default) vs sendDocument

**Default: `sendPhoto`** for inline display. Rationale:
- Image shows directly in chat — zero taps to view
- JPEG compression at phone resolution is visually acceptable for dark-background status cards
- Better UX for the daily rhythm (morning check, evening log)
- Telegram compresses to max ~2560px — our 2400x1600 images are under this threshold at deviceScaleFactor:2, and 1200x800 at deviceScaleFactor:1

**When to use `sendDocument`:** If pixel-perfect quality is needed (e.g., detailed charts with fine text). This can be a future skill parameter.

### Bot Setup

Already configured — NanoClaw uses grammy and has a bot token. The main bot sends images. Bot pool image support is out of scope for v1.

---

## Dependencies

### New npm packages (container only)

| Package | Purpose | Size | Pin Version |
|---------|---------|------|-------------|
| `puppeteer-core` | HTML-to-PNG rendering (uses system Chromium) | ~3 MB | `24.2.0` |

Add to `container/agent-runner/package.json` (NOT a global `npm install` in Dockerfile). Use `puppeteer-core` (NOT `puppeteer`) — the `-core` variant never downloads Chromium.

**Supply chain check:** Verify with `npm audit` after adding. Check if `agent-browser` already bundles `puppeteer-core` to avoid duplicate installations.

### No new packages needed for host

Baileys and grammy already support image sending. No new host dependencies.

---

## Security Mitigations (from security review)

| Threat | Mitigation | Location |
|--------|-----------|----------|
| **Path traversal via imagePath** | `realpathSync` + prefix validation on host; path validation in container MCP tool | ipc.ts, ipc-mcp-stdio.ts |
| **HTML injection via template data** | HTML-escape all user values; skill instructs agent to escape; JS disabled in Puppeteer | cascade-media skill, render_image tool |
| **Script execution in rendered HTML** | `page.setJavaScriptEnabled(false)` | render_image tool |
| **Network exfiltration from rendered page** | `page.setRequestInterception(true)` — block all except `data:` URIs | render_image tool |
| **Filename injection** | Auto-generated unique filenames (timestamp + random), user cannot specify filename | render_image tool |
| **Resource exhaustion (OOM)** | HTML size limit (512KB), viewport clamped (100-2400 x 100-2000), render timeout (10s) | render_image tool |
| **Missing auth on image IPC** | Same `isMain \|\| sourceGroup === targetFolder` check as text messages | ipc.ts |
| **Temp file accumulation** | try/finally cleanup on every send; periodic cleanup job for orphans > 1 hour | ipc.ts, new cleanup interval |
| **Rate limiting** | 10 renders/min, 5 sends/min in MCP tools | ipc-mcp-stdio.ts |
| **Data exfiltration via images** | Log HTML hash for audit trail; skill restricts which files agent reads | ipc-mcp-stdio.ts, cascade-media skill |
| **Non-atomic IPC writes** | Use existing `writeIpcFile()` helper (temp + rename) | ipc-mcp-stdio.ts |
| **`--no-sandbox` Chromium** | Acceptable because JS is disabled. If JS is ever re-enabled, this becomes critical. | Documented risk |

---

## File Summary

### NanoClaw repo changes (8 files):

| File | Change | LOC estimate |
|------|--------|-------------|
| `src/types.ts` | Add optional `sendImage?` to Channel interface | ~3 lines |
| `src/channels/whatsapp.ts` | Implement `sendImage` with prefix + disconnect handling | ~15 lines |
| `src/channels/telegram.ts` | Implement `sendImage` via grammy `sendPhoto` with null guard | ~12 lines |
| `src/ipc.ts` | Add `sendImage` to `IpcDeps`; handle `type: "image"` with auth, path validation, try/finally | ~40 lines |
| `src/router.ts` | Add `routeOutboundImage` function with `sendImage` capability check | ~12 lines |
| `src/container-runner.ts` | Add `media/` subdir creation in `buildVolumeMounts` | ~1 line |
| `container/agent-runner/src/ipc-mcp-stdio.ts` | Add `render_image` + `send_image` MCP tools, lazy Puppeteer init, rate limiter, security hardening | ~150 lines |
| `container/agent-runner/package.json` | Add `puppeteer-core: "24.2.0"` | ~1 line |

Also update `container/Dockerfile` to add `/workspace/ipc/media` mkdir (~1 line).

### New files:

| File | Purpose |
|------|---------|
| `nanoclaw/container/skills/cascade-media/cascade-media.md` | Skill definition with embedded templates, escaping rules, and generation instructions |

### Development artifacts (not runtime dependencies):

| File | Purpose |
|------|---------|
| `cascade/templates/cards/*.html` | Preview/development copies of templates for local browser testing |

---

## Implementation Order

1. **Channel interface** (`types.ts`) — add optional `sendImage?`
2. **WhatsApp channel** (`whatsapp.ts`) — implement with prefix + disconnect handling
3. **Telegram channel** (`telegram.ts`) — implement with `sendPhoto` + null guard
4. **Router** (`router.ts`) — add `routeOutboundImage` with capability check
5. **IPC handler** (`ipc.ts`) — add `sendImage` to `IpcDeps`, handle `type: "image"` with auth + path validation + try/finally
6. **Container runner** (`container-runner.ts`) — add `media/` dir creation
7. **Dockerfile** — add `media/` mkdir, add `puppeteer-core` to agent-runner package.json
8. **MCP tools** (`ipc-mcp-stdio.ts`) — `render_image` + `send_image` with all security hardening
9. **Skill** (`cascade-media.md`) — templates + escaping rules + generation instructions
10. **Test end-to-end** — generate card → render PNG → send via WhatsApp/Telegram
11. **Scheduled task prompts** — update Sunday review + Monday kickoff prompts

Steps 1-7 are plumbing. Step 8 is the core rendering engine. Step 9 is content. Steps 10-11 are integration.

---

## Testing Plan

### Unit Tests

| Test | What | Expected |
|------|------|----------|
| `render_image` happy path | Simple HTML → PNG | File exists, valid PNG header, < 4MB |
| `render_image` empty HTML | `html: ""` | Returns PNG (blank), no crash |
| `render_image` oversized HTML | 1MB HTML string | Returns error: "HTML too large" |
| `render_image` huge viewport | `width: 50000` | Clamped to 2400, succeeds |
| `render_image` timeout | HTML with `<meta http-equiv="refresh">` (blocked by JS off) | Succeeds (refresh ignored) |
| `render_image` rate limit | 11 calls in 1 minute | 11th returns rate limit error |
| `send_image` happy path | Valid `media/*.png` path | IPC file written atomically |
| `send_image` path traversal | `image_path: "../../etc/passwd"` | Returns error: "must be within media/" |
| `send_image` nonexistent file | `image_path: "media/nonexistent.png"` | Returns error: "not found" |
| `sendImage` WhatsApp | Mock Baileys sock | `sendMessage` called with `{ image: Buffer, caption }` |
| `sendImage` WhatsApp disconnected | `this.connected = false` | Logs warning, returns without throwing |
| `sendImage` Telegram | Mock grammy bot | `sendPhoto` called with `InputFile` |
| `sendImage` Telegram null bot | `this.bot = null` | Logs warning, returns without throwing |

### Integration Tests

| Test | What | Expected |
|------|------|----------|
| IPC `type: "image"` | Write image IPC JSON to messages/ dir | Host picks up, reads PNG, calls `sendImage`, deletes PNG |
| IPC auth — main group | Image IPC from main group targeting any JID | Sends successfully |
| IPC auth — non-main group own JID | Image IPC targeting own group JID | Sends successfully |
| IPC auth — non-main group other JID | Image IPC targeting different group | Blocked, logged |
| IPC path traversal | `imagePath: "../../etc/passwd"` | Blocked by `realpathSync` + prefix check |
| IPC send failure | Image send throws | Caption sent as text fallback, PNG deleted |
| IPC nonexistent image | `imagePath` points to deleted file | Error logged, no crash |

### Edge Case Tests

| Test | What | Expected |
|------|------|----------|
| Empty tracker.csv | Render card with headers-only CSV | "No progress logged" state |
| Missing week file | Render card when no week-*.md exists | "No plan generated" state |
| Zero tasks | 0 Core, 0 Flex | Shows 0/0 (0%), no division by zero |
| Unicode task names | Emoji, CJK, accents in tasks | Renders correctly (Liberation fonts support Latin + CJK via Noto) |
| Long task descriptions | 500-char task name | Truncated to 80 chars with "..." |
| HTML in user notes | `<script>alert(1)</script>` in tracker notes | Escaped to `&lt;script&gt;` in rendered card |
| Concurrent renders | 3 simultaneous `render_image` calls | All succeed with unique filenames |
| Large PNG retry | Complex template > 4MB at 2x | Re-renders at 1x, succeeds under 4MB |
| Orphan cleanup | Render without send, wait 1 hour | Periodic cleanup removes orphaned PNGs |

### E2E Tests

| Test | What | Expected |
|------|------|----------|
| Full pipeline (WhatsApp) | Agent generates HTML → renders → sends | User receives image in WhatsApp |
| Full pipeline (Telegram) | Agent generates HTML → renders → sends | User receives inline photo in Telegram |
| Scheduled Sunday review | Trigger Sunday review task | Image + text summary sent |
| Render failure fallback | Kill Chromium mid-render | Text-only caption sent as fallback |

---

## Rollback Strategy

All changes can be disabled without code rollback:

1. **Feature flag:** Add `ENABLE_IMAGE_SUPPORT=true` env var. Check in IPC handler and MCP tools. Set to `false` to revert to text-only.
2. **`sendImage` is optional on Channel interface.** If images cause issues, the `routeOutboundImage` fallback sends text-only.
3. **Puppeteer is lazy-initialized.** If it's never called, it uses zero resources. Removing the skill prompt stops all image generation.
4. **No existing code is removed or modified destructively.** New code is additive — `else if` in IPC, new function in router, new methods on channels.

---

## Periodic Cleanup Job

Add to NanoClaw host (e.g., in `src/index.ts` initialization):

```typescript
// Clean up orphaned PNG files in media directories every 30 minutes
setInterval(() => {
  const ipcBaseDir = path.join(DATA_DIR, 'ipc');
  const groups = fs.readdirSync(ipcBaseDir, { withFileTypes: true })
    .filter(d => d.isDirectory());

  for (const group of groups) {
    const mediaDir = path.join(ipcBaseDir, group.name, 'media');
    if (!fs.existsSync(mediaDir)) continue;

    const files = fs.readdirSync(mediaDir);
    const now = Date.now();
    for (const file of files) {
      const filePath = path.join(mediaDir, file);
      try {
        const stat = fs.statSync(filePath);
        if (now - stat.mtimeMs > 3600000) { // Older than 1 hour
          fs.unlinkSync(filePath);
          logger.info({ filePath }, 'Cleaned up orphaned media file');
        }
      } catch {}
    }
  }
}, 1800000); // Every 30 minutes
```

---

## Open Questions / Future Work

1. **Font quality:** Templates use system fonts (Liberation Sans/Mono). If higher design quality is needed, bundle JetBrains Mono and DM Sans as `.woff2` files in the container and reference via `data:` URI or local `@font-face`. Network-loaded Google Fonts are blocked by request interception.
2. **Satori + resvg:** If templates prove to be simple enough (Flexbox-only, inline styles), Satori + resvg would be 10-50ms per render with zero Chromium attack surface. Evaluate after v1 templates are finalized.
3. **Telegram `sendDocument` option:** Add as a skill parameter for when pixel-perfect quality is explicitly needed.
4. **WhatsApp image queue:** Extend `outgoingQueue` to support image payloads for retry-on-reconnect. Low priority — disconnections during image sends fall back to text.
5. **Bot pool images:** If agent team messages need image support, extend `sendPoolMessage` in `telegram.ts`.

---

*Research inputs:*
- `docs/research-whatsapp-images.md`
- `docs/research-telegram-images.md`
- `docs/research-html-to-png.md`
- `docs/research-nanoclaw-architecture.md`

*Review inputs (all findings incorporated):*
- `docs/review-staff-engineer.md` — 13 findings (1 critical, 3 high, 7 medium, 2 low)
- `docs/review-security-engineer.md` — 10 findings (1 critical, 3 high, 4 medium, 2 low)
- `docs/review-qa-engineer.md` — 23 findings (2 blocker, 5 critical, 8 major, 8 minor)
