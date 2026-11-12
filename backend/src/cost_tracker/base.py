"""Shared types and the interface every cost provider implements."""

from __future__ import annotations

from datetime import date
from typing import Protocol, TypedDict

METRICS = ("UnblendedCost", "AmortizedCost", "NetUnblendedCost", "NetAmortizedCost", "BlendedCost")

# Every Cost Explorer dimension worth slicing the whole bill by.
DIMENSIONS = {
    "SERVICE": "Service",
    "LINKED_ACCOUNT": "Account",
    "REGION": "Region",
    "USAGE_TYPE": "Usage type",
    "RECORD_TYPE": "Charge type",
    "PURCHASE_TYPE": "Purchase option",
    "INSTANCE_TYPE": "Instance type",
    "OPERATION": "Operation",
}

GRANULARITIES = ("DAILY", "MONTHLY")


class BreakdownItem(TypedDict):
    key: str
    label: str
    amount: float


class Period(TypedDict):
    start: str
    total: float
    groups: dict[str, float]


class CostProvider(Protocol):
    """Dates are ISO dates; ``end`` is exclusive, matching Cost Explorer."""

    name: str

    def total(self, start: date, end: date, metric: str) -> tuple[float, str]: ...

    def breakdown(self, start: date, end: date, group_by: str, metric: str) -> list[BreakdownItem]: ...

    def timeseries(
        self, start: date, end: date, granularity: str, metric: str, group_by: str | None
    ) -> list[Period]: ...

    def forecast(self, start: date, end: date, metric: str) -> float | None: ...

    def tag_keys(self, start: date, end: date) -> list[str]: ...

    def clear_cache(self) -> None: ...
