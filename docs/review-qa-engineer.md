# QA Engineer Review: NanoClaw Media Implementation Plan

**Reviewer:** QA Engineer
**Date:** February 19, 2026
**Document Reviewed:** `docs/nanoclaw-media-plan.md`
**Source Files Reviewed:** `src/ipc.ts`, `src/types.ts`, `src/channels/whatsapp.ts`, `src/channels/telegram.ts`, `src/container-runner.ts`, `src/task-scheduler.ts`, `src/router.ts`, `container/agent-runner/src/ipc-mcp-stdio.ts`, `container/agent-runner/src/index.ts`, `container/Dockerfile`

---

## Executive Summary

The plan is well-scoped and correctly identifies that most infrastructure exists. However, several failure modes, edge cases, and integration risks are unaddressed. This review identifies **23 findings** across 10 focus areas, ranging from 2 Blockers to 6 Minor issues.

---

## Finding 1: Image File Size May Exceed WhatsApp 5MB Limit

**Severity:** Blocker
**Area:** Image sizing / WhatsApp constraints

**Analysis:**

The plan specifies `deviceScaleFactor: 2` on a `1200x800` viewport. This produces a **2400x1600 pixel** PNG image.

Estimated file size calculation:
- Raw pixel data: 2400 x 1600 x 4 bytes (RGBA) = **15.36 MB** uncompressed
- PNG compression on a dark-background card with text, flat colors, and minimal gradients typically achieves 10:1 to 20:1 compression
- **Estimated PNG size: 0.8 MB to 1.5 MB** for a typical status card
- However, cards with many elements (monthly dashboard, goal tracker with charts) could push toward **2-3 MB**
- Cards with embedded base64 images, complex gradients, or anti-aliased text on varied backgrounds can reach **3-5 MB**

WhatsApp's hard limit is **5 MB** for images. Telegram's `sendDocument` limit is 50 MB (safe).

**Risk:** A complex monthly dashboard card could approach or exceed the 5 MB limit, especially if the template includes visual elements like progress bars with gradients, sparklines, or multiple data sections.

**Recommended Test Cases:**
1. Render each template with **maximum realistic data** (12 weeks of history, all fields populated, long strings) and measure file size
2. Render with `optimizeForSpeed: true` vs `false` and compare sizes
3. Test with 1200x800 viewport at `deviceScaleFactor: 1` (halves resolution) as a fallback
4. Test WhatsApp rejection when file exceeds 5 MB -- verify the error is caught and fallback text is sent

**Recommendation:** Add a file size check after rendering. If PNG exceeds 4 MB, either reduce `deviceScaleFactor` to 1 and re-render, or convert to JPEG (lossy but smaller). The plan should define this fallback explicitly.

---

## Finding 2: Google Font Loading in Offline/Containerized Environment

**Severity:** Blocker
**Area:** Font loading / container environment

**Analysis:**

The templates use `@import` for Google Fonts (JetBrains Mono, DM Sans). The container runs with network access (it runs Claude Code which needs API access), so fonts **should** load. However:

1. **First render latency:** Google Fonts are fetched at render time. With `waitUntil: 'domcontentloaded'`, the page renders **before** fonts load. The DOM is ready but `@import` stylesheets are still fetching. Text will render in fallback fonts (serif/sans-serif system defaults), producing an ugly card.
2. **Google Fonts CDN outage:** If `fonts.googleapis.com` is slow or unreachable (DNS issues, rate limiting, China/corporate firewall), render will either timeout or use fallback fonts silently.
3. **No font files in container:** The Dockerfile installs `fonts-liberation` and `fonts-noto-color-emoji` but not JetBrains Mono or DM Sans.

**Reproduction Scenario:**
1. Start container
2. Render a card immediately (cold cache)
3. Observe that text renders in Liberation Sans / serif instead of the intended fonts

**Recommended Test Cases:**
1. Render a card in the container with network access and verify fonts load correctly. Time the render.
2. Render with `waitUntil: 'networkidle0'` instead of `domcontentloaded` and compare output. Measure added latency.
3. Render with fonts.googleapis.com blocked (simulate via `/etc/hosts` or Chromium `--host-resolver-rules`) and verify graceful degradation
4. Render 3 cards in sequence -- verify whether font caching works across page instances with the long-lived browser

**Recommendation:** Change `waitUntil` from `'domcontentloaded'` to `'networkidle0'` to ensure fonts load before screenshot. Add a timeout (e.g., 5 seconds) to prevent hanging if fonts are unreachable. Alternatively, bundle the font files in the container image and reference them with local `@font-face` declarations in `_base.css`, eliminating the network dependency entirely. This is the more robust approach.

---

## Finding 3: IPC Handler Only Handles `type: "message"` -- No `type: "image"` Support

**Severity:** Critical
**Area:** IPC message handling

**Analysis:**

The current `ipc.ts` (line 75) only handles `data.type === 'message'`. The plan proposes adding a `case 'image'` handler, but the current IPC structure processes messages by reading JSON files from the `messages/` directory, not via a switch statement.

Looking at the actual code:

```typescript
if (data.type === 'message' && data.chatJid && data.text) {
  // ... send message
}
```

This is a simple if-condition, not a switch. The plan shows a `case 'image'` block (plan line 115-121), which implies a switch statement. The implementation will need to add an `else if` for image type, or refactor to a switch.

Additionally, the IPC handler currently only calls `deps.sendMessage()`, but the `IpcDeps` interface (lines 18-30 of `ipc.ts`) does **not include `sendImage`**. The plan doesn't mention updating `IpcDeps`.

**Recommended Test Cases:**
1. Write a `type: "image"` JSON file to the IPC messages directory and verify it's picked up and processed
2. Write a `type: "image"` file with missing `imagePath` field -- verify error handling
3. Write a `type: "image"` file pointing to a non-existent PNG -- verify error handling
4. Write a `type: "image"` file where `imagePath` is outside the IPC directory (path traversal attempt) -- verify it's rejected
5. Verify the JSON file is deleted after successful processing (matching current behavior for message files)
6. Verify failed image sends move the JSON to the `errors/` directory (matching current error behavior)

**Recommendation:** The plan should explicitly list `IpcDeps` interface update as a required change. Also add input validation for `imagePath` to prevent path traversal.

---

## Finding 4: Channel Interface Change Breaks Existing Implementations

**Severity:** Critical
**Area:** Regression risk / interface changes

**Analysis:**

The plan adds `sendImage` to the `Channel` interface:

```typescript
interface Channel {
  sendMessage(jid: string, text: string): Promise<void>;
  sendImage(jid: string, buffer: Buffer, caption?: string): Promise<void>;  // NEW
}
```

The current `Channel` interface (in `types.ts` line 82-91) does **not** have `sendImage`. Adding a required method to the interface means **every class implementing `Channel` must implement it**, or TypeScript will fail to compile.

Currently two classes implement `Channel`:
- `WhatsAppChannel` in `channels/whatsapp.ts`
- `TelegramChannel` in `channels/telegram.ts`

Both must implement `sendImage`. The plan accounts for this in files #2 and #3.

However, the `router.ts` `routeOutbound` function (line 36-44) currently routes outbound messages by finding the channel via `channels.find(c => c.ownsJid(jid))` and calling `channel.sendMessage()`. There is no equivalent `routeOutboundImage()`. The plan mentions the router update (item #6) but only vaguely: "ensure it can pass through image-type messages without stripping them as text."

**Risk:** If a third-party or future channel implementation doesn't implement `sendImage`, the application will crash at runtime on image sends to that channel.

**Recommended Test Cases:**
1. TypeScript compilation passes after adding `sendImage` to the interface and both implementations
2. Calling `sendImage` on WhatsApp channel succeeds with a valid buffer
3. Calling `sendImage` on Telegram channel succeeds with a valid buffer
4. Calling `sendImage` with an empty buffer -- verify behavior (does Baileys accept it? Does grammy?)
5. Calling `sendImage` with a very large buffer (10 MB) -- verify WhatsApp rejects it gracefully
6. Verify `routeOutbound` or a new `routeOutboundImage` routes correctly

**Recommendation:** Make `sendImage` optional on the interface (like `setTyping?`) so channels that don't support images don't break. The IPC handler should check if the channel supports `sendImage` before calling it:

```typescript
if (typeof channel.sendImage === 'function') {
  await channel.sendImage(jid, buffer, caption);
} else {
  // fallback: send text caption only
  await channel.sendMessage(jid, caption || '[Image not supported on this channel]');
}
```

---

## Finding 5: Telegram `sendDocument` UX Degradation

**Severity:** Major
**Area:** Telegram user experience

**Analysis:**

The plan chooses `sendDocument` over `sendPhoto` to preserve PNG quality. This is technically correct -- `sendPhoto` re-encodes to JPEG and degrades text quality. However, the UX tradeoff is significant:

- **`sendPhoto`:** Image displays **inline** in the chat. Users see it immediately without tapping. The image is part of the conversation flow.
- **`sendDocument`:** Displays as a **file attachment** with a tiny thumbnail. Users must tap "Download" and then open the file to see the full image. On mobile, this is 2-3 taps.

For a status card that's part of the daily rhythm (morning tasks, weekly review), requiring extra taps to view the content undermines the "quick glance" value proposition.

**Reproduction Scenario:**
1. Send the same PNG via both `sendPhoto` and `sendDocument` to a Telegram chat
2. Compare the UX on mobile (iPhone and Android)
3. Evaluate whether the text quality difference is visible on a phone screen

**Recommended Test Cases:**
1. Render a weekly progress card at 2400x1600px and send via both `sendPhoto` and `sendDocument`
2. View on mobile at normal zoom -- can you read the text after `sendPhoto` compression?
3. View the `sendDocument` thumbnail -- is it usable without opening the full file?
4. Time the user flow: how many seconds from receiving notification to reading the card content, for both methods?

**Recommendation:** Consider a hybrid approach:
- Use `sendPhoto` as the default (inline display, most users won't notice JPEG compression at phone resolution)
- Provide `sendDocument` as an option in the skill when the agent or user explicitly requests "high quality" or "full resolution"
- If `sendPhoto` is used: don't use `deviceScaleFactor: 2`. A 1200x800 image at the Telegram compression threshold (~2560px) won't be downscaled

---

## Finding 6: WhatsApp 24-Hour Window Failure Is Under-Specified

**Severity:** Major
**Area:** WhatsApp session window handling

**Analysis:**

The plan acknowledges the 24-hour window (lines 355-369) and proposes pre-approved templates for Sunday/Monday messages. However, the actual failure handling is vague:

1. **The plan uses Baileys, not the Cloud API.** Baileys wraps the WhatsApp Web protocol, which has **different** session rules than the Cloud API. The 24-hour template window is a **Cloud API / Business API** constraint. Baileys (as an unofficial client using the WhatsApp Web protocol) doesn't have template messages at all -- it either sends or fails.
2. **Baileys failure mode on session expiry:** When Baileys can't send (e.g., the connection drops, or the recipient blocked the number), it throws an error. The plan says "send text-only version and note that the image couldn't be delivered" but doesn't specify where this fallback logic lives.
3. **The template registration advice (lines 364-369) is irrelevant for Baileys.** Template messages are a Cloud API concept. If the project switches to Cloud API later, this section applies. For Baileys, it doesn't.

**Risk:** Confusion about which API is actually being used. The plan mixes Baileys-specific implementation with Cloud API-specific concepts.

**Recommended Test Cases:**
1. Send an image via Baileys when connection is active -- verify success
2. Send an image via Baileys when connection is dropped -- verify error is caught
3. Send an image to a JID that has blocked the bot number -- verify error handling
4. Verify the `sendImage` implementation has try/catch with fallback to text-only
5. Test the WhatsApp reconnection flow (existing in `whatsapp.ts`) -- do queued image sends retry after reconnection?

**Recommendation:**
- Remove or clearly label the Cloud API / template sections as "future consideration" since the current implementation uses Baileys
- Add retry/queue logic for `sendImage` matching the existing `outgoingQueue` pattern in `whatsapp.ts`
- The `sendImage` implementation should catch errors and fall back to `sendMessage` with the caption text

---

## Finding 7: No Cleanup of Rendered PNG Files on Failure

**Severity:** Major
**Area:** Resource management / disk space

**Analysis:**

The plan's IPC handler (line 119) calls `fs.unlinkSync(msg.imagePath)` after sending. But what happens when:

1. **`channel.sendImage()` throws:** The PNG is never deleted. Over time, failed sends accumulate PNGs in the `media/` directory.
2. **The agent calls `render_image` but never calls `send_image`:** The rendered PNG sits in `media/` forever.
3. **The container crashes between `render_image` and `send_image`:** Orphaned PNG.
4. **Multiple renders with the same filename:** The `render_image` tool defaults to `rendered.png`. If two renders happen before a send, the first PNG is overwritten.

**Recommended Test Cases:**
1. Call `render_image` then simulate `send_image` failure -- verify PNG persists (and is eventually cleaned up)
2. Call `render_image` twice with `filename: 'rendered.png'` -- verify second overwrites first
3. Verify cleanup logic runs on IPC handler success
4. Run 100 render/send cycles and check disk usage
5. Kill the container mid-render -- verify no corrupted files are left

**Recommendation:**
- Wrap the IPC handler's `sendImage` call in try/finally to ensure cleanup:
  ```typescript
  try {
    const imageBuffer = fs.readFileSync(msg.imagePath);
    await channel.sendImage(msg.chatJid, imageBuffer, msg.caption);
  } finally {
    try { fs.unlinkSync(msg.imagePath); } catch {}
  }
  ```
- Add a periodic cleanup job that removes PNGs older than 1 hour from `media/`
- Use unique filenames (timestamp + random) instead of allowing user-specified names to prevent overwrites

---

## Finding 8: Scheduled Task + Container Lifecycle Interaction

**Severity:** Major
**Area:** Container lifecycle / scheduling

**Analysis:**

The plan's step 7 (line 341-349) says: "The scheduled task handler invokes the container with a specific prompt." Looking at the actual `task-scheduler.ts`:

1. Scheduled tasks call `runContainerAgent()` which spawns a Docker container
2. The container runs the agent, which generates HTML, calls `render_image`, and calls `send_image`
3. `render_image` needs Puppeteer, which needs the long-lived browser

The problem: **the long-lived browser is initialized at container startup** (plan line 229-236). But the current container entrypoint compiles TypeScript and runs `index.ts`. The browser initialization would need to happen in the agent-runner process, not in the MCP server process.

The MCP server (`ipc-mcp-stdio.ts`) runs as a **separate process** spawned by the Claude Code SDK. Looking at `index.ts` line 441-449:

```typescript
mcpServers: {
  nanoclaw: {
    command: 'node',
    args: [mcpServerPath],
    env: { ... },
  },
},
```

The MCP server is a separate Node.js process. It doesn't share memory with the main agent-runner process. So `puppeteer.launch()` in the MCP server process would create its own browser instance.

**Key concern:** The MCP server process lifecycle is managed by the Claude Code SDK, not by the agent-runner. If the MCP server crashes or is restarted, the browser process may be orphaned.

**Recommended Test Cases:**
1. Verify Puppeteer launches successfully inside the container (Chromium path, sandbox flags)
2. Verify the MCP server can hold a Puppeteer browser across multiple `render_image` calls within a single session
3. Kill the MCP server process -- verify the Chromium process is also terminated (no zombies)
4. Run a scheduled task that generates an image -- verify end-to-end flow
5. Run two scheduled tasks back-to-back for the same group -- verify no port/lock conflicts with Chromium
6. Measure container memory usage with Puppeteer idle vs. active -- ensure it fits within container limits

**Recommendation:**
- Add explicit browser cleanup on MCP server exit: `process.on('exit', () => browser?.close())`
- Add `process.on('SIGTERM', ...)` handler for graceful shutdown
- Consider lazy-initializing the browser on first `render_image` call instead of at startup, to save memory when no images are needed
- Document the memory impact: Chromium adds ~100-200 MB RAM to each container

---

## Finding 9: Concurrency Issues with Simultaneous Renders

**Severity:** Major
**Area:** Concurrency / resource contention

**Analysis:**

The `render_image` MCP tool creates a new page per render (`browser.newPage()`) and closes it after. This is correct for sequential renders. However:

1. **Within a single session:** The Claude agent could theoretically call `render_image` multiple times concurrently (e.g., via agent teams). Multiple pages rendering simultaneously with Chromium could cause memory pressure or OOM in a constrained container.
2. **Filename collisions:** Two concurrent renders with `filename: 'rendered.png'` would race on the same output file. One would overwrite the other.
3. **IPC race:** Two `send_image` IPC files written at `Date.now()` in the same millisecond could collide, though the random suffix mitigates this.

**Recommended Test Cases:**
1. Call `render_image` 5 times concurrently with different filenames -- verify all succeed
2. Call `render_image` 5 times concurrently with the same filename -- verify behavior (likely file corruption or overwrite)
3. Measure memory usage during concurrent renders
4. Send 5 `send_image` IPC messages simultaneously -- verify all are processed

**Recommendation:**
- Force unique filenames in `render_image` by appending a timestamp and random suffix, ignoring user-provided filenames:
  ```typescript
  const safeFilename = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}.png`;
  ```
- Add a render semaphore limiting to 1-2 concurrent renders to prevent OOM
- Document in the skill that the agent should render sequentially, not in parallel

---

## Finding 10: `render_image` Missing Error Handling for Puppeteer Failures

**Severity:** Critical
**Area:** Error handling

**Analysis:**

The `render_image` handler in the plan (lines 178-188) has no try/catch. If Puppeteer crashes, the page fails to load, or the screenshot fails, the error propagates uncaught to the MCP framework.

Possible failures:
1. Chromium process died (OOM, signal) -- `browser.newPage()` throws
2. HTML contains an infinite loop in JavaScript -- page hangs indefinitely
3. Disk full -- `page.screenshot()` fails
4. Invalid HTML -- may render but produce unexpected output
5. The viewport dimensions are unreasonable (0x0, or 100000x100000) -- Chromium behavior is undefined

**Recommended Test Cases:**
1. Call `render_image` with empty HTML string -- verify output (blank PNG? error?)
2. Call `render_image` with HTML containing `<script>while(true){}</script>` -- verify timeout
3. Call `render_image` with width=0, height=0 -- verify error
4. Call `render_image` with width=50000, height=50000 -- verify behavior (likely OOM)
5. Call `render_image` after killing Chromium -- verify error is returned, not a crash
6. Call `render_image` when disk is full -- verify error message
7. Call `render_image` with HTML containing very large inline SVGs or images -- verify memory limits

**Recommendation:**
- Wrap the handler in try/catch with a meaningful MCP error response
- Add a page-level timeout: `await page.setDefaultTimeout(10000)`
- Validate `width` and `height` inputs (e.g., 100 <= width <= 4096, 100 <= height <= 4096)
- Add `page.on('pageerror', ...)` logging for debugging
- Ensure `page.close()` runs even on error (use try/finally)

---

## Finding 11: `send_image` IPC File Uses Non-Atomic Write

**Severity:** Minor
**Area:** Data integrity

**Analysis:**

The `send_image` handler (plan lines 205-219) uses `fs.writeFileSync()` directly. But the existing `writeIpcFile()` function in `ipc-mcp-stdio.ts` (lines 23-35) already does **atomic writes** (temp file + rename). The plan's `send_image` should use `writeIpcFile()` instead of raw `fs.writeFileSync()`.

The IPC watcher polls and reads files. If it reads a partially-written file, `JSON.parse()` will fail, and the message will be moved to the `errors/` directory and lost.

**Recommended Test Case:**
1. Verify `send_image` uses `writeIpcFile()` for atomic writes
2. Simulate a large IPC JSON file being read mid-write (by writing slowly) -- verify the watcher handles it

**Recommendation:** Use the existing `writeIpcFile(MESSAGES_DIR, ipcMessage)` helper.

---

## Finding 12: Authorization Check Missing for Image IPC Messages

**Severity:** Critical
**Area:** Security / authorization

**Analysis:**

The current IPC message handler (lines 76-101 of `ipc.ts`) checks authorization:

```typescript
if (isMain || (targetGroup && targetGroup.folder === sourceGroup)) {
  // authorized
}
```

The plan's `type: "image"` handler must apply the **same authorization check**. A non-main group container could craft a `type: "image"` IPC message targeting a different group's JID. Without the authorization check, it would send the image to an unauthorized chat.

**Recommended Test Cases:**
1. From a non-main group, send an image IPC targeting that group's own JID -- should succeed
2. From a non-main group, send an image IPC targeting a different group's JID -- should be blocked
3. From the main group, send an image IPC targeting any JID -- should succeed

**Recommendation:** Copy the exact authorization pattern from the existing message handler.

---

## Finding 13: `media/` Directory Not Created in Container's IPC Mount

**Severity:** Major
**Area:** Directory setup

**Analysis:**

The plan says (item #5, lines 139-146) to add `media/` to the IPC mount. Looking at the actual `container-runner.ts` (lines 152-155), the IPC directory is created with:

```typescript
fs.mkdirSync(path.join(groupIpcDir, 'messages'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'tasks'), { recursive: true });
fs.mkdirSync(path.join(groupIpcDir, 'input'), { recursive: true });
```

The Dockerfile (line 51) also creates these:
```
RUN mkdir -p /workspace/ipc/messages /workspace/ipc/tasks /workspace/ipc/input
```

Neither creates `media/`. The `render_image` tool writes to `/workspace/ipc/media/{filename}`, which will fail with `ENOENT` if `media/` doesn't exist.

**Recommended Test Cases:**
1. Start a fresh container and call `render_image` -- verify it doesn't fail with "no such file or directory"
2. Verify `media/` directory exists inside the container at `/workspace/ipc/media/`

**Recommendation:** Add `media/` to both locations:
- `container-runner.ts`: `fs.mkdirSync(path.join(groupIpcDir, 'media'), { recursive: true });`
- Dockerfile: add `/workspace/ipc/media` to the `mkdir` command
- Or better: have the `render_image` tool call `fs.mkdirSync(path.dirname(outputPath), { recursive: true })` defensively

---

## Finding 14: Template Token Injection via Untrusted Data

**Severity:** Major
**Area:** Data integrity / injection

**Analysis:**

Templates use placeholder tokens like `{{CORE_COMPLETION}}` that the agent replaces with data from `tracker.csv` and `week-*.md`. The current `tracker.csv` has a `notes` column that is free-text user input.

If the user's notes contain `{{CORE_COMPLETION}}` or HTML tags, and the agent does naive string replacement, the template could be corrupted:

1. **Token collision:** User note "I planned to hit {{CORE_COMPLETION}} today" would be double-replaced
2. **HTML injection:** User note containing `<script>alert(1)</script>` would be injected into the HTML, executed by Puppeteer, and potentially cause unexpected behavior
3. **CSS injection:** User note containing `</style><style>body{display:none}</style>` would break the card layout

The plan says "string interpolation" (line 30) but doesn't specify an escaping strategy.

**Recommended Test Cases:**
1. Set a tracker note containing `{{WEEK_NUMBER}}` -- verify it appears literally, not replaced with a number
2. Set a tracker note containing `<b>bold</b>` -- verify it appears as literal text, not bold
3. Set a tracker note containing `<script>document.title='hacked'</script>` -- verify no script execution
4. Set a tracker note containing characters: `& < > " '` -- verify correct HTML entity escaping
5. Set a tracker note with 10,000 characters -- verify layout doesn't break

**Recommendation:**
- HTML-escape all user data before template injection (at minimum: `& < > " '`)
- Use a different token format (e.g., `__CORE_COMPLETION__`) that's less likely to appear in user text
- Or use a proper templating library (Handlebars, EJS) that handles escaping by default
- Truncate long strings to prevent layout overflow

---

## Finding 15: Empty Data Edge Cases in Templates

**Severity:** Major
**Area:** Edge cases

**Analysis:**

The `tracker.csv` currently has only headers and no data rows. The week files have no checked checkboxes. Templates need to handle:

1. **Empty tracker.csv:** No data rows. `{{VELOCITY}}`, `{{CORE_PCT}}`, etc. would be undefined/NaN
2. **No week file for current week:** `week-*.md` might not exist yet (Monday kickoff before `plan` runs)
3. **All tasks unchecked:** `{{CORE_DONE}}` = 0, `{{CORE_PCT}}` = 0%. Division by zero if `{{CORE_TOTAL}}` = 0
4. **No monthly file:** `{month}-{year}.md` might not exist for a new month
5. **Unicode in task names:** Week files may contain emojis, accented characters, CJK characters
6. **Very long task descriptions:** A task name with 500 characters could overflow card layout

**Recommended Test Cases:**
1. Render weekly progress card with empty `tracker.csv` (headers only)
2. Render daily summary card when no week file exists
3. Render weekly progress card with 0 Core tasks, 0 Flex tasks
4. Render with task names containing: emoji, Arabic text, very long English text (500 chars), newlines
5. Render monthly dashboard with no completed months
6. Render with `energy_level` values of 0, negative numbers, non-numeric strings

**Recommendation:**
- Define default/fallback values for every template token
- Add "no data" state for each template (e.g., "No progress logged yet" card)
- Truncate task names to a reasonable length (e.g., 80 characters) with ellipsis
- Test with the actual current Cascade data (which is mostly empty)

---

## Finding 16: Cross-Platform Rendering Consistency

**Severity:** Minor
**Area:** Rendering consistency

**Analysis:**

Chromium in the Docker container (Debian-based `node:22-slim`) will use Linux font rendering (FreeType). Users view the images on mobile (iOS, Android) which have different display characteristics.

1. **Font hinting:** Linux renders fonts differently than macOS/Windows. Text may look slightly different in the container vs. a local browser preview
2. **Emoji rendering:** The Dockerfile installs `fonts-noto-color-emoji`, but Noto emoji look different from Apple emoji. If templates include emoji, the rendered card will show Noto emoji, which may look unfamiliar to iPhone users
3. **Subpixel rendering:** `deviceScaleFactor: 2` helps, but Chromium's subpixel rendering on Linux may differ from macOS

**Risk:** Low -- since images are viewed on mobile at phone resolution, minor rendering differences are unlikely to be noticeable.

**Recommended Test Cases:**
1. Render a card in the container and compare with the same HTML rendered in Chrome on macOS
2. View the container-rendered PNG on an iPhone and an Android phone
3. Verify emoji render correctly (not as tofu/boxes)

**Recommendation:** Accept Linux rendering as the standard. If pixel-perfect cross-platform consistency is needed later, consider Satori + resvg (mentioned in the plan as a fallback).

---

## Finding 17: Browser Process Zombie on Container Crash

**Severity:** Minor
**Area:** Resource cleanup

**Analysis:**

The plan initializes Puppeteer's browser at container startup. If the MCP server process is killed (OOM, SIGKILL, container timeout), the Chromium process may not be cleaned up.

Looking at the container lifecycle:
- Container runs `entrypoint.sh` which runs `node index.js`
- `index.js` spawns MCP server as a child process
- MCP server launches Chromium

If Docker sends SIGTERM to the container, only PID 1 receives it. Child processes (MCP server, Chromium) may not receive signals.

**Risk:** Within Docker, when the container stops, all processes are killed. Docker sends SIGTERM, waits 10 seconds, then SIGKILL. So zombie processes are cleaned up by container teardown. Risk is low.

**Recommended Test Case:**
1. Start container, render an image, then `docker stop` the container
2. Verify no Chromium processes remain on the host

**Recommendation:** Low priority. Docker container lifecycle handles this. No action needed unless running outside Docker.

---

## Finding 18: `puppeteer` vs `puppeteer-core` Inconsistency

**Severity:** Minor
**Area:** Dependency management

**Analysis:**

The plan has an inconsistency:
- Dockerfile section (line 240): `RUN npm install puppeteer` (full package with bundled Chromium)
- Dependencies table (line 406): `puppeteer-core` (~3 MB, uses system Chromium)

These are different packages. `puppeteer` will download its own Chromium even with `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true` (env var prevents download at install time, but the package is larger). `puppeteer-core` is the correct choice since Chromium is already in the container.

**Import difference:**
- `puppeteer`: `import puppeteer from 'puppeteer'`
- `puppeteer-core`: `import puppeteer from 'puppeteer-core'`

And `puppeteer-core` requires explicit `executablePath` (the plan provides this).

**Recommended Test Case:**
1. Install `puppeteer-core` (not `puppeteer`) in the container
2. Verify it uses `/usr/bin/chromium` correctly
3. Verify the container image size didn't increase significantly

**Recommendation:** Use `puppeteer-core` consistently in both the Dockerfile and code. Update the Dockerfile to:
```dockerfile
RUN npm install puppeteer-core
```

---

## Finding 19: Missing `media/` Path in IPC Message Validation

**Severity:** Minor
**Area:** Input validation

**Analysis:**

The `send_image` MCP tool (plan lines 205-219) takes an `image_path` string from the agent. There's no validation that:
1. The path actually exists
2. The path is within `/workspace/ipc/media/` (the agent could specify any container path)
3. The file is actually a PNG (could be any file)
4. The file size is reasonable

**Recommended Test Cases:**
1. Call `send_image` with a non-existent path -- verify error message
2. Call `send_image` with `image_path: '/etc/passwd'` -- verify it's rejected
3. Call `send_image` with a path to a text file -- verify behavior
4. Call `send_image` with a 100 MB file -- verify behavior

**Recommendation:**
- Validate the path starts with `/workspace/ipc/media/`
- Check file exists before writing IPC
- Optionally check file extension is `.png`

---

## Finding 20: Existing Test Coverage Gap -- No Tests for Channel `sendImage`

**Severity:** Minor
**Area:** Test coverage

**Analysis:**

The testing plan (lines 456-464) lists 6 test types. Looking at existing tests:
- `channels/whatsapp.test.ts` -- exists, likely tests `sendMessage`
- `channels/telegram.test.ts` -- exists, likely tests `sendMessage`
- `ipc-auth.test.ts` -- tests IPC authorization

The plan should add:
1. **Unit tests for `sendImage` on both channels** -- the plan mentions this (items 2-3)
2. **IPC integration test for `type: "image"`** -- mentioned (item 4)
3. **No negative test cases** -- the plan doesn't mention testing error paths

**Missing from the testing plan:**
- What happens when Baileys `sendMessage` with `{ image: buffer }` fails (network error, invalid JID)?
- What happens when grammy `sendDocument` fails (bot blocked, chat not found)?
- What happens when `render_image` is called with malformed HTML?
- Regression tests for existing functionality after the `Channel` interface change
- Load/stress testing (rendering 50 images in a row)

**Recommendation:** Add negative test cases for every new function. Each function should have at least one "happy path" and one "error path" test.

---

## Finding 21: `send_image` Tool Uses `currentChatJid` Global

**Severity:** Minor
**Area:** Code quality / globals

**Analysis:**

The plan's `send_image` handler (line 209) references `currentChatJid` and `currentGroupFolder`:

```typescript
chatJid: currentChatJid,
groupFolder: currentGroupFolder,
```

But the existing MCP server (`ipc-mcp-stdio.ts`) uses module-level constants:

```typescript
const chatJid = process.env.NANOCLAW_CHAT_JID!;
const groupFolder = process.env.NANOCLAW_GROUP_FOLDER!;
```

The plan should use these existing constants (`chatJid` and `groupFolder`), not introduce new globals.

**Recommendation:** Use the existing constants. This is a minor documentation inconsistency in the plan.

---

## Finding 22: `render_image` Does Not Wait for Page Load Completion

**Severity:** Critical
**Area:** Rendering correctness

**Analysis:**

The plan specifies `waitUntil: 'domcontentloaded'` (line 183). This fires when the HTML is parsed, but:

1. **CSS `@import` not loaded:** External stylesheets (Google Fonts) won't be fetched yet
2. **Images not loaded:** If templates include `<img>` tags (e.g., icons, logos), they may not be rendered
3. **CSS transitions/animations:** If templates use CSS animations for visual flair, they'll be captured mid-animation

The safer option is `waitUntil: 'networkidle0'` (no network requests for 500ms) which ensures everything is loaded. The tradeoff is higher latency (~1-3 seconds more).

This overlaps with Finding 2 (font loading) but is broader -- it affects any external resource.

**Recommended Test Cases:**
1. Render with `domcontentloaded` and check if fonts/images are present
2. Render with `networkidle0` and compare output
3. Render with `networkidle2` (allows 2 outstanding requests) as a middle ground
4. Measure render time for each option

**Recommendation:** Use `networkidle0` by default, or better yet, bundle all resources inline (fonts as base64, CSS inline in `<style>` tags) to eliminate external dependencies entirely.

---

## Finding 23: Plan Does Not Address Rollback Strategy

**Severity:** Minor
**Area:** Deployment risk

**Analysis:**

The plan modifies 7 existing files and adds 6 new files across 2 repos. If something goes wrong in production:

1. The `Channel` interface change affects all message sending -- a bug here could break all messaging
2. The IPC handler change could break existing text message delivery if the `else if` logic is wrong
3. Puppeteer in the container could cause OOM and crash the container for all requests, not just image ones

**Recommendation:**
- Implement the changes behind a feature flag (e.g., `ENABLE_IMAGE_SUPPORT=true` env var)
- Make `sendImage` optional on the interface (as noted in Finding 4)
- Add the Puppeteer initialization as lazy (only start browser when first `render_image` is called)
- This way, if images cause problems, setting the flag to `false` reverts to text-only without code changes

---

## Summary Table

| # | Finding | Severity | Area |
|---|---------|----------|------|
| 1 | Image file size may exceed WhatsApp 5MB limit | Blocker | Image sizing |
| 2 | Google Font loading fails in container | Blocker | Font loading |
| 3 | IPC handler has no `type: "image"` support / `IpcDeps` missing `sendImage` | Critical | IPC handling |
| 4 | Channel interface change breaks existing implementations | Critical | Regression |
| 5 | Telegram `sendDocument` UX degradation vs. `sendPhoto` | Major | UX |
| 6 | WhatsApp 24h window failure handling is under-specified | Major | WhatsApp |
| 7 | No cleanup of rendered PNG files on failure | Major | Resources |
| 8 | Scheduled task + container lifecycle interaction | Major | Lifecycle |
| 9 | Concurrency issues with simultaneous renders | Major | Concurrency |
| 10 | `render_image` missing error handling for Puppeteer failures | Critical | Error handling |
| 11 | `send_image` IPC file uses non-atomic write | Minor | Data integrity |
| 12 | Authorization check missing for image IPC messages | Critical | Security |
| 13 | `media/` directory not created in IPC mount | Major | Setup |
| 14 | Template token injection via untrusted data | Major | Injection |
| 15 | Empty data edge cases in templates | Major | Edge cases |
| 16 | Cross-platform rendering consistency | Minor | Rendering |
| 17 | Browser process zombie on container crash | Minor | Cleanup |
| 18 | `puppeteer` vs `puppeteer-core` inconsistency | Minor | Dependencies |
| 19 | Missing `media/` path validation in `send_image` | Minor | Validation |
| 20 | No negative test cases in testing plan | Minor | Test coverage |
| 21 | `send_image` references non-existent globals | Minor | Code quality |
| 22 | `render_image` does not wait for page load completion | Critical | Rendering |
| 23 | No rollback strategy | Minor | Deployment |

**Blockers (2):** Must fix before implementation begins.
**Critical (5):** Must fix during implementation. Will cause runtime failures if not addressed.
**Major (8):** Should fix. Will cause user-visible issues or data loss.
**Minor (8):** Nice to fix. Code quality, consistency, and minor UX improvements.

---

## Recommended Priority Order

1. **Fix Blockers first:** Font loading strategy (bundle locally or use `networkidle0`) and add image size validation with fallback
2. **Address Critical during implementation:** Error handling in `render_image`, authorization in IPC, `IpcDeps` interface update, page load waiting strategy, optional `sendImage` on Channel interface
3. **Address Major alongside implementation:** PNG cleanup, directory creation, template escaping, empty data handling, concurrency limits
4. **Address Minor in polish phase:** Atomic writes, path validation, test coverage, naming consistency

---

*Review based on actual source code in the NanoClaw repository as of February 19, 2026.*
