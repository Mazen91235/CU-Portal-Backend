from abc import abstractmethod
from typing import Coroutine
from fastapi import Request, Response, UploadFile
from core.iControllers.bases.iDeletableController import IDeletableController


class IPatientUserController(IDeletableController):
    @abstractmethod
    def find_one(
        self, request: Request, file: UploadFile
    ) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def create(
        self, request: Request, files: list[UploadFile]
    ) -> Coroutine[None, None, Response]:
        pass
