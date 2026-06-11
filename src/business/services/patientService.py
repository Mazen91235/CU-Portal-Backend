from sqlalchemy.orm import selectinload
from core.iServices.iPatientService import IPatientService
from core.entities.patient import Patient
from core.dtos.baseDtos import BaseResponseDto
from core.iRepositories.iBaseRepository import IBaseRepository
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iServices.iHelperService import IHelperService
from core.utils.stringHandler import StringHandler


class PatientService(IPatientService):
    def __init__(
        self,
        patient_repository: IBaseRepository[Patient],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.patient_repository = patient_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.patient_repository.begin_transaction()

    async def commit_transaction(self):
        await self.patient_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.patient_repository.rollback_transaction()

    # CRUD Functions
    async def find_one(
        self,
        data=None,
        includes=[],
        selects=[],
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=[],
        descending=False,
    ):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            if data:
                data.user_id = user.id
            predicate = self.helper_service.generate_dynamic_predicate(
                Patient, data, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Patient, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Patient", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Patient", order_by
            )
            result = await self.patient_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                    error=result.error,
                )
            patient = result.data
            return BaseResponseDto(success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while finding patient - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding patient",
                error=str(ex),
            )

    async def find(
        self,
        data=None,
        includes=[],
        selects=[],
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=[],
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto[None | list[Patient]](
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto[None | list[Patient]](
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            if data:
                data.user_id = user.id
            predicate = self.helper_service.generate_dynamic_predicate(
                Patient, data, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Patient, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Patient", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Patient", order_by
            )
            result = await self.patient_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto[None | list[Patient]](
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                    error=result.error,
                )
            patients = result.data
            return BaseResponseDto[None | list[Patient]](success=True, data=patients)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while finding patients - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto[None | list[Patient]](
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding patients",
                error=str(ex),
            )

    async def create(self, data):
        try:
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            data.user_id = user.id
            token = StringHandler.generate_random_string(8)
            refresh_token = StringHandler.generate_random_string(32)
            data.token = token
            data.refresh_token = refresh_token
            response = await self.patient_repository.create(data)
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            patient = response.data
            await self.logger.log(
                action="Create",
                entity="Patient",
                level="info",
                code=201,
                message="Patient created successfully",
                source="PatientService",
            )
            return BaseResponseDto(success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while creating patient - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating patient",
                error=str(ex),
            )

    async def update(self, data):
        try:
            patient_response = await self.patient_repository.find_one(
                Patient.id == data.id
            )
            if not patient_response.success:
                return BaseResponseDto(
                    success=False,
                    code=patient_response.code,
                    data=None,
                    message=patient_response.message,
                    error=patient_response.error,
                )
            patient = patient_response.data
            if not patient:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Patient not found",
                    error="Patient not found",
                )
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=None,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            if patient.user_id != user.id:
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="Forbidden: You do not have permission to update this patient",
                    error="You do not have permission to update this patient",
                )
            patient.name = data.name
            response = await self.patient_repository.update(patient, ["name"])
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            patient = response.data
            await self.logger.log(
                action="Update",
                entity="Patient",
                level="info",
                code=200,
                message="Patient updated successfully",
                source="PatientService",
            )
            return BaseResponseDto(success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while updating patient - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating patient",
                error=str(ex),
            )

    async def delete(self, data):
        try:
            patient_response = await self.patient_repository.find_one(
                Patient.id == (data.id if data else None)
            )
            if not patient_response.success:
                return BaseResponseDto(
                    success=False,
                    code=patient_response.code,
                    data=False,
                    message=patient_response.message,
                    error=patient_response.error,
                )
            patient = patient_response.data
            if not patient:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="Patient not found",
                    error="Patient not found",
                )
            user_response = await self.helper_service.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                    error=user_response.error,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=False,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            if patient.user_id != user.id:
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="Forbidden: You do not have permission to update this patient",
                    error="You do not have permission to update this patient",
                )
            response = await self.patient_repository.delete(patient)
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=False,
                    message=response.message,
                    error=response.error,
                )
            await self.logger.log(
                action="Delete",
                entity="Patient",
                level="info",
                code=200,
                message="Patient deleted successfully",
                source="PatientService",
            )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while deleting patient - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while deleting patient",
                error=str(ex),
            )

    # Patient Specific Functions
    async def login(self, token):
        try:
            patient_response = await self.patient_repository.find_one(
                Patient.token == token
            )

            if not patient_response.success:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=patient_response.code,
                    data=None,
                    message=patient_response.message,
                    error=patient_response.error,
                )

            patient = patient_response.data
            if not patient:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=404,
                    data=None,
                    message="Patient not found",
                    error="Invalid token",
                )

            await self.logger.log(
                action="Login",
                entity="Patient",
                level="info",
                code=200,
                message="Patient logged in successfully",
                source="PatientService",
            )

            return BaseResponseDto[Patient | None](success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="Login",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while patient login - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto[Patient | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while patient login",
                error=str(ex),
            )

    async def get_patient_data(self):
        try:
            patient_response = await self.helper_service.get_logged_in_patient()
            if not patient_response.success:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=patient_response.code,
                    data=None,
                    message=patient_response.message,
                    error=patient_response.error,
                )

            patient = patient_response.data
            if not patient:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in patient",
                    error="No logged in patient",
                )

            full_patient_response = await self.patient_repository.find_one(
                Patient.id == patient.id,
                includes=[selectinload(Patient.patient_users)],
            )
            if not full_patient_response.success:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=full_patient_response.code,
                    data=None,
                    message=full_patient_response.message,
                    error=full_patient_response.error,
                )
            patient = full_patient_response.data

            await self.logger.log(
                action="GetPatientData",
                entity="Patient",
                level="info",
                code=200,
                message="Logged-in patient data retrieved successfully",
                source="PatientService",
            )

            return BaseResponseDto[Patient | None](success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="GetPatientData",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while retrieving logged-in patient - {str(ex)}",
                source="PatientService",
            )
            return BaseResponseDto[Patient | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving logged-in patient",
                error=str(ex),
            )
