import json
from urllib.parse import unquote
from fastapi import Query
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Parser:
    @staticmethod
    def parse_query(
        cls: Type[T] | None = None,
    ):
        def _parse(
            query: str = Query(
                None,
                alias="query",
                description="JSON-stringified QueryModel filter object",
                openapi_examples={
                    "default": {
                        "summary": "Sample Filter JSON",
                        "value": """{
                                "data": {"Field values for the specific search DTO, e.g., UserSearchDto"},
                                "includes": ["users", "subjects"],
                                "selects": ["id", "year"],
                                "is_and": true,
                                "starts_with": false,
                                "is_exact": false,
                                "order_by": ["created_at"],
                                "descending": true,
                                "page": 1,
                                "limit": 10
                            }""",
                    }
                },
            ),
        ) -> T:
            if cls is None:
                raise ValueError("Class type must be provided for parsing")
            if not query:
                raise ValueError("Query string cannot be empty")

            try:
                # 1. Handle URL decoding and initial JSON parsing safely
                if isinstance(query, str):
                    parsed_query = json.loads(unquote(query))
                else:
                    parsed_query = query

                if isinstance(parsed_query, str):
                    parsed_query = json.loads(parsed_query)

                if not isinstance(parsed_query, dict):
                    raise ValueError("Parsed query must be a JSON object")

                # 2. Basic whitespace sanitization on top-level strings
                for key, val in parsed_query.items():
                    if isinstance(val, str):
                        parsed_query[key] = val.strip()

                # 3. Use Pydantic's native validation directly
                # This handles generic nesting (like QueryModel[UserSearchDto]) perfectly
                return cls.model_validate(parsed_query)

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")
            except Exception as e:
                raise ValueError(f"Error parsing query: {e}")

        return _parse
