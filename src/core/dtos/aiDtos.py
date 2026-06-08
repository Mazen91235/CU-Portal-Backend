from typing import TypedDict


class AIVoiceIdentificationResponseDto:
    def __init__(self, name: str, relation: str, path: str):
        self.name = name
        self.relation = relation
        self.path = path

    def to_dict(self):
        return {"name": self.name, "relation": self.relation, "path": self.path}

    class Model(TypedDict):
        name: str
        relation: str
        path: str
