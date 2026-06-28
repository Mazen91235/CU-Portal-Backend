from typing import Any, TypeVar, Generic, Type, get_args, get_origin
from pydantic import BaseModel
from .typesHandler import TypesHandler
from core.models.queryModel import QueryModel

T = TypeVar("T", bound=BaseModel)


class Generator(Generic[T]):

    @classmethod
    def _unwrap_list_type(cls, annotation: Any) -> type | None:
        """Safely extracts the inner type of a generic list or union containing a list."""
        origin = get_origin(annotation)

        if origin is list:
            args = get_args(annotation)
            return args[0] if args else None

        if origin is not None and hasattr(annotation, "__args__"):
            for arg in get_args(annotation):
                if get_origin(arg) is list:
                    sub_args = get_args(arg)
                    return sub_args[0] if sub_args else None
        return None

    @staticmethod
    def generate(cls: Type[T], data: dict) -> T:
        if not data:
            return cls.model_construct()

        init_kwargs = {}
        fields = cls.model_fields

        for key, value in data.items():
            if key not in fields:
                continue

            field_def = fields[key]
            annotation = field_def.annotation
            inner_type = Generator._unwrap_list_type(annotation)

            if inner_type and isinstance(value, list):
                if inner_type not in TypesHandler.PRIMITIVE_TYPES and issubclass(
                    inner_type, BaseModel
                ):
                    init_kwargs[key] = [
                        Generator.generate(inner_type, item)
                        for item in value
                        if isinstance(item, dict)
                    ]
                else:
                    init_kwargs[key] = value
            else:
                init_kwargs[key] = value

        return cls.model_validate(init_kwargs)

    @staticmethod
    def generate_from_query(cls: Type[T], query: QueryModel) -> T:
        if not query or not hasattr(query, "data") or query.data is None:
            return cls.model_construct()

        # Extract only the fields explicitly provided in the search criteria DTO
        search_criteria = query.data
        dict_payload = search_criteria.model_dump(exclude_unset=True)

        return Generator.generate(cls, dict_payload)
