import threading
from typing import Any, Dict, Optional


class AnalyticsCache:
    """
    In-memory thread-safe cache for precomputed graph analytics results.
    Prevents repeated expensive recomputations on interactive API requests.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._cache
