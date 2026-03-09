# Cascade Memory Infrastructure

> A portable, permission-gated personal memory system that ingests scattered digital history, links it semantically across sources, and lets users control who sees what — demonstrated through multi-persona Telegram bots.

## What It Does

Cascade Memory takes the data a person could export today — emails, calendar events, bank transactions, AI conversations, social posts, lifelogs, file metadata — and turns it into a unified, queryable knowledge graph they actually own. Each memory is classified by sensitivity, embedded for semantic search, and linked to related memories across sources. A permission layer controls access: your therapist notes never leak into group chat answers.

The demo runs 4 Telegram bots, each representing a different person's memory. Ask Jordan about his calendar and the bot searches his memory, filters by permission context, and synthesizes an answer. Tell the "You" bot something new and it extracts facts, embeds them, auto-links them to related memories, and persists everything — building a living knowledge graph from conversation.

---

## Quick Start

```bash
# Clone
git clone git@github.com:thinklikeadesigner/hackathon-demo.git
cd hackathon-demo/cascade-api

# Install dependencies
pip install uv
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Install Ollama models (local inference — no API keys needed for core demo)
ollama pull qwen3:8b
ollama pull nomic-embed-text

# Configure environment
cp .env.example .env
# Edit .env with your Telegram bot tokens (see below)

# Download persona datasets into data/personadata/personas/
# From: https://drive.google.com/drive/folders/1TEWhdzff-FgkDNY-53IDXIWaPZQ7_5F3

# Run
python main.py
```

### Required Environment Variables

```bash
# Telegram bots (create via @BotFather)
TELEGRAM_BOT_TOKEN_JORDAN=...   # Persona p01
TELEGRAM_BOT_TOKEN_MAYA=...     # Persona p02
TELEGRAM_BOT_TOKEN_THEO=...     # Persona p05
TELEGRAM_BOT_TOKEN_YOU=...      # Your personal bot
TELEGRAM_OWNER_CHAT_ID=...      # Your Telegram user ID

# Optional: Supabase (for enriched export with goals/tasks)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Reproducing the Demo

1. Create 4 Telegram bots via [@BotFather](https://t.me/BotFather) and add tokens to `.env`
2. Get your Telegram chat ID (message [@userinfobot](https://t.me/userinfobot))
3. Place persona data in `../data/personadata/personas/persona_p01/`, etc.
4. Run `python main.py` — first run takes ~60s to ingest and embed all records
5. Message any bot in Telegram. Try:
   - Ask Jordan: *"What meetings do I have this week?"*
   - Ask Maya: *"How am I feeling about residency?"*
   - Tell You bot: *"I just signed a new client today"*
   - Run `/export` in DM with any bot to get the full memory JSON
6. Open `static/graph.html` in a browser and load the exported JSON to visualize the memory graph

---

## Tech Stack & Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    TELEGRAM BOTS                         │
│  Jordan (p01) │ Maya (p02) │ Theo (p05) │ You (k2)      │
└───────┬──────────────┬──────────────┬──────────────┬─────┘
        │              │              │              │
        └──────────────┴──────┬───────┴──────────────┘
                              │
                 ┌────────────▼────────────┐
                 │     MESSAGE HANDLER     │
                 │  context → recall →     │
                 │  permission filter →    │
                 │  synthesize → extract   │
                 └────────────┬────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
  ┌───────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐
  │  PERMISSION   │  │ MEMORY CLIENT │  │   SYNTHESIS   │
  │    LAYER      │  │  save/recall/ │  │   (Ollama)    │
  │ public/private│  │  extract/link │  │   qwen3:8b    │
  │ dm/group gate │  │  decay scores │  │               │
  └───────────────┘  └───────┬───────┘  └───────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
      ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
      │  EMBEDDER    │ │ STORE    │ │ EXTRACTOR   │
      │ nomic-embed  │ │ InMemory │ │ Ollama LLM  │
      │ (Ollama)     │ │ +pickle  │ │ fact/pattern │
      │ 768 dims     │ │ cache    │ │ extraction  │
      └──────────────┘ └──────────┘ └─────────────┘
                             │
                    ┌────────▼────────┐
                    │  GRAPH VISUAL   │
                    │  D3.js force    │
                    │  graph.html     │
                    └─────────────────┘
```

**Runtime:** Python 3.12, fully local (Ollama) — no cloud API keys required for core demo

| Component | Technology |
|-----------|-----------|
| LLM (synthesis + extraction) | Ollama / qwen3:8b (local) |
| Embeddings | Ollama / nomic-embed-text (768 dims, local) |
| Vector store | InMemoryStore with cosine similarity + pickle cache |
| Bot framework | python-telegram-bot 21+ |
| Graph visualization | D3.js force-directed graph |
| Data format | JSONL (hackathon dataset) + Portable Memory Format JSON |
| Optional cloud store | Supabase + pgvector (production path) |

---

## Datasets

**Primary:** Hackathon-provided synthetic persona datasets (5 personas, 8 sources each)
- Source: [Google Drive — Data Portability Hackathon 2026](https://drive.google.com/drive/folders/1TEWhdzff-FgkDNY-53IDXIWaPZQ7_5F3)
- Personas used: **p01 (Jordan Lee)**, **p02 (Maya Patel)**, **p05 (Theo Nakamura)**
- ~530 records per persona across: lifelog, email, calendar, social posts, transactions, AI conversations, file metadata
- Each record includes `refs` for cross-source linking

**Secondary:** Live Cascade user data from Supabase (goals, tasks, tracker entries, adaptations) ingested into the "You" bot's memory.

---

## How It Works

### 1. Ingestion Pipeline
Each persona's JSONL files are loaded, classified by sensitivity (`public_email`, `private_finance`, etc.), embedded via nomic-embed-text, and saved to the memory store. Cross-references from the `refs` field create explicit `cross_reference` links. A second pass samples memories and creates semantic `related` links across different source types (e.g., a calendar meeting linked to the email that scheduled it).

### 2. Permission Layer
Every memory gets a type like `private_ai_chat` or `public_social`. When a query comes in, the system checks context:
- **Owner DM**: Full access to all memories
- **Group chat**: Only `public_*` memories returned
- **Stranger DM**: Blocked entirely

This means Jordan's therapy notes and bank statements never surface in group conversations — only his public calendar events and social posts.

### 3. Recall + Synthesis
Questions are embedded and matched against the memory store using cosine similarity, weighted by decay score and confidence. The top results are passed to a local LLM (qwen3:8b) along with the persona's core memory profile to synthesize a natural answer. Source attribution is included (calendar, email, lifelog, etc.).

### 4. Memory Extraction + Auto-Linking
When the owner tells the bot something new, the conversation is sent to an extractor that pulls out facts, preferences, patterns, and goals. Each extracted memory is embedded, saved, and automatically linked to similar existing memories (threshold 0.4). The graph grows with every conversation.

### 5. Portable Export
`/export` dumps the full memory graph as JSON: core memory, all archival memories with metadata, and all links. This is the **Portable Memory Format** — a self-contained file that can be loaded into the graph visualizer or imported into another system.

---

## Portable Memory Format (v0.1)

```json
{
  "tenant_id": "p01",
  "persona_name": "Jordan",
  "core_memory": { "content": "## Profile\n- Name: Jordan Lee\n...", "version": 7 },
  "memories": [
    {
      "id": "uuid",
      "content": "Meeting with design team to review Q2 roadmap",
      "memory_type": "public_calendar",
      "tags": ["work", "meetings"],
      "confidence": 1.0,
      "decay_score": 0.95,
      "source_id": "cal_0042",
      "created_at": "2024-01-08T01:40:00-05:00"
    }
  ],
  "links": [
    { "source_id": "uuid1", "target_id": "uuid2", "link_type": "related" }
  ]
}
```

Link types: `cross_reference`, `related`, `part_of`, `supports`, `contradicts`, `supersedes`

---

## Known Limitations & Next Steps

### Limitations
- **In-memory store**: Demo uses pickle-cached InMemoryStore. Not suitable for production at scale (Supabase + pgvector store exists but wasn't used for the demo to keep it fully local).
- **Embedding quality**: nomic-embed-text is good but not state-of-the-art. Cross-source linking depends heavily on embedding quality.
- **No contradiction detection**: The extractor protocol supports `check_contradictions()` but it's not wired into the local Ollama pipeline yet.
- **Single-machine**: All 4 bots run in one process. Production would need separate workers.

### Next Steps
- Add contradiction detection during extraction (flag conflicting memories)
- Implement memory decay cron job (exponential decay formula exists, just needs scheduling)
- Add Google Takeout importer for real personal data (ChatGPT importer already working)
- Production deployment with Supabase store + pgvector HNSW index
- Portable Memory Format spec formalization for cross-system interoperability

---

## Project Structure

```
cascade-api/
├── main.py                          # Entry point: ingest, cache, run bots
├── cascade_api/
│   ├── config.py                    # Bot configs (name, tenant, token)
│   ├── handlers.py                  # Message handler (recall → filter → synthesize → extract)
│   ├── synthesize.py                # LLM answer synthesis (Ollama)
│   ├── permissions.py               # Sensitivity classification + access control
│   ├── ingest.py                    # JSONL persona ingestion + cross-source linking
│   ├── ingest_supabase.py           # Supabase data ingestion (goals, tasks, tracker)
│   ├── multi_bot.py                 # Multi-persona Telegram bot coordinator
│   ├── ollama_embedder.py           # Local embedding via Ollama/nomic-embed-text
│   ├── ollama_extractor.py          # Local memory extraction via Ollama/qwen3:8b
│   └── memory/
│       ├── client.py                # MemoryClient — save, recall, extract, link, decay
│       ├── core.py                  # CoreMemory — always-in-context markdown doc
│       ├── models.py                # MemoryRecord, MemoryLink, SearchResult, ExtractedMemory
│       ├── decay.py                 # Exponential decay scoring
│       ├── protocols/               # Pluggable interfaces (Embedder, Store, Extractor)
│       ├── stores/memory.py         # InMemoryStore (cosine similarity search)
│       ├── stores/supabase.py       # SupabaseStore (pgvector, production)
│       ├── embedders/               # Gemini, Fake embedder implementations
│       └── extractors/anthropic.py  # Claude-based extraction (production)
├── static/
│   └── graph.html                   # D3.js Obsidian-style memory graph visualizer
└── data/personadata/personas/       # Hackathon synthetic persona datasets
```

---

## Team

| Name | Role | Contact |
|------|------|---------|
| Rebecca Burch | Solo Engineer | [LinkedIn](https://www.linkedin.com/in/rebecca-burch/) |

---

## License

MIT
