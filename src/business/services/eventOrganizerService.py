from sqlalchemy import func, and_
from core.iServices.iEventOrganizerService import IEventOrganizerService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.baseDtos import BaseResponseDto


class EventOrganizerService(IEventOrganizerService):
    def __init__(
        self,
        event_organizer_repository: IBaseRepository[EventOrganizer],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.event_organizer_repository = event_organizer_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.event_organizer_repository.begin_transaction()

    async def commit_transaction(self):
        await self.event_organizer_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.event_organizer_repository.rollback_transaction()

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
                EventOrganizer, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                EventOrganizer, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "EventOrganizer", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "EventOrganizer", order_by
            )
            result = await self.event_organizer_repository.find_one(
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

            event_organizer = result.data
            return BaseResponseDto(
                success=True,
                code=200,
                data=event_organizer,
            )
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while finding event organizer",
                details={"error": str(ex)},
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding event organizer",
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
                EventOrganizer, data, ["name"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                EventOrganizer, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "EventOrganizer", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "EventOrganizer", order_by
            )

            result = await self.event_organizer_repository.find(
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

            event_organizers = result.data
            return BaseResponseDto(success=True, data=event_organizers)

        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while finding event organizers",
                details={"error": str(ex)},
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding event organizers",
            )

    async def create(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Organizer Creation.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user for Event Organizer Creation.",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Organizer Creation.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user found for Event Organizer Creation.",
                )
            existing_event_organizer_response = (
                await self.event_organizer_repository.find_one(
                    and_(
                        func.lower(EventOrganizer.name) == func.lower(data.name),
                    )
                )
            )
            if not existing_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_organizer_response.code,
                    data=None,
                    message=existing_event_organizer_response.message,
                )
            existing_event_organizer = existing_event_organizer_response.data
            if existing_event_organizer:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="An event organizer with the same name already exists.",
                    details={
                        "name": data.name,
                    },
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="An event organizer with the same name already exists.",
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
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="No valid Logo provided for the event organizer.",
                    details={"details": data.details},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No valid Logo provided for the event organizer.",
                )
            create_response = await self.event_organizer_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_event_organizer = create_response.data
            if not created_event_organizer:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to create event organizer.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event organizer.",
                )
            attachment_response = await self.helper_service.create_attachment(
                is_file=True,
                url=url,
                author_id=logged_in_user.id,
                source_name="event_organizer_logo_id",
                source_id=created_event_organizer.id,
            )
            if not attachment_response.success:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=attachment_response.code or 500,
                    message="Failed to create attachment for event organizer logo.",
                    details={"url": url},
                    source="EventOrganizerService",
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
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to create attachment for event organizer logo without a specific error.",
                    details={"url": url},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event organizer logo attachment.",
                )
            created_event_organizer.logo_id = attachment.id
            update_response = await self.event_organizer_repository.update(
                created_event_organizer, ["logo_id"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_event_organizer = update_response.data
            if not updated_event_organizer:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to update event organizer with logo_id.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating event organizer logo attachment.",
                )
            for url in urls:
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="event_organizer_id",
                    source_id=updated_event_organizer.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="EventOrganizer",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event organizer.",
                        details={"url": url},
                        source="EventOrganizerService",
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event organizer without a specific error.",
                        details={"url": url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating event organizer logo attachment.",
                    )
            for link in links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="event_organizer_id",
                    source_id=updated_event_organizer.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="EventOrganizer",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event organizer.",
                        details={"url": link_url},
                        source="EventOrganizerService",
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event organizer without a specific error.",
                        details={"url": link_url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating event organizer",
                    )
            await self.logger.log(
                action="Create",
                entity="EventOrganizer",
                level="info",
                code=201,
                message="Event organizer created successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=updated_event_organizer,
                message="Event organizer created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while creating event organizer",
                details={"error": str(ex)},
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating event organizer",
            )

    async def update(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                EventOrganizer, ["logo", "attachments"]
            )
            target_event_organizer_response = (
                await self.event_organizer_repository.find_one(
                    EventOrganizer.id == data.id, dynamic_includes
                )
            )
            if not target_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_event_organizer_response.code,
                    data=None,
                    message=target_event_organizer_response.message,
                )
            target_event_organizer = target_event_organizer_response.data
            if not target_event_organizer:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="warning",
                    code=404,
                    message="Event organizer not found for update",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event organizer not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Organizer Update.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve logged-in user for Event Organizer Update.",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Organizer Update.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="No logged-in user found for Event Organizer Update.",
                )
            existing_event_organizer_response = (
                await self.event_organizer_repository.find_one(
                    and_(
                        func.lower(EventOrganizer.name) == func.lower(data.name),
                    )
                )
            )
            if not existing_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_organizer_response.code,
                    data=None,
                    message=existing_event_organizer_response.message,
                )
            existing_event_organizer = existing_event_organizer_response.data
            if existing_event_organizer and existing_event_organizer.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="An event organizer with the same name already exists.",
                    details={
                        "name": data.name,
                        "existing_event_organizer_id": existing_event_organizer.id,
                        "target_event_organizer_id": target_event_organizer.id,
                    },
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="An event organizer with the same name already exists.",
                )
            old_logo = target_event_organizer.logo
            old_attachments = target_event_organizer.attachments or []
            data.details = data.details or {}
            url = data.details.get("url")
            urls = data.details.get("urls", [])
            links = data.details.get("links", [])
            data.details.pop("url", None)
            data.details.pop("urls", None)
            data.details.pop("links", None)
            target_event_organizer.name = data.name
            update_response = await self.event_organizer_repository.update(
                target_event_organizer
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_event_organizer = update_response.data
            if not updated_event_organizer:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to update event organizer.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating event organizer",
                )
            if not url:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="No valid Logo provided for the event organizer update.",
                    details={"details": data.details},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No valid Logo provided for the event organizer update.",
                )
            if url != old_logo.url:
                await self.helper_service.delete_attachment(attachment=old_logo)
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=url,
                    author_id=logged_in_user.id,
                    source_name="event_organizer_logo_id",
                    source_id=updated_event_organizer.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event organizer logo during update.",
                        details={"url": url},
                        source="EventOrganizerService",
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event organizer logo during update without a specific error.",
                        details={"url": url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event organizer logo attachment",
                    )
                updated_event_organizer.logo_id = attachment.id
                update_response = await self.event_organizer_repository.update(
                    updated_event_organizer, ["logo_id"]
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to update event organizer with new logo_id.",
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event organizer logo attachment",
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
                    source_name="event_organizer_id",
                    source_id=updated_event_organizer.id,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event organizer.",
                        details={"url": url},
                        source="EventOrganizerService",
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event organizer without a specific error.",
                        details={"url": url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event organizer logo attachment",
                    )
            for link in new_links:
                link_name = link.get("name", link.get("title", ""))
                link_url = link.get("url", "")
                attachment_response = await self.helper_service.create_attachment(
                    is_file=False,
                    url=link_url,
                    author_id=logged_in_user.id,
                    source_name="event_organizer_id",
                    source_id=updated_event_organizer.id,
                    link_title=link_name,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=attachment_response.code or 500,
                        message="Failed to create attachment for event organizer.",
                        details={"url": link_url},
                        source="EventOrganizerService",
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
                        entity="EventOrganizer",
                        level="error",
                        code=500,
                        message="Failed to create attachment for event organizer without a specific error.",
                        details={"url": link_url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while updating event organizer logo attachment",
                    )
            await self.logger.log(
                action="Update",
                entity="EventOrganizer",
                level="info",
                code=200,
                message="Event organizer updated successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_event_organizer,
                message="Event organizer updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while updating event organizer",
                details={"error": str(ex)},
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating event organizer",
            )

    async def delete(self, data):
        try:
            target_event_organizer_response = (
                await self.event_organizer_repository.find_one(
                    EventOrganizer.id == data.id
                )
            )
            if not target_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_event_organizer_response.code,
                    data=None,
                    message=target_event_organizer_response.message,
                )
            target_event_organizer = target_event_organizer_response.data
            if not target_event_organizer:
                await self.logger.log(
                    action="Delete",
                    entity="EventOrganizer",
                    level="warning",
                    code=404,
                    message="Event organizer not found for deletion",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event organizer not found",
                )
            delete_response = await self.event_organizer_repository.delete(
                target_event_organizer
            )
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="EventOrganizer",
                level="info",
                code=200,
                message="Event organizer deleted successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Event organizer deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="EventOrganizer",
                level="error",
                code=500,
                message="An error occurred while deleting event organizer",
                details={"error": str(ex)},
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting event organizer",
            )
