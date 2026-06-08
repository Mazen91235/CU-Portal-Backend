from abc import ABC, abstractmethod
from typing import Any, Coroutine


class IBaseService(ABC):
    @abstractmethod
    def begin_transaction(self) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def commit_transaction(self) -> Coroutine[Any, Any, None]:
        pass

    @abstractmethod
    def rollback_transaction(self) -> Coroutine[Any, Any, None]:
        pass
