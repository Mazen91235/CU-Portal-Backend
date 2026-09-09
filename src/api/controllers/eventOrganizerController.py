from typing import cast
from core.iControllers.iEventOrganizerController import IEventOrganizerController
from core.iServices.iEventOrganizerService import IEventOrganizerService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.eventOrganizerDtos import (
    EventOrganizerCreateDto,
    EventOrganizerResponseDto,
    EventOrganizerUpdateDto,
    EventOrganizerSearchDto,
    EventOrganizerDeleteDto,
)


class EventOrganizerController(IEventOrganizerController):
    def __init__(
        self, event_organizer_service: IEventOrganizerService, logger: IBaseLogger
    ):
        self.event_organizer_service = event_organizer_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[EventOrganizerSearchDto].generate(
                EventOrganizerSearchDto, {"id": id}
            )

            response = await self.event_organizer_service.find_one(
                entity_search_dto,
                [
                    "events.user_events.user",
                    "logo",
                    "attachments",
                ],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            event_organizer = response.data
            if not event_organizer:
                await self.logger.log(
                    action="FindOne",
                    entity="EventOrganizer",
                    level="info",
                    code=404,
                    message="Event Organizer not found",
                    source="EventOrganizerController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Event Organizer not found",
                )
            event_organizer_mapped = Mapper[
                EventOrganizer, EventOrganizerResponseDto
            ].map(event_organizer, EventOrganizerResponseDto, True)

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=event_organizer_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="EventOrganizer",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventOrganizerController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[EventOrganizerSearchDto].generate_from_query(
                EventOrganizerSearchDto, query
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

            response = await self.event_organizer_service.find(
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

            event_organizers = response.data
            event_organizers_mapped = Mapper[
                EventOrganizer, EventOrganizerResponseDto
            ].map_list(event_organizers or [], EventOrganizerResponseDto, True)

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=event_organizers_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="EventOrganizer",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventOrganizerController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.event_organizer_service.begin_transaction()
            event_organizer = Mapper[EventOrganizerCreateDto, EventOrganizer].map(
                data, EventOrganizer
            )

            response = await self.event_organizer_service.create(event_organizer)

            if not response.success:
                await self.event_organizer_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_event_organizer = response.data
            if not created_event_organizer:
                await self.event_organizer_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to create event organizer",
                    source="EventOrganizerController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create event organizer",
                )
            event_organizer_mapped = Mapper[
                EventOrganizer, EventOrganizerResponseDto
            ].map(created_event_organizer, EventOrganizerResponseDto, True)

            await self.event_organizer_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=event_organizer_mapped,
                message="Event Organizer created successfully",
            )
        except Exception as e:
            await self.event_organizer_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="EventOrganizerController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.event_organizer_service.begin_transaction()
            event_organizer = cast(
                EventOrganizer,
                Mapper[EventOrganizerUpdateDto, EventOrganizer].map(
                    data, EventOrganizer
                ),
            )
            event_organizer.id = id

            response = await self.event_organizer_service.update(event_organizer)

            if not response.success:
                await self.event_organizer_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_event_organizer = response.data
            if not updated_event_organizer:
                await self.event_organizer_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to update event organizer",
                    source="EventOrganizerController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update event organizer",
                )
            event_organizer_mapped = Mapper[
                EventOrganizer, EventOrganizerResponseDto
            ].map(updated_event_organizer, EventOrganizerResponseDto, True)

            await self.event_organizer_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=event_organizer_mapped,
                message="Event Organizer updated successfully",
            )
        except Exception as e:
            await self.event_organizer_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="EventOrganizerController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.event_organizer_service.begin_transaction()
            data = Generator[EventOrganizerDeleteDto].generate(
                EventOrganizerDeleteDto, {"id": id}
            )
            entity = Mapper[EventOrganizerDeleteDto, EventOrganizer].map(
                data, EventOrganizer
            )

            response = await self.event_organizer_service.delete(entity)

            if not response.success:
                await self.event_organizer_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.event_organizer_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Event Organizer deleted successfully",
            )
        except Exception as e:
            await self.event_organizer_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="EventOrganizerController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
