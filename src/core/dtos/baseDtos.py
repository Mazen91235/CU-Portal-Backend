from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponseDto(BaseModel, Generic[T]):
    success: bool = Field(..., description="Indicates if the operation was successful")
    code: int | None = Field(
        default=None, description="HTTP status code of the response"
    )
    message: str | None = Field(
        default=None, description="Message providing additional information"
    )
    error: str | None = Field(
        default=None, description="Error message if the operation failed"
    )
    data: T | None = Field(
        default=None, description="The actual data returned by the operation"
    )

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True,
    }


class BaseSearchDto(BaseModel):
    query: str | None = Field(default=None, description="Search query string")
    # page: int | None = Field(
    #     default=None, ge=1, description="Page number for pagination"
    # )
    # limit: int | None = Field(
    #     default=None, ge=1, le=50, description="Number of items per page for pagination"
    # )
