from abc import abstractmethod
from typing import Any, Coroutine
from core.dtos.baseResponseDto import BaseResponseDto
from core.iServices.bases.iCrudService import ICrudService
from core.entities.patient import Patient
from core.dtos.patientDtos import (
    PatientSearchDto,
)


class IPatientService(ICrudService[Patient, PatientSearchDto]):
    @abstractmethod
    def login(
        self, token: str
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[Patient | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass

    @abstractmethod
    def get_patient_data(
        self,
    ) -> (
        Coroutine[Any, Any, BaseResponseDto[Patient | None]]
        | Coroutine[Any, Any, BaseResponseDto[None]]
    ):
        pass
