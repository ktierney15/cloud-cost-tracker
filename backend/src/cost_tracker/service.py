"""Composes provider calls into the views the API, CLI and email report need."""

from __future__ import annotations

from datetime import date, timedelta

from .base import CostProvider


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, 1)


def previous_month(today: date | None = None) -> tuple[date, date]:
    """(first day of last month, first day of this month) - end exclusive."""
    today = today or date.today()
    this = month_start(today)
    return add_months(this, -1), this


def summary(provider: CostProvider, metric: str, today: date | None = None) -> dict:
    """Headline numbers for the whole account: MTD, last month, projected, change."""
    today = today or date.today()
    this_month = month_start(today)
    next_month = add_months(this_month, 1)
    last_start, last_end = previous_month(today)

    # Month-to-date covers complete days only (today's data is partial in AWS).
    mtd, unit = provider.total(this_month, today, metric)
    last_month, _ = provider.total(last_start, last_end, metric)

    # Same number of days last month, for a fair "are we trending up?" comparison.
    days_elapsed = (today - this_month).days
    same_period_end = min(last_start + timedelta(days=days_elapsed), last_end)
    last_mtd, _ = provider.total(last_start, same_period_end, metric)

    remaining = provider.forecast(today, next_month, metric)
    projected = mtd + remaining if remaining is not None else None

    def pct(a: float, b: float) -> float | None:
        return (a - b) / b * 100 if b else None

    return {
        "provider": provider.name,
        "metric": metric,
        "unit": unit,
        "as_of": str(today),
        "month_to_date": mtd,
        "month_to_date_days": days_elapsed,
        "last_month": last_month,
        "last_month_same_period": last_mtd,
        "mtd_change_pct": pct(mtd, last_mtd) if days_elapsed else None,
        "projected_month": projected,
        "projected_change_pct": pct(projected, last_month) if projected is not None else None,
        "periods": {
            "month_to_date": [str(this_month), str(today)],
            "last_month": [str(last_start), str(last_end)],
            "projected_month": [str(this_month), str(next_month)],
        },
    }
