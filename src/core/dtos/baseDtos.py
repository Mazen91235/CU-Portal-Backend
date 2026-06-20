from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponseDto(Generic[T]):
    def __init__(
        self,
        success: bool = False,
        code: int | None = None,
        message: str | None = None,
        error: str | None = None,
        data: T | None = None,
    ):
        self.success = success
        self.code = code
        self.message = message
        self.error = error
        self.data = data


class BaseSearchDto(BaseModel):
    query: str = Field("", description="Search query string")
    page: int | None = Field(None, ge=1, description="Page number for pagination")
    limit: int | None = Field(
        None, ge=1, le=50, description="Number of items per page for pagination"
    )
