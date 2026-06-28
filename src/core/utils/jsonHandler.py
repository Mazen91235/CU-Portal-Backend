import json


class JSONHandler:
    @staticmethod
    def stringify(data: dict) -> str:
        """
        Convert a dictionary to a JSON string.
        """
        try:
            return json.dumps(data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Error converting dictionary to JSON string: {e}")

    @staticmethod
    def parse(json_string: str) -> dict:
        """
        Convert a JSON string to a dictionary.
        """
        try:
            return json.loads(json_string)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Error parsing JSON string to dictionary: {e}")
