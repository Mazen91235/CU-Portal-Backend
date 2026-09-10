import os
import json
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()  # Load environment variables from .env file


class CachingHandler:
    def __init__(self):
        self.redis_client = Redis.from_url(
            os.environ.get("REDIS_URL", ""), decode_responses=True
        )

    async def get(self, key: str) -> dict | None:
        result = await self.redis_client.get(key)
        return json.loads(result) if result and type(result) == str else None

    async def set(self, key: str, value: dict, expire: int | None = None) -> None:
        await self.redis_client.set(key, json.dumps(value), ex=expire)

    async def delete(self, *keys: str) -> None:
        await self.redis_client.delete(*keys)

    async def invalidate_module_cache(self, module: str) -> None:
        keys = await self.redis_client.keys(f"*/{module}*")
        if keys:
            await self.redis_client.delete(*keys)
        if any(
            [x in module for x in ["task", "exam", "announcement", "event", "note"]]
        ):
            await self.invalidate_module_cache("calendar")

    async def acquire_lock(self, lock_key: str, expire: int = 60) -> bool:
        acquired = await self.redis_client.set(lock_key, "1", nx=True, ex=expire)
        if acquired:
            return True
        return False

    async def release_lock(self, lock_key: str) -> None:
        await self.redis_client.delete(lock_key)
