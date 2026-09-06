import os
from cryptography.fernet import Fernet


class FernetHandler:
    @classmethod
    def get_fernet(cls) -> Fernet:
        fernet_key = os.environ.get("FERNET_KEY", "")
        if not fernet_key:
            raise ValueError("FERNET_KEY environment variable is not set.")
        return Fernet(fernet_key.encode())

    @classmethod
    def encrypt(cls, data: str) -> str:
        return cls.get_fernet().encrypt(data.encode()).decode() if data else ""

    @classmethod
    def decrypt(cls, token: str) -> str:
        return cls.get_fernet().decrypt(token.encode()).decode() if token else ""
