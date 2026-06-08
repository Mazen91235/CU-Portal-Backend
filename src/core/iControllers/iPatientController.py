from abc import abstractmethod
from typing import Coroutine
from fastapi import Request, Response
from core.iControllers.bases.iCrudController import ICrudController


class IPatientController(ICrudController):
    @abstractmethod
    def login(self, request: Request) -> Coroutine[None, None, Response]:
        pass

    @abstractmethod
    def get_patient_data(self, request: Request) -> Coroutine[None, None, Response]:
        pass
