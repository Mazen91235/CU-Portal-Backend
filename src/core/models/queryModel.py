from typing import TypeVar, Generic
from pydantic import BaseModel, Field

U = TypeVar("U")  # EntitySearchDto Type


class QueryModel(BaseModel, Generic[U]):
    data: U = Field(..., description="The search criteria for the query")
    includes: list[str] = Field(
        ..., description="List of related entities to include in the response"
    )
    selects: list[str] = Field(
        ..., description="List of fields to include in the response"
    )
    is_and: bool = Field(..., description="Whether to use AND logic for filtering")
    starts_with: bool = Field(
        ..., description="Whether to match the beginning of the string"
    )
    is_exact: bool = Field(..., description="Whether to perform an exact match")
    order_by: list[str] = Field(
        ..., description="List of fields to order the results by"
    )
    descending: bool = Field(
        ..., description="Whether to order the results in descending order"
    )
    page: int | None = Field(None, ge=1, description="Page number for pagination")
    limit: int | None = Field(
        None, ge=1, le=50, description="Number of items per page for pagination"
    )
