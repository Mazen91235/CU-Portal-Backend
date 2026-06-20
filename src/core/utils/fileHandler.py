from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import FileModel, FetchedModel


class FileHandler:
    @staticmethod
    async def fetch_from_drive(
        id: str, api_key: str, visited: set[str] | None = None, max_retries: int = 6
    ) -> BaseResponseDto[FetchedModel]:
        