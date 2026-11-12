from datetime import date

import boto3
from botocore.stub import Stubber

from cost_tracker.aws import AwsCostProvider
from cost_tracker.cache import TTLCache


def _provider():
    session = boto3.session.Session(
        aws_access_key_id="x", aws_secret_access_key="x", region_name="us-east-1"
    )
    p = AwsCostProvider(TTLCache(60), session=session)
    return p, Stubber(p.client)


def _group(key, amount):
    return {"Keys": [key], "Metrics": {"UnblendedCost": {"Amount": str(amount), "Unit": "USD"}}}


def test_breakdown_follows_pagination_and_cleans_tag_keys():
    p, stub = _provider()
    period = {"Start": "2026-10-01", "End": "2026-11-01"}
    stub.add_response(
        "get_cost_and_usage",
        {"ResultsByTime": [{"TimePeriod": period, "Groups": [_group("team$web", 5)]}],
         "NextPageToken": "t"},
    )
    stub.add_response(
        "get_cost_and_usage",
        {"ResultsByTime": [{"TimePeriod": period, "Groups": [_group("team$", 2), _group("team$data", 9)]}]},
    )
    with stub:
        items = p.breakdown(date(2026, 10, 1), date(2026, 11, 1), "TAG:team", "UnblendedCost")
        # Second call is served from cache: no more stubbed responses needed.
        p.breakdown(date(2026, 10, 1), date(2026, 11, 1), "TAG:team", "UnblendedCost")
    assert [(i["key"], i["amount"]) for i in items] == [("data", 9), ("web", 5), ("(untagged)", 2)]


def test_forecast_returns_none_when_aws_has_no_data():
    p, stub = _provider()
    stub.add_client_error("get_cost_forecast", "DataUnavailableException")
    with stub:
        assert p.forecast(date(2026, 11, 11), date(2026, 12, 1), "UnblendedCost") is None


def test_tag_keys_empty_without_permission():
    p, stub = _provider()
    stub.add_client_error("get_tags", "AccessDeniedException")
    with stub:
        assert p.tag_keys(date(2026, 8, 1), date(2026, 11, 11)) == []
