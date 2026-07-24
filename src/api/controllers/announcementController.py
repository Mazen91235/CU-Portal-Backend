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
)
from core.models.queryModel import QueryModel


class AnnouncementController(IAnnouncementController):
    def __init__(self, announcement_service: IAnnouncementService, logger: IBaseLogger):
        self.announcement_service = announcement_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            id_val = request.path_params.get("announcement_id")
            if not id_val:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Announcement ID is required",
                )
                
            if not str(id_val).isdigit():
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Invalid Announcement ID format",
                )
            
            entity_search_dto = Generator[AnnouncementSearchDto].generate(
                AnnouncementSearchDto, {"id": int(id_val)}
            )
            
            response = await self.announcement_service.find_one(
                entity_search_dto,
                ["author", "subject", "faculty", "department", "year"],
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

            # Security Scope Check in Controller
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user and "View Announcements" not in permissions:
                if (announcement.faculty_id != current_user.faculty_id or 
                    announcement.department_id != current_user.department_id or 
                    announcement.year_id != current_user.year_id):
                    return ResponseHandler.generate_response(
                        success=False,
                        code=403,
                        message="You are not authorized to view this announcement"
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
            
            # Security Scope Check in Controller
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user:
                if "View Announcements" not in permissions:
                    entity_search_dto.faculty_id = current_user.faculty_id
                    entity_search_dto.department_id = current_user.department_id
                    entity_search_dto.year_id = current_user.year_id
                else:
                    if "Access All Faculties" not in permissions:
                        entity_search_dto.faculty_id = current_user.faculty_id
                    if "Access All Departments" not in permissions:
                        entity_search_dto.department_id = current_user.department_id
                    if "Access All Years" not in permissions:
                        entity_search_dto.year_id = current_user.year_id
            
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
            
            try:
                payload = await request.json()
            except json.JSONDecodeError:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Invalid or missing JSON payload",
                )

            data = Generator[AnnouncementCreateDto].generate(AnnouncementCreateDto, payload)
            response = await self.announcement_service.create(data)
            
            if not response.success:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            
            response_data = response.data
            if not response_data:
                await self.announcement_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to retrieve announcement data after creation",
                    source="AnnouncementController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )

            await self.announcement_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=response_data, 
                message="Announcement created successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Create",
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

    async def update(self, request):
        try:
            await self.announcement_service.begin_transaction()
            id_val = request.path_params.get("announcement_id")
            
            if not id_val or not str(id_val).isdigit():
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Valid Announcement ID is required",
                )
            
            try:
                payload = await request.json()
            except json.JSONDecodeError:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Invalid or missing JSON payload",
                )
                
            data = Generator[AnnouncementUpdateDto].generate(AnnouncementUpdateDto, payload)
            response = await self.announcement_service.update(int(id_val), data)
            
            if not response.success:
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
                
            response_data = response.data
            if not response_data:
                await self.announcement_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Announcement",
                    level="error",
                    code=500,
                    message="Failed to update announcement",
                    source="AnnouncementController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )

            await self.announcement_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=response_data,
                message="Announcement updated successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Update",
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

    async def delete(self, request):
        try:
            await self.announcement_service.begin_transaction()
            id_val = request.path_params.get("announcement_id")
            
            if not id_val or not str(id_val).isdigit():
                await self.announcement_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Valid Announcement ID is required",
                )
                
            response = await self.announcement_service.delete(int(id_val))
            
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
                data=True,
                message="Announcement deleted successfully",
            )
        except Exception as e:
            await self.announcement_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
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

    # Additional Query Functions
    async def search(self, request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[AnnouncementSearchDto],
            )
            entity_search_dto = Generator[AnnouncementSearchDto].generate_from_query(
                AnnouncementSearchDto, query
            )
            
            # Security Scope Check in Controller
            current_user = getattr(request.state, 'current_user', None)
            permissions = getattr(request.state, 'permissions', [])
            
            if current_user:
                if "View Announcements" not in permissions:
                    entity_search_dto.faculty_id = current_user.faculty_id
                    entity_search_dto.department_id = current_user.department_id
                    entity_search_dto.year_id = current_user.year_id
                else:
                    if "Access All Faculties" not in permissions:
                        entity_search_dto.faculty_id = current_user.faculty_id
                    if "Access All Departments" not in permissions:
                        entity_search_dto.department_id = current_user.department_id
                    if "Access All Years" not in permissions:
                        entity_search_dto.year_id = current_user.year_id
            
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
                    action="Search",
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
                action="Search",
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