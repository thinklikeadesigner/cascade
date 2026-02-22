# NanoClaw Architecture & Integration Points for Image Sending

**Date:** February 19, 2026
**Purpose:** Document the current NanoClaw + Cascade architecture and identify where image generation + sending capabilities would plug in.

---

## 1. Project Layout

```
/Users/k2/Desktop/moltathon/
  cascade/           <-- Cascade goal execution system (this repo)
  nanoclaw/          <-- NanoClaw WhatsApp/Telegram agent (sibling repo)
```

### Cascade Repo Structure

```
cascade/
  CLAUDE.md              # Master spec: Cascade methodology + NanoClaw WhatsApp agent spec
  NANOCLAW-SETUP-PLAN.md # Setup instructions for NanoClaw integration
  package.json           # Node.js; depends on office-skills (HTML-to-PPTX)
  generate-presentation.js # HTML slide generation (existing pattern)
  data/                  # User goal data (mounted into NanoClaw container)
    2026-goals.md
    q1-jan-feb-mar.md
    feb-2026.md
    week-feb14-20.md
    week-feb21-27.md
    tracker.csv
    CLAUDE.md            # Data-level ground truth for agents
  templates/             # Templates for weekly plans, daily schedules
    week.md, month.md, quarter.md, year-goals.md, adaptations.md
    daily/               # Day-of-week templates
  tools/
    cascade-research/    # Python CLI for vector search (ChromaDB)
  reverse-cascade/       # LangGraph.js service for upward propagation
    src/                 # Express + LangGraph StateGraph
  outputs/
    cascade-pitch-deck/slides/  # 11 HTML slide files
    product-research/           # 23 markdown research docs
    landing/index.html          # Landing page variant
    february-targets.html       # HTML visualization
  site/
    index.html           # Landing page (deployed to Vercel)
    cascade-og-image.png
    cascade-twitter-card.png
  docs/
    vector-db-implementation-plan.md
```

### NanoClaw Repo Structure (Sibling)

```
nanoclaw/
  src/
    index.ts             # Main orchestrator: message loop, agent invocation
    channels/
      whatsapp.ts        # WhatsApp connection via @whiskeysockets/baileys
      telegram.ts        # Telegram bot via grammy
    router.ts            # Message formatting, outbound routing
    container-runner.ts  # Spawns Docker containers for Claude agents
    task-scheduler.ts    # Cron/interval/once task execution
    ipc.ts               # IPC watcher: processes JSON files for messaging + tasks
    config.ts            # Trigger patterns, paths, intervals
    db.ts                # SQLite (better-sqlite3) for messages, sessions, tasks
    group-queue.ts       # Queue for processing group messages
  container/
    Dockerfile           # node:22-slim + Chromium + agent-browser + claude-code
    agent-runner/src/
      index.ts           # Agent runner entry point
      ipc-mcp-stdio.ts   # MCP server with send_message, schedule_task, etc.
    skills/              # Container-available skills (agent-browser)
  skills-engine/         # Skill application, state management, backup
  groups/
    main/CLAUDE.md       # Main group memory + Cascade coaching spec
    global/              # Shared read-only memory
  data/
    sessions/            # Per-group Claude sessions
    ipc/                 # Per-group IPC directories
  store/                 # SQLite database
```

---

## 2. Current Architecture

### Message Flow

```
User (WhatsApp/Telegram)
  |
  v
NanoClaw Host Process (src/index.ts)
  |-- channels/whatsapp.ts (Baileys) receives message
  |-- db.ts stores message in SQLite
  |-- Checks if message is from a registered group
  |-- Checks trigger pattern (non-main groups need @mention)
  |-- Formats messages as XML: <messages><message sender="..." time="...">text</message></messages>
  |
  v
Docker Container (container/Dockerfile)
  |-- Claude Agent SDK runs with mounted workspace
  |-- Has access to /workspace/group, /workspace/ipc, /workspace/extra
  |-- MCP tools: send_message, schedule_task, list_tasks, pause/resume/cancel
  |-- Claude generates text response
  |
  v
Streaming Output (stdout markers: ---NANOCLAW_OUTPUT_START--- / ---NANOCLAW_OUTPUT_END---)
  |
  v
NanoClaw Host Process routes response
  |-- channels/whatsapp.ts sendMessage(jid, text) -- TEXT ONLY
  |-- router.ts strips <internal> tags, formats output
```

### Key Dependency Stack

**NanoClaw Host:**
- `@whiskeysockets/baileys` ^7.0.0 -- WhatsApp Web API
- `grammy` ^1.39.3 -- Telegram Bot API
- `better-sqlite3` -- Message/session/task storage
- `cron-parser` -- Scheduled task timing
- `pino` -- Logging

**Container (Agent):**
- `@anthropic-ai/claude-code` -- Claude Agent SDK
- `@modelcontextprotocol/sdk` -- MCP server for IPC tools
- `agent-browser` -- Headless Chromium automation
- Chromium installed in container

### IPC System

The container communicates with the host via JSON files written to `/workspace/ipc/`:

| Directory | Purpose |
|-----------|---------|
| `messages/` | Send messages to chat (host picks up and delivers) |
| `tasks/` | Schedule/pause/resume/cancel tasks, register groups |
| `input/` | Follow-up messages piped to running container |

**Current IPC message format** (text only):
```json
{
  "type": "message",
  "chatJid": "120363336345536173@g.us",
  "text": "Week 2, day 3. Core: 5/9 tasks done (56%)...",
  "sender": "Cascade",
  "groupFolder": "main",
  "timestamp": "2026-02-19T15:30:00.000Z"
}
```

### Cascade Data Integration

Cascade's `data/` directory is mounted into NanoClaw's main group container at:
- **Container path:** `/workspace/extra/cascade-data`
- **Host path:** `~/Desktop/moltathon/cascade/data`
- **Access:** read-write

The agent reads weekly plans, monthly targets, tracker.csv, and writes to tracker.csv + week checkboxes + adaptations.md.

---

## 3. Current Limitations (No Image Support)

### WhatsApp Channel (`whatsapp.ts`)

The `sendMessage` method only supports text:

```typescript
// Line 226-248 of nanoclaw/src/channels/whatsapp.ts
async sendMessage(jid: string, text: string): Promise<void> {
  const prefixed = ASSISTANT_HAS_OWN_NUMBER ? text : `${ASSISTANT_NAME}: ${text}`;
  await this.sock.sendMessage(jid, { text: prefixed });
}
```

Baileys supports sending images via:
```typescript
await this.sock.sendMessage(jid, {
  image: Buffer.from(pngData),
  caption: "Weekly progress chart"
});
```

But the current `Channel` interface and `sendMessage` signature only accept text strings.

### Telegram Channel (`telegram.ts`)

The `grammy` library supports image sending via:
```typescript
await bot.api.sendPhoto(chatId, new InputFile(buffer, "chart.png"), { caption: "..." });
```

But again, the current Channel interface only routes text.

### IPC System (`ipc.ts`)

The IPC message processor only handles `type: "message"` with a `text` field. There is no support for `type: "image"` or a `media` field.

### Container Agent (`ipc-mcp-stdio.ts`)

The MCP `send_message` tool only accepts a `text` parameter. No mechanism for the agent to send images.

### Container Environment

The Docker container has Chromium installed (for agent-browser). This means **HTML-to-PNG rendering is already possible inside the container** using Chromium's headless screenshot capability.

---

## 4. Existing Patterns for HTML/Visual Generation

### HTML Slide Generation (`generate-presentation.js`)

The Cascade repo already has an established pattern for generating styled HTML content:

1. **Template approach:** JavaScript generates HTML strings with embedded CSS
2. **Color palette:** Dark minimal aesthetic (`#2A2D34` bg, `#F59E0B` accent, etc.)
3. **Dimensions:** 720pt x 405pt (16:9 slides)
4. **Conversion:** Uses `office-skills/html2pptx-local.cjs` to convert HTML to PPTX slides

This pattern can be adapted for status cards, progress charts, and weekly summaries.

### HTML Outputs

Several HTML files already exist in `outputs/`:
- `outputs/february-targets.html` -- Monthly targets visualization
- `outputs/product-research/cascade-lean-canvas.html` -- Lean canvas card
- `outputs/landing/index.html` -- Landing page variant

### Site Assets

OG image and Twitter card already exist:
- `site/cascade-og-image.png`
- `site/cascade-twitter-card.png`

---

## 5. Integration Points for Image Generation + Sending

### Where New Code Goes

#### A. NanoClaw Host: Add Image Sending to Channels

**File:** `nanoclaw/src/channels/whatsapp.ts`
- Add `sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void>` method
- Uses Baileys' `sock.sendMessage(jid, { image: buffer, caption })`

**File:** `nanoclaw/src/channels/telegram.ts`
- Add `sendImage(chatId: string, buffer: Buffer, caption?: string): Promise<void>` method
- Uses grammy's `bot.api.sendPhoto(chatId, new InputFile(buffer), { caption })`

**File:** `nanoclaw/src/types.ts`
- Extend `Channel` interface with `sendImage` method

#### B. NanoClaw IPC: Add Image Message Type

**File:** `nanoclaw/src/ipc.ts`
- Handle `type: "image"` IPC messages
- Read image data from a file path (container writes PNG to mounted volume)
- Route to appropriate channel's `sendImage` method

**New IPC message format:**
```json
{
  "type": "image",
  "chatJid": "120363336345536173@g.us",
  "imagePath": "/workspace/ipc/media/weekly-progress.png",
  "caption": "Week 2 Progress: Core 56%, Flex 25%",
  "groupFolder": "main",
  "timestamp": "2026-02-19T15:30:00.000Z"
}
```

#### C. Container MCP: Add send_image Tool

**File:** `nanoclaw/container/agent-runner/src/ipc-mcp-stdio.ts`
- Add `send_image` MCP tool that:
  1. Accepts `image_path` (file in container) and `caption`
  2. Copies/moves the image to `/workspace/ipc/media/`
  3. Writes an IPC JSON file with `type: "image"`

#### D. Image Generation Inside Container

The container already has Chromium installed. Two approaches:

**Option 1: agent-browser screenshot (already available)**
```bash
# Generate HTML -> open in headless Chrome -> screenshot
agent-browser open file:///tmp/chart.html
agent-browser screenshot /workspace/ipc/media/chart.png
```

**Option 2: Direct Puppeteer/Playwright (add to container)**
```typescript
const browser = await puppeteer.launch({ executablePath: '/usr/bin/chromium' });
const page = await browser.newPage();
await page.setContent(htmlString);
await page.screenshot({ path: '/workspace/ipc/media/chart.png' });
```

**Option 3: Sharp library (for simpler graphics, no browser needed)**
```typescript
import sharp from 'sharp';
// Compose images, add text overlays, etc.
```

#### E. Cascade Templates for Status Cards

**New directory:** `cascade/templates/cards/` or `nanoclaw/container/skills/cascade-cards/`
- HTML templates for: weekly progress card, daily summary, monthly overview
- CSS matching Cascade's dark aesthetic
- Mermaid diagram support for progress visualization

### Data Flow for Image Sending

```
1. Cascade agent reads data/tracker.csv + week-*.md
2. Agent generates HTML status card from template
3. Agent uses headless Chromium to render HTML -> PNG
4. Agent saves PNG to /workspace/ipc/media/weekly-progress.png
5. Agent calls send_image MCP tool with path + caption
6. MCP tool writes IPC JSON: { type: "image", imagePath: "...", caption: "..." }
7. NanoClaw host (ipc.ts) picks up the IPC file
8. Host reads the PNG file from the media directory
9. Host calls channel.sendImage(jid, buffer, caption)
10. Baileys/grammy sends image to WhatsApp/Telegram
```

### Volume Mount Addition

A new shared media directory is needed:

**In `container-runner.ts` `buildVolumeMounts()`:**
```typescript
// IPC media directory for image exchange
const mediaDir = path.join(DATA_DIR, 'ipc', group.folder, 'media');
fs.mkdirSync(mediaDir, { recursive: true });
// Already mounted as part of the IPC directory at /workspace/ipc/
```

The existing IPC mount (`/workspace/ipc/`) already covers this -- just need to create a `media/` subdirectory.

---

## 6. Skill Definition Points

NanoClaw has a skills engine (`skills-engine/`) that manages skill application. Container skills are synced from `container/skills/` into each group's `.claude/skills/` directory.

A "Cascade image cards" skill could be added as:
```
nanoclaw/container/skills/cascade-media/
  cascade-media.md  # Skill prompt: how to generate and send status images
```

This would teach the agent:
- When to generate images (status requests, weekly reviews, daily morning summaries)
- HTML template patterns for each card type
- How to render HTML to PNG using the container's Chromium
- How to call send_image MCP tool

---

## 7. Summary of Changes Needed

| Component | File(s) | Change |
|-----------|---------|--------|
| **Channel interface** | `nanoclaw/src/types.ts` | Add `sendImage(jid, buffer, caption?)` to Channel |
| **WhatsApp sending** | `nanoclaw/src/channels/whatsapp.ts` | Implement `sendImage` using Baileys |
| **Telegram sending** | `nanoclaw/src/channels/telegram.ts` | Implement `sendImage` using grammy |
| **IPC handler** | `nanoclaw/src/ipc.ts` | Handle `type: "image"` messages |
| **MCP tool** | `nanoclaw/container/agent-runner/src/ipc-mcp-stdio.ts` | Add `send_image` tool |
| **HTML-to-PNG** | Container (already has Chromium) | Use agent-browser or Puppeteer |
| **Status card templates** | New: templates/cards/ or skill | HTML templates for Cascade data visualization |
| **IPC media dir** | `nanoclaw/src/container-runner.ts` | Ensure media/ subdir in IPC mount |
| **Router** | `nanoclaw/src/router.ts` | Add image routing logic |
| **Task scheduler** | `nanoclaw/src/task-scheduler.ts` | Support image output from scheduled tasks |

### What Already Exists

- Chromium in Docker container (for HTML rendering)
- IPC file-based communication system
- MCP tool framework for adding new agent capabilities
- HTML generation patterns in Cascade (slides, landing pages)
- Baileys library supports image sending natively
- grammy library supports image sending natively
- Skills engine for adding agent behaviors
- Scheduled task system for automated daily/weekly image sends
- Cascade data directory mounted into container

### What Does NOT Exist Yet

- `sendImage` method on any channel
- Image-type IPC messages
- `send_image` MCP tool
- HTML-to-PNG rendering pipeline (though tools are present)
- Status card HTML templates
- Media exchange directory in IPC

---

## 8. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Chromium screenshot memory usage in container | Medium | Set viewport size limits, clean up after render |
| Large PNG files in IPC directory | Low | Clean up after sending; cap image dimensions |
| Baileys image sending rate limits | Medium | Queue images, respect WhatsApp rate limits |
| Container startup time with Chromium | Already managed | Chromium already installed; no new overhead |
| Template rendering errors | Low | Fallback to text-only status message |

---

*Generated: Feb 19, 2026*
*Source: Full codebase exploration of cascade/ and nanoclaw/ repositories*
