import os
from cryptography.fernet import Fernet


class FernetHandler:
    fernet = Fernet((os.environ.get("FERNET_KEY", "")).encode())

    @staticmethod
    def encrypt(data: str) -> str:
        return FernetHandler.fernet.encrypt(data.encode()).decode() if data else ""

    @staticmethod
    def decrypt(token: str) -> str:
        return FernetHandler.fernet.decrypt(token.encode()).decode() if token else ""
