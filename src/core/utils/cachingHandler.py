import os
import json
import asyncio
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv()  # Load environment variables from .env file

CACHE_TTL = int(os.environ.get("CACHE_TTL", 120))  # Default cache TTL in seconds


class CachingHandler:
    def __init__(self):
        self.redis_client = Redis.from_url(
            os.environ.get("REDIS_URL", ""), decode_responses=True
        )
        self._refresh_tasks: set[asyncio.Task] = set()

    def _schedule_refresh(self, key: str, value: str, expire: int) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return

        async def _refresh() -> None:
            # Refresh only if the key still contains the value that was read. This
            # keeps the desired GET->SET TTL refresh behavior without resurrecting
            # a key that was deleted and replaced concurrently.
            try:
                await self.redis_client.eval(
                    """
                    if redis.call('GET', KEYS[1]) == ARGV[1] then
                        return redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
                    end
                    return 0
                    """,
                    1,
                    key,
                    value,
                    str(expire),
                )
            except Exception:
                pass

        task = asyncio.create_task(_refresh())
        self._refresh_tasks.add(task)
        task.add_done_callback(self._refresh_tasks.discard)

    async def get(self, key: str, expire: int = CACHE_TTL) -> dict | None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return None
        result = await self.redis_client.get(key)
        if isinstance(result, str):
            self._schedule_refresh(key, result, expire)
            try:
                return json.loads(result)
            except Exception:
                return None
        return None

    async def get_raw(self, key: str, expire: int = CACHE_TTL) -> str | None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return None
        result = await self.redis_client.get(key)
        if isinstance(result, str):
            self._schedule_refresh(key, result, expire)
            return result
        return None

    async def set(self, key: str, value: dict, expire: int = CACHE_TTL) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.set(key, json.dumps(value), ex=expire)

    async def set_raw(
        self, key: str, value: bytes | str, expire: int = CACHE_TTL
    ) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.set(key, value, ex=expire)

    async def delete(self, *keys: str) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return
        await self.redis_client.delete(*keys)

    async def invalidate_module_cache(self, module: str) -> None:
        if os.environ.get("TESTING", "false").lower() == "true":
            return

        batch: list[str] = []
        async for key in self.redis_client.scan_iter(match=f"*{module}*", count=500):
            batch.append(key)
            if len(batch) >= 500:
                await self.redis_client.delete(*batch)
                batch.clear()
        if batch:
            await self.redis_client.delete(*batch)

        if any(
            [x in module for x in ["task", "exam", "announcement", "event", "note"]]
        ):
            await self.invalidate_module_cache("calendar")
        if any([x in module for x in ["course", "subject"]]):
            await self.invalidate_module_cache("material")
            await self.invalidate_module_cache("task")
            await self.invalidate_module_cache("exam")
            await self.invalidate_module_cache("announcement")
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
