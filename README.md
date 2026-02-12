# Cascade

> Turn yearly ambitions into daily action.

A Claude-powered planning system that breaks down ambitious goals through cascading time horizons—from year to quarter to month to week to day to hour.

---

## What is Cascade?

Cascade is a **structured planning system** for ambitious engineers who want to achieve big goals. It uses Claude AI to help you:

- Break down overwhelming yearly goals into manageable daily tasks
- Maintain consistency through weekly planning and progress tracking
- Adapt your plan dynamically based on real progress
- Balance ambition with sustainability (Core vs Flex hours)
- Never lose sight of your end goal while staying grounded in daily action

**Think of it as:** Your personal planning coach that cascades "I want to land a job at Google by June" down to "Today I will solve 3 graph problems."

---

## Who is this for?

Anyone with **ambitious multi-month goals** who struggles with:

- Breaking big goals into actionable steps
- Staying consistent week-to-week
- Adjusting plans when life happens
- Balancing multiple goals without burnout
- Knowing if you're on track or falling behind

**Common use cases:**

- 🎯 **Job search:** Track applications, interviews, networking, skill development
- 📚 **Skill building:** LeetCode grind, course completion, certifications, portfolio projects
- 💪 **Fitness:** Weight loss, strength building, race training
- 🚀 **Side projects:** Launch a product, build an audience, hit revenue milestones
- 🎓 **Learning:** Master a new language, domain, or technology stack

---

## Why use this instead of a todo list?

**Traditional todo lists fail at:**
- Connecting daily tasks to long-term goals
- Adapting when you fall behind
- Balancing multiple priorities
- Preventing burnout

**Cascade succeeds by:**
- **Cascading time horizons:** Year → Quarter → Month → Week → Day → Hour (each level informs the next)
- **Human-in-the-loop checkpoints:** Claude presents a plan, you approve or adjust
- **Dynamic adaptation:** `next week` command auto-calculates remaining work and distributes it across weeks
- **Built-in sustainability:** Core vs Flex hours, mandatory rest day, weekly review ritual
- **Progress tracking:** `log` command parses your notes and updates tracker.csv
- **Calendar integration:** `calendar` command generates .ics files for seamless Google Calendar import

---

## Core Concepts

### Cascading Time Horizons

Break goals down through each level with approval at each step:

1. **Year** → Define success criteria (e.g., "Land FAANG job by June")
2. **Quarterly** → Major milestones (e.g., "Q1: Master DSA, Q2: System Design + Interviews")
3. **Monthly** → Concrete targets (e.g., "February: Complete all 114 Structy problems")
4. **Weekly** → Task breakdown (e.g., "Week of Feb 9-15: 18 DP problems, 1 mock interview")
5. **Daily** → Schedule integration (e.g., "Monday 5:30-7:30pm: 3 graph problems")
6. **Hourly** → Time-blocked templates (e.g., "Monday template: 2hr Core + 1hr Flex")

### Core vs Flex Hours

**Core hours:** Non-negotiable, committed work toward your goal (e.g., 10 hrs/week)

**Flex hours:** Bonus hours when energy is high (e.g., additional 5-10 hrs/week)

This distinction prevents burnout and gives you permission to scale back when life happens.

### Weekly Rhythm

- **Monday:** Weekly Kickoff (10 min) — Review targets, commit to #1 priority
- **Daily:** Work on goals, log progress in tracker.csv
- **Sunday:** Weekly Review (15-30 min) — Reflect, adjust, plan next week

### Human-in-the-Loop Approval

Claude presents plans at each level. You:
- ✅ Approve → Continue to next level
- ✏️ Give feedback → Claude incorporates and re-presents
- ❓ Ask questions → Claude answers and re-presents

This keeps you in control while letting Claude handle the detail work.

---

## Quick Start

### Prerequisites

- **Claude Code CLI** or **Claude API access** (requires Claude Pro or API credits)
- Basic familiarity with markdown files
- A yearly goal you're serious about achieving

### Installation

```bash
# Clone the repository
git clone https://github.com/thinklikeadesigner/cascade.git
cd cascade

# Copy templates to your data directory
cp templates/year-goals.md data/2026-goals.md
cp templates/tracker.csv data/tracker.csv

# Open in Claude Code
claude data/
```

See **[QUICKSTART.md](QUICKSTART.md)** for detailed setup instructions.

---

## Commands Reference

### Core Commands

#### `next week`
Generate next week's planning file based on current progress and monthly targets.

**What it does:**
1. Reads `data/tracker.csv` for latest progress
2. Reads current `data/week-*.md` for context
3. Reads monthly file for targets
4. Calculates remaining work and distributes across weeks
5. Generates `data/week-{dates}.md` with daily breakdown

**Example:**
```
> next week

Reading tracker.csv... Last entry: Feb 8, 28/114 problems
Reading feb-2026.md... Monthly target: 114 problems

Remaining: 86 problems, 3 weeks left
Weekly target: ~29 problems

[Presents week-feb-9-15.md for approval]
```

---

#### `log`
Parse your daily notes and update tracker.csv automatically.

**What it does:**
1. You paste freeform notes (e.g., from Telegram, Notes app, etc.)
2. Claude parses dates, metrics, activities
3. Shows you what it understood
4. Updates tracker.csv with new rows

**Example:**
```
> log

Feb 10 - finished 12 problems, gym
Feb 11 - 8 more problems, skipped run

---

Parsed:
- Feb 10: problems +12 (total: 40), activity: gym
- Feb 11: problems +8 (total: 48), activity: skipped run

Update tracker.csv? [y/n]
```

---

#### `calendar`
Generate .ics file for the current week's schedule to import into Google Calendar.

**What it does:**
1. Reads current `data/week-*.md` and day templates
2. Generates calendar events for:
   - Core and Flex work blocks
   - Recurring activities (exercise, meetings, etc.)
   - Weekly Kickoff (Monday)
   - Weekly Review (Sunday)
3. Saves to `calendar/week-{dates}.ics`

**Example:**
```
> calendar

Created calendar/week-feb-9-15.ics with 18 events
Import: Open file or drag into Google Calendar
```

---

## Customization

### Adapt to Your Goals

**The system is domain-agnostic.** Customize `data/tracker.csv` columns to match your goals:

**Job Search:**
```csv
date,applications,phone_screens,onsites,networking,notes
```

**Coding Practice:**
```csv
date,problems_done,problems_total,chapter,mocks_done,notes
```

**Fitness:**
```csv
date,weight,workout_type,duration_min,calories,notes
```

**Side Project:**
```csv
date,features_shipped,users,revenue,marketing_hours,notes
```

### Modify Daily Templates

Edit `templates/daily/*.md` to match your schedule:

- Morning person? Put Core hours at 6-8am
- Night owl? Put Core hours at 10pm-12am
- Commute patterns? Adjust for office vs WFH days
- Workout schedule? Block out gym time

The `calendar` command will read these templates and generate events accordingly.

---

## FAQ

### Do I need Claude Pro?

**Yes**, or API access with credits. The system relies on Claude's reasoning capabilities to:
- Parse your goals and break them down intelligently
- Calculate remaining work and redistribute across weeks
- Parse freeform log entries into structured data

### Can I use this for non-job-search goals?

**Absolutely.** The system is fully customizable. Just modify:
- `data/tracker.csv` columns for your metrics
- Template files for your goal type
- CLAUDE.md instructions if you want custom commands

### How do I protect my personal data?

**The `data/` directory is gitignored.** This means:
- Your personal goals, progress, and notes never get committed to git
- You can fork/clone the repo without exposing your data
- Keep your planning private while benefiting from the system

### Can I use this with ChatGPT or other LLMs?

The system is **optimized for Claude** (structured reasoning, long context, instruction following), but you could adapt the CLAUDE.md prompt for other models. Note that:
- Commands rely on Claude's tool use capabilities
- Parsing quality may vary with other models
- No guarantees for non-Claude LLMs

### What if I fall behind on my goals?

**This is where the system shines.** Use the `next week` command, and Claude will:
1. Calculate how far behind you are
2. Redistribute remaining work across remaining weeks
3. Flag if you're overcommitted
4. Suggest scaling back Flex hours or adjusting targets

You'll get an honest assessment and adaptive plan, not guilt.

### How much time does this system require?

**Setup:** 1-2 hours (customize templates, define yearly goals)

**Weekly:**
- Sunday review: 15-30 min
- Monday kickoff: 10 min
- Daily logging: 2-5 min
- `next week` command: 5-10 min

**Total overhead:** ~1 hour/week for planning and tracking

The ROI is **massive** if you're working toward a goal that matters.

---

## Examples in the Wild

Want to see how others are using Cascade?

- **Job search:** [Example link - coming soon]
- **LeetCode grind:** [Example link - coming soon]
- **Fitness journey:** [Example link - coming soon]
- **Side project launch:** [Example link - coming soon]

(Submit a PR to add your own!)

---

## Contributing

Contributions welcome! Areas of interest:

- **New templates:** Example personas for different goal types
- **Custom commands:** Domain-specific commands (e.g., `rehearse` for interview prep)
- **Integrations:** Export to Notion, Obsidian, etc.
- **Documentation:** Video walkthroughs, blog posts, tutorials

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built with [Claude AI](https://claude.ai) by Anthropic.

Inspired by:
- GTD (Getting Things Done) by David Allen
- Atomic Habits by James Clear
- Deep Work by Cal Newport
- The cascading goals framework from OKRs

---

## Support

- **Issues:** [GitHub Issues](https://github.com/thinklikeadesigner/cascade/issues)
- **Discussions:** [GitHub Discussions](https://github.com/thinklikeadesigner/cascade/discussions)
- **Twitter:** [@thinkLikeADev](https://twitter.com/thinkLikeADev)

---

**Ready to turn your yearly goals into daily action?**

👉 **[Get Started with the Quick Start Guide](QUICKSTART.md)**
