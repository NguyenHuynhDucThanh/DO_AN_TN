"""Small bounded in-process limiter for the single-instance Windows deployment."""

from __future__ import annotations

from collections import deque
from hashlib import blake2b
from math import ceil
from threading import Lock
import time
from typing import Callable

from fastapi import Request

from app.core.errors import TooManyRequestsError


class RateLimiter:
    """Fixed-window-like sliding limiter without retaining raw identity or IP data."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    @staticmethod
    def _digest(scope: str, client: str, identity: str) -> str:
        value = f"{scope}\0{client}\0{identity}".encode("utf-8", errors="replace")
        return blake2b(value, digest_size=20).hexdigest()

    def check(
        self,
        *,
        scope: str,
        client: str,
        identity: str = "",
        limit: int,
        window_seconds: int,
    ) -> None:
        now = self._clock()
        cutoff = now - window_seconds
        key = self._digest(scope, client, identity)
        with self._lock:
            bucket = self._hits.get(key)
            if bucket is None:
                if len(self._hits) >= self._max_keys:
                    self._hits.pop(next(iter(self._hits)))
                bucket = deque()
                self._hits[key] = bucket
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = ceil(window_seconds - (now - bucket[0]))
                raise TooManyRequestsError(retry_after_seconds=retry_after)
            bucket.append(now)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    identity: str = "",
    limit: int,
    window_seconds: int,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    client = request.client.host if request.client else "unknown"
    rate_limiter.check(
        scope=scope,
        client=client,
        identity=identity.casefold().strip(),
        limit=limit,
        window_seconds=window_seconds,
    )
