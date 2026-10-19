"""Abuse protection for a public deployment: per-client rate limit and a global daily LLM budget.

In-memory on purpose: the app runs as a single instance. Behind several instances, move the
counters to Redis or the database.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from datetime import UTC, datetime

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    """Allow at most ``limit`` calls per ``window`` seconds for each key."""

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> float:
        """Record a call; return 0 when allowed, otherwise the seconds to wait."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.window - (now - hits[0])
            hits.append(now)
            if len(self._hits) > 10_000:  # Forget idle clients so memory stays bounded.
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < self.window}
            return 0.0


class DailyBudget:
    """Counts LLM-backed requests per UTC day; once spent, callers degrade to deterministic mode."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._day = ""
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        today = datetime.now(UTC).date().isoformat()
        with self._lock:
            if today != self._day:
                self._day, self._used = today, 0
            if self.limit and self._used >= self.limit:
                return False
            self._used += 1
            return True


def client_key(request: Request) -> str:
    # Render and most PaaS put the real client first in X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def enforce(limiter: SlidingWindowLimiter, request: Request) -> None:
    wait = limiter.check(client_key(request))
    if wait > 0:
        raise HTTPException(429, "Too many requests, please slow down.", headers={"Retry-After": str(math.ceil(wait))})
