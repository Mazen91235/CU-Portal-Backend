from abc import ABC, abstractmethod


class IBaseLogger(ABC):
    @abstractmethod
    async def log(
        self,
        action: str,
        entity: str,
        level: str,
        code: int,
        message: str,
        source: str,
        details: dict | None = None,
    ) -> None:
        pass
