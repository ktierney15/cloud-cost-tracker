"""Tests run against an in-memory fake so they never call (or bill) AWS."""

from collections import defaultdict
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from cost_tracker.api import app, get_provider

# (service, account, region, tag:team) -> USD per day
ROWS = {
    ("Amazon EC2", "111111111111", "us-east-1", "web"): 10.0,
    ("Amazon RDS", "111111111111", "us-east-1", "data"): 6.0,
    ("Amazon S3", "222222222222", "us-west-2", ""): 2.5,
    ("AWS Lambda", "222222222222", "us-east-1", "web"): 1.5,
}
INDEX = {"SERVICE": 0, "LINKED_ACCOUNT": 1, "REGION": 2, "TAG:team": 3}


class FakeProvider:
    name = "aws"

    def _days(self, start, end):
        d = start
        while d < end:
            yield d
            d += timedelta(days=1)

    def _groups(self, group_by):
        out = defaultdict(float)
        for key, cost in ROWS.items():
            k = key[INDEX[group_by]] if group_by in INDEX else "Usage"
            out[k or "(untagged)"] += cost
        return out

    def total(self, start, end, metric):
        return sum(ROWS.values()) * len(list(self._days(start, end))), "USD"

    def breakdown(self, start, end, group_by, metric):
        n = len(list(self._days(start, end)))
        items = [{"key": k, "label": k, "amount": v * n} for k, v in self._groups(group_by).items()]
        return sorted(items, key=lambda i: -i["amount"])

    def timeseries(self, start, end, granularity, metric, group_by):
        buckets = {}
        for d in self._days(start, end):
            key = str(d if granularity == "DAILY" else d.replace(day=1))
            b = buckets.setdefault(key, defaultdict(float))
            for k, v in self._groups(group_by or "SERVICE").items():
                b[k] += v
        return [
            {"start": k, "total": sum(g.values()), "groups": dict(g) if group_by else {}}
            for k, g in buckets.items()
        ]

    def forecast(self, start, end, metric):
        return sum(ROWS.values()) * (end - start).days

    def tag_keys(self, start, end):
        return ["team"]

    def clear_cache(self):
        pass


@pytest.fixture
def client():
    app.dependency_overrides[get_provider] = FakeProvider
    yield TestClient(app)
    app.dependency_overrides.clear()
