from importlib import import_module
from typing import Any, TypeVar, Generic, Type
from pydantic import BaseModel
from sqlalchemy import inspect
from sqlalchemy.ext.associationproxy import (
    AssociationProxy,
    _AssociationList,
    _AssociationSet,
)

T = TypeVar("T")
U = TypeVar("U")


class Mapper(Generic[T, U]):
    _response_dto_cache: dict[type, type | None] = {}
    PROXIES = {
        "user.subjects": "user_subject_links",
        "subject.users": "user_subject_links",
        "role.exact_roles": "role_links",
        "exactrole.roles": "role_links",
        "user.notifications": "user_notifications",
        "notification.users": "user_notifications",
        "user.going_events": "user_events",
        "event.attendees": "user_events",
        "user.completed_week_items": "user_completions",
        "user.completed_tasks": "user_completions",
        "weekitem.completed_by_users": "user_completions",
        "task.completed_by_users": "user_completions",
        "material.weeks": "week_items",
        "week.materials": "week_items",
    }

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
    def _map_nested_value(
        cls,
        value: Any,
        visited: dict[int, Any],
        limit_nesting: int | None = None,
        active: set[int] | None = None,
    ) -> Any:
        if value is None:
            return None

        # Check for iterable/collection types
        if isinstance(value, (list, tuple, set, _AssociationList, _AssociationSet)):
            items = list(value)
            if limit_nesting is not None and limit_nesting >= 0:
                items = items[:limit_nesting]

            mapped_items = []
            for item in items:
                mapped_item = cls._map_nested_value(
                    item, visited, limit_nesting=limit_nesting, active=active
                )
                if mapped_item is not None:
                    mapped_items.append(mapped_item)

            return mapped_items

        if not cls._is_orm_instance(value):
            return value

        val_id = id(value)

        # Return cached mapped object if already processed in this graph execution
        if val_id in visited:
            return visited[val_id]

        # ORM relationships are bidirectional. Do not follow a back-reference
        # while its parent is still being mapped.
        if active is not None and val_id in active:
            return None

        dto_cls = cls._resolve_response_dto(type(value))
        if not dto_cls:
            return value

        return cls.map(
            value,
            dto_cls,
            to_dict=False,
            visited=visited,
            active=active,
            limit_nesting=limit_nesting,
        )

    @staticmethod
    def map(
        src: Any,
        cls: Type[U],
        to_dict: bool = False,
        visited: dict[int, Any] | None = None,
        limit_nesting: int | None = None,
        active: set[int] | None = None,
    ) -> U | dict:
        mapped_values = {}
        active_visited = visited if visited is not None else {}
        active_ids = active if active is not None else set()
        src_id = id(src)

        if src_id in active_ids:
            return cls()

        active_ids.add(src_id)

        try:
            if isinstance(src, BaseModel):
                source_attrs = list(type(src).model_fields.keys())
            elif isinstance(src, dict):
                source_attrs = list(src.keys())
            else:
                try:
                    inspected = inspect(src)
                    source_attrs = list(inspected.dict.keys()) if inspected else []
                    if inspected and hasattr(inspected, "mapper"):
                        for (
                            key,
                            descriptor,
                        ) in inspected.mapper.all_orm_descriptors.items():
                            proxy_key = f"{src.__class__.__name__.lower()}.{key}"
                            if (
                                issubclass(type(descriptor), AssociationProxy)
                                and Mapper.PROXIES.get(proxy_key, "") in source_attrs
                                and key not in source_attrs
                            ):
                                source_attrs.append(key)

                except Exception:
                    source_attrs = dir(src)

                if (
                    hasattr(src, "google_details_token")
                    and "google_details_token" not in source_attrs
                ):
                    source_attrs.append("google_details_token")

                if hasattr(src, "seen") and "seen" not in source_attrs:
                    source_attrs.append("seen")

            target_fields = (
                cls.model_fields.keys() if issubclass(cls, BaseModel) else dir(cls)
            )

            for attr in target_fields:
                if attr.startswith("_") or attr.startswith("Model"):
                    continue

                if attr in source_attrs:
                    raw_value = (
                        getattr(src, attr)
                        if not isinstance(src, dict)
                        else src.get(attr)
                    )
                    mapped_value = Mapper._map_nested_value(
                        raw_value,
                        active_visited,
                        limit_nesting=limit_nesting,
                        active=active_ids,
                    )
                    mapped_values[attr] = mapped_value

            dest = cls(**mapped_values)

            # Cache mapped result for this instance ID so shared nested references re-use it
            active_visited[src_id] = dest

            if to_dict:
                return (
                    dest.model_dump(mode="json")
                    if isinstance(dest, BaseModel)
                    else dest.__dict__
                )

            return dest
        finally:
            active_ids.discard(src_id)

    @staticmethod
    def map_list(
        src_list: list[T],
        cls: Type[U],
        to_dict: bool = False,
        limit_nesting: int | None = None,
    ) -> list[U] | list[dict]:
        return [
            Mapper.map(src, cls, to_dict=to_dict, limit_nesting=limit_nesting)
            for src in src_list
        ]
