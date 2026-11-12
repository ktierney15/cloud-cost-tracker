"""AWS Cost Explorer provider: covers every service, account, region and charge type."""

from __future__ import annotations

import re
from datetime import date

import boto3
from botocore.exceptions import ClientError

from .base import BreakdownItem, Period
from .cache import TTLCache, cached

FORECAST_METRIC = {
    "UnblendedCost": "UNBLENDED_COST",
    "AmortizedCost": "AMORTIZED_COST",
    "NetUnblendedCost": "NET_UNBLENDED_COST",
    "NetAmortizedCost": "NET_AMORTIZED_COST",
    "BlendedCost": "BLENDED_COST",
}


def _group_spec(group_by: str) -> dict:
    """``SERVICE`` -> dimension group; ``TAG:team`` -> tag group."""
    if group_by.startswith("TAG:"):
        return {"Type": "TAG", "Key": group_by[4:]}
    return {"Type": "DIMENSION", "Key": group_by}


def _clean_key(group_by: str, raw: str) -> str:
    # Tag groups come back as "team$platform"; an empty value means untagged.
    if group_by.startswith("TAG:"):
        value = raw.split("$", 1)[1] if "$" in raw else raw
        return value or "(untagged)"
    return raw or "(none)"


class AwsCostProvider:
    name = "aws"

    def __init__(self, cache: TTLCache, session: boto3.session.Session | None = None):
        self.cache = cache
        # Cost Explorer is a global API served from us-east-1.
        self.client = (session or boto3.session.Session()).client("ce", region_name="us-east-1")

    def clear_cache(self) -> None:
        self.cache.clear()

    def _cost_and_usage(self, **params) -> list[dict]:
        """Call GetCostAndUsage, following pagination, and return all ResultsByTime."""
        results: list[dict] = []
        token = None
        while True:
            if token:
                params["NextPageToken"] = token
            resp = self.client.get_cost_and_usage(**params)
            # Grouped results can be split across pages for the same period.
            for period in resp["ResultsByTime"]:
                if results and results[-1]["TimePeriod"] == period["TimePeriod"]:
                    results[-1].setdefault("Groups", []).extend(period.get("Groups", []))
                else:
                    results.append(period)
            token = resp.get("NextPageToken")
            if not token:
                return results

    @cached
    def total(self, start: date, end: date, metric: str) -> tuple[float, str]:
        if start >= end:
            return 0.0, "USD"
        results = self._cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="MONTHLY",
            Metrics=[metric],
        )
        unit = "USD"
        amount = 0.0
        for period in results:
            m = period["Total"][metric]
            amount += float(m["Amount"])
            unit = m.get("Unit", unit)
        return amount, unit

    @cached
    def breakdown(self, start: date, end: date, group_by: str, metric: str) -> list[BreakdownItem]:
        if start >= end:
            return []
        results = self._cost_and_usage(
            TimePeriod={"Start": str(start), "End": str(end)},
            Granularity="MONTHLY",
            Metrics=[metric],
            GroupBy=[_group_spec(group_by)],
        )
        totals: dict[str, float] = {}
        for period in results:
            for group in period.get("Groups", []):
                key = _clean_key(group_by, group["Keys"][0])
                totals[key] = totals.get(key, 0.0) + float(group["Metrics"][metric]["Amount"])

        labels = self._account_names(start, end) if group_by == "LINKED_ACCOUNT" else {}
        items = [
            BreakdownItem(key=k, label=labels.get(k, k), amount=v) for k, v in totals.items()
        ]
        return sorted(items, key=lambda i: i["amount"], reverse=True)

    @cached
    def timeseries(
        self, start: date, end: date, granularity: str, metric: str, group_by: str | None
    ) -> list[Period]:
        if start >= end:
            return []
        params: dict = {
            "TimePeriod": {"Start": str(start), "End": str(end)},
            "Granularity": granularity,
            "Metrics": [metric],
        }
        if group_by:
            params["GroupBy"] = [_group_spec(group_by)]
        out: list[Period] = []
        for period in self._cost_and_usage(**params):
            groups: dict[str, float] = {}
            for group in period.get("Groups", []):
                key = _clean_key(group_by or "", group["Keys"][0])
                groups[key] = groups.get(key, 0.0) + float(group["Metrics"][metric]["Amount"])
            total = (
                sum(groups.values()) if group_by else float(period["Total"][metric]["Amount"])
            )
            out.append(Period(start=period["TimePeriod"]["Start"], total=total, groups=groups))
        return out

    @cached
    def forecast(self, start: date, end: date, metric: str) -> float | None:
        if start >= end:
            return 0.0
        try:
            resp = self.client.get_cost_forecast(
                TimePeriod={"Start": str(start), "End": str(end)},
                Metric=FORECAST_METRIC[metric],
                Granularity="MONTHLY",
            )
        except ClientError as err:
            # New accounts or sparse history: AWS refuses to forecast.
            if err.response["Error"]["Code"] in {"DataUnavailableException", "ValidationException"}:
                return None
            raise
        return float(resp["Total"]["Amount"])

    @cached
    def tag_keys(self, start: date, end: date) -> list[str]:
        try:
            resp = self.client.get_tags(TimePeriod={"Start": str(start), "End": str(end)})
        except ClientError as err:
            # Tag grouping is optional; don't break the dashboard without ce:GetTags.
            if err.response["Error"]["Code"] == "AccessDeniedException":
                return []
            raise
        return sorted(t for t in resp.get("Tags", []) if t and not re.match(r"^aws:", t))

    @cached
    def _account_names(self, start: date, end: date) -> dict[str, str]:
        try:
            resp = self.client.get_dimension_values(
                TimePeriod={"Start": str(start), "End": str(end)}, Dimension="LINKED_ACCOUNT"
            )
        except ClientError:
            return {}
        return {
            v["Value"]: f'{v["Attributes"].get("description", v["Value"])} ({v["Value"]})'
            for v in resp.get("DimensionValues", [])
        }
