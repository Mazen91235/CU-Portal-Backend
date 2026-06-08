from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iCreatableService import ICreatableService
from core.iServices.bases.iDeletableService import IDeletableService
from core.entities.patientUser import PatientUser
from core.dtos.patientUserDtos import PatientUserSearchDto


class IPatientUserService(
    IQueryableService[PatientUser, PatientUserSearchDto],
    ICreatableService[PatientUser],
    IDeletableService[PatientUser],
):
    pass
