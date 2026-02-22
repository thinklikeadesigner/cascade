# Telegram Bot API: Sending Images — Research Notes

## 1. Bot Creation via BotFather

### Steps
1. Open Telegram, search for `@BotFather`
2. Send `/newbot`
3. Choose a display name (e.g., "NanoClaw Bot")
4. Choose a username ending in `bot` (e.g., `nanoclaw_bot`)
5. BotFather returns an **API token** like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
6. Store the token securely (env var, secrets manager — never commit to git)

### Useful BotFather Commands
- `/setdescription` — bot description shown on its profile
- `/setabouttext` — short about text
- `/setuserpic` — bot avatar
- `/mybots` — manage existing bots

---

## 2. Getting the chat_id

A bot can only send messages to users who have **started a conversation** with it (sent `/start`). To get the `chat_id`:

### Method A: getUpdates endpoint
1. User sends any message to the bot
2. Call `GET https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Parse the JSON response — look for `result[].message.chat.id`

### Method B: Webhook payload
If using webhooks, the incoming update payload contains `message.chat.id`.

### Method C: Forward from user
If the bot is in a group, the `chat.id` will be the **group's ID** (negative number). For 1-on-1 chats, it's the **user's ID** (positive number).

**Important:** `chat_id` values are stable — store them after the initial interaction.

---

## 3. Core API Methods

### 3.1 sendPhoto

Sends a photo with **lossy compression** applied by Telegram. Images are resized to max ~2560px on the longest edge and compressed to ~85% JPEG quality.

**Endpoint:** `POST https://api.telegram.org/bot<TOKEN>/sendPhoto`

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat ID or @username |
| `photo` | InputFile or String | Yes | Photo to send (file upload, file_id, or URL) |
| `caption` | String | No | Caption, 0-1024 characters |
| `parse_mode` | String | No | `HTML`, `Markdown`, or `MarkdownV2` |
| `show_caption_above_media` | Boolean | No | Show caption above image |
| `has_spoiler` | Boolean | No | Cover with spoiler animation |
| `disable_notification` | Boolean | No | Silent message |
| `protect_content` | Boolean | No | Prevent forwarding/saving |
| `reply_parameters` | ReplyParameters | No | Reply configuration |
| `reply_markup` | Markup | No | Inline keyboard, custom keyboard, etc. |

**Photo size limits for sendPhoto:**
- Upload (multipart): **10 MB** max for photos
- Via URL: **5 MB** max (Telegram downloads it server-side)
- Supported formats: JPEG, PNG, GIF (first frame), BMP, TIFF, WebP
- PNG files are **re-encoded as JPEG** with lossy compression

### 3.2 sendDocument

Sends a file **without compression**. The original file is preserved byte-for-byte. Telegram generates a thumbnail for preview, but the download is the original quality.

**Endpoint:** `POST https://api.telegram.org/bot<TOKEN>/sendDocument`

**Key Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat ID or @username |
| `document` | InputFile or String | Yes | File to send |
| `thumbnail` | InputFile or String | No | Custom thumbnail (JPEG, max 200kB, 320x320px) |
| `caption` | String | No | Caption, 0-1024 characters |
| `parse_mode` | String | No | `HTML`, `Markdown`, or `MarkdownV2` |
| `disable_content_type_detection` | Boolean | No | Skip auto MIME type detection |
| `disable_notification` | Boolean | No | Silent message |
| `protect_content` | Boolean | No | Prevent forwarding/saving |
| `reply_markup` | Markup | No | Inline keyboard, etc. |

**Document size limit:** **50 MB** max upload.

**Note:** sendDocument via URL only works for `.pdf` and `.zip` files. For images, use multipart upload or file_id.

### 3.3 sendPhoto vs sendDocument — Which to Use

| Aspect | sendPhoto | sendDocument |
|--------|-----------|--------------|
| Compression | Yes — lossy JPEG recompression | None — original file preserved |
| Max resolution | ~2560px long edge | Unlimited (within 50MB) |
| Inline preview | Full-size image in chat | Thumbnail + download link |
| PNG quality | Degraded (re-encoded to JPEG) | Preserved exactly |
| User experience | Image displays inline, tappable | File attachment with preview thumbnail |
| Max file size | 10 MB (upload) / 5 MB (URL) | 50 MB |

**Recommendation for NanoClaw:** Use `sendDocument` for generated PNG status cards/reports to preserve quality. Use `sendPhoto` only if inline display matters more than quality (e.g., quick chart previews).

---

## 4. Three Ways to Send Files (InputFile)

### 4.1 Multipart Upload (recommended for generated images)
Upload the file directly from your server. Best for dynamically generated PNGs.

```
POST multipart/form-data
- photo=@/path/to/image.png
- chat_id=123456789
```

### 4.2 file_id (for re-sending previously uploaded files)
After any successful send, the response contains a `file_id`. Use it to re-send without re-uploading:

```json
{ "photo": "AgACAgIAAxkBAAI..." }
```

`file_id` values are persistent and can be reused across requests. They are specific to the bot (cannot be shared between bots).

### 4.3 HTTP URL (Telegram downloads server-side)
Pass a public URL. Telegram servers fetch and cache it:

```json
{ "photo": "https://example.com/image.png" }
```

5 MB limit for photos via URL. Not usable for sendDocument (except .pdf and .zip).

---

## 5. Code Examples

### 5.1 Python — Raw HTTP (requests)

Simplest approach, no library dependency beyond `requests`:

```python
import requests

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_photo(chat_id: str, image_path: str, caption: str = ""):
    """Send a photo with compression."""
    with open(image_path, "rb") as photo:
        resp = requests.post(
            f"{API_URL}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": photo},
        )
    resp.raise_for_status()
    return resp.json()

def send_document(chat_id: str, file_path: str, caption: str = ""):
    """Send a file without compression (preserves PNG quality)."""
    with open(file_path, "rb") as doc:
        resp = requests.post(
            f"{API_URL}/sendDocument",
            data={"chat_id": chat_id, "caption": caption},
            files={"document": doc},
        )
    resp.raise_for_status()
    return resp.json()

# Usage
send_document(CHAT_ID, "/tmp/weekly-status.png", caption="Week 3 Status")
```

### 5.2 Python — python-telegram-bot v20+ (async)

```python
import asyncio
import telegram

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

async def send_status_image(image_path: str, caption: str = ""):
    bot = telegram.Bot(token=TOKEN)
    async with bot:
        # sendDocument preserves PNG quality
        with open(image_path, "rb") as f:
            await bot.send_document(
                chat_id=CHAT_ID,
                document=f,
                caption=caption,
            )

asyncio.run(send_status_image("/tmp/weekly-status.png", "Week 3 Status"))
```

### 5.3 Python — Send from Buffer (in-memory image)

```python
import io
import requests

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_png_buffer(chat_id: str, png_bytes: bytes, filename: str = "status.png", caption: str = ""):
    """Send an in-memory PNG as a document."""
    buf = io.BytesIO(png_bytes)
    buf.name = filename  # Telegram uses this for the filename display
    resp = requests.post(
        f"{API_URL}/sendDocument",
        data={"chat_id": chat_id, "caption": caption},
        files={"document": buf},
    )
    resp.raise_for_status()
    return resp.json()
```

### 5.4 Node.js — node-telegram-bot-api

```javascript
const TelegramBot = require("node-telegram-bot-api");
const fs = require("fs");

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;
const bot = new TelegramBot(TOKEN);

// Send photo (with compression)
async function sendPhoto(imagePath, caption = "") {
  const stream = fs.createReadStream(imagePath);
  return bot.sendPhoto(CHAT_ID, stream, { caption });
}

// Send document (no compression — preserves PNG quality)
async function sendDocument(filePath, caption = "") {
  const stream = fs.createReadStream(filePath);
  return bot.sendDocument(CHAT_ID, stream, { caption }, {
    filename: "status.png",
    contentType: "image/png",
  });
}

// Send from buffer (in-memory generated PNG)
async function sendPngBuffer(pngBuffer, caption = "") {
  return bot.sendDocument(CHAT_ID, pngBuffer, { caption }, {
    filename: "status.png",
    contentType: "image/png",
  });
}

sendDocument("/tmp/weekly-status.png", "Week 3 Status");
```

**Note:** For `sendDocument` with node-telegram-bot-api, the 4th argument is `fileOptions` — you must pass `{}` as the 3rd argument (query options) even if empty, or the file options will be misinterpreted.

### 5.5 Node.js — Telegraf v4

```javascript
const { Telegraf, Input } = require("telegraf");
const fs = require("fs");

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;

// From local file
await bot.telegram.sendDocument(CHAT_ID, Input.fromLocalFile("/tmp/status.png"), {
  caption: "Week 3 Status",
});

// From buffer
const pngBuffer = generateStatusImage(); // returns Buffer
await bot.telegram.sendDocument(CHAT_ID, Input.fromBuffer(pngBuffer, "status.png"), {
  caption: "Week 3 Status",
});

// From readable stream
const stream = fs.createReadStream("/tmp/status.png");
await bot.telegram.sendDocument(CHAT_ID, Input.fromReadableStream(stream, "status.png"), {
  caption: "Week 3 Status",
});
```

### 5.6 curl (for testing)

```bash
# Send photo (compressed)
curl -X POST \
  -F chat_id="$CHAT_ID" \
  -F photo=@"/tmp/status.png" \
  "https://api.telegram.org/bot$TOKEN/sendPhoto"

# Send document (uncompressed, preserves PNG)
curl -X POST \
  -F chat_id="$CHAT_ID" \
  -F document=@"/tmp/status.png" \
  -F caption="Week 3 Status" \
  "https://api.telegram.org/bot$TOKEN/sendDocument"

# Send from stdin (piped from image generator)
generate_png | curl -X POST \
  -F chat_id="$CHAT_ID" \
  -F document=@- \
  "https://api.telegram.org/bot$TOKEN/sendDocument"
```

---

## 6. Rate Limits

| Scope | Limit |
|-------|-------|
| Per chat (1-on-1) | ~1 message/second (short bursts OK) |
| Per group | 20 messages/minute |
| Bulk notifications | ~30 users/second (free tier) |
| Paid broadcasts | Up to 1000/second (requires 100K Stars balance + 100K MAU) |

Exceeding limits returns HTTP 429 with a `retry_after` field (seconds to wait).

**For NanoClaw:** Sending 1 status image to 1 user per scheduled event is well within limits. No rate limit concerns for single-user usage.

---

## 7. File Size Limits Summary

| Method | Upload Limit | Notes |
|--------|-------------|-------|
| sendPhoto (multipart) | 10 MB | Compressed by Telegram |
| sendPhoto (URL) | 5 MB | Telegram downloads server-side |
| sendDocument (multipart) | 50 MB | Original quality preserved |
| sendDocument (URL) | 50 MB | Only .pdf and .zip via URL |
| getFile (download) | 20 MB | For retrieving files from Telegram |

**For NanoClaw:** Generated PNG status cards will be well under 1 MB. No size concerns.

---

## 8. Image Compression Behavior

### sendPhoto compression pipeline:
1. PNG is re-encoded as JPEG (lossy)
2. Long edge capped at ~2560px
3. Quality target ~85%
4. Result: visible quality loss, especially on text, sharp edges, and transparency

### sendDocument behavior:
1. No re-encoding — file is stored and served as-is
2. Telegram generates a small thumbnail for inline preview
3. User taps to view/download the full-quality original
4. PNG transparency is preserved

### Recommendation
For generated status cards with text, charts, and sharp graphics: **always use sendDocument**. The slight UX cost (user taps to view full size) is worth the quality preservation. Text on compressed photos can become blurry and hard to read.

---

## 9. Implementation Considerations for NanoClaw

### Simplest Path: Raw HTTP with requests/fetch
- No library dependency beyond HTTP client
- Direct multipart POST to `https://api.telegram.org/bot<TOKEN>/sendDocument`
- Works identically in Python and Node.js
- Easy to test with curl

### Authentication
- Single bot token (from BotFather) stored as env var
- No OAuth, no session management, no token refresh
- Token is the only credential needed

### Delivery Flow
1. Generate PNG (from HTML-to-PNG pipeline)
2. POST to `/sendDocument` with the PNG bytes and chat_id
3. Check response for `ok: true`
4. On 429 error, wait `retry_after` seconds and retry

### Error Handling
- 400: Bad request (invalid chat_id, file too large, etc.)
- 401: Invalid bot token
- 403: Bot was blocked by the user or kicked from group
- 429: Rate limited — respect `retry_after`
- 5xx: Telegram server error — retry with backoff

### Setup Checklist
1. Create bot via BotFather
2. Store token in env var (`TELEGRAM_BOT_TOKEN`)
3. User sends `/start` to the bot
4. Fetch chat_id via getUpdates
5. Store chat_id in env var or config (`TELEGRAM_CHAT_ID`)
6. Test with curl sendDocument
7. Integrate into NanoClaw scheduled message pipeline

---

## Sources

- [Telegram Bot API — Official Documentation](https://core.telegram.org/bots/api)
- [Telegram Bots FAQ — Rate Limits and File Sizes](https://core.telegram.org/bots/faq)
- [Telegram Bot Tutorial — From BotFather to Hello World](https://core.telegram.org/bots/tutorial)
- [node-telegram-bot-api — Usage Documentation](https://github.com/yagop/node-telegram-bot-api/blob/master/doc/usage.md)
- [Telegraf v4 Documentation](https://telegraf.js.org/)
- [python-telegram-bot v22 — Bot Class Reference](https://docs.python-telegram-bot.org/telegram.bot.html)
- [Telegram Bot API curl Examples (Gist)](https://gist.github.com/SanariSan/4c7cca1aef10dfe0e27e55cfd97e9a53)
- [How to Get Telegram Bot Chat ID (Gist)](https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a)
