"""
Lightweight in-memory sliding-window rate limiter for FastAPI endpoints.

Usage (as a dependency factory):

    from ..utils.rate_limit import RateLimiter

    login_limiter = RateLimiter(max_requests=10, window_seconds=60, scope="auth:login")

    @router.post("/login")
    async def login(creds: UserLogin, _=Depends(login_limiter)):
        ...

Notes:
- In-memory only. Not suitable behind multiple workers/replicas without sticky
  sessions or a shared store (Redis). For single-instance deployments it is
  sufficient and dependency-free.
- Keys are built from the client IP and an optional per-request key extractor
  (e.g. for per-email OTP limits).
- Uses a monotonic clock for correctness across system-time changes.
- Expired entries are lazily pruned on each call; memory footprint is bounded
  by the number of active keys within the window.
"""

import logging
import os
import threading
import time
from collections import deque
from typing import Callable, Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Master kill-switch for rate limiting (useful in dev / load-testing).
_DISABLED = os.getenv("RATE_LIMIT_DISABLED", "false").lower() in ("1", "true", "yes")


class _WindowBucket:
    """Thread-safe sliding-window bucket keyed by identifier."""

    __slots__ = ("_hits", "_lock")

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, max_requests: int, window_seconds: float) -> Tuple[bool, float]:
        """
        Attempt to record a hit for ``key``.

        Returns a tuple ``(allowed, retry_after_seconds)``. When ``allowed`` is
        False, ``retry_after_seconds`` is a conservative hint for the client.
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            dq = self._hits.get(key)
            if dq is None:
                dq = deque()
                self._hits[key] = dq
            # Drop expired entries
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= max_requests:
                retry_after = max(0.0, dq[0] + window_seconds - now)
                return False, retry_after
            dq.append(now)
            return True, 0.0


# A single shared bucket store across all limiters keeps memory tight.
_bucket = _WindowBucket()


KeyFunc = Callable[[Request], Optional[str]]


class RateLimiter:
    """
    FastAPI dependency that enforces a sliding-window rate limit.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed per ``window_seconds`` per key.
    window_seconds:
        Window length in seconds.
    scope:
        Short label used as the storage namespace and in log messages.
    key_func:
        Optional callable that returns an additional string to scope the limit
        by (e.g. the request body's ``email``). If it returns ``None`` or raises,
        the client IP alone is used.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        scope: str,
        key_func: Optional[KeyFunc] = None,
    ) -> None:
        if max_requests <= 0 or window_seconds <= 0:
            raise ValueError("max_requests and window_seconds must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.scope = scope
        self.key_func = key_func

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Trust X-Forwarded-For only if explicitly configured (left-most entry).
        # Otherwise fall back to the direct peer IP.
        if os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("1", "true", "yes"):
            fwd = request.headers.get("x-forwarded-for")
            if fwd:
                return fwd.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def __call__(self, request: Request) -> None:
        if _DISABLED:
            return
        extra = None
        if self.key_func is not None:
            try:
                extra = self.key_func(request)
            except Exception:  # defensive: never let key extraction break the request
                extra = None
        ip = self._client_ip(request)
        key = f"{self.scope}:{ip}"
        if extra:
            key = f"{key}:{extra}"
        allowed, retry_after = _bucket.allow(key, self.max_requests, self.window_seconds)
        if not allowed:
            request_id = getattr(request.state, "request_id", "n/a")
            logger.warning(
                "rate_limit exceeded request_id=%s scope=%s ip=%s extra=%s retry_after=%.1fs",
                request_id,
                self.scope,
                ip,
                extra or "-",
                retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many requests. Please wait "
                    f"{int(retry_after) + 1}s before trying again."
                ),
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
