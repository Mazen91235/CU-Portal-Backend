from importlib import import_module
from typing import Any, TypeVar, Generic, Type
from pydantic import BaseModel
from sqlalchemy import inspect

T = TypeVar("T")
U = TypeVar("U")


class Mapper(Generic[T, U]):
    _response_dto_cache: dict[type, type | None] = {}

    @classmethod
    def _resolve_response_dto(cls, entity_cls: type) -> type | None:
        if entity_cls in cls._response_dto_cache:
            return cls._response_dto_cache[entity_cls]

        dto_cls_name = f"{entity_cls.__name__}ResponseDto"
        dto_module_name = (
            f"{entity_cls.__name__[0].lower()}{entity_cls.__name__[1:]}Dtos"
        )

        try:
            dto_module = import_module(f"core.dtos.{dto_module_name}")
            dto_cls = getattr(dto_module, dto_cls_name, None)
        except Exception:
            dto_cls = None

        cls._response_dto_cache[entity_cls] = dto_cls
        return dto_cls

    @staticmethod
    def _is_orm_instance(value: Any) -> bool:
        inspected_value = inspect(value, raiseerr=False)
        return inspected_value is not None and hasattr(inspected_value, "mapper")

    @classmethod
    def _map_nested_value(cls, value: Any, visited: set[int]) -> Any:
        if value is None:
            return None

        if isinstance(value, list):
            return [cls._map_nested_value(item, visited) for item in value]

        if not cls._is_orm_instance(value):
            return value

        # FIX: Track the individual instance ID to break cycles without blocking sibling objects
        if id(value) in visited:
            return None

        visited.add(id(value))

        dto_cls = cls._resolve_response_dto(type(value))
        if not dto_cls:
            return value

        return cls.map(value, dto_cls, False, visited)

    @staticmethod
    def map(
        src: Any,
        cls: Type[U],
        to_dict: bool = False,
        visited: set[int] | None = None,
    ) -> U | dict:
        dest = cls()
        active_visited = set(visited) if visited is not None else set()
        active_visited.add(id(src))

        # Identify source attributes cleanly based on structure type
        if isinstance(src, BaseModel):
            source_attrs = list(src.model_fields.keys())
        else:
            try:
                inspected = inspect(src)
                source_attrs = list(inspected.dict.keys()) if inspected else []
            except Exception:
                source_attrs = dir(src)

            # Keep your explicit property visible to the mapper
            if (
                hasattr(src, "google_details_token")
                and "google_details_token" not in source_attrs
            ):
                source_attrs.append("google_details_token")

        # Map matching field names directly across
        for attr in source_attrs:
            if attr.startswith("_") or attr.startswith("Model"):
                continue

            if hasattr(dest, attr):
                raw_value = getattr(src, attr)
                mapped_value = Mapper._map_nested_value(raw_value, active_visited)
                setattr(dest, attr, mapped_value)

        if to_dict:
            return dest.model_dump() if isinstance(dest, BaseModel) else dest.__dict__

        return dest

    @staticmethod
    def map_list(
        src_list: list[T], cls: Type[U], to_dict: bool = False
    ) -> list[U] | list[dict]:
        return [Mapper.map(src, cls, to_dict=to_dict) for src in src_list]
