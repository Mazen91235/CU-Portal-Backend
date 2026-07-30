from core.iControllers.iMaterialController import IMaterialController
from core.iServices.iMaterialService import IMaterialService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

from core.dtos.materialDtos import (
    MaterialUpdateDto,
)


class MaterialController(IMaterialController):
    def __init__(self, material_service: IMaterialService, logger: IBaseLogger):
        self.material_service = material_service
        self.logger = logger

    async def create(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = await request.json()
            response = await self.material_service.create(payload)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=response.data,
                message="Material created successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = await request.json()
            # Path param wins over any id the client sent in the body
            payload["id"] = request.path_params.get("material_id")
            data = Generator[MaterialUpdateDto].generate(MaterialUpdateDto, payload)
            response = await self.material_service.update(data)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
                message="Material updated successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_by_id(self, request):
        try:
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            response = await self.material_service.get_by_id(int(material_id))
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
            )
        except Exception as e:
            await self.logger.log(
                action="GetById",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_detail(self, request):
        try:
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            response = await self.material_service.get_detail(int(material_id))
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
            )
        except Exception as e:
            await self.logger.log(
                action="GetDetail",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def get_parents(self, request):
        try:
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            response = await self.material_service.get_parents(int(material_id))
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
            )
        except Exception as e:
            await self.logger.log(
                action="GetParents",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete_many(self, request):
        try:
            await self.material_service.begin_transaction()
            material_ids_param = request.path_params.get("material_ids", "")
            raw_ids = (
                material_ids_param.split(",")
                if "," in material_ids_param
                else [material_ids_param]
            )
            if not raw_ids or any(not id.isdigit() or int(id) < 1 for id in raw_ids):
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Invalid Request."
                )
            if any(raw_ids.count(id) > 1 for id in raw_ids):
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False, code=400, message="Invalid Request."
                )
            ids = [int(id) for id in raw_ids]

            response = await self.material_service.delete_many(ids)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Material(s) deleted successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="DeleteMany",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def copy_many(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = await request.json()
            response = await self.material_service.copy_many(payload)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                message="Material(s) copied successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="CopyMany",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def move_many(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = await request.json()
            response = await self.material_service.move_many(payload)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Material(s) moved successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="MoveMany",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def fetch_one_material_from_drive(self, request):
        try:
            payload = dict(request.query_params)
            response = await self.material_service.fetch_one_material_from_drive(
                payload
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response.data,
            )
        except Exception as e:
            await self.logger.log(
                action="FetchOneFromDrive",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def fetch_materials_from_drive(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = dict(request.query_params)
            response = await self.material_service.fetch_materials_from_drive(payload)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=response.data,
                message="Materials fetched and created successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="FetchFromDrive",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
