from fastapi import Response
from starlette.requests import Request

from core.iControllers.iMaterialController import IMaterialController
from core.iServices.iMaterialService import IMaterialService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.mapper import Mapper
from core.utils.parser import Parser

# Entities & DTOs
from core.entities.material import Material
from core.dtos.materialDtos import (
    MaterialCreateDto,
    MaterialResponseDto,
    MaterialUpdateDto,
    MaterialsDeleteDto,
    MaterialSearchDto,
    MaterialsCopyOrMoveDto,
    MaterialsFetchFromDriveDto,
)
from core.models.queryModel import QueryModel


class MaterialController(IMaterialController):
    def __init__(self, material_service: IMaterialService, logger: IBaseLogger):
        self.material_service = material_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            entity_search_dto = Generator[MaterialSearchDto].generate(
                MaterialSearchDto, {"id": material_id}
            )
            response = await self.material_service.find_one(
                entity_search_dto,
                [
                    "author",
                ],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            material = response.data
            if not material:
                await self.logger.log(
                    action="FindOne",
                    entity="Material",
                    level="info",
                    code=404,
                    message="Material not found",
                    source="MaterialController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Material not found",
                )
            material_mapped = Mapper[Material, MaterialResponseDto].map(
                material, MaterialResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=material_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[MaterialSearchDto],
            )
            entity_search_dto = Generator[MaterialSearchDto].generate_from_query(
                MaterialSearchDto, query
            )
            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.material_service.find(
                entity_search_dto,
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

            materials = response.data

            if not materials:
                await self.logger.log(
                    action="Find",
                    entity="Material",
                    level="info",
                    code=404,
                    message="Materials not found",
                    source="MaterialController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Materials not found",
                )

            materials_mapped = Mapper[Material, MaterialResponseDto].map_list(
                materials, MaterialResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=materials_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.material_service.begin_transaction()
            payload = await request.json()
            payload["details"] = {
                "description": payload.get("description"),
            }
            data = Generator[MaterialCreateDto].generate(MaterialCreateDto, payload)
            material = Mapper[MaterialCreateDto, Material].map(data, Material)
            response = await self.material_service.create(material)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            created_material = response.data
            if not created_material:
                await self.material_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=500,
                    message="Failed to create material",
                    source="MaterialController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            created_material_mapped = Mapper[Material, MaterialResponseDto].map(
                created_material, MaterialResponseDto, True
            )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=created_material_mapped,
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
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
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            payload = await request.json()
            payload["id"] = int(material_id)
            payload["details"] = {
                "description": payload.get("description"),
            }
            data = Generator[MaterialUpdateDto].generate(MaterialUpdateDto, payload)
            material = Mapper[MaterialUpdateDto, Material].map(data, Material)
            response = await self.material_service.update(material)
            if not response.success:
                await self.material_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            updated_material = response.data
            if not updated_material:
                await self.material_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=500,
                    message="Failed to update material",
                    source="MaterialController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            updated_material_mapped = Mapper[Material, MaterialResponseDto].map(
                updated_material, MaterialResponseDto, True
            )
            await self.material_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=updated_material_mapped,
                message="Material updated successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
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
            material_ids = request.path_params.get("material_ids")
            if not material_ids:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material IDs are required",
                )
            data = Generator[MaterialsDeleteDto].generate(
                MaterialsDeleteDto, {"material_ids": material_ids.split(",").map(int)}
            )
            response = await self.material_service.delete_many(data)
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
                message="Materials deleted successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="DeleteMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # Material Specific Functions
    async def get_parents(self, request):
        try:
            material_id = request.path_params.get("material_id")
            if not material_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Material ID is required",
                )
            response = await self.material_service.get_parents(material_id)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            parents = response.data
            parents_mapped = Mapper[Material, MaterialResponseDto].map_list(
                parents or [], MaterialResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=parents_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="GetParents",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
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
            data = Generator[MaterialsCopyOrMoveDto].generate(
                MaterialsCopyOrMoveDto, payload
            )
            response = await self.material_service.copy_many(data)
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
                message="Materials copied successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="CopyMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
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
            data = Generator[MaterialsCopyOrMoveDto].generate(
                MaterialsCopyOrMoveDto, payload
            )
            response = await self.material_service.move_many(data)
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
                message="Materials moved successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="MoveMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
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
            payload = await request.json()
            data = Generator[MaterialsFetchFromDriveDto].generate(
                MaterialsFetchFromDriveDto, payload
            )
            response = await self.material_service.fetch_materials_from_drive(data)
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
                message="Materials fetched from drive successfully",
            )
        except Exception as e:
            await self.material_service.rollback_transaction()
            await self.logger.log(
                action="FetchMaterialsFromDrive",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="MaterialController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
