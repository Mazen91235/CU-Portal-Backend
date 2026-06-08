from abc import ABC, abstractmethod
from typing import Any, Coroutine


class IBaseLogger(ABC):
    @abstractmethod
    def log(
        self, action: str, entity: str, level: str, code: int, message: str, source: str
    ) -> Coroutine[Any, Any, None]:
        pass
