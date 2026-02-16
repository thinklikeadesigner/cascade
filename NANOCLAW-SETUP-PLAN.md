# NanoClaw Setup Plan for Cascade

## Overview
Install NanoClaw alongside Cascade to send WhatsApp reminders about goal progress, running in Apple Containers on macOS 26.

## Prerequisites
- [ ] macOS 26 (Tahoe) — updating OS now
- [ ] Node.js 20+
- [ ] Apple Container CLI ([download .pkg from GitHub releases](https://github.com/apple/container/releases))
- [ ] Claude Code CLI

## Tasks

### 1. Check Prerequisites
After OS update, verify:
```bash
sw_vers                  # macOS 26
node --version           # 20+
container --version      # Apple Container CLI
claude --version         # Claude Code
```

### 2. Clone NanoClaw
```bash
git clone https://github.com/gavrielc/nanoclaw.git /Users/k2/Desktop/moltathon/nanoclaw
```

### 3. Install Dependencies
```bash
cd /Users/k2/Desktop/moltathon/nanoclaw
npm install
```

### 4. Run NanoClaw Setup
```bash
cd /Users/k2/Desktop/moltathon/nanoclaw
claude
```
Then inside Claude Code, run `/setup`. This handles:
- Apple Container configuration
- WhatsApp authentication (QR code scan required — have your phone ready)
- Agent container build (`./container/build.sh`)
- launchd service install (`~/Library/LaunchAgents/com.nanoclaw.plist`)

### 5. Integrate Cascade Goals
- Mount `cascade/data/` into the NanoClaw agent container
- Create a group `CLAUDE.md` with Cascade context so the agent understands your goals
- Set up scheduled WhatsApp tasks:
  - **Daily morning**: Summary of today's tasks from weekly plan
  - **Daily evening**: Reminder to log progress
  - **Weekly Sunday**: Weekly review reminder with progress stats
  - **Weekly Monday**: New week kickoff with targets

## Architecture
```
Cascade (markdown/CSV)
    ↓ (mounted into container)
NanoClaw (Node.js)
    ↓
WhatsApp (baileys) → SQLite → Polling loop → Apple Container (Claude Agent SDK) → Response
```

## Key References
- NanoClaw repo: https://github.com/qwibitai/nanoclaw
- Apple Container: https://github.com/apple/container
- Claude Agent SDK: https://github.com/anthropics/claude-agent-sdk-typescript

## Resume
After OS update, open a new Claude Code session in the cascade directory and say "resume NanoClaw setup".
