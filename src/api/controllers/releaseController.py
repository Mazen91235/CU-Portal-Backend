from typing import cast
from core.iControllers.iReleaseController import IReleaseController
from core.iServices.iReleaseService import IReleaseService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.release import Release
from core.dtos.releaseDtos import (
    ReleaseCreateDto,
    ReleaseResponseDto,
    ReleaseUpdateDto,
    ReleaseSearchDto,
    ReleaseDeleteDto,
)


class ReleaseController(IReleaseController):
    def __init__(self, release_service: IReleaseService, logger: IBaseLogger):
        self.release_service = release_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[ReleaseSearchDto].generate(
                ReleaseSearchDto, {"id": id}
            )
            response = await self.release_service.find_one(
                entity_search_dto,
                ["release_version", "release_items"],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            release = response.data
            if not release:
                await self.logger.log(
                    action="FindOne",
                    entity="Release",
                    level="info",
                    code=404,
                    message="Release not found",
                    source="ReleaseController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Release not found",
                )
            release_mapped = Mapper[Release, ReleaseResponseDto].map(
                release, ReleaseResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=release_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ReleaseController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[ReleaseSearchDto].generate_from_query(
                ReleaseSearchDto, query
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

            response = await self.release_service.find(
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

            releases = response.data
            releases_mapped = Mapper[Release, ReleaseResponseDto].map_list(
                releases or [], ReleaseResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=releases_mapped,
                next_page=response.next_page,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ReleaseController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.release_service.begin_transaction()
            response = await self.release_service.create(data)
            if not response.success:
                await self.release_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_release = response.data
            if not created_release:
                await self.release_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Release",
                    level="error",
                    code=500,
                    message="Failed to create release",
                    source="ReleaseController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create release, Please try again later",
                )
            release_mapped = Mapper[Release, ReleaseResponseDto].map(
                created_release, ReleaseResponseDto, True
            )
            await self.release_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=release_mapped,
                message="Release created successfully",
            )
        except Exception as e:
            await self.release_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ReleaseController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.release_service.begin_transaction()
            response = await self.release_service.update(data)
            if not response.success:
                await self.release_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_release = response.data
            if not updated_release:
                await self.release_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Release",
                    level="error",
                    code=500,
                    message="Failed to update release",
                    source="ReleaseController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update release, Please try again later",
                )
            release_mapped = Mapper[Release, ReleaseResponseDto].map(
                updated_release, ReleaseResponseDto, True
            )
            await self.release_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=release_mapped,
                message="Release updated successfully",
            )
        except Exception as e:
            await self.release_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ReleaseController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.release_service.begin_transaction()
            data = Generator[ReleaseDeleteDto].generate(ReleaseDeleteDto, {"id": id})
            entity = Mapper[ReleaseDeleteDto, Release].map(data, Release)
            response = await self.release_service.delete(entity)
            if not response.success:
                await self.release_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.release_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Release deleted successfully",
            )
        except Exception as e:
            await self.release_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="ReleaseController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
