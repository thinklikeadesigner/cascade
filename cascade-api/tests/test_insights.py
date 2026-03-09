"""Tests for the cross-source insight engine."""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from cascade_api.insights import (
    parse_amount,
    week_key,
    group_by_week,
    compute_weekly_stats,
    detect_patterns,
    load_records,
)


def test_parse_amount():
    assert parse_amount("$85.00 - Easy Tiger - social") == 85.00
    assert parse_amount("$2,100.00 - rent - housing") == 2100.00
    assert parse_amount("$32.00 - BookPeople - books") == 32.00
    assert parse_amount("no amount here") is None
    assert parse_amount("") is None


def test_week_key():
    dt = datetime(2024, 1, 10, 16, 0, 0)
    result = week_key(dt)
    assert result == "2024-W02"

    dt2 = datetime(2024, 1, 1, 0, 0, 0)
    result2 = week_key(dt2)
    assert result2 == "2024-W01"


def test_group_by_week():
    records = [
        {"ts": "2024-01-10T16:00:00-05:00", "source": "calendar", "text": "event1"},
        {"ts": "2024-01-11T09:00:00-05:00", "source": "calendar", "text": "event2"},
        {"ts": "2024-01-20T10:00:00-05:00", "source": "bank", "text": "$50.00 - food"},
        {"ts": None, "source": "calendar", "text": "no timestamp"},
    ]
    weeks = group_by_week(records)
    # Jan 10 and 11 are same ISO week (W02), Jan 20 is W03
    assert len(weeks) == 2
    week_sizes = sorted(len(v) for v in weeks.values())
    assert week_sizes == [1, 2]


def test_compute_weekly_stats():
    records = {
        "2024-W02": [
            {"source": "calendar", "text": "Meeting", "tags": ["work"]},
            {"source": "calendar", "text": "Therapy session", "tags": ["therapy", "mental_health"]},
            {"source": "bank", "text": "$85.00 - Easy Tiger - social", "tags": ["social"]},
            {"source": "bank", "text": "$2,100.00 - rent - housing", "tags": ["rent", "housing"]},
            {"source": "lifelog", "text": "Feeling exhausted after work", "tags": ["health"]},
            {"source": "lifelog", "text": "Great workout today", "tags": ["fitness"]},
            {"source": "social", "text": "Posted something fun", "tags": ["humor"]},
        ],
    }
    stats = compute_weekly_stats(records)
    assert len(stats) == 1
    s = stats[0]
    assert s["week"] == "2024-W02"
    assert s["cal_events"] == 2
    assert s["stress_events"] == 1  # therapy is a stress tag
    assert s["total_spend"] == 2185.00
    assert s["discretionary_spend"] == 85.00  # rent is recurring
    assert s["negative_mood"] == 1  # "exhausted"
    assert s["positive_mood"] == 1  # "Great"
    assert s["social_posts"] == 1


def test_detect_stress_spending_pattern():
    """Detect stress_spending when discretionary spending spikes after stress events."""
    stats = [
        {
            "week": "2024-W01", "cal_events": 5, "stress_events": 3,
            "total_spend": 100, "discretionary_spend": 50,
            "negative_mood": 0, "positive_mood": 0, "social_posts": 1,
        },
        {
            "week": "2024-W02", "cal_events": 3, "stress_events": 0,
            "total_spend": 300, "discretionary_spend": 200,
            "negative_mood": 0, "positive_mood": 0, "social_posts": 1,
        },
        {
            "week": "2024-W03", "cal_events": 3, "stress_events": 0,
            "total_spend": 100, "discretionary_spend": 50,
            "negative_mood": 0, "positive_mood": 0, "social_posts": 1,
        },
        {
            "week": "2024-W04", "cal_events": 3, "stress_events": 0,
            "total_spend": 100, "discretionary_spend": 50,
            "negative_mood": 0, "positive_mood": 0, "social_posts": 1,
        },
    ]
    # avg discretionary = (50+200+50+50)/4 = 87.5, W02 has 200 > 87.5*1.3=113.75
    patterns = detect_patterns(stats)
    types = [p["type"] for p in patterns]
    assert "stress_spending" in types


def test_load_records_real_data():
    """Load actual persona_p01 data if available."""
    persona_dir = Path(__file__).parent.parent.parent / "data" / "personadata" / "personas" / "persona_p01"
    if not persona_dir.exists():
        pytest.skip("persona_p01 data not available")

    records = load_records(persona_dir)
    assert len(records) > 0
    # Check that records have expected fields
    for r in records[:5]:
        assert "id" in r
        assert "source" in r
        assert "text" in r
