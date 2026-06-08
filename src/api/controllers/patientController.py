from typing import cast
from core.iControllers.iPatientController import IPatientController
from core.iServices.iPatientService import IPatientService
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# Entities & DTOs
from core.entities.patient import Patient
from core.dtos.patientDtos import (
    PatientRegisterDto,
    PatientResponseDto,
    PatientUpdateDto,
    PatientSearchDto,
    PatientLoginDto,
    PatientLoginResponseDto,
    PatientDeleteDto,
)
from core.models.queryModel import QueryModel


class PatientController(IPatientController):
    def __init__(self, patient_service: IPatientService, logger: IBaseLogger):
        self.patient_service = patient_service
        self.logger = logger

    async def find_one(self, request):
        try:
            patient_id = int(request.path_params.get("id") or "0")
            patient_entity = Generator[PatientSearchDto].generate(
                PatientSearchDto, {"id": patient_id}
            )
            response = await self.patient_service.find_one(
                patient_entity, ["patient_users"], is_and=True
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            patient = response.data

            if not patient:
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Patient not found",
                )

            patient = Mapper[Patient, PatientResponseDto].map(
                patient, PatientResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patient,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def find(self, request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[PatientSearchDto.Model],
            )
            patient_entity = Generator[PatientSearchDto].generate_from_query(
                PatientSearchDto, query
            )
            includes = query.get("includes", ["patient_users"])
            selects = query.get("selects", [])
            is_and = query.get("is_and", True)
            starts_with = query.get("starts_with", True)
            is_exact = query.get("is_exact", True)
            order_by = query.get("order_by", [])
            descending = query.get("descending", False)
            page = cast(int, query.get("page", 1))
            limit = cast(int, query.get("limit", 50))

            response = await self.patient_service.find(
                patient_entity,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            patients = response.data

            if not patients:
                return ResponseHandler.generate_response(
                    success=True,
                    code=200,
                    data=[],
                )

            patients = Mapper[Patient, PatientResponseDto].map_list(
                patients, PatientResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patients,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def create(self, request):
        try:
            await self.patient_service.begin_transaction()
            payload = await request.json()
            data = Generator[PatientRegisterDto].generate(PatientRegisterDto, payload)

            patient = Mapper[PatientRegisterDto, Patient].map(data, Patient)

            response = await self.patient_service.create(patient)

            if not response.success:
                await self.patient_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.patient_service.commit_transaction()
            patient = Mapper[Patient, PatientResponseDto].map(
                response.data, PatientResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=patient,
            )
        except Exception as e:
            await self.patient_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def update(self, request):
        try:
            await self.patient_service.begin_transaction()
            patient_id = int(request.path_params.get("id") or "0")
            payload = await request.json()
            payload["id"] = patient_id
            data = Generator[PatientUpdateDto].generate(PatientUpdateDto, payload)

            patient = Mapper[PatientUpdateDto, Patient].map(data, Patient)

            response = await self.patient_service.update(patient)

            if not response.success:
                await self.patient_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.patient_service.commit_transaction()
            patient = Mapper[Patient, PatientResponseDto].map(
                response.data, PatientResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patient,
            )
        except Exception as e:
            await self.patient_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def delete(self, request):
        try:
            await self.patient_service.begin_transaction()
            patient_id = int(request.path_params.get("id") or "0")
            data = Generator[PatientDeleteDto].generate(
                PatientDeleteDto, {"id": patient_id}
            )

            patient = Mapper[PatientDeleteDto, Patient].map(data, Patient)
            response = await self.patient_service.delete(patient)

            if not response.success:
                await self.patient_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.patient_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Patient deleted successfully",
            )
        except Exception as e:
            await self.patient_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def login(self, request):
        try:
            await self.patient_service.begin_transaction()
            payload = await request.json()
            data = Generator[PatientLoginDto].generate(PatientLoginDto, payload)

            token = data.token

            response = await self.patient_service.login(token)

            if not response.success:
                await self.patient_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            patient = Mapper[Patient, PatientLoginResponseDto].map(
                response.data, PatientLoginResponseDto, True
            )
            await self.patient_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patient,
            )
        except Exception as e:
            await self.patient_service.rollback_transaction()
            await self.logger.log(
                action="Login",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def get_patient_data(self, request):
        try:
            response = await self.patient_service.get_patient_data()

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            patient = Mapper[Patient, PatientResponseDto].map(
                response.data, PatientResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patient,
            )
        except Exception as e:
            await self.logger.log(
                action="GetPatientData",
                entity="Patient",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )
