import os
import json
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()  # Load environment variables from .env file

CACHE_TTL = int(os.environ.get("CACHE_TTL", 120))  # Default cache TTL in seconds


class CachingHandler:
    def __init__(self):
        self.redis_client = Redis.from_url(
            os.environ.get("REDIS_URL", ""), decode_responses=True
        )

    async def get(self, key: str) -> dict | None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return None
        result = await self.redis_client.get(key)
        return json.loads(result) if result and type(result) == str else None

    async def set(self, key: str, value: dict, expire: int = CACHE_TTL) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.set(key, json.dumps(value), ex=expire)

    async def delete(self, *keys: str) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.delete(*keys)

    async def invalidate_module_cache(self, module: str) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        keys = await self.redis_client.keys(f"*/{module}*")
        if keys:
            await self.redis_client.delete(*keys)
        if any(
            [x in module for x in ["task", "exam", "announcement", "event", "note"]]
        ):
            await self.invalidate_module_cache("calendar")
        if any([x in module for x in ["auth"]]):
            await self.invalidate_module_cache("user")
        if any([x in module for x in ["material"]]):
            await self.invalidate_module_cache("week")
        if any([x in module for x in ["event"]]):
            await self.invalidate_module_cache("event")

    async def acquire_lock(self, lock_key: str, expire: int = 60) -> bool:
        if os.environ.get("TESTING", "false").lower() == "true":
            return True
        acquired = await self.redis_client.set(lock_key, "1", nx=True, ex=expire)
        if acquired:
            return True
        return False

    async def release_lock(self, lock_key: str) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.delete(lock_key)


caching_handler = CachingHandler()
