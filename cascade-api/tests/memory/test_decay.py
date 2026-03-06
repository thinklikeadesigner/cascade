from datetime import datetime, timezone, timedelta
from cascade_api.memory.decay import calculate_decay


class TestCalculateDecay:
    def test_zero_days(self):
        now = datetime.now(timezone.utc)
        assert calculate_decay(now, rate=0.95) == 1.0

    def test_one_day(self):
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        score = calculate_decay(one_day_ago, rate=0.95)
        assert abs(score - 0.95) < 0.01

    def test_seven_days(self):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        score = calculate_decay(week_ago, rate=0.95)
        assert abs(score - 0.6983) < 0.01

    def test_thirty_days(self):
        month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        score = calculate_decay(month_ago, rate=0.95)
        assert abs(score - 0.2146) < 0.01

    def test_custom_rate(self):
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        score = calculate_decay(one_day_ago, rate=0.90)
        assert abs(score - 0.90) < 0.01

    def test_future_date_returns_one(self):
        future = datetime.now(timezone.utc) + timedelta(days=5)
        assert calculate_decay(future, rate=0.95) == 1.0

    def test_naive_datetime_treated_as_utc(self):
        one_day_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        score = calculate_decay(one_day_ago, rate=0.95)
        assert abs(score - 0.95) < 0.01
