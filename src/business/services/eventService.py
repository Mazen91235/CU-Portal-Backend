from sqlalchemy import func, and_
from core.iServices.iEventService import IEventService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.event import Event
from core.entities.userEvent import UserEvent
from core.entities.eventOrganizer import EventOrganizer
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator


class EventService(IEventService):
    def __init__(
        self,
        event_repository: IBaseRepository[Event],
        user_event_repository: IBaseRepository[UserEvent],
        event_organizer_repository: IBaseRepository[EventOrganizer],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.event_repository = event_repository
        self.user_event_repository = user_event_repository
        self.event_organizer_repository = event_organizer_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.event_repository.begin_transaction()

    async def commit_transaction(self):
        await self.event_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.event_repository.rollback_transaction()

    # CRUD Functions
    async def find_one(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Event, data, ["title", "location"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Event", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Event", order_by
            )
            result = await self.event_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while finding event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding event",
            )

    async def find(
        self,
        data=None,
        includes=None,
        selects=None,
        is_and=False,
        starts_with=True,
        is_exact=True,
        order_by=None,
        descending=False,
        page=1,
        limit=50,
    ):
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Event, data, ["title", "location"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Event", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Event", order_by
            )
            result = await self.event_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
                page,
                limit,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            return BaseResponseDto(success=True, data=result.data)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while finding events",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding events",
            )

    async def create(self, data):
        try:
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to create event for the specified criteria.",
                )
            event_organizer_response = await self.event_organizer_repository.find_one(
                EventOrganizer.id == data.event_organizer_id
            )
            if not event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=event_organizer_response.code,
                    data=None,
                    message=event_organizer_response.message,
                )
            if not event_organizer_response.data:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event Organizer not found for event creation.",
                    details={"event_organizer_id": data.event_organizer_id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event Organizer not found for event creation.",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Creation.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user for Event Creation.",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Creation.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user found for Event Creation.",
                )
            data.author_id = logged_in_user.id
            if data.location_type == "Online" and not Validator.is_valid_external_url(
                data.location
            ):
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="Invalid online event location URL provided.",
                    details={"location": data.location},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="Invalid online event location URL provided.",
                )
            if data.end_date and data.end_date <= data.start_date:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="End date must be after start date for event creation.",
                    details={
                        "start_date": str(data.start_date),
                        "end_date": str(data.end_date),
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="End date must be after start date for event creation.",
                )
            existing_event_response = await self.event_repository.find_one(
                and_(
                    Event.faculty_id.is_not_distinct_from(data.faculty_id),
                    Event.department_id.is_not_distinct_from(data.department_id),
                    Event.year_id.is_not_distinct_from(data.year_id),
                    Event.event_organizer_id == data.event_organizer_id,
                    func.lower(Event.title) == func.lower(data.title),
                )
            )
            if not existing_event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_response.code,
                    data=None,
                    message=existing_event_response.message,
                )
            existing_event = existing_event_response.data
            if existing_event:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="An event with the same title already exists for the specified faculty, department, and year.",
                    details={
                        "title": data.title,
                        "faculty_id": data.faculty_id,
                        "department_id": data.department_id,
                        "year_id": data.year_id,
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="An event with the same title already exists for the specified details.",
                )
            data.details = data.details or {}
            url = data.details.get("url")
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("url", None)
            data.details.pop("urls", None)
            data.details.pop("links", None)
            if not url:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="No valid Logo provided for the event.",
                    details={"details": data.details},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No valid Logo provided for the event.",
                )
            create_response = await self.event_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_event = create_response.data
            if not created_event:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to create event.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event",
                )
            attachment_response = await self.helper_service.create_attachment(
                is_file=True,
                url=url,
                author_id=logged_in_user.id,
                source_name="event_logo_id",
                source_id=created_event.id,
            )
            if not attachment_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=attachment_response.code or 500,
                    message="Failed to create attachment for event logo.",
                    details={"url": url},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=attachment_response.code or 500,
                    data=None,
                    message=attachment_response.message,
                )
            attachment = attachment_response.data
            if not attachment:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to create attachment for event logo without a specific error.",
                    details={"url": url},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event",
                )
            created_event.logo_id = attachment.id
            update_response = await self.event_repository.update(
                created_event, ["logo_id"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_event = update_response.data
            if not updated_event:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to update event with logo_id.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event",
                )
            for url in urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="event_id",
                    source_id=updated_event.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event without a specific error.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating event",
                    )
            for link in links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="event_id",
                    source_id=updated_event.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event.",
                        details={"url": link_url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event without a specific error.",
                        details={"url": link_url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating event",
                    )
            share_link = f"/user/events/{updated_event.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.EVENT,
                updated_event.id,
                f"New Event '{updated_event.title}' has been posted.",
                share_link,
                faculty_id=updated_event.faculty_id,
                department_id=updated_event.department_id,
                year_id=updated_event.year_id,
            )
            await self.logger.log(
                action="Create",
                entity="Event",
                level="info",
                code=201,
                message="Event created successfully",
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=updated_event,
                message="Event created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while creating event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating event",
            )

    async def update(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, ["logo", "attachments"]
            )
            target_event_response = await self.event_repository.find_one(
                Event.id == data.id, dynamic_includes
            )
            if not target_event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_event_response.code,
                    data=None,
                    message=target_event_response.message,
                )
            target_event = target_event_response.data
            if not target_event:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for update",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=target_event.faculty_id,
                    department_id=target_event.department_id,
                    year_id=target_event.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update event for the specified criteria.",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=data.faculty_id,
                    department_id=data.department_id,
                    year_id=data.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to update event for the specified criteria.",
                )
            event_organizer_response = await self.event_organizer_repository.find_one(
                EventOrganizer.id == data.event_organizer_id
            )
            if not event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=event_organizer_response.code,
                    data=None,
                    message=event_organizer_response.message,
                )
            event_organizer = event_organizer_response.data
            if not event_organizer:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event Organizer not found for event update.",
                    details={"event_organizer_id": data.event_organizer_id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event Organizer not found for event update.",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Update.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user for Event Update.",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Update.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user found for Event Update.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Event Update.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user permissions for Event Update.",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Event Update.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user permissions found for Event Update.",
                )
            if (
                logged_in_user.id != target_event.author_id
                and "Manage All Events" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=403,
                    message="User does not have permission to update this event.",
                    details={
                        "user_id": logged_in_user.id,
                        "event_id": target_event.id,
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="User does not have permission to update this event.",
                )
            data.author_id = logged_in_user.id
            if data.end_date and data.end_date <= data.start_date:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="End date must be after start date for event update.",
                    details={
                        "start_date": str(data.start_date),
                        "end_date": str(data.end_date),
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="End date must be after start date for event update.",
                )
            if data.location_type == "Online" and not Validator.is_valid_external_url(
                data.location
            ):
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="Invalid online event location URL provided for update.",
                    details={"location": data.location},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid online event location URL provided for update.",
                )
            existing_event_response = await self.event_repository.find_one(
                and_(
                    Event.faculty_id.is_not_distinct_from(data.faculty_id),
                    Event.department_id.is_not_distinct_from(data.department_id),
                    Event.year_id.is_not_distinct_from(data.year_id),
                    Event.event_organizer_id == data.event_organizer_id,
                    func.lower(Event.title) == func.lower(data.title),
                )
            )
            if not existing_event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_response.code,
                    data=None,
                    message=existing_event_response.message,
                )
            existing_event = existing_event_response.data
            if existing_event and existing_event.id != target_event.id:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="An event with the same title already exists for the specified faculty, department, and year.",
                    details={
                        "title": data.title,
                        "faculty_id": data.faculty_id,
                        "department_id": data.department_id,
                        "year_id": data.year_id,
                        "event_organizer_id": data.event_organizer_id,
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="An event with the same title already exists for the specified details.",
                )
            old_logo = target_event.logo
            old_attachments = target_event.attachments or []
            data.details = data.details or {}
            url = data.details.get("url")
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("url", None)
            data.details.pop("urls", None)
            data.details.pop("links", None)
            target_event.title = data.title
            target_event.start_date = data.start_date
            target_event.end_date = data.end_date
            target_event.price = data.price
            target_event.location_type = data.location_type
            target_event.location = data.location
            target_event.details = data.details
            target_event.faculty_id = data.faculty_id
            target_event.department_id = data.department_id
            target_event.year_id = data.year_id
            target_event.author_id = data.author_id
            target_event.event_organizer_id = data.event_organizer_id
            update_response = await self.event_repository.update(target_event)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_event = update_response.data
            if not updated_event:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to update event.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating event",
                )
            if not url:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="No valid Logo provided for the event update.",
                    details={"details": data.details},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No valid Logo provided for the event update.",
                )
            if url != old_logo.url:
                await self.helper_service.delete_attachment(attachment=old_logo)
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="event_logo_id",
                    source_id=updated_event.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event logo during update.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event logo during update without a specific error.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event",
                    )
                updated_event.logo_id = attachment.id
                update_response = await self.event_repository.update(
                    updated_event, ["logo_id"]
                )
                if not update_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_response.code,
                        data=None,
                        message=update_response.message,
                    )
                updated_event = update_response.data
                if not updated_event:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to update event with new logo_id.",
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event",
                    )
            new_urls = [
                u
                for u in urls
                if u not in [a.url for a in old_attachments if a.is_file]
            ]
            new_links = [
                l
                for l in links
                if l.get("url", "")
                not in [a.url for a in old_attachments if not a.is_file]
            ]
            to_be_removed_attachments = []
            for attachment in old_attachments:
                if attachment.is_file and attachment.url not in urls:
                    to_be_removed_attachments.append(attachment)
                elif not attachment.is_file and not any(
                    link.get("url", "") == attachment.url for link in links
                ):
                    to_be_removed_attachments.append(attachment)
            for attachment in to_be_removed_attachments:
                await self.helper_service.delete_attachment(attachment=attachment)
            for url in new_urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="event_id",
                    source_id=updated_event.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event without a specific error.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event",
                    )
            for link in new_links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="event_id",
                    source_id=updated_event.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event.",
                        details={"url": link_url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code or 500,
                        data=None,
                        message=attachment_response.message,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event without a specific error.",
                        details={"url": link_url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event",
                    )
            share_link = f"/user/events/{updated_event.id}"
            await self.helper_service.send_notification(
                Notification.NotificationType.EVENT,
                updated_event.id,
                f"Event '{updated_event.title}' has been updated.",
                share_link,
                faculty_id=updated_event.faculty_id,
                department_id=updated_event.department_id,
                year_id=updated_event.year_id,
            )
            await self.logger.log(
                action="Update",
                entity="Event",
                level="info",
                code=200,
                message="Event updated successfully",
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_event,
                message="Event updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while updating event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating event",
            )

    async def delete(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, ["logo", "attachments"]
            )
            target_event_response = await self.event_repository.find_one(
                Event.id == data.id, dynamic_includes
            )
            if not target_event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_event_response.code,
                    data=None,
                    message=target_event_response.message,
                )
            target_event = target_event_response.data
            if not target_event:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for deletion",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    faculty_id=target_event.faculty_id,
                    department_id=target_event.department_id,
                    year_id=target_event.year_id,
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="warning",
                    code=403,
                    message=f"Failed to verify restricted access for user: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    message="User does not have access to delete event for the specified criteria.",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Deletion.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user for Event Deletion.",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Deletion.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user found for Event Deletion.",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user permissions for Event Deletion.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user permissions for Event Deletion.",
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user permissions found for Event Deletion.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user permissions found for Event Deletion.",
                )
            if (
                logged_in_user.id != target_event.author_id
                and "Manage All Events" not in logged_in_user_permissions
            ):
                await self.logger.log(
                    action="Delete",
                    entity="Event",
                    level="warning",
                    code=403,
                    message="User does not have permission to delete this event.",
                    details={
                        "user_id": logged_in_user.id,
                        "event_id": target_event.id,
                    },
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="User does not have permission to delete this event.",
                )
            to_be_removed_attachments = [target_event.logo] + (
                target_event.attachments or []
            )
            delete_response = await self.event_repository.delete(target_event)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            for attachment in to_be_removed_attachments:
                await self.helper_service.delete_attachment(attachment=attachment)
            await self.logger.log(
                action="Delete",
                entity="Event",
                level="info",
                code=200,
                message="Event deleted successfully",
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Event deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while deleting event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting event",
            )

    async def register(self, event_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Register.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Register.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in user found for Event Register.",
                )
            event_response = await self.event_repository.find_one(Event.id == event_id)
            if not event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=event_response.code,
                    data=None,
                    message=event_response.message,
                )
            event = event_response.data
            if not event:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for registration",
                    details={"event_id": event_id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Event not found"
                )
            existing_registration_response = await self.user_event_repository.find_one(
                and_(
                    UserEvent.user_id == logged_in_user.id,
                    UserEvent.event_id == event.id,
                )
            )
            if not existing_registration_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_registration_response.code,
                    data=None,
                    message=existing_registration_response.message,
                )
            existing_registration = existing_registration_response.data
            if existing_registration:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="User is already registered for this event.",
                    details={"user_id": logged_in_user.id, "event_id": event.id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="You are already registered for this event",
                )
            registration = UserEvent(user_id=logged_in_user.id, event_id=event.id)
            create_response = await self.user_event_repository.create(registration)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_registration = create_response.data
            if not created_registration:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to register user for event without a specific error.",
                    details={"user_id": logged_in_user.id, "event_id": event.id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while registering for event",
                )
            await self.logger.log(
                action="Register",
                entity="Event",
                level="info",
                code=200,
                message="User registered for event successfully.",
                details={
                    "user_id": created_registration.user_id,
                    "event_id": created_registration.event_id,
                },
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Registered for event successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Register",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while registering for event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while registering for event",
            )

    async def unregister(self, event_id):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Unregister.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Unegister.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in user found for Event Unregister.",
                )
            event_response = await self.event_repository.find_one(Event.id == event_id)
            if not event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=event_response.code,
                    data=None,
                    message=event_response.message,
                )
            event = event_response.data
            if not event:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for unregistration",
                    details={"event_id": event_id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Event not found"
                )
            existing_registration_response = await self.user_event_repository.find_one(
                and_(
                    UserEvent.user_id == logged_in_user.id,
                    UserEvent.event_id == event.id,
                )
            )
            if not existing_registration_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_registration_response.code,
                    data=None,
                    message=existing_registration_response.message,
                )
            existing_registration = existing_registration_response.data
            if not existing_registration:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="User is not registered for this event.",
                    details={"user_id": logged_in_user.id, "event_id": event.id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="You are not registered for this event",
                )
            delete_response = await self.user_event_repository.delete(
                existing_registration
            )
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Unregister",
                entity="Event",
                level="info",
                code=200,
                message="User unregistered from event successfully.",
                details={"user_id": logged_in_user.id, "event_id": event.id},
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Unregistered from event successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Unregister",
                entity="Event",
                level="error",
                code=500,
                message="An error occurred while unregistering from event",
                details={"error": str(ex)},
                source="EventService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while unregistering from event",
            )
