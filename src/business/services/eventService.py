from sqlalchemy import func, and_, or_
from core.iServices.iEventService import IEventService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.event import Event
from core.entities.faculty import Faculty
from core.entities.department import Department
from core.entities.year import Year
from core.entities.notification import Notification
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator
from core.dtos.userEventDtos import (UserEventRegisterDto,UserEventUnregisterDto)


class EventService(IEventService):
    def __init__(
        self,
        event_repository: IBaseRepository[Event],
        faculty_repository: IBaseRepository[Faculty],
        department_repository: IBaseRepository[Department],
        year_repository: IBaseRepository[Year],
        event_organizer_repository: IBaseRepository[EventOrganizer],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.event_repository = event_repository
        self.faculty_repository = faculty_repository
        self.department_repository = department_repository
        self.year_repository = year_repository
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
                Event, data, ["title","location"], is_and, starts_with, is_exact
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
                Event, data, ["title","location"], is_and, starts_with, is_exact
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
            existing_event_response = await self.event_repository.find_one(
                and_(
                    Event.title == data.title,
                    Event.start_date==data.start_date
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
                    message="Event with the same title and start date already exists.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Event with the same title and start date already exists.",
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
                    code=logged_in_user_response.code,
                    data=None,
                    message=logged_in_user_response.message,
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="error",
                    code=401,
                    message="No logged-in user found for Event Creation.",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in user found for Event Creation.",
                )

            event_organizer_dynamic_includes = self.helper_service.generate_dynamic_includes(
                            EventOrganizer, None
                        )
            event_organizer_response = await self.event_organizer_repository.find_one(
                EventOrganizer.id == data.event_organizer_id, event_organizer_dynamic_includes
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
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event organizer not found for event creation",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event organizer not found for event creation",
                )

            if data.faculty_id:
                faculty_dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Faculty, None
                )
                faculty_response = await self.faculty_repository.find_one(
                    Faculty.id == data.faculty_id, faculty_dynamic_includes
                )
                if not faculty_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=faculty_response.code,
                        data=None,
                        message=faculty_response.message,
                    )
                if not faculty_response.data:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=404,
                        message="Faculty not found for event creation",
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False, code=404, data=None, message="Faculty not found for event creation"
                    )

            if data.department_id:
                department_dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Department, None
                )
                department_response = await self.department_repository.find_one(
                    Department.id == data.department_id, department_dynamic_includes
                )
                if not department_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=department_response.code,
                        data=None,
                        message=department_response.message,
                    )
                if not department_response.data:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=404,
                        message="Department not found for event creation",
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False, code=404, data=None, message="Department not found for event creation"
                    )

            if data.year_id:
                year_dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Year, None
                )
                year_response = await self.year_repository.find_one(
                    Year.id == data.year_id, year_dynamic_includes
                )
                if not year_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=year_response.code,
                        data=None,
                        message=year_response.message,
                    )
                if not year_response.data:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=404,
                        message="Year not found for event creation",
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False, code=404, data=None, message="Year not found for event creation"
                    )
                
            if data.end_date and data.end_date < data.start_date:
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="End date cannot be before start date",
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="End date cannot be before start date",
                )
            files = []            
            for url in data.urls:
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(url)
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="File does not exist for Event Creation.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_exists_response.code,
                        data=None,
                        message=file_exists_response.message,
                    )
                file_data = file_exists_response.data
                if not file_data:
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="Failed to fetch file data from Google Drive for Event Creation.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Failed to fetch file data from Google Drive",
                    )
                files.append(file_data.model_dump())
            for link_name, link_url in (data.links or {}).items():
                if not Validator.is_valid_external_url(link_url):
                    await self.logger.log(
                        action="Create",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="Invalid URL provided for Event Creation.",
                        details={"link_name": link_name, "link_url": link_url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid URL provided",
                    )

            if data.url and not Validator.is_valid_external_url(data.url):
                await self.logger.log(
                    action="Create",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="Invalid Event URL provided for Event Creation.",
                    details={"url": data.url},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Event URL provided",
                )

            data.author_id = logged_in_user.id
            data.details = {"files_data": files} if files else {}

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
            await self.logger.log(
                action="Create",
                entity="Event",
                level="info",
                code=201,
                message="Event created successfully.",
                details={"event_id": create_response.data.id, "author_id": logged_in_user.id},
                source="EventService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_event,
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
            target_event_response = await self.event_repository.find_one(
                Event.id == data.id
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
                    message="Event not found for update",
                )

            existing_event_response = await self.event_repository.find_one(
                and_(Event.title == data.title, Event.start_date == data.start_date)
            )
            if not existing_event_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_response.code,
                    data=None,
                    message=existing_event_response.message,
                )
            existing_event = existing_event_response.data
            if existing_event and existing_event.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="Another event with the same title and start date already exists.",
                    details={"title": data.title, "start_date": str(data.start_date)},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Another event with the same title and start date already exists.",
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

            if data.end_date and data.end_date < data.start_date:
                await self.logger.log(
                    action="Update",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="End date cannot be before start date",
                    details={"start_date": str(data.start_date), "end_date": str(data.end_date)},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="End date cannot be before start date",
                )

            old_urls = target_event.urls or []
            to_be_removed_urls = (
                [url for url in old_urls if url not in data.urls]
                if data.urls
                else old_urls
            )

            files = []
            for url in data.urls:
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(url)
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="File does not exist on Google Drive for Event Update.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_exists_response.code,
                        data=None,
                        message=file_exists_response.message,
                    )
                file_data = file_exists_response.data
                if not file_data:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="error",
                        code=500,
                        message="Failed to fetch file data from Google Drive for Event Update.",
                        details={"url": url},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="Failed to fetch file data from Google Drive for Event Update.",
                    )
                files.append(file_data.model_dump())

            for link_name, link_url in (data.links or {}).items():
                if not link_url or not Validator.is_valid_external_url(link_url):
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="Invalid link provided for Event Update.",
                        details={"link_name": link_name},
                        source="EventService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid link provided for Event Update.",
                    )

            data.details = {"files_data": files} if files else {}

            target_event.title = data.title
            target_event.start_date = data.start_date
            target_event.end_date = data.end_date
            target_event.price = data.price
            target_event.location = data.location
            target_event.location_type=data.location_type
            target_event.urls = data.urls
            target_event.links = data.links
            target_event.details = data.details
            target_event.faculty_id = data.faculty_id

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

            if len(to_be_removed_urls) > 0:
                remove_response = await self.helper_service.remove_files_from_drive(
                    [
                        {
                            "user_id": updated_event.author_id,
                            "file_id": self.helper_service.get_file_id_from_url(url),
                        }
                        for url in to_be_removed_urls
                    ]
                )
                if not remove_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="Failed to Remove Files from Drive during Event Update.",
                        details={"urls": to_be_removed_urls},
                        source="EventService",
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
            target_event_response = await self.event_repository.find_one(
                Event.id == data.id
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

            urls_to_remove = target_event.urls or []

            delete_response = await self.event_repository.delete(target_event)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )

            if len(urls_to_remove) > 0:
                remove_response = await self.helper_service.remove_files_from_drive(
                    [
                        {
                            "user_id": target_event.author_id,
                            "file_id": self.helper_service.get_file_id_from_url(url),
                        }
                        for url in urls_to_remove
                    ]
                )
                if not remove_response.success:
                    await self.logger.log(
                        action="Delete",
                        entity="Event",
                        level="warning",
                        code=400,
                        message="Failed to Remove Files from Drive during Event Deletion.",
                        details={"urls": urls_to_remove},
                        source="EventService",
                    )

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

    async def register(self, data):
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
                    success=False, code=logged_in_user_response.code, data=None, message=logged_in_user_response.message
                )
            user = logged_in_user_response.data
            if not user:
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
                    message="No logged-in user found for Event Register.")

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, ["attendees"]
            )
            event_response = await self.event_repository.find_one(
                Event.id == data.event_id, dynamic_includes
            )
            if not event_response.success:
                return BaseResponseDto(
                    success=False, code=event_response.code, data=None, message=event_response.message
                )
            event = event_response.data
            if not event:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for registration",
                    details={"event_id": data.event_id},
                    source="EventService",
                )
                return BaseResponseDto(success=False, code=404, data=None, message="Event not found")

            attendee_ids = [attendee.id for attendee in event.attendees] if event.attendees else []
            if user.id in attendee_ids:
                await self.logger.log(
                    action="Register",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="User already registered for this event.",
                    details={"user_id": user.id, "event_id": event.id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="User already registered for this event"
                )

            event.attendees.append(user)

            update_response = await self.event_repository.update(event)
            if not update_response.success:
                return BaseResponseDto(
                    success=False, code=update_response.code, data=None, message=update_response.message
                )

            await self.logger.log(
                action="Register",
                entity="Event",
                level="info",
                code=200,
                message="User registered for event successfully.",
                details={"user_id": user.id, "event_id": event.id},
                source="EventService",
            )
            return BaseResponseDto(success=True, code=200, data=True, message="Registered for event successfully")
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
                success=False, code=500, data=None, message="An error occurred while registering for event"
            )

    async def unregister(self, data: UserEventUnregisterDto) -> BaseResponseDto:
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
                    success=False, code=logged_in_user_response.code, data=None, message=logged_in_user_response.message
                )
            user = logged_in_user_response.data
            if not user:
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
                    message="No logged-in user found for Event Unregister.")

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Event, ["attendees"]
            )
            event_response = await self.event_repository.find_one(
                Event.id == data.event_id, dynamic_includes
            )
            if not event_response.success:
                return BaseResponseDto(
                    success=False, code=event_response.code, data=None, message=event_response.message
                )
            event = event_response.data
            if not event:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="warning",
                    code=404,
                    message="Event not found for unregistration",
                    details={"event_id": data.event_id},
                    source="EventService",
                )
                return BaseResponseDto(success=False, code=404, data=None, message="Event not found")

            attendee_ids = [attendee.id for attendee in event.attendees] if event.attendees else []
            if user.id not in attendee_ids:
                await self.logger.log(
                    action="Unregister",
                    entity="Event",
                    level="warning",
                    code=400,
                    message="User is not registered for this event.",
                    details={"user_id": user.id, "event_id": event.id},
                    source="EventService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="You are not registered for this event"
                )

            event.attendees = [attendee for attendee in event.attendees if attendee.id != user.id]

            update_response = await self.event_repository.update(event)
            if not update_response.success:
                return BaseResponseDto(
                    success=False, code=update_response.code, data=None, message=update_response.message
                )

            await self.logger.log(
                action="Unregister",
                entity="Event",
                level="info",
                code=200,
                message="User unregistered from event successfully.",
                details={"user_id": user.id, "event_id": event.id},
                source="EventService",
            )
            return BaseResponseDto(success=True, code=200, data=True, message="Unregistered from event successfully")
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
                success=False, code=500, data=None, message="An error occurred while unregistering from event"
            )