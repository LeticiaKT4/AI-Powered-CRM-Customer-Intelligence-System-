"""TTL cache with degraded-mode fallback (FR-011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Generic, TypeVar

from config import get_settings

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    cached_at: datetime


@dataclass
class CacheResult(Generic[T]):
    data: T
    degraded: bool = False
    warning: str | None = None
    cached_at: datetime | None = None


class CRMCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._ttl = get_settings().cache_ttl_seconds

    def get_or_fetch(self, key: str, fetcher: Callable[[], T]) -> CacheResult[T]:
        now = datetime.now(timezone.utc)
        entry = self._store.get(key)

        try:
            fresh = fetcher()
            self._store[key] = CacheEntry(value=fresh, cached_at=now)
            return CacheResult(data=fresh, degraded=False, cached_at=now)
        except Exception:  # noqa: BLE001
            if entry is not None:
                return CacheResult(
                    data=entry.value,
                    degraded=True,
                    warning="CRM data source unavailable. Showing last cached data.",
                    cached_at=entry.cached_at,
                )
            raise

    def has(self, key: str) -> bool:
        return key in self._store


_cache: CRMCache | None = None


def get_cache() -> CRMCache:
    global _cache
    if _cache is None:
        _cache = CRMCache()
    return _cache
