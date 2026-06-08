from pgvector import Vector
from abc import ABC, abstractmethod


class IAIService(ABC):

    @abstractmethod
    def generate_embeddings(self, path: str) -> Vector | None:
        pass
