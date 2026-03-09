"""Cross-source insight engine.

Loads raw JSONL from a persona directory, groups records by ISO week,
computes weekly stats, and detects cross-source correlations.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:8b"

STRESS_TAGS = {"anxiety", "mental_health", "therapy", "deadline", "overwork"}

RECURRING_KEYWORDS = {"rent", "housing", "utilities", "insurance", "subscription"}

NEGATIVE_KEYWORDS = [
    "not sustainable", "burned out", "exhausted", "stressed", "anxious",
    "frustrated", "distance", "overwhelmed", "tired",
]

POSITIVE_KEYWORDS = [
    "great", "energized", "proud", "excited", "happy",
    "peaceful", "accomplished", "breakthrough",
]


def load_records(persona_dir: Path) -> list[dict]:
    """Load all .jsonl files from a persona directory."""
    records = []
    for fp in sorted(persona_dir.glob("*.jsonl")):
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def parse_ts(record: dict) -> datetime | None:
    """Parse ISO timestamp from a record."""
    ts = record.get("ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def week_key(dt: datetime) -> str:
    """Return 'YYYY-WNN' ISO week key."""
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def group_by_week(records: list[dict]) -> dict[str, list[dict]]:
    """Group records by ISO week."""
    weeks: dict[str, list[dict]] = {}
    for r in records:
        dt = parse_ts(r)
        if dt is None:
            continue
        wk = week_key(dt)
        weeks.setdefault(wk, []).append(r)
    return weeks


def parse_amount(text: str) -> float | None:
    """Extract dollar amount from text like '$85.00 - Easy Tiger'."""
    m = re.search(r"\$([0-9,]+(?:\.\d{2})?)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def compute_weekly_stats(weeks: dict[str, list[dict]]) -> list[dict]:
    """Compute per-week stats across all sources."""
    stats = []
    for wk in sorted(weeks.keys()):
        records = weeks[wk]
        cal_count = 0
        stress_events = 0
        total_spend = 0.0
        discretionary_spend = 0.0
        negative_mood = 0
        positive_mood = 0
        social_posts = 0

        for r in records:
            source = r.get("source", "")
            text = r.get("text", "").lower()
            tags = set(r.get("tags", []))

            if source == "calendar":
                cal_count += 1
                if tags & STRESS_TAGS:
                    stress_events += 1

            elif source == "bank":
                amt = parse_amount(r.get("text", ""))
                if amt is not None:
                    total_spend += amt
                    # Check if recurring
                    is_recurring = any(kw in text for kw in RECURRING_KEYWORDS)
                    if not is_recurring:
                        discretionary_spend += amt

            elif source == "lifelog":
                if any(kw in text for kw in NEGATIVE_KEYWORDS):
                    negative_mood += 1
                if any(kw in text for kw in POSITIVE_KEYWORDS):
                    positive_mood += 1

            elif source == "social":
                social_posts += 1

        stats.append({
            "week": wk,
            "cal_events": cal_count,
            "stress_events": stress_events,
            "total_spend": round(total_spend, 2),
            "discretionary_spend": round(discretionary_spend, 2),
            "negative_mood": negative_mood,
            "positive_mood": positive_mood,
            "social_posts": social_posts,
        })

    return stats


def detect_patterns(stats: list[dict]) -> list[dict]:
    """Find cross-source correlations from weekly stats."""
    if not stats:
        return []

    patterns = []

    avg_disc = sum(s["discretionary_spend"] for s in stats) / len(stats) if stats else 0
    avg_events = sum(s["cal_events"] for s in stats) / len(stats) if stats else 0
    avg_neg = sum(s["negative_mood"] for s in stats) / len(stats) if stats else 0

    # stress_spending: discretionary spending >1.3x avg in week after 2+ stress events
    for i in range(len(stats) - 1):
        if stats[i]["stress_events"] >= 2:
            next_disc = stats[i + 1]["discretionary_spend"]
            if avg_disc > 0 and next_disc > avg_disc * 1.3:
                patterns.append({
                    "type": "stress_spending",
                    "week": stats[i + 1]["week"],
                    "detail": (
                        f"Discretionary spending ${next_disc:.0f} "
                        f"(avg ${avg_disc:.0f}) following {stats[i]['stress_events']} "
                        f"stress events in {stats[i]['week']}"
                    ),
                })

    # social_withdrawal: 0 social posts during weeks with >1.3x avg events
    for s in stats:
        if avg_events > 0 and s["cal_events"] > avg_events * 1.3 and s["social_posts"] == 0:
            patterns.append({
                "type": "social_withdrawal",
                "week": s["week"],
                "detail": (
                    f"No social posts during {s['week']} "
                    f"with {s['cal_events']} events (avg {avg_events:.1f})"
                ),
            })

    # overload_mood: 2+ negative lifelog entries in weeks with >1.2x avg events
    for s in stats:
        if avg_events > 0 and s["cal_events"] > avg_events * 1.2 and s["negative_mood"] >= 2:
            patterns.append({
                "type": "overload_mood",
                "week": s["week"],
                "detail": (
                    f"{s['negative_mood']} negative entries during {s['week']} "
                    f"with {s['cal_events']} events (avg {avg_events:.1f})"
                ),
            })

    # stress_spending_trend: avg spending in high-stress vs calm weeks
    high_stress_weeks = [s for s in stats if s["stress_events"] >= 2]
    calm_weeks = [s for s in stats if s["stress_events"] == 0]
    if high_stress_weeks and calm_weeks:
        high_avg = sum(s["discretionary_spend"] for s in high_stress_weeks) / len(high_stress_weeks)
        calm_avg = sum(s["discretionary_spend"] for s in calm_weeks) / len(calm_weeks)
        if calm_avg > 0:
            patterns.append({
                "type": "stress_spending_trend",
                "week": "overall",
                "detail": (
                    f"Avg discretionary spend during high-stress weeks: ${high_avg:.0f} "
                    f"vs calm weeks: ${calm_avg:.0f} "
                    f"({high_avg / calm_avg:.1f}x)"
                ),
            })

    # mood_decline / improvement: first half vs second half negative mood rates
    if len(stats) >= 4:
        mid = len(stats) // 2
        first_half = stats[:mid]
        second_half = stats[mid:]
        first_neg_rate = sum(s["negative_mood"] for s in first_half) / len(first_half)
        second_neg_rate = sum(s["negative_mood"] for s in second_half) / len(second_half)
        if first_neg_rate > 0 and second_neg_rate > first_neg_rate * 1.2:
            patterns.append({
                "type": "mood_decline",
                "week": "trend",
                "detail": (
                    f"Negative mood increased: {first_neg_rate:.1f}/week (first half) "
                    f"to {second_neg_rate:.1f}/week (second half)"
                ),
            })
        elif second_neg_rate > 0 and first_neg_rate > second_neg_rate * 1.2:
            patterns.append({
                "type": "mood_improvement",
                "week": "trend",
                "detail": (
                    f"Negative mood decreased: {first_neg_rate:.1f}/week (first half) "
                    f"to {second_neg_rate:.1f}/week (second half)"
                ),
            })

    return patterns


async def synthesize_insights(persona_name: str, patterns: list[dict], stats: list[dict]) -> str:
    """Use Ollama to write a human-readable insight report."""
    if not patterns:
        return f"No significant cross-source patterns detected for {persona_name}."

    pattern_text = "\n".join(f"- [{p['type']}] {p['detail']}" for p in patterns)
    total_weeks = len(stats)
    avg_events = sum(s["cal_events"] for s in stats) / total_weeks if total_weeks else 0
    avg_spend = sum(s["discretionary_spend"] for s in stats) / total_weeks if total_weeks else 0

    prompt = f"""Analyze these cross-source patterns for {persona_name} and write 3-5 bullet points as a personal insight report. Cite the data sources (calendar, bank, lifelog, social) in each bullet. Be specific with numbers.

Summary: {total_weeks} weeks of data, avg {avg_events:.1f} calendar events/week, avg ${avg_spend:.0f} discretionary spending/week.

Detected patterns:
{pattern_text}

Write concise, actionable insights. No preamble. /no_think"""

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["message"]["content"]
    except Exception as e:
        logger.warning(f"Ollama synthesis failed, returning raw patterns: {e}")
        lines = [f"Cross-source insights for {persona_name}:\n"]
        for p in patterns:
            lines.append(f"- [{p['type']}] {p['detail']}")
        return "\n".join(lines)


async def generate_insights(persona_name: str, persona_dir: Path) -> str:
    """Full pipeline: load data, compute stats, detect patterns, synthesize."""
    records = load_records(persona_dir)
    if not records:
        return f"No data found for {persona_name}."

    weeks = group_by_week(records)
    stats = compute_weekly_stats(weeks)
    patterns = detect_patterns(stats)

    return await synthesize_insights(persona_name, patterns, stats)
