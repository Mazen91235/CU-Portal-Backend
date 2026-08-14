import os
from sqlalchemy import and_
from core.iServices.iEventOrganizerService import IEventOrganizerService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.baseDtos import BaseResponseDto
from core.utils.validator import Validator


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
                EventOrganizer, data, ["name", "url"], is_and, starts_with, is_exact
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
                EventOrganizer, data, ["name", "url"], is_and, starts_with, is_exact
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
            existing_event_organizer_response = (
                await self.event_organizer_repository.find_one(
                    EventOrganizer.name == data.name
                )
            )
            if not existing_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_event_organizer_response.code,
                    data=None,
                    message=existing_event_organizer_response.message,
                )
            existing_organizer = existing_event_organizer_response.data
            if existing_organizer:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="Event Organizer with the same name already exists.",
                    details={"name": data.name},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Event Organizer with the same name already exists.",
                )

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
                    message="An error occurred while creating event organizer",
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
                    message="An error occurred while creating event organizer",
                )
            
            data.author_id = logged_in_user.id

            if not Validator.is_valid_drive_url(data.url):
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=400,
                    message="Invalid logo Google Drive URL format provided.",
                    details={"url": data.url},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid logo Google Drive URL format provided.",
                )
            logo_file_id = self.helper_service.get_file_id_from_url(data.url)
            if not logo_file_id:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="Invalid file URL provided for Event Organizer logo",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid file URL provided for logo, please try again with a valid file.",
                )
            logo_response = await self.helper_service.fetch_from_drive(logo_file_id)
            if not logo_response.success:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=logo_response.code or 500,
                    message="Failed to fetch logo file from Google Drive",
                    details={"error": logo_response.error},
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logo_response.code,
                    data=None,
                    message=logo_response.message,
                )
            
            logo_file = logo_response.data
            if not logo_file:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="Logo file not found on Google Drive",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="The uploaded logo file could not be found, please try again.",
                )
            if not self.helper_service.verify_file_type(
                logo_file.data.mime_type, "image"
            ):
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="warning",
                    code=400,
                    message="Uploaded logo file is not an image",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="The uploaded logo must be an image, please try again with a valid image file.",
                )
            
            logo_data = logo_file.data 
            files = []
            for url in data.urls:
                if not Validator.is_valid_drive_url(url):
                    await self.logger.log(
                        action="Create",
                        entity="EventOrganizer",
                        level="error",
                        code=400,
                        message="Invalid Google Drive URL format provided for an attachment.",
                        details={"url": url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Invalid Google Drive URL format: {url}",
                    )

                file_id = self.helper_service.get_file_id_from_url(url)
                if not file_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Invalid file URL provided for attachment: {url}"
                    )

                file_response = await self.helper_service.fetch_from_drive(file_id)
                if not file_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="EventOrganizer",
                        level="warning",
                        code=file_response.code or 500,
                        message="Failed to fetch attachment from Google Drive",
                        details={"error": file_response.error, "url": url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=file_response.code,
                        data=None,
                        message=file_response.message,
                    )
                
                file = file_response.data
                if not file:
                    return BaseResponseDto(
                        success=False, code=400, data=None, message="Attachment file not found on Google Drive"
                    )
                files.append(file.data.model_dump())

            for link_name, link_url in (data.links).items():
                if not Validator.is_valid_external_url(link_url):
                    await self.logger.log(
                        action="Create",
                        entity="EventOrganizer",
                        level="warning",
                        code=400,
                        message="Invalid URL provided for Event Organizer Creation.",
                        details={"link_name": link_name, "link_url": link_url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid URL provided",
                    )

            details = {}
            if logo_data:
                details["logo_data"] = logo_data.model_dump()
            if files:
                details["files_data"] = files
            data.details = details

            create_event_organizer_response = (
                await self.event_organizer_repository.create(data)
            )
            if not create_event_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_event_organizer_response.code,
                    data=None,
                    message=create_event_organizer_response.message,
                )
            created_event_organizer = create_event_organizer_response.data
            if not created_event_organizer:
                await self.logger.log(
                    action="Create",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to create event organizer without a specific error.",
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
                message="Event Organizer created successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_event_organizer,
                message="Event Organizer created successfully",
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
            target_organizer_response = await self.event_organizer_repository.find_one(
                EventOrganizer.id == data.id
            )
            if not target_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_organizer_response.code,
                    data=None,
                    message=target_organizer_response.message,
                )
            
            target_organizer = target_organizer_response.data
            if not target_organizer:
                await self.logger.log(
                    action="Update",
                    entity="EventOrganizer",
                    level="info",
                    code=404,
                    message="Event Organizer not found for update",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event Organizer not found",
                )

            if data.name and data.name != target_organizer.name:
                existing_organizer_response = await self.event_organizer_repository.find_one(
                    EventOrganizer.name == data.name
                )
                if existing_organizer_response.success and existing_organizer_response.data:
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=400,
                        message="Another Event Organizer with the same name already exists.",
                        details={"name": data.name},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Another Event Organizer with the same name already exists.",
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
                    message="An error occurred while updating event organizer",
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
                    message="An error occurred while updating event organizer",
                )

            current_logo_url = target_organizer.url
            logo_to_remove = None
            new_logo_data = None
            
            if data.url and data.url != current_logo_url:
                if not Validator.is_valid_drive_url(data.url):
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=400,
                        message="Invalid logo Google Drive URL format provided.",
                        details={"url": data.url},
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid logo URL provided.",
                    )

                logo_file_id = self.helper_service.get_file_id_from_url(data.url)
                if not logo_file_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid file URL uploaded for logo."
                    )

                logo_file_response = await self.helper_service.fetch_from_drive(logo_file_id)
                if not logo_file_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=logo_file_response.code,
                        data=None,
                        message=logo_file_response.message
                    )
                
                logo_file = logo_file_response.data
                if not logo_file:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Logo file not found on Google Drive."
                    )

                if not self.helper_service.verify_file_type(logo_file.data.mime_type, "image"):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Only image files are allowed for the logo."
                    )

                if not self.helper_service.verify_file_size(
                    logo_file.data.size, EventOrganizer.MAX_ALLOWED_FILE_SIZE_B
                ):
                    await self.logger.log(
                        action="Update",
                        entity="EventOrganizer",
                        level="warning",
                        code=400,
                        message="Uploaded logo file exceeds maximum allowed size",
                        source="EventOrganizerService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"The uploaded logo exceeds the maximum allowed size of {EventOrganizer.MAX_ALLOWED_FILE_SIZE_MB} MB, please try again with a smaller file.",
                    )

                new_logo_data = logo_file.data.model_dump()
                logo_to_remove = current_logo_url

            old_urls = target_organizer.urls or []
            to_be_removed_urls = (
                [url for url in old_urls if url not in data.urls]
                if data.urls
                else old_urls
            )
            
            files_data = []
            if data.urls:
                for url in data.urls:
                    if not Validator.is_valid_drive_url(url):
                        return BaseResponseDto(
                            success=False,
                            code=400,
                            data=None,
                            message=f"Invalid Google Drive URL format: {url}"
                        )

                    file_id = self.helper_service.get_file_id_from_url(url)
                    if not file_id:
                        return BaseResponseDto(
                            success=False,
                            code=400,
                            data=None,
                            message=f"Invalid file URL uploaded for attachment: {url}"
                        )

                    file_exists_response = await self.helper_service.fetch_from_drive(attach_file_id)
                    if not file_exists_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=file_exists_response.code,
                            data=None,
                            message=file_exists_response.message
                        )
                    
                    file_data = file_exists_response.data
                    if not file_data:
                        return BaseResponseDto(
                            success=False,
                            code=500,
                            data=None,
                            message="Failed to fetch attachment from Google Drive"
                        )
                    files_data.append(file_data.data.model_dump())

            if data.links:
                for link_name, link_url in data.links.items():
                    if not Validator.is_valid_external_url(link_url):
                        await self.logger.log(
                            action="Update",
                            entity="EventOrganizer",
                            level="warning",
                            code=400,
                            message="Invalid URL provided for Event Organizer Update.",
                            details={"link_name": link_name, "link_url": link_url},
                            source="EventOrganizerService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=400,
                            data=None,
                            message="Invalid external URL provided"
                        )

            new_details = {}
            if new_logo_data:
                new_details["logo_data"] = new_logo_data
            elif target_organizer.details and "logo_data" in target_organizer.details:
                new_details["logo_data"] = target_organizer.details["logo_data"]
            if files_data:
                new_details["files_data"] = files_data

            target_organizer.name = data.name if data.name else target_organizer.name
            target_organizer.url = data.url if data.url else target_organizer.url
            target_organizer.urls = data.urls
            target_organizer.links = data.links if data.links is not None else target_organizer.links
            target_organizer.details = new_details

            update_response = await self.event_organizer_repository.update(target_organizer)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message
                )
            
            updated_organizer = update_response.data
            if not updated_organizer:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating event organizer"
                )
            
            if logo_to_remove or len(to_be_removed_urls) > 0:
                access_token_response = await self.helper_service.get_google_access_token(
                    logged_in_user.google_refresh_token or ""
                )
                if access_token_response.success and access_token_response.data:
                    access_token = access_token_response.data
                    
                    if logo_to_remove:
                        logo_id_to_remove = self.helper_service.get_file_id_from_url(logo_to_remove)
                        if logo_id_to_remove:
                            remove_logo_response = await self.helper_service.delete_file_from_drive(
                                access_token, logo_id_to_remove
                            )
                            if not remove_logo_response.success:
                                await self.logger.log(
                                    action="Update",
                                    entity="EventOrganizer",
                                    level="warning",
                                    code=400,
                                    message="Failed to Remove old logo from Drive.",
                                    source="EventOrganizerService",
                                )
                    
                    for url_to_remove in to_be_removed_urls:
                        file_id_to_remove = self.helper_service.get_file_id_from_url(url_to_remove)
                        if file_id_to_remove:
                            remove_attach_response = await self.helper_service.delete_file_from_drive(
                                access_token, file_id_to_remove
                            )
                            if not remove_attach_response.success:
                                await self.logger.log(
                                    action="Update",
                                    entity="EventOrganizer",
                                    level="warning",
                                    code=400,
                                    message="Failed to Remove old attachment from Drive.",
                                    details={"url": url_to_remove},
                                    source="EventOrganizerService",
                                )

            await self.logger.log(
                action="Update",
                entity="EventOrganizer",
                level="info",
                code=200,
                message="Event Organizer updated successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_organizer,
                message="Event Organizer updated successfully",
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
            target_organizer_response = await self.event_organizer_repository.find_one(
                EventOrganizer.id == data.id
            )
            if not target_organizer_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_organizer_response.code,
                    data=None,
                    message=target_organizer_response.message,
                )
            
            target_organizer = target_organizer_response.data
            if not target_organizer:
                await self.logger.log(
                    action="Delete",
                    entity="EventOrganizer",
                    level="warning",
                    code=404,
                    message="Event Organizer not found for deletion",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Event Organizer not found",
                )

            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="Failed to retrieve logged-in user for Event Organizer Deletion.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting event organizer",
                )
            
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="EventOrganizer",
                    level="error",
                    code=500,
                    message="No logged-in user found for Event Organizer Deletion.",
                    source="EventOrganizerService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while deleting event organizer",
                )

            delete_response = await self.event_organizer_repository.delete(
                target_organizer
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
                message="Event Organizer deleted successfully",
                source="EventOrganizerService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Event Organizer deleted successfully",
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