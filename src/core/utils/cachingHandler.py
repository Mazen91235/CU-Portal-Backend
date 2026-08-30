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

    async def delete(self, key: str) -> None:
        await self.redis_client.delete(key)
