# Research: HTML-to-PNG Generation Approaches

## Context

NanoClaw needs to generate PNG images from HTML templates for sending visual status cards and weekly reviews via WhatsApp/Telegram. The solution must work in a production environment (server or container), handle a single 1200x800 image at a time, and produce pixel-perfect output matching modern CSS/HTML rendering.

---

## 1. Headless Chrome / Chromium

### 1a. Direct Chrome CLI

The simplest approach. Chrome's `--screenshot` flag captures a page to PNG directly from the command line.

**Command:**
```bash
chrome --headless --screenshot=/tmp/output.png --window-size=1200,800 file:///path/to/template.html
```

**Confirmed working on dev machine:**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --screenshot --window-size=1200,800 file:///path/to/file.html
```

**Pros:**
- Zero dependencies beyond Chrome/Chromium itself
- No Node.js, no npm packages, no library code
- Pixel-perfect rendering (it IS a real browser)
- Works with any HTML/CSS including animations frozen at render time
- Can be called from any language via subprocess

**Cons:**
- Cold start is slow (~1-2s to launch Chrome, render, capture, exit)
- No programmatic control over wait conditions or viewport beyond CLI flags
- Cannot reuse a browser instance across multiple screenshots
- Requires Chrome/Chromium installed in the environment

**Production deployment:**
- On a server: install `chromium-browser` via package manager
- In Docker: use `zenika/alpine-chrome` image (~423 MB compressed) or install Chromium in your base image
- Chrome flags for containers: `--no-sandbox --disable-gpu --disable-dev-shm-usage`

**Best for:** Simple, infrequent screenshot needs where cold start latency is acceptable.

---

### 1b. Puppeteer (Node.js)

High-level Node.js API for controlling headless Chrome. The most popular programmatic approach.

**Code example:**
```javascript
const puppeteer = require('puppeteer');

async function htmlToPng(htmlString, outputPath) {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 800, deviceScaleFactor: 2 });
  await page.setContent(htmlString, { waitUntil: 'networkidle0' });
  await page.screenshot({
    path: outputPath,
    type: 'png',
    optimizeForSpeed: true  // faster PNG encoding (zlib q1 / RLE)
  });
  await browser.close();
}
```

**Performance optimizations:**
- `optimizeForSpeed: true` -- uses faster PNG encoding, slightly larger files but noticeably faster capture
- `page.setContent()` instead of `page.goto()` -- avoids network round-trip for local HTML
- Return as Buffer instead of writing to disk to skip I/O
- Reuse browser instance across calls (launch once, create new pages)
- `deviceScaleFactor: 2` for Retina-quality output
- `waitForSelector()` instead of `waitUntil: 'networkidle0'` for faster triggering

**Typical timing (single 1200x800 screenshot from HTML string):**
- Cold start (launch browser + render + capture): ~1.5-3s
- Warm (reuse browser, new page): ~200-800ms
- With optimizeForSpeed: potentially 30-50% faster capture step

**Pros:**
- Full programmatic control (viewport, wait conditions, element selection)
- Can reuse browser instance for multiple screenshots (warm path is fast)
- Massive community, well-documented, actively maintained
- Pixel-perfect rendering
- Can screenshot specific DOM elements, not just full page
- Downloads its own Chromium -- no system dependency management

**Cons:**
- Requires Node.js runtime
- Chromium download is ~170-280 MB
- Memory-heavy (~100-300 MB per browser instance)
- Cold start latency

**Production deployment:**
- Puppeteer downloads its own Chromium by default
- For Docker, use `puppeteer/puppeteer` official image or configure `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD` with system Chromium
- Consider keeping a long-lived browser process and creating pages on demand

**Best for:** Production systems that generate screenshots frequently and need programmatic control.

---

### 1c. Playwright (Node.js / Python)

Microsoft's browser automation library. Similar to Puppeteer but supports multiple browsers.

**Code example (Node.js):**
```javascript
const { chromium } = require('playwright');

async function htmlToPng(htmlString, outputPath) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  await page.setContent(htmlString);
  await page.screenshot({ path: outputPath, type: 'png' });
  await browser.close();
}
```

**Code example (Python):**
```python
from playwright.sync_api import sync_playwright

def html_to_png(html_string, output_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 800})
        page.set_content(html_string)
        page.screenshot(path=output_path, type="png")
        browser.close()
```

**Performance vs Puppeteer:**
- Navigation-heavy scenarios: Playwright ~4.5s vs Puppeteer ~4.8s (Playwright slightly faster)
- Quick automation tasks: Puppeteer can be ~30% faster
- For single screenshot from HTML string: performance is nearly identical

**Pros:**
- Cross-browser support (Chromium, Firefox, WebKit)
- Python API available (useful if NanoClaw backend is Python)
- Auto-wait for elements -- less manual waitFor configuration
- Active development by Microsoft

**Cons:**
- Slightly heavier install (downloads browser binaries for all supported browsers by default, can be configured)
- Similar memory footprint to Puppeteer
- Slightly larger API surface to learn

**Best for:** Teams already using Playwright, or Python-based backends.

---

### 1d. chrome-headless-shell

As of Chrome v132 (January 2025), the old headless mode was extracted into a separate binary called `chrome-headless-shell`. It starts up faster than full headless Chrome and is specifically optimized for screenshots, PDF generation, and scraping.

**Pros:**
- Faster startup than full headless Chrome
- Purpose-built for exactly this use case
- Smaller footprint than full Chrome

**Cons:**
- Separate binary to install/manage
- Less commonly documented
- Fewer features than full headless (no extensions, limited DevTools)

**Best for:** High-performance screenshot pipelines where startup time matters.

---

## 2. Lightweight Alternatives (No Browser)

### 2a. Satori + resvg (Vercel)

Satori converts HTML/CSS to SVG using Yoga Layout (same as React Native). resvg-js converts SVG to PNG via Rust bindings. No browser needed.

**Code example:**
```javascript
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';

const svg = await satori(
  <div style={{ color: 'black', fontSize: 32 }}>Hello World</div>,
  {
    width: 1200,
    height: 800,
    fonts: [{ name: 'Inter', data: fontBuffer, weight: 400, style: 'normal' }],
  }
);

const resvg = new Resvg(svg, { fitTo: { mode: 'width', value: 1200 } });
const png = resvg.render().asPng();
```

**CSS Support (partial list):**
- Flexbox layout (full support)
- Typography (fontFamily, fontSize, fontWeight, lineHeight, letterSpacing, textAlign, textTransform, textOverflow, textDecoration, textShadow)
- Borders (width, style, color, radius)
- Backgrounds (color, image, gradients, position, size)
- Transforms (2D only -- no 3D)
- opacity, boxShadow, filter, clipPath, masks
- display: flex | none | contents
- position: relative | absolute | static

**Limitations:**
- No CSS selectors -- styles must be inline on every element
- No `<style>` tags, no external CSS, no `<link>` or `<script>`
- No `calc()` expressions
- No `z-index` (SVG paint order is DOM order)
- No CSS Grid
- No RTL languages
- No advanced typography (kerning, ligatures, OpenType features)
- No `currentColor` (except on `color` property itself)
- Fonts must be provided as Buffer/ArrayBuffer (TTF, OTF, WOFF only -- no WOFF2)
- Input is JSX-like, not raw HTML strings

**Performance:**
- Extremely fast: ~10-50ms for typical OG-style images
- No browser startup overhead
- Low memory: ~20-50 MB
- Works in serverless/edge runtimes (Vercel Edge, Cloudflare Workers, Deno)

**Pros:**
- Order-of-magnitude faster than browser-based approaches
- Tiny footprint, no browser dependency
- Works in edge/serverless environments
- Perfect for templated card-style images

**Cons:**
- Limited CSS subset -- cannot render arbitrary HTML
- JSX input, not HTML strings (need a conversion layer or write templates in JSX)
- Font management is manual
- Complex layouts may not render correctly

**Best for:** Templated image generation (OG images, status cards) where CSS needs are known and limited.

---

### 2b. wkhtmltoimage

Legacy tool using QtWebKit to render HTML to images.

**Status: DEPRECATED AND UNMAINTAINED**

- Deprecated since January 2023
- Depends on QtWebKit (deprecated in 2015, removed in 2016)
- Homebrew cask disabled as of December 2024
- Known security vulnerabilities in the underlying WebKit1 engine
- CSS/HTML rendering is stuck at ~2015-era browser capabilities

**Verdict:** Do not use for new projects. Included here only for completeness.

---

### 2c. html2canvas / dom-to-image / html-to-image

Client-side JavaScript libraries that render DOM to canvas/SVG/PNG.

- **html2canvas** (~50KB): Most popular, reads DOM and re-renders to canvas. Does not use browser rendering -- re-implements CSS in JS, so output often differs from actual browser rendering.
- **dom-to-image** (~15KB): Converts DOM to SVG using foreignObject. More accurate but browser-dependent.
- **html-to-image**: Modern fork of dom-to-image with bug fixes.

**Verdict:** These are client-side browser libraries. They require a DOM environment and are not suitable for server-side generation. Not applicable for NanoClaw's use case.

---

## 3. Containerized / Cloud Approaches

### 3a. Browserless (Docker)

Browserless provides headless Chrome in Docker with REST APIs for screenshots, PDFs, and scraping.

**Screenshot API:**
```bash
curl -X POST https://chrome.browserless.io/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"html": "<h1>Hello</h1>", "options": {"type": "png", "fullPage": false}}'
```

**Deployment options:**
- **Cloud hosted:** Managed service, free tier (2 concurrent, 1k units/month)
- **Self-hosted Docker:** `docker run -p 3000:3000 browserless/chrome`
- **Enterprise:** Self-hosted with license key for production workloads

**Pricing:**
- Free: 2 concurrent browsers, 1k units/month
- Paid plans scale up from there
- Self-hosted is free for non-commercial use; commercial requires license

**Pros:**
- REST API -- language-agnostic, call from any backend
- Pre-configured Docker image with all dependencies
- Handles resource management, connection pooling
- Supports Puppeteer, Playwright, and Selenium connections

**Cons:**
- Commercial use requires paid license
- Additional service to manage
- Overkill for single-image generation

---

### 3b. Alpine Chrome Docker Image

`zenika/alpine-chrome` -- minimal headless Chrome on Alpine Linux.

**Size:** ~423 MB compressed

**Variants:**
- Base: Chrome only
- `with-puppeteer`: Chrome + Puppeteer pre-installed
- `with-playwright`: Chrome + Playwright pre-installed

**Usage:**
```bash
docker run --rm zenika/alpine-chrome --no-sandbox --screenshot --window-size=1200,800 file:///tmp/input.html
```

**Best for:** Dockerfile base image when you need Chrome in a container.

---

### 3c. Custom Dockerfile

Build your own minimal image with exactly what you need.

**Example (Puppeteer on Debian slim):**
```dockerfile
FROM node:20-slim

RUN apt-get update && apt-get install -y \
    chromium \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app
COPY package.json .
RUN npm install puppeteer
COPY render.js .

CMD ["node", "render.js"]
```

**Key notes:**
- Install `fonts-noto-cjk` and `fonts-noto-color-emoji` for CJK text and emoji support
- Use `--no-sandbox` in Chrome args (container provides isolation)
- Use `--disable-dev-shm-usage` to avoid shared memory issues (or mount tmpfs)
- Set `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD` to use system Chromium instead of Puppeteer's bundled version

---

## 4. Comparison Matrix

| Approach | Speed (single image) | Memory | Dependencies | CSS Support | Complexity | Production-Ready |
|----------|---------------------|--------|-------------|-------------|------------|-----------------|
| Chrome CLI | ~1.5-3s | ~200 MB | Chrome/Chromium | Full | Low | Yes |
| Puppeteer (warm) | ~200-800ms | ~100-300 MB | Node.js + Chromium | Full | Medium | Yes |
| Playwright (warm) | ~200-800ms | ~100-300 MB | Node.js + Chromium | Full | Medium | Yes |
| chrome-headless-shell | ~1-2s | ~150 MB | Binary only | Full | Low | Yes |
| Satori + resvg | ~10-50ms | ~20-50 MB | Node.js (no browser) | Partial | Medium | Yes |
| wkhtmltoimage | ~500ms-1s | ~50 MB | Binary (Qt) | 2015-era | Low | **No (deprecated)** |
| Browserless | ~500ms-1s | ~300 MB+ | Docker | Full | Low (API) | Yes (paid for commercial) |

---

## 5. Recommendation for NanoClaw

### Primary: Puppeteer with long-lived browser process

**Why:**
1. **Full CSS support** -- NanoClaw's HTML templates can use any modern CSS (gradients, Grid, custom properties, etc.) without worrying about rendering limitations
2. **Fast warm path** -- keep the browser process alive and create new pages per screenshot. 200-800ms per image is well within acceptable latency for a messaging bot
3. **Node.js native** -- if NanoClaw runs on Node.js, Puppeteer is a direct dependency with no subprocess overhead
4. **Battle-tested in production** -- massive community, well-documented failure modes, widely deployed
5. **Programmatic control** -- can wait for specific elements, set viewport precisely, screenshot specific elements, inject fonts/styles dynamically

**Implementation pattern:**
```javascript
// Launch once at startup
const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
});

// Per screenshot (fast path)
async function renderCard(html, width = 1200, height = 800) {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 2 });
  await page.setContent(html, { waitUntil: 'domcontentloaded' });
  const buffer = await page.screenshot({
    type: 'png',
    optimizeForSpeed: true
  });
  await page.close();
  return buffer;
}
```

### Fallback: Satori + resvg (if templates are simple enough)

If NanoClaw's status cards turn out to use only Flexbox layouts with inline styles and known fonts, Satori + resvg would be dramatically faster (~10-50ms vs ~200-800ms) and lighter weight. However, it requires:
- Templates written in JSX, not HTML
- All styles inline (no CSS classes or selectors)
- Manual font loading
- No CSS Grid, no z-index, no calc()

Worth evaluating once the template designs are finalized. If templates stay simple, Satori is the better choice for edge/serverless deployment.

### For Docker deployment:
- Use `node:20-slim` as base image
- Install system Chromium + fonts
- Set `PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true`
- Total image size: ~500-700 MB (acceptable for a service container)

---

## Sources

- [Puppeteer Screenshot Documentation](https://pptr.dev/guides/screenshots)
- [Puppeteer optimizeForSpeed](https://screenshotone.com/blog/optimize-for-speed-when-rendering-screenshots-in-puppeteer-and-chrome-devtools-protocol/)
- [Puppeteer vs Playwright Performance](https://www.skyvern.com/blog/puppeteer-vs-playwright-complete-performance-comparison-2025/)
- [Playwright vs Puppeteer Comparison](https://www.browserstack.com/guide/playwright-vs-puppeteer)
- [Chrome Headless Mode Documentation](https://developer.chrome.com/docs/chromium/headless)
- [chrome-headless-shell Announcement](https://developer.chrome.com/blog/chrome-headless-shell)
- [Removing --headless=old from Chrome](https://developer.chrome.com/blog/removing-headless-old-from-chrome)
- [Satori GitHub Repository](https://github.com/vercel/satori)
- [Satori + resvg Tutorial](https://anasrin.dev/blog/generate-image-from-html-using-satori-and-resvg/)
- [wkhtmltopdf Deprecation Status](https://wkhtmltopdf.org/status.html)
- [Alpine Chrome Docker Image](https://github.com/jlandure/alpine-chrome)
- [Browserless Documentation](https://docs.browserless.io/rest-apis/intro)
- [Docker Chrome Setup Guide](https://www.baeldung.com/ops/docker-google-chrome-headless)
- [Puppeteer Performance Tips](https://www.bannerbear.com/blog/ways-to-speed-up-puppeteer-screenshots/)
- [Docker Screenshot Automation](https://oneuptime.com/blog/post/2026-02-08-how-to-set-up-docker-for-automated-screenshot-generation/view)
