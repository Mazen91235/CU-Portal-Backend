from typing import cast
from core.iControllers.iPatientUserController import IPatientUserController
from core.iServices.iPatientUserService import IPatientUserService
from core.iServices.iHelperService import IHelperService
from core.iServices.iAIService import IAIService
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.patientUser import PatientUser
from core.dtos.patientUserDtos import (
    PatientUserResponseDto,
    PatientUserRegisterDto,
    PatientUserDeleteDto,
    PatientUserSearchDto,
)


class PatientUserController(IPatientUserController):
    def __init__(
        self,
        patient_user_service: IPatientUserService,
        helper_service: IHelperService,
        ai_service: IAIService,
        logger: IBaseLogger,
    ):
        self.patient_user_service = patient_user_service
        self.helper_service = helper_service
        self.ai_service = ai_service
        self.logger = logger

    async def find_one(self, request, file):
        img_path = ""
        try:
            payload = await request.json()
            data = Generator[PatientUserSearchDto].generate(
                PatientUserSearchDto, payload
            )

            image_validation_response = self.helper_service.validate_image_file(file)
            if not image_validation_response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=image_validation_response.code,
                    message=image_validation_response.message,
                )

            img_response = await self.helper_service.store_file(file)
            if not img_response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=img_response.code,
                    message=f"Failed to store image file - {img_response.message}",
                )
            img_path = cast(str, img_response.data)
            if not img_path:
                await self.logger.log(
                    action="FindOne",
                    entity="PatientUser",
                    level="error",
                    code=500,
                    message="Failed to retrieve stored image path for patient user identification",
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to retrieve stored image path for patient user identification",
                )
            img_vector = self.ai_service.generate_embeddings(img_path)
            if not img_vector:
                await self.helper_service.delete_file(img_path)
                await self.logger.log(
                    action="FindOne",
                    entity="PatientUser",
                    level="error",
                    code=400,
                    message="Failed to recognize faces in the provided image for patient user identification",
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Failed to recognize faces in the provided image for patient user identification",
                )
            data.img_vector = img_vector
            response = await self.patient_user_service.find_one(data, is_and=True)
            if not response.success:
                await self.helper_service.delete_file(img_path)
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            patient_user = response.data
            if not patient_user:
                await self.helper_service.delete_file(img_path)
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Patient user not found",
                )
            patient_user = Mapper[PatientUser, PatientUserResponseDto].map(
                patient_user, PatientUserResponseDto, True
            )
            await self.helper_service.delete_file(img_path)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=patient_user,
            )
        except Exception as e:
            if img_path:
                await self.helper_service.delete_file(img_path)
            await self.logger.log(
                action="FindOne",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientUserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def create(self, request, files):
        voice_path = ""
        img_path = ""
        try:
            await self.patient_user_service.begin_transaction()
            payload = await request.json()
            data = Generator[PatientUserRegisterDto].generate(
                PatientUserRegisterDto, payload
            )
            data.relation = int(payload.get("relation", 0))

            media_files_response = self.helper_service.resolve_voice_and_image_files(
                files
            )
            if not media_files_response.success:
                await self.patient_user_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="PatientUser",
                    level="error",
                    code=media_files_response.code,
                    message=media_files_response.message,
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=media_files_response.code,
                    message=media_files_response.message,
                )

            voice_file, image_file = cast(
                tuple,
                media_files_response.data,
            )

            voice_response = await self.helper_service.store_file(voice_file)
            if not voice_response.success:
                await self.patient_user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=voice_response.code,
                    message=f"Failed to store voice file - {voice_response.message}",
                )
            voice_path = cast(str, voice_response.data)
            if not voice_path:
                await self.patient_user_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="PatientUser",
                    level="error",
                    code=500,
                    message="Failed to retrieve stored voice path for patient user registration",
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to retrieve stored voice path for patient user registration",
                )
            img_response = await self.helper_service.store_file(image_file)
            if not img_response.success:
                await self.patient_user_service.rollback_transaction()
                await self.helper_service.delete_file(voice_path)
                return ResponseHandler.generate_response(
                    success=False,
                    code=img_response.code,
                    message=f"Failed to store image file - {img_response.message}",
                )
            img_path = cast(str, img_response.data)
            if not img_path:
                await self.patient_user_service.rollback_transaction()
                await self.helper_service.delete_file(voice_path)
                await self.logger.log(
                    action="Create",
                    entity="PatientUser",
                    level="error",
                    code=500,
                    message="Failed to retrieve stored image path for patient user registration",
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to retrieve stored image path for patient user registration",
                )
            data.voice = voice_path
            data.img = img_path
            img_vector = self.ai_service.generate_embeddings(img_path)
            if not img_vector:
                await self.patient_user_service.rollback_transaction()
                await self.helper_service.delete_file(voice_path)
                await self.helper_service.delete_file(img_path)
                await self.logger.log(
                    action="Create",
                    entity="PatientUser",
                    level="error",
                    code=400,
                    message="Failed to recognize faces in the provided image for patient user registration",
                    source="PatientUserController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Failed to recognize faces in the provided image for patient user registration",
                )
            data.img_vector = img_vector
            patient_user_entity = Mapper[PatientUserRegisterDto, PatientUser].map(
                data, PatientUser
            )
            response = await self.patient_user_service.create(patient_user_entity)
            if not response.success:
                await self.patient_user_service.rollback_transaction()
                await self.helper_service.delete_file(voice_path)
                await self.helper_service.delete_file(img_path)
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            patient_user = response.data
            patient_user = Mapper[PatientUser, PatientUserResponseDto].map(
                patient_user, PatientUserResponseDto, True
            )
            await self.patient_user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=patient_user,
            )
        except Exception as e:
            await self.patient_user_service.rollback_transaction()
            if voice_path:
                await self.helper_service.delete_file(voice_path)
            if img_path:
                await self.helper_service.delete_file(img_path)
            await self.logger.log(
                action="Create",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientUserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )

    async def delete(self, request):
        try:
            await self.patient_user_service.begin_transaction()
            patient_user_id = int(request.path_params.get("id") or "0")
            data = Generator[PatientUserDeleteDto].generate(
                PatientUserDeleteDto, {"id": patient_user_id}
            )
            patient_user = cast(
                PatientUser,
                Mapper[PatientUserDeleteDto, PatientUser].map(data, PatientUser),
            )
            response = await self.patient_user_service.delete(patient_user)

            if not response.success:
                await self.patient_user_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.helper_service.delete_file(patient_user.voice)
            await self.helper_service.delete_file(patient_user.img)
            await self.patient_user_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Patient user deleted successfully",
            )
        except Exception as e:
            await self.patient_user_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="PatientUser",
                level="error",
                code=500,
                message=f"An error occurred while processing the request - {str(e)}",
                source="PatientUserController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request",
            )
