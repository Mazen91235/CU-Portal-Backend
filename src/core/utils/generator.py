from typing import TypeVar, Generic, Type
from .typesHandler import TypesHandler
from core.models.queryModel import QueryModel

T = TypeVar("T")


class Generator(Generic[T]):

    @staticmethod
    def generate(cls: Type[T], data: dict) -> T:
        item = cls()
        for key, value in data.items():
            if hasattr(item, key):
                attr_type = type(getattr(item, key))
                if attr_type in TypesHandler.PRIMITIVE_TYPES:
                    setattr(item, key, value)
                elif issubclass(attr_type, list) and isinstance(value, list):
                    single_item_type = (
                        getattr(attr_type, "__args__", [None])[0]
                        if hasattr(attr_type, "__args__")
                        else None
                    )
                    if (
                        not single_item_type
                        or single_item_type in TypesHandler.PRIMITIVE_TYPES
                    ):
                        setattr(item, key, value)
                    else:
                        setattr(
                            item,
                            key,
                            [
                                Generator[single_item_type].generate(
                                    single_item_type, v
                                )
                                for v in value
                            ],
                        )
                else:
                    setattr(item, key, value)
        return item

    @staticmethod
    def generate_from_query(cls: Type[T], data: QueryModel) -> T:
        item = cls()
        if not data or not hasattr(data, "data"):
            return item
        model = data["data"]
        for key, value in getattr(model, "items")():
            if hasattr(item, key):
                attr_type = type(getattr(item, key))
                if attr_type in TypesHandler.PRIMITIVE_TYPES:
                    setattr(item, key, value)
                elif issubclass(attr_type, list) and isinstance(value, list):
                    single_item_type = (
                        getattr(attr_type, "__args__", [None])[0]
                        if hasattr(attr_type, "__args__")
                        else None
                    )
                    if (
                        not single_item_type
                        or single_item_type in TypesHandler.PRIMITIVE_TYPES
                    ):
                        setattr(item, key, value)
                    else:
                        setattr(
                            item,
                            key,
                            [
                                Generator[single_item_type].generate(
                                    single_item_type, v
                                )
                                for v in value
                            ],
                        )
                else:
                    setattr(item, key, value)
        return item
