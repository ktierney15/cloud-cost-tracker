"""Tiny in-memory TTL cache. Cost Explorer bills $0.01 per request, so we cache hard."""

from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: Any, fn: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            hit = self._data.get(key)
            if hit and now - hit[0] < self.ttl:
                return hit[1]
        value = fn()
        with self._lock:
            self._data[key] = (now, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def cached(method: Callable) -> Callable:
    """Cache a provider method's result in ``self.cache`` keyed on its arguments."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        key = (method.__name__, args, tuple(sorted(kwargs.items())))
        return self.cache.get_or_set(key, lambda: method(self, *args, **kwargs))

    return wrapper
