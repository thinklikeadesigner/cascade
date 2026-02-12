# Tracker Customization Guide

## Overview

The `tracker.csv` file is your progress tracking database. Customize the columns to match your specific goals.

## Basic Structure

- **First column:** Always `date` (required for `next week` command)
- **Last column:** Always `notes` (catch-all for context)
- **Middle columns:** Your domain-specific metrics

## Example Column Sets

### Job Search
```csv
date,applications,phone_screens,onsites,offers,networking_touchpoints,linkedin_posts,behavioral_rehearsed,mocks_done,notes
```

### Coding Practice
```csv
date,problems_done,problems_total,chapter,mock_interviews,system_design_problems,notes
```

### Fitness
```csv
date,weight,workout_type,duration_min,calories,steps,notes
```

### Side Project
```csv
date,features_shipped,users_acquired,revenue,marketing_hours,coding_hours,notes
```

### Learning
```csv
date,course_progress,book_chapter,practice_hours,projects_completed,certifications,notes
```

### Multiple Goals (Combined)
```csv
date,goal1_metric,goal2_metric,goal3_metric,energy_level,notes
```

## How to Customize

1. Open `templates/tracker.csv`
2. Replace the header row with your column names (see examples above)
3. Copy to `data/tracker.csv`
4. Add your first entry manually or use the `log` command

## Tips

- **Numeric columns:** Use for things you want to track progress on (problems solved, weight, revenue)
- **Text columns:** Use for activities ("ran", "lifted", "rest day")
- **Notes column:** Always include - Claude reads this for context when planning
- **Start minimal:** Add only columns you'll actually track. You can always add more later.

## Using the `log` Command

Once your tracker is set up, paste your daily notes and Claude will parse them:

```
> log

Feb 5 - finished 10 problems
Feb 6 - 12 more problems, started chapter 3
Feb 7 - skipped workout, sick

---

Parsed:
- Feb 5: problems_done: 10
- Feb 6: problems_done: 12, chapter: 3
- Feb 7: workout: skipped (note: sick)

Update tracker.csv? [y/n]
```

Claude will intelligently map your natural language entries to the appropriate columns.
