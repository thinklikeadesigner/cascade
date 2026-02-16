# Cascade

> Plans are cheap. Everyone has one on January 1st. Cascade is the system that makes them survive February.

---

## What is Cascade?

Cascade is a goal-execution methodology that uses Claude AI to break yearly goals into daily structure — and then **adapts based on what actually happens**.

Most planning tools assume you'll execute perfectly. Cascade assumes you won't. It tracks your real velocity, learns your patterns, and adjusts your plan to match reality instead of pretending reality will match your plan.

### Three principles:

**Gravity** — Plans cascade down (year → week → day). Reality flows up. Last week's actuals reshape next week's targets. The original plan is a starting point, not a contract.

**Core/Flex** — Your plan must succeed on Core hours alone. Flex hours are bonus when energy allows. If you need Flex to hit targets, the targets are wrong.

**Checkpoints** — Human approval at every level. Not because AI might be wrong — because approving makes the plan yours.

---

## Why not just use ChatGPT?

ChatGPT can make you a plan. So can a notebook. The plan isn't the hard part.

| | ChatGPT | Cascade |
|---|---------|---------|
| **Memory** | Forgets everything between sessions | Tracks your velocity, patterns, and rest debt across weeks |
| **Opinions** | "Sure, I can plan 4 goals in 10 hrs/week!" | "Your data says 8 hrs. I believe your data." |
| **Adaptation** | Generates plans in a vacuum | Plans from your actual completion rate, not your intentions |
| **Patterns** | Can't observe behavior over time | "You skip Fridays. I moved those tasks to Saturday." |
| **Honesty** | "Great job!" for 40% completion | "40% this week. Bad week or scope too high?" |

---

## Who is this for?

Builders with ambitious multi-month goals who need structure, not motivation. You already know what you want — you need a system that keeps you honest about whether you're actually getting there.

**Common use cases:**
- **Side projects:** Ship features, acquire users, hit revenue milestones
- **Job search:** Applications, interviews, networking, skill building
- **Fitness:** Weight, strength, nutrition, consistency
- **Learning:** Courses, certifications, practice hours
- **Business:** Outreach, deals, revenue targets

---

## Quick Start

```bash
git clone https://github.com/thinklikeadesigner/cascade.git
cd cascade
claude .
```

Then run `cascade` in the Claude Code conversation. It will:
1. Help you define a specific, measurable goal
2. Break it down through each time horizon (year → quarter → month → week) with your approval at each level
3. Set your Core and Flex hours based on your actual available time
4. Generate all planning files and a custom tracker for your goal type

Setup takes about 30 minutes of focused conversation.

---

## Commands

| Command | What it does |
|---------|-------------|
| `cascade` | Initial setup — define your goal, generate all files |
| `plan` | Generate next week's plan based on actual progress |
| `status` | Quick pulse — velocity, forecast, rest debt, honest assessment |
| `review` | Weekly reflection — planned vs actual, pattern detection |
| `adapt` | Surface what Cascade has learned about you over time |
| `log` | Parse your progress notes into tracker.csv |
| `sync` | Generate .ics calendar file for the week |

### The adaptive loop

This is what makes Cascade a system, not a prompt:

```
cascade (setup) → log (track daily) → review (weekly reflection)
    ↓                                        ↓
  plan (next week) ← ← ← ← ← ← adapt (learn patterns)
```

Each week, Cascade has more data. Your plans get more realistic. The system learns that you don't work Fridays, that your real velocity is 8 hours not 12, that you need a rest day every 6 days. It stops planning for who you wish you were and starts planning for who you actually are.

---

## Core Concepts

### Core vs Flex Hours

**Core** is the plan. If you complete only Core tasks, you're on track. Core is not the minimum — it's the sustainable output that keeps you moving every week.

**Flex** is acceleration. Reach for it when energy is high. But if your monthly targets depend on Flex hours, Cascade will tell you: the targets are too high.

This gives you explicit permission to have bad weeks without derailing the system. "Core only this week" is always a valid plan.

### Gravity

Most planning tools set targets once and judge you against them forever. Cascade doesn't. If you planned 15 hours but completed 8, next week's plan starts from 8. The system adjusts to reality — your job is to show up, not to be perfect.

### Adaptations

After a few weeks, Cascade starts noticing patterns. These get stored in `data/adaptations.md` and automatically shape future plans:

- "You skip Fridays → moved Friday tasks to Saturday"
- "Average velocity is 8 hrs, not 12 → adjusted Core to 8"
- "Low energy Wednesdays → lighter Wednesday schedules"
- "Completion rate improved after scope reduction → keeping reduced scope"

Run `adapt` anytime to see what Cascade has learned about you.

---

## File Structure

```
cascade/
├── CLAUDE.md              # The methodology (this is the product)
├── README.md
├── templates/             # Scaffolding for generated files
│   ├── week.md
│   ├── month.md
│   ├── quarter.md
│   ├── year-goals.md
│   ├── adaptations.md
│   ├── tracker.csv
│   └── daily/             # Day-specific schedule templates
├── data/                  # Your data (gitignored, private)
│   ├── 2026-goals.md
│   ├── q1-jan-feb-mar.md
│   ├── feb-2026.md
│   ├── week-feb14-20.md
│   ├── tracker.csv
│   └── adaptations.md
└── calendar/              # Generated .ics files (gitignored)
```

The `data/` directory is **gitignored** — your goals, progress, and notes are never committed. You can fork this repo without exposing personal data.

---

## FAQ

**Do I need Claude Pro?**
Yes, or API credits. Cascade runs inside Claude Code and uses Claude's reasoning and tool capabilities.

**Can I use this for any goal?**
Yes. The tracker columns, weekly structure, and coaching focus are all shaped by your goals during `cascade` setup. The system is domain-agnostic.

**What if I fall behind?**
That's where Cascade is different. Run `status` for an honest assessment. Run `plan` and Cascade will redistribute remaining work based on your actual velocity — not the original plan. You'll get realistic targets, not guilt.

**How much time overhead?**
Setup: ~30 minutes. Weekly: ~45 minutes (15-min review + 10-min plan + daily logging). The system saves you time by eliminating the "what should I work on today?" question.

---

## Contributing

Contributions welcome:
- New templates for different goal domains
- Custom commands for specific use cases
- Integrations (Notion, Obsidian, etc.)
- Documentation and walkthroughs

---

## License

MIT — see [LICENSE](LICENSE).

Built with [Claude AI](https://claude.ai) by Anthropic.

---

**Ready?**

```bash
git clone https://github.com/thinklikeadesigner/cascade.git && cd cascade && claude .
```

Then type `cascade` and be honest about your goal.
