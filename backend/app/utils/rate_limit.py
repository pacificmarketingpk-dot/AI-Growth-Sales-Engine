"""Small in-memory sliding-window rate limiter. For multi-instance deployments, swap for Redis."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many requests. Please wait a moment and try again.")
        q.append(now)


auth_limiter = RateLimiter(limit=10, window_seconds=60)
ai_limiter = RateLimiter(limit=60, window_seconds=60)


def client_key(request: Request) -> str:
    # X-Real-IP is set by our Nginx from the actual TCP peer, so clients can't spoof it.
    # (X-Forwarded-For is not used: its first entry is client-controlled.)
    real = request.headers.get("x-real-ip")
    if real and get_settings().trust_proxy_headers:
        return real.strip()
    return request.client.host if request.client else "unknown"
