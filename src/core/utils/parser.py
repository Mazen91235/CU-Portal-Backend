import json
from urllib.parse import unquote
from typing import Type, TypeVar
from .generator import Generator

T = TypeVar("T")  # Entity Type


class Parser:
    @staticmethod
    def parse_query(query: str, cls: Type[T] | None = None) -> T:
        if not cls:
            raise ValueError("Class type must be provided for parsing")
        if not query:
            raise ValueError("Query string cannot be empty")
        try:
            if isinstance(query, str):
                parsed_query = json.loads(unquote(query))
            else:
                parsed_query = query
            if isinstance(parsed_query, str):
                parsed_query = json.loads(parsed_query)
            if not isinstance(parsed_query, dict):
                raise ValueError("Parsed query must be a JSON object")
            for key in parsed_query.keys():
                if isinstance(parsed_query[key], str):
                    parsed_query[key] = parsed_query[key].strip()
            return Generator[T].generate(cls, parsed_query)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing query: {e}")
