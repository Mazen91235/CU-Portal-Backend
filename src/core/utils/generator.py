from typing import Any, TypeVar, Generic, Type, get_args, get_origin
from pydantic import BaseModel
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapper
from .typesHandler import TypesHandler
from core.models.queryModel import QueryModel

T = TypeVar("T")


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
    def _is_pydantic(cls: Type) -> bool:
        """Check if the class is a Pydantic model."""
        return isinstance(cls, type) and issubclass(cls, BaseModel)

    @staticmethod
    def _is_sqlalchemy(cls: Type) -> bool:
        """Check if the class is a mapped SQLAlchemy ORM model."""
        try:
            return inspect(cls) is not None
        except Exception:
            return False

    @staticmethod
    def generate(cls: Type[T], data: dict) -> T:
        if not data:
            if Generator._is_pydantic(cls):
                return cls.model_construct()
            elif Generator._is_sqlalchemy(cls):
                return cls()
            return cls()

        init_kwargs = {}

        # ---------------------------------------------------------------------
        # PATH A: Pydantic Model
        # ---------------------------------------------------------------------
        if Generator._is_pydantic(cls):
            fields = cls.model_fields

            for key, value in data.items():
                if key not in fields:
                    continue

                field_def = fields[key]
                annotation = field_def.annotation
                inner_type = Generator._unwrap_list_type(annotation)

                if inner_type and isinstance(value, list):
                    if (
                        inner_type not in TypesHandler.PRIMITIVE_TYPES
                        and Generator._is_pydantic(inner_type)
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

            # Use model_construct to bypass validation & lazy descriptors
            return cls.model_construct(**init_kwargs)

        # ---------------------------------------------------------------------
        # PATH B: SQLAlchemy ORM Model
        # ---------------------------------------------------------------------
        elif Generator._is_sqlalchemy(cls):
            mapper: Mapper = inspect(cls)
            valid_columns = set(mapper.columns.keys())
            valid_relationships = set(mapper.relationships.keys())

            for key, value in data.items():
                # Process Column Attributes
                if key in valid_columns:
                    init_kwargs[key] = value

                # Process Nested Relationships
                elif key in valid_relationships:
                    rel_property = mapper.relationships[key]
                    target_cls = rel_property.mapper.class_

                    if rel_property.uselist and isinstance(value, list):
                        init_kwargs[key] = [
                            Generator.generate(target_cls, item)
                            for item in value
                            if isinstance(item, dict)
                        ]
                    elif isinstance(value, dict):
                        init_kwargs[key] = Generator.generate(target_cls, value)

            # Instantiates the ORM object directly without lazy-load triggers
            return cls(**init_kwargs)

        # ---------------------------------------------------------------------
        # PATH C: Fallback for Plain Python Classes / Dataclasses
        # ---------------------------------------------------------------------
        return cls(**data)

    @staticmethod
    def generate_from_query(cls: Type[T], query: QueryModel) -> T:
        if not query or not hasattr(query, "data") or query.data is None:
            if Generator._is_pydantic(cls):
                return cls.model_construct()
            return cls()

        search_criteria = query.data

        if isinstance(search_criteria, BaseModel):
            dict_payload = search_criteria.model_dump(exclude_unset=True)
        elif isinstance(search_criteria, dict):
            dict_payload = search_criteria
        else:
            dict_payload = getattr(search_criteria, "__dict__", {})

        return Generator.generate(cls, dict_payload)
