from abc import ABC, abstractmethod


class IBaseService(ABC):
    @abstractmethod
    async def begin_transaction(self) -> None:
        pass

    @abstractmethod
    async def commit_transaction(self) -> None:
        pass

    @abstractmethod
    async def rollback_transaction(self) -> None:
        pass
