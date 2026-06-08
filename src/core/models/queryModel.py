from typing import TypedDict, TypeVar, Generic

U = TypeVar("U")  # EntitySearchDto Type


class QueryModel(TypedDict, Generic[U]):
    data: U
    includes: list[str]
    selects: list[str]
    is_and: bool
    starts_with: bool
    is_exact: bool
    order_by: list[str]
    descending: bool
    page: int | None
    limit: int | None
