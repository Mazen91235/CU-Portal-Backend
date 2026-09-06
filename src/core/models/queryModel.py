from typing import TypeVar, Generic
from pydantic import BaseModel, Field

U = TypeVar("U")  # EntitySearchDto Type


class QueryModel(BaseModel, Generic[U]):
    data: U | None = Field(
        default=None, description="The search criteria for the query"
    )
    includes: list[str] = Field(
        default_factory=list,
        description="List of related entities to include in the response",
    )
    selects: list[str] = Field(
        default_factory=list, description="List of fields to include in the response"
    )
    is_and: bool = Field(
        default=True, description="Whether to use AND logic for filtering"
    )
    starts_with: bool = Field(
        default=False, description="Whether to match the beginning of the string"
    )
    is_exact: bool = Field(
        default=False, description="Whether to perform an exact match"
    )
    order_by: list[str] = Field(
        default_factory=list, description="List of fields to order the results by"
    )
    descending: bool = Field(
        default=False, description="Whether to order the results in descending order"
    )
    page: int | None = Field(
        default=None, ge=1, description="Page number for pagination"
    )
    limit: int | None = Field(
        default=None, ge=1, description="Number of items per page for pagination"
    )
