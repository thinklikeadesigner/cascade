# WhatsApp Image Sending API Research

## Summary

There are two main paths to send images programmatically via WhatsApp:

1. **Meta WhatsApp Cloud API (direct)** -- Free to use (pay only per-message Meta fees), full control, more setup
2. **Third-party providers (Twilio, Bird/MessageBird, etc.)** -- Easier setup, add a per-message markup

Both paths require a WhatsApp Business Account and phone number. The On-Premises API was deprecated in October 2025; Cloud API (hosted by Meta) is now the only option.

---

## Option 1: Meta WhatsApp Cloud API (Direct)

### Setup Requirements

1. Create a Meta for Developers app at developers.facebook.com
2. Add WhatsApp product to the app
3. Create a System User in Meta Business Manager for a permanent access token
4. Get a WhatsApp Business phone number (test number provided for free in sandbox)
5. Configure webhooks to receive inbound messages

### Endpoints

All requests go through the Graph API v21.0 (current as of Feb 2026).

**Send a message (including images):**
```
POST https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages
```

**Upload media (to get a media_id):**
```
POST https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/media
```

**Retrieve/delete media:**
```
GET  https://graph.facebook.com/v21.0/{MEDIA_ID}
DELETE https://graph.facebook.com/v21.0/{MEDIA_ID}
```

### Headers

```
Authorization: Bearer {PERMANENT_ACCESS_TOKEN}
Content-Type: application/json
```

Token should be generated via System Users (never expires). Never expose in frontend or git repos.

### Sending an Image by URL

The simplest approach -- provide a publicly accessible HTTPS URL:

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "15551234567",
  "type": "image",
  "image": {
    "link": "https://example.com/chart.png",
    "caption": "Your weekly progress report"
  }
}
```

### Sending an Image by Media ID (Upload First)

Step 1 -- Upload the file:

```bash
curl -X POST \
  'https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/media' \
  -H 'Authorization: Bearer {TOKEN}' \
  -F 'file=@"/path/to/image.png"' \
  -F 'type="image/png"' \
  -F 'messaging_product="whatsapp"'
```

Response:
```json
{ "id": "1234567890" }
```

Step 2 -- Send using the media_id:

```json
{
  "messaging_product": "whatsapp",
  "recipient_type": "individual",
  "to": "15551234567",
  "type": "image",
  "image": {
    "id": "1234567890",
    "caption": "Your weekly progress report"
  }
}
```

### Python Example (Direct API, requests library)

```python
import requests
import os

PHONE_NUMBER_ID = os.environ["WA_PHONE_NUMBER_ID"]
ACCESS_TOKEN = os.environ["WA_ACCESS_TOKEN"]
RECIPIENT = "15551234567"

BASE_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}"
HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

# --- Method A: Send image by URL ---
def send_image_by_url(to: str, image_url: str, caption: str = ""):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption,
        },
    }
    resp = requests.post(f"{BASE_URL}/messages", json=payload, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

# --- Method B: Upload then send by media_id ---
def upload_image(file_path: str) -> str:
    upload_headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    with open(file_path, "rb") as f:
        files = {"file": (file_path, f, "image/png")}
        data = {"type": "image/png", "messaging_product": "whatsapp"}
        resp = requests.post(f"{BASE_URL}/media", headers=upload_headers, files=files, data=data)
    resp.raise_for_status()
    return resp.json()["id"]

def send_image_by_id(to: str, media_id: str, caption: str = ""):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption,
        },
    }
    resp = requests.post(f"{BASE_URL}/messages", json=payload, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

# Usage:
# send_image_by_url(RECIPIENT, "https://example.com/chart.png", "Weekly report")
# media_id = upload_image("/tmp/chart.png")
# send_image_by_id(RECIPIENT, media_id, "Weekly report")
```

### Node.js Example (Direct API, axios)

```javascript
const axios = require("axios");

const PHONE_NUMBER_ID = process.env.WA_PHONE_NUMBER_ID;
const ACCESS_TOKEN = process.env.WA_ACCESS_TOKEN;
const BASE_URL = `https://graph.facebook.com/v21.0/${PHONE_NUMBER_ID}`;

// --- Method A: Send image by URL ---
async function sendImageByUrl(to, imageUrl, caption = "") {
  const { data } = await axios.post(
    `${BASE_URL}/messages`,
    {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "image",
      image: { link: imageUrl, caption },
    },
    { headers: { Authorization: `Bearer ${ACCESS_TOKEN}` } }
  );
  return data;
}

// --- Method B: Upload then send by media_id ---
const FormData = require("form-data");
const fs = require("fs");

async function uploadImage(filePath) {
  const form = new FormData();
  form.append("file", fs.createReadStream(filePath));
  form.append("type", "image/png");
  form.append("messaging_product", "whatsapp");

  const { data } = await axios.post(`${BASE_URL}/media`, form, {
    headers: {
      Authorization: `Bearer ${ACCESS_TOKEN}`,
      ...form.getHeaders(),
    },
  });
  return data.id;
}

async function sendImageById(to, mediaId, caption = "") {
  const { data } = await axios.post(
    `${BASE_URL}/messages`,
    {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "image",
      image: { id: mediaId, caption },
    },
    { headers: { Authorization: `Bearer ${ACCESS_TOKEN}` } }
  );
  return data;
}
```

---

## Option 2: Twilio WhatsApp API

### Why Twilio

- Official WhatsApp Business API partner since 2018
- Simpler setup than direct Meta API (no Meta Business Manager configuration)
- Sandbox for immediate testing (no phone number purchase required)
- Handles webhook infrastructure, token management, message queuing
- SDKs for Python, Node.js, PHP, Java, C#, Go

### Setup

1. Create a Twilio account
2. Activate the WhatsApp Sandbox (for testing) or register a WhatsApp-enabled number (production)
3. Install SDK: `pip install twilio` or `npm install twilio`
4. Set env vars: `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`

### Python Example

```python
from twilio.rest import Client
import os

client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])

message = client.messages.create(
    from_="whatsapp:+14155238886",       # Your Twilio WhatsApp number
    to="whatsapp:+15551234567",          # Recipient
    media_url=["https://example.com/chart.png"],  # Publicly accessible URL
    body="Your weekly progress report",  # Caption (optional for images)
)
print(message.sid)
```

### Node.js Example

```javascript
const twilio = require("twilio");
const client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);

async function sendImage() {
  const message = await client.messages.create({
    from: "whatsapp:+14155238886",
    to: "whatsapp:+15551234567",
    mediaUrl: ["https://example.com/chart.png"],
    body: "Your weekly progress report",
  });
  console.log(message.sid);
}
```

### Twilio Limitations

- Media must be at a **publicly accessible URL** (no local file upload through the SDK -- you host the image and provide the URL)
- **One media attachment per message**, max 5 MB
- WhatsApp does not support body text in the same message as video, audio, document, vCard, or location (images with body text ARE supported)
- Outside the 24-hour session window, only pre-approved templates can be sent

---

## Option 3: Other Third-Party Providers

| Provider | Markup per message | Notes |
|----------|-------------------|-------|
| **Twilio** | ~$0.005 on top of Meta fees | Best docs, largest community, sandbox for testing |
| **Bird (MessageBird)** | ~$0.005 per message | Visual flow builder, good for non-technical users |
| **Infobip** | Custom pricing | Enterprise-focused, omnichannel |
| **WATI** | From $39/mo + per-message | Dashboard + API, good for small businesses |
| **Respond.io** | From $79/mo | Multi-channel inbox with API access |

For NanoClaw's use case (programmatic image sending from a server), **Twilio or direct Meta Cloud API** are the best fits. Bird/MessageBird is a solid alternative if omnichannel is needed later.

---

## Media Constraints

| Property | Limit |
|----------|-------|
| **Image formats** | JPEG, PNG, WebP |
| **Max image size** | 5 MB |
| **Max video size** | 16 MB |
| **Max document size** | 100 MB |
| **Sticker size** | 100 KB (static) / 500 KB (animated), 512x512px, transparent bg |
| **Media upload rate limit** | 25 requests/sec per phone number |
| **Message send rate limit** | 80 msg/sec (Cloud API), up to 500 msg/sec at scale |
| **Hosted media retention** | 30 days on WhatsApp servers |

---

## The 24-Hour Session Window

This is the single most important constraint for NanoClaw's image-sending use case.

### How it works:
- When a user sends a message to your WhatsApp Business number, a **24-hour session window** opens
- Within this window, you can send **free-form messages** including images, without template approval
- Outside the window, you can ONLY send **pre-approved template messages**

### Implications for NanoClaw:
- **Morning tasks message**: If the user replied the previous evening (log prompt), the 24h window is likely open. Free-form images work.
- **Evening log prompt**: If the user replied that morning, the window is open. Free-form images work.
- **Sunday review / Monday kickoff**: If the user hasn't messaged in >24 hours, these need to be template messages. Images CAN be included in templates, but the template must be pre-approved by Meta.
- **Proactive status images**: Only possible within 24h of user's last message, unless sent via an approved template.

### Template Messages with Media:
- Templates can include a **header** of type `image` (with a media URL or media_id)
- The template text and header must be submitted and approved by Meta before use
- Approval typically takes minutes to 48 hours
- Templates cannot be edited after submission -- create a new one for changes
- Meta may pause templates with low engagement (read rate) for 3-6 hours

---

## Pricing (as of Feb 2026)

Meta charges per-message based on category. Media (images) do NOT have a separate surcharge -- they're billed at the same rate as text for the same category.

| Category | US price (per msg) | Notes |
|----------|-------------------|-------|
| **Marketing** | ~$0.025 | Proactive promotional messages |
| **Utility** | ~$0.004 | Transactional notifications (order updates, etc.) |
| **Authentication** | ~$0.004 | OTP / login codes |
| **Service** | Free | Replies within 24h customer-initiated window |

NanoClaw's daily progress images would likely fall under **Utility** ($0.004/msg) if sent as templates, or **Service** (free) if sent within a user-initiated 24h window.

At $0.004/msg for 4 daily messages = ~$0.48/month per user. Very cheap.

Third-party providers add ~$0.005/msg markup on top.

---

## Recommended Approach for NanoClaw

### Simplest Path: Twilio

1. **Why**: Sandbox for instant testing, no Meta Business Manager setup, simple SDK, handles webhooks
2. **How**: Host the rendered PNG at a public URL (e.g., S3, Cloudflare R2, or a simple Express static server), pass URL in `media_url` parameter
3. **Cost**: Meta fees + $0.005/msg Twilio markup
4. **Effort**: ~1 hour to send first image in sandbox

### Most Control: Direct Meta Cloud API

1. **Why**: No third-party markup, full API access, upload media directly (no need for public URL hosting)
2. **How**: Upload PNG via multipart form to `/media` endpoint, get media_id, send via `/messages` endpoint
3. **Cost**: Meta fees only
4. **Effort**: ~2-4 hours including Meta Business Manager setup

### Recommendation

Start with **Twilio sandbox** for development and testing. Switch to **direct Meta Cloud API** for production if cost optimization matters at scale. The API surface is nearly identical -- the migration is straightforward.

For the specific NanoClaw use case (sending a rendered PNG of a weekly status card):
1. Render the HTML status card to PNG (see separate rendering research)
2. Upload PNG to cloud storage or WhatsApp's media endpoint
3. Send image message to user within the 24h window, or via approved template outside it
4. The image `caption` field serves as the text summary alongside the visual

---

## Gotchas and Pitfalls

1. **24-hour window is strict** -- messages sent outside it without an approved template will be rejected outright, not queued
2. **Image URL must be HTTPS** -- HTTP will not work. For Twilio, the URL must be publicly accessible (no localhost)
3. **Uploaded media expires after 30 days** on WhatsApp servers -- re-upload if needed
4. **Template approval is not instant** -- plan for 24-48h approval time; have templates submitted well before you need them
5. **Templates cannot be edited** -- create a new version, submit for approval, delete the old one
6. **Low-engagement templates get paused** -- if users don't read your messages, Meta may pause the template for 3-6 hours or permanently deactivate it
7. **Phone number format** -- always use E.164 format without the + prefix for Meta API (e.g., `15551234567`), with `whatsapp:+` prefix for Twilio
8. **Rate limits on media upload** -- 25 uploads/sec per phone number. Not a concern for NanoClaw's scale, but worth knowing
9. **Sandbox limitations** -- Twilio sandbox only works with pre-registered recipient numbers. Production requires a verified WhatsApp Business number
10. **WhatsApp does NOT support body text with video/audio/document** -- but images with captions ARE supported
