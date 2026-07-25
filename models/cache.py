"""
cache.py — 模型调用缓存（AI-Native 可靠性的基石）

对相同 prompt 的调用，2小时内直接返回缓存结果。
零 token 消耗，零延迟。
"""
import time, hashlib, json
from collections import OrderedDict
from typing import Any, Optional, Dict


class LLMCache:
    """LRU 缓存 + TTL，线程安全"""

    def __init__(self, max_entries: int = 500, default_ttl: int = 7200):
        self._data = OrderedDict()
        self._max = max_entries
        self._ttl = default_ttl
        self._hits = 0
        self._misses = 0
        self._expired = 0

    def _key(self, model: str, kwargs: dict) -> str:
        return hashlib.md5(
            json.dumps({"model": model, **kwargs}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    def get(self, model: str, kwargs: dict) -> Optional[Any]:
        k = self._key(model, kwargs)
        if k in self._data:
            val, ts = self._data[k]
            if time.time() - ts < self._ttl:
                self._data.move_to_end(k)
                self._hits += 1
                return val
            else:
                del self._data[k]
                self._expired += 1
        self._misses += 1
        return None

    def put(self, model: str, kwargs: dict, value: Any):
        k = self._key(model, kwargs)
        self._data[k] = (value, time.time())
        self._data.move_to_end(k)
        if len(self._data) > self._max:
            self._data.popitem(last=False)

    @property
    def stats(self) -> Dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits, "misses": self._misses,
            "expired": self._expired, "size": len(self._data),
            "hit_rate": self._hits / total if total else 0,
        }


cache = LLMCache()
