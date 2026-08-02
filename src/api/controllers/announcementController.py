from core.iControllers.iAnnouncementController import IAnnouncementController
from core.iServices.iAnnouncementService import IAnnouncementService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser
import json

# Entities & DTOs
from core.entities.announcement import Announcement
from core.dtos.announcementDtos import (
    AnnouncementCreateDto,
    AnnouncementUpdateDto,
    AnnouncementResponseDto,
    AnnouncementSearchDto,
    AnnouncementDeleteDto,
)
from core.models.queryModel import QueryModel


class AnnouncementController(IAnnouncementController):
    def __init__(self, announcement_service: IAnnouncementService, logger: IBaseLogger):
        self.announcement_service = announcement_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            announcement_id = request.path_params.get("announcement_id")
            if not announcement_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Announcement ID is required",
                )
                
            entity_search_dto = Generator[AnnouncementSearchDto].generate(
                AnnouncementSearchDto, {"id": announcement_id}
            )
            
            response = await self.announcement_service.find_one(
                entity_search_dto,
                [
                    "author",
                    "subject",
                    "faculty",
                    "department",
                    "year",
                ],
            )
            
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
                
            announcement = response.data
            if not announcement:
                await self.logger.log(
                    action="FindOne",
                    entity="Announcement",
                    level="info",
                    code=404,
                    message="Announcement not found",
                    source="AnnouncementController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Announcement not found",
                )
            announcement_mapped = Mapper[Announcement, AnnouncementResponseDto].map(
                announcement, AnnouncementResponseDto, True
            )
            
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=announcement_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Announcement",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="AnnouncementController",
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
                QueryModel[AnnouncementSearchDto],
            )
            entity_search_dto = Generator[AnnouncementSearchDto].generate_from_query(
                AnnouncementSearchDto, query
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

            response = await self.announcement_service.find(
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

            announcements = response.data
            if not announcements:
                await self.logger.log(
                    action="Find",
                    entity="Announcement",
                    level="info",
                    code=404,
                    message="Announcements not found",
                    source="AnnouncementController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Announcements not found",
                )

            announcements_mapped = Mapper[Announcement, AnnouncementResponseDto].map_list(
                announcements, AnnouncementResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=announcements_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Announcement",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="AnnouncementController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.announcement_service.begin_transaction()
            payload = await request.json()
            
            data = Generator[AnnouncementCreateDto].generate(AnnouncementCreateDto, payload)
            announcement = Mapper[AnnouncementCreateDto, Announcement].map(data, Announcement)
            
            response = await self.announcement_service.create(announcement)
            
            if not response.success:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_announcement = response.data
            announcement_mapped = Mapper[Announcement, AnnouncementResponseDto].map(
                created_announcement, AnnouncementResponseDto, True
            )
            
            await self.announcement_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=announcement_mapped,
                message="Announcement created successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="AnnouncementController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.announcement_service.begin_transaction()
            announcement_id = request.path_params.get("announcement_id")
            
            if not announcement_id:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Announcement ID is required",
                )

            payload = await request.json()
            
            data = Generator[AnnouncementUpdateDto].generate(AnnouncementUpdateDto, payload)
            announcement = Mapper[AnnouncementUpdateDto, Announcement].map(data, Announcement)
            announcement.id = int(announcement_id)

            response = await self.announcement_service.update(announcement)
            
            if not response.success:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_announcement = response.data
            announcement_mapped = Mapper[Announcement, AnnouncementResponseDto].map(
                updated_announcement, AnnouncementResponseDto, True
            )
            
            await self.announcement_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=announcement_mapped,
                message="Announcement updated successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="AnnouncementController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request):
        try:
            await self.announcement_service.begin_transaction()
            announcement_id = request.path_params.get("announcement_id")
            
            if not announcement_id:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Announcement ID is required",
                )

            data = Generator[AnnouncementDeleteDto].generate(
                AnnouncementDeleteDto, {"id": int(announcement_id)}
            )
            entity = Mapper[AnnouncementDeleteDto, Announcement].map(data, Announcement)
            
            response = await self.announcement_service.delete(entity)
            
            if not response.success:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.announcement_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Announcement deleted successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Announcement",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="AnnouncementController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )