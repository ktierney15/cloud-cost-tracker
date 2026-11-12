"""FastAPI app: JSON cost API under /api, and the dashboard UI at /."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import __version__, service
from .aws import AwsCostProvider
from .base import DIMENSIONS, GRANULARITIES, METRICS, CostProvider
from .cache import TTLCache
from .config import settings


@lru_cache
def get_provider() -> CostProvider:
    return AwsCostProvider(TTLCache(settings.cache_ttl_seconds))


app = FastAPI(title="Cloud Cost Tracker", version=__version__)

MetricQ = Query("UnblendedCost", description="Cost Explorer metric")


def _check_metric(metric: str) -> str:
    if metric not in METRICS:
        raise HTTPException(422, f"metric must be one of {', '.join(METRICS)}")
    return metric


def _check_group(group_by: str) -> str:
    if group_by in DIMENSIONS or (group_by.startswith("TAG:") and len(group_by) > 4):
        return group_by
    raise HTTPException(422, f"group_by must be one of {', '.join(DIMENSIONS)} or TAG:<key>")


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    """Default to the current month. ``end`` is exclusive."""
    today = date.today()
    start = start or service.month_start(today)
    end = end or today + timedelta(days=1)
    if start >= end:
        raise HTTPException(422, "start must be before end")
    # Cost Explorer only keeps ~14 months of history by default.
    if start < service.add_months(service.month_start(today), -13):
        raise HTTPException(422, "start is older than the 14 months Cost Explorer retains")
    return start, end


@app.get("/api/health")
def health(provider: CostProvider = Depends(get_provider)):
    return {"status": "ok", "provider": provider.name, "version": __version__}


@app.get("/api/meta")
def meta(provider: CostProvider = Depends(get_provider)):
    return {
        "provider": provider.name,
        "metrics": list(METRICS),
        "dimensions": DIMENSIONS,
        "granularities": list(GRANULARITIES),
    }


@app.get("/api/summary")
def summary(metric: str = MetricQ, provider: CostProvider = Depends(get_provider)):
    return service.summary(provider, _check_metric(metric))


@app.get("/api/breakdown")
def breakdown(
    group_by: str = "SERVICE",
    start: date | None = None,
    end: date | None = None,
    metric: str = MetricQ,
    provider: CostProvider = Depends(get_provider),
):
    """Every line of spend in the range, grouped by one dimension or tag."""
    start, end = _range(start, end)
    items = provider.breakdown(start, end, _check_group(group_by), _check_metric(metric))
    total = sum(i["amount"] for i in items)
    return {
        "group_by": group_by,
        "start": str(start),
        "end": str(end),
        "total": total,
        "items": [{**i, "share": i["amount"] / total if total else 0} for i in items],
    }


@app.get("/api/timeseries")
def timeseries(
    start: date | None = None,
    end: date | None = None,
    granularity: str = "DAILY",
    group_by: str | None = "SERVICE",
    metric: str = MetricQ,
    provider: CostProvider = Depends(get_provider),
):
    start, end = _range(start, end)
    if granularity not in GRANULARITIES:
        raise HTTPException(422, f"granularity must be one of {', '.join(GRANULARITIES)}")
    group = _check_group(group_by) if group_by else None
    periods = provider.timeseries(start, end, granularity, _check_metric(metric), group)
    return {"start": str(start), "end": str(end), "granularity": granularity, "periods": periods}


@app.get("/api/tags")
def tags(provider: CostProvider = Depends(get_provider)):
    today = date.today()
    return {"tags": provider.tag_keys(service.add_months(service.month_start(today), -3), today)}


@app.post("/api/refresh")
def refresh(provider: CostProvider = Depends(get_provider)):
    """Drop cached Cost Explorer responses so the next request fetches fresh data."""
    provider.clear_cache()
    return {"status": "cleared"}


if settings.ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.ui_dir, html=True), name="ui")
