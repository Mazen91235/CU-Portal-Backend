import os
from cryptography.fernet import Fernet


class FernetHandler:
    @classmethod
    def get_fernet(cls) -> Fernet:
        fernet_key = os.environ.get("FERNET_KEY", "")
        if not fernet_key:
            raise ValueError("FERNET_KEY environment variable is not set.")
        return Fernet(fernet_key.encode())

    @staticmethod
    def encrypt(data: str) -> str:
        return (
            FernetHandler.get_fernet().encrypt(data.encode()).decode() if data else ""
        )

    @staticmethod
    def decrypt(token: str) -> str:
        return (
            FernetHandler.get_fernet().decrypt(token.encode()).decode() if token else ""
        )
