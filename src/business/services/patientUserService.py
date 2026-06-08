from typing import cast
from pgvector import Vector
from sqlalchemy.orm import selectinload
from core.iServices.iPatientUserService import IPatientUserService
from core.entities.patientUser import PatientUser
from core.dtos.baseResponseDto import BaseResponseDto
from core.iRepositories.iBaseRepository import IBaseRepository
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iServices.iHelperService import IHelperService
from core.iServices.iAIService import IAIService


class PatientUserService(IPatientUserService):
    def __init__(
        self,
        patient_user_repository: IBaseRepository[PatientUser],
        logger: IBaseLogger,
        helper_service: IHelperService,
        ai_service: IAIService,
    ):
        self.patient_user_repository = patient_user_repository
        self.logger = logger
        self.helper_service = helper_service
        self.ai_service = ai_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.patient_user_repository.begin_transaction()

    async def commit_transaction(self):
        await self.patient_user_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.patient_user_repository.rollback_transaction()

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
            if not data or not data.img_vector:
                await self.logger.log(
                    action="FindOne",
                    entity="PatientUser",
                    level="warning",
                    code=400,
                    message="Bad Request: Missing data or image vector for finding patient user",
                    source="PatientUserService",
                )
                return BaseResponseDto[PatientUser | None](
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request: Missing data or image vector for finding patient user",
                    error="Missing data or image vector for finding patient user",
                )
            # patient_response = await self.helper_service.get_logged_in_patient()
            # if not patient_response.success:
            #     return BaseResponseDto[PatientUser | None](
            #         success=False,
            #         code=patient_response.code,
            #         data=None,
            #         message=patient_response.message,
            #         error=patient_response.error,
            #     )
            # patient = patient_response.data
            # if not patient:
            #     await self.logger.log(
            #         action="FindOne",
            #         entity="PatientUser",
            #         level="warning",
            #         code=401,
            #         message="Unauthorized: No logged in patient for finding patient user",
            #         source="PatientUserService",
            #     )
            #     return BaseResponseDto[PatientUser | None](
            #         success=False,
            #         code=401,
            #         data=None,
            #         message="Unauthorized: No logged in patient for finding patient user",
            #         error="No logged in patient for finding patient user",
            #     )
            # data.patient_id = patient.id
            predicate = self.helper_service.generate_dynamic_predicate(
                PatientUser, data, is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                PatientUser, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "PatientUser", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "PatientUser", order_by
            )
            result = await self.patient_user_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )
            if not result.success:
                return BaseResponseDto[PatientUser | None](
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                    error=result.error,
                )
            patient_user = result.data
            if not patient_user:
                await self.logger.log(
                    action="FindOne",
                    entity="PatientUser",
                    level="info",
                    code=404,
                    message="PatientUser not found",
                    source="PatientUserService",
                )
                return BaseResponseDto[PatientUser | None](
                    success=False,
                    code=404,
                    data=None,
                    message="PatientUser not found",
                    error="No patient user found matching the criteria",
                )
            return BaseResponseDto[PatientUser | None](success=True, data=patient_user)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while finding patient user - {str(ex)}",
                source="PatientUserService",
            )
            return BaseResponseDto[PatientUser | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding patient user",
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
        return BaseResponseDto[None | list[PatientUser]](success=True, data=[])

    async def create(self, data):
        try:
            patient_response = await self.helper_service.get_logged_in_patient()
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
                await self.logger.log(
                    action="Create",
                    entity="PatientUser",
                    level="warning",
                    code=401,
                    message="Unauthorized: No logged in patient",
                    source="PatientUserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Unauthorized: No logged in patient",
                    error="No logged in patient",
                )
            data.patient_id = patient.id
            response = await self.patient_user_repository.create(data)
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
                entity="PatientUser",
                level="info",
                code=201,
                message="PatientUser created successfully",
                source="PatientUserService",
            )
            return BaseResponseDto(success=True, data=patient)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while creating patient user - {str(ex)}",
                source="PatientUserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating patient user",
                error=str(ex),
            )

    async def delete(self, data):
        try:
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
                await self.logger.log(
                    action="Delete",
                    entity="PatientUser",
                    level="warning",
                    code=401,
                    message="Unauthorized: No logged in user",
                    source="PatientUserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=False,
                    message="Unauthorized: No logged in user",
                    error="No logged in user",
                )
            patient_user_response = await self.patient_user_repository.find_one(
                PatientUser.id == (data.id if data else None),
                includes=[selectinload(PatientUser.patient)],
            )
            if not patient_user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=patient_user_response.code,
                    data=False,
                    message=patient_user_response.message,
                    error=patient_user_response.error,
                )
            patient_user = patient_user_response.data
            if not patient_user:
                await self.logger.log(
                    action="Delete",
                    entity="PatientUser",
                    level="info",
                    code=404,
                    message="PatientUser not found for deletion",
                    source="PatientUserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="PatientUser not found for deletion",
                    error="No patient user found with the provided ID",
                )
            patient = patient_user.patient
            if patient.user_id != user.id:
                await self.logger.log(
                    action="Delete",
                    entity="PatientUser",
                    level="warning",
                    code=403,
                    message="Forbidden: Patient user does not belong to the logged in patient",
                    source="PatientUserService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="Forbidden: Patient user does not belong to the logged in patient",
                    error="Patient user does not belong to the logged in patient",
                )
            response = await self.patient_user_repository.delete(patient_user)
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
                entity="PatientUser",
                level="info",
                code=200,
                message="PatientUser deleted successfully",
                source="PatientUserService",
            )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while deleting patient user - {str(ex)}",
                source="PatientUserService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while deleting patient user",
                error=str(ex),
            )
