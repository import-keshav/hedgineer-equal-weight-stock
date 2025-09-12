import json
import redis
import os
from typing import Optional, Any
from datetime import date

class RedisService:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.default_ttl = 3600
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True
            )
        return self._client

    def _make_key(self, prefix: str, **kwargs) -> str:
        key_parts = [prefix]
        for key, value in sorted(kwargs.items()):
            if isinstance(value, date):
                value = value.isoformat()
            key_parts.append(f"{key}:{value}")
        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            return self.client.setex(key, ttl, serialized)
        except Exception:
            return False

    async def get_index_performance(self, start_date: date, end_date: date) -> Optional[Any]:
        key = self._make_key("index_performance", start_date=start_date, end_date=end_date)
        return await self.get(key)

    async def set_index_performance(self, start_date: date, end_date: date, data: Any) -> bool:
        key = self._make_key("index_performance", start_date=start_date, end_date=end_date)
        return await self.set(key, data)

    async def get_index_composition(self, target_date: date) -> Optional[Any]:
        key = self._make_key("index_composition", date=target_date)
        return await self.get(key)

    async def set_index_composition(self, target_date: date, data: Any) -> bool:
        key = self._make_key("index_composition", date=target_date)
        return await self.set(key, data)

    async def get_composition_changes(self, start_date: date, end_date: date) -> Optional[Any]:
        key = self._make_key("composition_changes", start_date=start_date, end_date=end_date)
        return await self.get(key)

    async def set_composition_changes(self, start_date: date, end_date: date, data: Any) -> bool:
        key = self._make_key("composition_changes", start_date=start_date, end_date=end_date)
        return await self.set(key, data)
