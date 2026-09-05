from core.iControllers.iEventController import IEventController
from core.iServices.iEventService import IEventService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# Entities & DTOs
from core.entities.event import Event
from core.dtos.eventDtos import (
    EventCreateDto,
    EventUpdateDto,
    EventResponseDto,
    EventSearchDto,
    EventDeleteDto,
)
from core.dtos.userEventDtos import (UserEventRegisterDto,UserEventUnregisterDto)
from core.models.queryModel import QueryModel


class EventController(IEventController):
    def __init__(self, event_service: IEventService, logger: IBaseLogger):
        self.event_service = event_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            event_id = request.path_params.get("event_id")
            if not event_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Event ID is required",
                )
            entity_search_dto = Generator[EventSearchDto].generate(
                EventSearchDto, {int(event_id)}
            )
            response = await self.event_service.find_one(
                entity_search_dto,
                [
                    "author",
                    "faculty",
                    "department",
                    "year",
                    "event_organizer",
                    "attendees"
                ],
            )
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            event = response.data
            if not event:
                await self.logger.log(
                    action="FindOne",
                    entity="Event",
                    level="info",
                    code=404,
                    message="Event not found",
                    source="EventController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Event not found",
                )
            event_mapped = Mapper[Event, EventResponseDto].map(event, EventResponseDto, True)
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=event_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Event",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventController",
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
                QueryModel[EventSearchDto],
            )
            entity_search_dto = Generator[EventSearchDto].generate_from_query(
                EventSearchDto, query
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

            response = await self.event_service.find(
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

            events = response.data

            if not events:
                await self.logger.log(
                    action="Find",
                    entity="Event",
                    level="info",
                    code=404,
                    message="Events not found",
                    source="EventController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Events not found",
                )

            events_mapped = Mapper[Event, EventResponseDto].map_list(
                events, EventResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=events_mapped,
            )
        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Event",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request):
        try:
            await self.event_service.begin_transaction()
            payload = await request.json()
            data = Generator[EventCreateDto].generate(EventCreateDto, payload)
            event = Mapper[EventCreateDto, Event].map(data, Event)
            response = await self.event_service.create(event)
            if not response.success:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            created_event = response.data
            if not created_event:
                await self.event_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to create event",
                    source="EventController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create event, Please try again later",
                )
                      
            event_mapped = Mapper[Event, EventResponseDto].map(
                            created_event, EventResponseDto, True
                        )
            await self.event_service.commit_transaction()
            return ResponseHandler.generate_response(
                            success=True,
                            code=201,
                            data=event_mapped,
                        )
        except Exception as e:
            await self.event_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Event",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request):
        try:
            await self.event_service.begin_transaction()
            event_id = request.path_params.get("event_id")
            if not event_id:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Event ID is required",
                )

            payload = await request.json()
            payload["id"] = int(event_id)
            data = Generator[EventUpdateDto].generate(EventUpdateDto, payload)
            event = Mapper[EventUpdateDto, Event].map(data, Event)
            response = await self.event_service.update(event)
            if not response.success:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )
            event = response.data
            if not event:
                await self.event_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to update event",
                    source="EventController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="An error occurred while processing the request, please try again later",
                )
            event_mapped = Mapper[Event, EventResponseDto].map(event, EventResponseDto, True)
            await self.event_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=event_mapped,
                message="Event updated successfully",
            )
        except Exception as e:
            await self.event_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Event",
                level="error",
                code=500,
                message=f"An error occurred while processing the request",
                details={"error": str(e)},
                source="EventController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
        
    async def delete(self, request):
        try:
            await self.event_service.begin_transaction()

            event_id = request.path_params.get("event_id")

            if not event_id:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Event ID is required",
                )

            data = Generator[EventDeleteDto].generate(
                EventDeleteDto, {"id": int(event_id)}
            )
            entity = Mapper[EventDeleteDto, Event].map(data, Event)

            response = await self.event_service.delete(entity)

            if not response.success:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.event_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Event deleted successfully",
            )

        except Exception as e:
            await self.event_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="EventController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    # Event Specific Functions
    async def register(self, request):
        try:
            await self.event_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserEventRegisterDto].generate(UserEventRegisterDto, payload)

            response = await self.event_service.register(data)
            if not response.success:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            await self.event_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True, code=200, message="Registered for event successfully", data=response.data
            )
        except Exception as e:
            await self.event_service.rollback_transaction()
            await self.logger.log(
                action="Register", entity="Event", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="EventController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")

    async def unregister(self, request):
        try:
            await self.event_service.begin_transaction()
            payload = await request.json()
            data = Generator[UserEventUnregisterDto].generate(UserEventUnregisterDto, payload)

            response = await self.event_service.unregister(data)
            if not response.success:
                await self.event_service.rollback_transaction()
                return ResponseHandler.generate_response(success=False, code=response.code, message=response.message)

            await self.event_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True, code=200, message="Unregistered from event successfully", data=response.data
            )
        except Exception as e:
            await self.event_service.rollback_transaction()
            await self.logger.log(
                action="Unregister", entity="Event", level="error", code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)}, source="EventController",
            )
            return ResponseHandler.generate_response(success=False, code=500, message="An error occurred while processing the request, please try again later")   