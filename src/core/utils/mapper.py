from importlib import import_module
from typing import Any, TypeVar, Generic, Type

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

        dto_cls = None
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

        if id(value) in visited:
            # Break cyclic ORM references (e.g., Patient -> PatientUser -> Patient).
            return None

        visited.add(id(type(value)))

        dto_cls = cls._resolve_response_dto(type(value))
        if not dto_cls:
            return value

        return cls.map(value, dto_cls, False, visited)

    @staticmethod
    def map(
        src: T,
        cls: Type[U],
        to_dict: bool = False,
        visited: set[int] | None = None,
    ) -> U | dict:
        dest = cls()  # Create an instance of the destination type
        active_visited = set(visited) if visited is not None else set()
        active_visited.add(id(src))

        try:
            inspected = inspect(src)
            loaded_attrs = inspected.dict.keys() if inspected else []
        except Exception:
            loaded_attrs = dir(src)  # Fallback to dir() if inspect fails

        for attr in loaded_attrs:
            if (
                not attr.startswith("_")
                and not attr.startswith("Model")
                and not attr.startswith("to_dict")
                and hasattr(dest, attr)
            ):
                raw_value = getattr(src, attr)
                mapped_value = Mapper._map_nested_value(raw_value, active_visited)
                setattr(dest, attr, mapped_value)

        if to_dict and hasattr(dest, "to_dict"):
            return getattr(dest, "to_dict")()
        return dest

    @staticmethod
    def map_list(
        src_list: list[T], cls: Type[U], to_dict: bool = False
    ) -> list[U] | list[dict]:
        return [Mapper.map(src, cls, to_dict) for src in src_list]
