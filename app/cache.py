import asyncio
from collections import OrderedDict
from typing import Any, Optional

class LRUCache:
    def __init__(self, capacity: int = 500):
        self.capacity = capacity
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Optional[Any]:
        async with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

    async def put(self, key: str, value: Any) -> None:
        async with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    async def invalidate(self, key: str) -> None:
        async with self.lock:
            self.cache.pop(key, None)

    async def get_stats(self) -> dict:
        async with self.lock:
            total = self.hits + self.misses
            hit_ratio = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self.cache),
                "capacity": self.capacity,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_percent": round(hit_ratio, 2)
            }

plan_cache = LRUCache(capacity=500)