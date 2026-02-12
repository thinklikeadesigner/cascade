# Quick Start Guide

Get up and running with Cascade in **under 10 minutes**.

---

## Prerequisites

Before you begin, make sure you have:

- ✅ **Claude Code CLI** installed ([Installation guide](https://docs.anthropic.com/claude/docs/claude-code))
  - OR **Claude API access** with credits
  - OR **Claude Pro subscription** for web interface
- ✅ **Git** installed (to clone the repo)
- ✅ **A text editor** (VS Code, Sublime, etc.) or use Claude Code's built-in editor
- ✅ **A yearly goal** you're committed to achieving

---

## Step 1: Clone the Repository

```bash
# Clone the repo to your local machine
git clone https://github.com/yourusername/cascade.git

# Navigate into the directory
cd cascade

# Verify structure
ls
# You should see: CLAUDE.md, README.md, templates/, data/, LICENSE
```

---

## Step 2: Set Up Your Data Directory

The `data/` directory is where **your personal planning files** will live. It's gitignored to protect your privacy.

```bash
# Copy year goals template
cp templates/year-goals.md data/2026-goals.md

# Copy tracker template
cp templates/tracker.csv data/tracker.csv

# Verify
ls data/
# You should see: .gitkeep, 2026-goals.md, tracker.csv
```

---

## Step 3: Open in Claude Code

```bash
# Launch Claude Code in the project directory
claude .

# OR open just the data directory for a cleaner workspace
claude data/
```

Claude Code will:
- Load the `CLAUDE.md` system prompt automatically
- Give Claude access to read/write files in the directory
- Enable commands like `next week`, `log`, `calendar`

---

## Step 4: Define Your Yearly Goals

Now comes the fun part. Talk to Claude and let it guide you through the planning process.

### Example conversation:

**You:**
```
I want to land a software engineering job at a top tech company by June 2026.
I'm currently employed, working 9-5, and can dedicate 10-15 hours/week to prep.
```

**Claude will ask:**
- What's your current skill level? (DSA, system design, behavioral prep)
- What companies are you targeting?
- What's your timeline? (phases, milestones)
- What are your constraints? (work schedule, commute, family, etc.)

**Claude will then:**
1. Present a **yearly goal breakdown** with success criteria
2. Wait for your approval
3. Generate a **quarterly breakdown** with major milestones
4. Wait for your approval
5. Generate a **monthly breakdown** for the current month
6. Wait for your approval
7. Generate a **weekly breakdown** for the current week
8. Wait for your approval

**At each step, you can:**
- ✅ Approve → Claude moves to next level
- ✏️ Give feedback → Claude adjusts and re-presents
- ❓ Ask questions → Claude clarifies and re-presents

---

## Step 5: Customize Your Tracker

Edit `data/tracker.csv` to match your specific metrics.

**Default (generic):**
```csv
date,notes
```

**Example for job search:**
```csv
date,problems_done,problems_total,mocks_done,networking,applications,notes
```

**Example for fitness:**
```csv
date,weight,workout_type,duration_min,calories,notes
```

**Example for side project:**
```csv
date,features_shipped,users,revenue,hours_worked,notes
```

**Tip:** Add only the columns you'll actually track. Start minimal, add more later if needed.

---

## Step 6: Set Up Daily Templates (Optional)

If you want time-blocked schedules and calendar integration, customize daily templates.

```bash
# Copy a day template to customize
cp templates/daily/monday.md templates/daily/my-monday.md

# Edit in your preferred editor
code templates/daily/my-monday.md
```

**Customize:**
- Wake/sleep times
- Work hours
- Core vs Flex study blocks
- Exercise times
- Meal times

**Repeat for each day type** (you may have different schedules for office days vs WFH days).

---

## Step 7: Start Your First Week

Once Claude has generated your first `week-*.md` file, you're ready to go!

### Monday Morning: Weekly Kickoff (10 min)

1. Read your `data/week-feb-9-15.md` file
2. Review the weekly targets
3. Identify the #1 priority for the week
4. Mentally commit: "This week I will _______________"

### Daily: Do the work

Work on your goals according to the weekly plan.

### Daily: Log your progress (2-5 min)

Keep notes throughout the day (in Telegram, Notes app, journal, etc.):

```
Feb 9 - 5 problems done, gym session
Feb 10 - 8 problems, started chapter 3
Feb 11 - skipped gym, sick
```

At the end of the day (or week), paste into Claude:

```
> log

[Paste your notes here]
```

Claude will:
1. Parse your entries
2. Show what it understood
3. Ask for confirmation
4. Update `tracker.csv`

### Sunday: Weekly Review (15-30 min)

1. Open `templates/daily/sunday.md` for the review template
2. Reflect on what worked and what didn't
3. Check your energy levels
4. Update `tracker.csv` with final entries
5. Run `next week` command:

```
> next week
```

Claude will:
1. Read your tracker for latest progress
2. Calculate remaining work for the month
3. Generate next week's plan
4. Present for your approval

6. (Optional) Generate calendar events:

```
> calendar
```

7. Import the generated `calendar/week-*.ics` file into Google Calendar

---

## Daily Workflow (Once Set Up)

### Morning (5 min)
- Open today's section in `data/week-*.md`
- Review daily checklist
- Mentally commit to Core hours

### During the day
- Work on your goals
- Take notes on progress

### Evening (2-5 min)
- Check off completed tasks in `data/week-*.md`
- Jot down notes for logging later

### Sunday (15-30 min)
- Weekly review ritual
- Log all progress: `> log`
- Generate next week: `> next week`
- Generate calendar: `> calendar`
- Import to Google Calendar

---

## Tips for Success

### 1. Start with Core hours only

Don't overcommit. Start with **Core hours only** (e.g., 10 hrs/week). Add Flex hours later if you have energy.

### 2. Protect your rest day

**Sunday is sacred.** No guilt, no grind. Weekly review is allowed, but keep it light.

### 3. Use the `log` command liberally

The more you log, the better Claude can adapt your weekly plans. Aim to log at least 3-4 times/week.

### 4. Trust the `next week` command

When you fall behind, don't panic. Run `next week` and let Claude redistribute the work. It'll give you an honest assessment.

### 5. Iterate on your templates

Your first week won't be perfect. After Week 1, adjust:
- Core vs Flex hours
- Daily schedule times
- Tracker columns
- Weekly targets

The system is designed to adapt to you, not the other way around.

### 6. Don't skip the human-in-the-loop approval

**Never let Claude generate plans without your approval.** Review every weekly plan before committing to it. You're in control.

---

## Common Issues

### "Claude isn't reading my CLAUDE.md file"

**Solution:** Make sure you're running `claude .` from the **root directory** of the repo, not from `data/`. The CLAUDE.md file should be in the current working directory or a parent directory.

### "The `next week` command isn't working"

**Solution:** Ensure you have:
1. `data/tracker.csv` with at least one entry
2. A current `data/week-*.md` file
3. A `data/{month}-{year}.md` file with monthly targets

Claude needs these files to calculate remaining work.

### "My tracker.csv isn't updating"

**Solution:** After running `> log`, make sure you:
1. Review the parsed output
2. Type `y` to confirm the update
3. Check `data/tracker.csv` to verify rows were added

### "I'm feeling overwhelmed"

**Solution:** This is a sign to:
1. Reduce Flex hours to 0 (Core only)
2. Extend your timeline (push monthly targets back)
3. Take a true rest day (no planning, no guilt)
4. Talk to Claude: "I'm overwhelmed. Can you help me scale back?"

Claude will help you adjust your plan to be sustainable.

---

## Next Steps

Once you're comfortable with the basic workflow:

1. **Explore customization:** Add custom commands, modify templates, create your own rituals
2. **Share your setup:** Submit a PR with your example persona (with personal data removed)
3. **Join the community:** [GitHub Discussions](https://github.com/yourusername/goal-planning-engine/discussions)

---

**You're all set! 🎉**

Start your first planning session with Claude and let the cascading breakdown begin.

**Questions?** Check the [FAQ in README.md](README.md#faq) or open an issue on [GitHub](https://github.com/yourusername/cascade/issues).

---

**Pro tip:** Print out your weekly plan and put it somewhere visible (desk, fridge, bathroom mirror). Physical reminders work.
