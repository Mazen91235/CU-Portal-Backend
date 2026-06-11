from typing import Generic, TypeVar, TypedDict
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponseDto(Generic[T], BaseModel):
    success: bool
    code: int
    message: str
    error: str
    data: T | None

    def __init__(
        self,
        success: bool,
        code: int = 200,
        message: str = "",
        error: str = "",
        data: T = None,
    ):
        self.success = success
        self.code = code
        self.message = message
        self.error = error
        self.data = data

    def to_dict(self):
        return {
            "success": self.success,
            "code": self.code,
            "message": self.message,
            "error": self.error,
            "data": self.data,
        }


class BaseSearchDto(BaseModel):
    query: str = Field("", description="Search query string")
    page: int | None = Field(None, ge=1, description="Page number for pagination")
    limit: int | None = Field(
        None, ge=1, le=50, description="Number of items per page for pagination"
    )

    def to_dict(self):
        return {"query": self.query, "page": self.page, "limit": self.limit}

    class Model(TypedDict):
        query: str
        page: int | None
        limit: int | None
