from sqlalchemy import and_
from core.iServices.iMaterialService import IMaterialService
from core.iServices.iMaterialService import IMaterialService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.material import Material
from core.entities.subject import Subject
from core.entities.user import User
from core.entities.notification import Notification
from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import FetchedModel
from core.utils.validator import Validator
from core.utils.fernetHandler import FernetHandler


class MaterialService(IMaterialService):
    def __init__(
        self,
        material_repository: IBaseRepository[Material],
        subject_repository: IBaseRepository[Subject],
        user_repository: IBaseRepository[User],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.material_repository = material_repository
        self.subject_repository = subject_repository
        self.user_repository = user_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.material_repository.begin_transaction()

    async def commit_transaction(self):
        await self.material_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.material_repository.rollback_transaction()

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
                Material,
                data,
                ["name"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Material", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Material", order_by
            )
            result = await self.material_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                [],
                descending,
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            material = result.data
            return BaseResponseDto(success=True, data=material)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while finding material",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding material",
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
                Material,
                data,
                ["name"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Material", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Material", order_by
            )
            result = await self.material_repository.find(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                [],
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
            materials = result.data
            return BaseResponseDto(
                success=True, data=materials, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while finding materials",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding materials",
            )

    async def create(self, data):
        try:
            if not Validator.is_allowed_type(data.material_type):
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Invalid material type: {data.material_type}",
                    details={"error": "Invalid material type"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid material type: {data.material_type}",
                )
            if data.material_type != "folder" and not data.url:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"URL is required for material type: {data.material_type}",
                    details={"error": "URL is required for non-folder materials"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"URL is required for material type: {data.material_type}",
                )
            if (
                data.material_type != "folder"
                and not Validator.is_valid_url_based_on_type(
                    data.url or "", data.material_type
                )
            ):
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Invalid URL for material type: {data.material_type}",
                    details={"error": "Invalid URL for the specified material type"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid URL for material type: {data.material_type}",
                )
            parent_id = None
            if data.parent_id:
                parent_material_response = await self.material_repository.find_one(
                    Material.id == data.parent_id
                )
                if not parent_material_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=parent_material_response.code,
                        data=None,
                        message=parent_material_response.message,
                    )
                parent_material = parent_material_response.data
                if not parent_material:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Parent material with ID {data.parent_id} not found",
                        details={"error": "Parent material not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Parent material with ID {data.parent_id} not found",
                    )
                parent_id = parent_material.id
            subject_id = None
            if not data.subject_id:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Subject ID is required for material creation",
                    details={"error": "Subject ID is missing"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Subject ID is required for material creation",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["user_subject_links.user"]
            )
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id,
                dynamic_includes,
            )
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )
            subject = subject_response.data
            if not subject:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Subject with ID {data.subject_id} not found",
                    details={"error": "Subject not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Subject with ID {data.subject_id} not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=subject.id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user {logged_in_user.id} on subject {subject.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            user_ids = [user.id for user in subject.users] if subject.users else []
            data.author_id = logged_in_user.id
            data.details = data.details or {}
            data.details["fetched"] = False
            if data.material_type == "file":
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(
                        data.url or ""
                    )
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=file_exists_response.code or 500,
                        message=f"Failed to verify file existence on Google Drive: {file_exists_response.message}",
                        details={"error": file_exists_response.error},
                        source="MaterialService",
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
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"File not found on Google Drive for URL: {data.url}",
                        details={"error": "File not found on Google Drive"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"File not found on Google Drive for the provided URL.",
                    )
                data.details["file_data"] = file_data.model_dump(mode="json")
            unique_name_response = await self._generate_unique_name(
                data.name, subject_id, parent_id
            )
            if not unique_name_response.success:
                return BaseResponseDto(
                    success=False,
                    code=unique_name_response.code,
                    data=None,
                    message=unique_name_response.message,
                )
            data.name = unique_name_response.data
            created_material_response = await self.material_repository.create(data)
            if not created_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=created_material_response.code,
                    data=None,
                    message=created_material_response.message,
                )
            created_material = created_material_response.data
            if not created_material:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to create material, no data returned from repository",
                    details={"error": "No data returned from repository"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to create material, please try again later.",
                )
            share_link = f"/user/materials/{subject_id}"
            if parent_id:
                share_link += f"/{parent_id}"
            if data.material_type == "file":
                share_link += f"?material_id={created_material.id}"
            elif data.material_type != "folder":
                share_link = created_material.url
            await self.helper_service.send_notification(
                Notification.NotificationType.MATERIAL,
                created_material.id,
                user_ids,
                f"New material '{created_material.name}' has been created for subject {subject.name}.",
                share_link,
            )
            await self.logger.log(
                action="Create",
                entity="Material",
                level="info",
                code=201,
                message=f"Material created successfully: {created_material.name}",
                details={"material_id": created_material.id},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_material,
                message="Material created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while creating material",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating material",
            )

    async def update(self, data):
        try:
            if not Validator.is_allowed_type(data.material_type):
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Invalid material type: {data.material_type}",
                    details={"error": "Invalid material type"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid material type: {data.material_type}",
                )
            if data.material_type != "folder" and not data.url:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"URL is required for material type: {data.material_type}",
                    details={"error": "URL is required for non-folder materials"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"URL is required for material type: {data.material_type}",
                )
            if (
                data.material_type != "folder"
                and not Validator.is_valid_url_based_on_type(
                    data.url or "", data.material_type
                )
            ):
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Invalid URL for material type: {data.material_type}",
                    details={"error": "Invalid URL for the specified material type"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid URL for material type: {data.material_type}",
                )
            existing_material_response = await self.material_repository.find_one(
                Material.id == data.id
            )
            if not existing_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_material_response.code,
                    data=None,
                    message=existing_material_response.message,
                )
            existing_material = existing_material_response.data
            if not existing_material:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Material with ID {data.id} not found",
                    details={"error": "Material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Material with ID {data.id} not found",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["user_subject_links.user"]
            )
            subject_response = await self.subject_repository.find_one(
                Subject.id == existing_material.subject_id, dynamic_includes
            )
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )
            subject = subject_response.data
            if not subject:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Subject with ID {existing_material.subject_id} not found",
                    details={"error": "Subject not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Subject with ID {existing_material.subject_id} not found",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    action="Update",
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=subject.id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user {logged_in_user.id} on subject {subject.id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=logged_in_user_permissions_response.code or 500,
                    message=f"Failed to get logged in user permissions for user {logged_in_user.id}: {logged_in_user_permissions_response.message}",
                    details={"error": logged_in_user_permissions_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_permissions_response.code,
                    data=None,
                    message=logged_in_user_permissions_response.message,
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=403,
                    message=f"Logged in user {logged_in_user.id} has no permissions",
                    details={"error": "Logged in user has no permissions"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You do not have the necessary permissions to update this material.",
                )
            user_ids = [user.id for user in subject.users] if subject.users else []
            if existing_material.author_id != logged_in_user.id:
                if "Manage All Materials" not in logged_in_user_permissions:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=403,
                        message=f"User {logged_in_user.id} is not authorized to update material {existing_material.id}",
                        details={
                            "error": "User not authorized to update this material"
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=None,
                        message=f"You are not authorized to update this material.",
                    )
            if data.name and data.name != existing_material.name:
                unique_name_response = await self._generate_unique_name(
                    data.name, existing_material.subject_id, existing_material.parent_id
                )
                if not unique_name_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=unique_name_response.code,
                        data=None,
                        message=unique_name_response.message,
                    )
                data.name = unique_name_response.data
            to_be_removed = ""
            to_be_removed_data = {
                "user_id": 0,
                "file_id": "",
            }
            data.details = data.details or {}
            data.details["fetched"] = False
            if (
                data.material_type == "file"
                and existing_material.material_type == "file"
                and data.url != existing_material.url
            ):
                file_exists_response = (
                    await self.helper_service.verify_file_exists_on_drive(
                        data.url or ""
                    )
                )
                if not file_exists_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=file_exists_response.code or 500,
                        message=f"Failed to verify file existence on Google Drive: {file_exists_response.message}",
                        details={"error": file_exists_response.error},
                        source="MaterialService",
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
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"File not found on Google Drive for URL: {data.url}",
                        details={"error": "File not found on Google Drive"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"File not found on Google Drive for the provided URL.",
                    )
                data.details["file_data"] = file_data.model_dump(mode="json")
                to_be_removed = (
                    existing_material.url
                    if not existing_material.details.get("fetched")
                    else ""
                )
                if to_be_removed:
                    to_be_removed_data = {
                        "user_id": existing_material.author_id,
                        "file_id": self.helper_service.get_file_id_from_url(
                            existing_material.url or ""
                        ),
                    }
            data.author_id = logged_in_user.id
            updated_material_response = await self.material_repository.update(
                data, ["name", "material_type", "url", "details", "author_id"]
            )
            if not updated_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=updated_material_response.code,
                    data=None,
                    message=updated_material_response.message,
                )
            updated_material = updated_material_response.data
            if not updated_material:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to update material, no data returned from repository",
                    details={"error": "No data returned from repository"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to update material, please try again later.",
                )
            if to_be_removed:
                await self._remove_files([to_be_removed_data])
            user_ids = [user.id for user in subject.users] if subject.users else []
            share_link = f"/user/materials/{updated_material.subject_id}"
            if updated_material.parent_id:
                share_link += f"/{updated_material.parent_id}"
            if updated_material.material_type == "file":
                share_link += f"?material_id={updated_material.id}"
            elif updated_material.material_type != "folder":
                share_link = updated_material.url
            await self.helper_service.send_notification(
                Notification.NotificationType.MATERIAL,
                updated_material.id,
                user_ids,
                f"Material '{updated_material.name}' has been updated for subject {subject.name}.",
                share_link,
            )
            await self.logger.log(
                action="Update",
                entity="Material",
                level="info",
                code=200,
                message=f"Material updated successfully: {updated_material.name}",
                details={"material_id": updated_material.id},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_material,
                message="Material updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while updating material",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating material",
            )

    async def delete_many(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="DeleteMany",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    action="DeleteMany",
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            logged_in_user_permissions_response = (
                await self.helper_service.get_logged_in_user_permissions()
            )
            if not logged_in_user_permissions_response.success:
                await self.logger.log(
                    action="DeleteMany",
                    entity="Material",
                    level="error",
                    code=logged_in_user_permissions_response.code or 500,
                    message=f"Failed to get logged in user permissions for user {logged_in_user.id}: {logged_in_user_permissions_response.message}",
                    details={"error": logged_in_user_permissions_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=logged_in_user_permissions_response.code,
                    data=None,
                    message=logged_in_user_permissions_response.message,
                )
            logged_in_user_permissions = logged_in_user_permissions_response.data
            if not logged_in_user_permissions:
                await self.logger.log(
                    action="DeleteMany",
                    entity="Material",
                    level="error",
                    code=403,
                    message=f"Logged in user {logged_in_user.id} has no permissions",
                    details={"error": "Logged in user has no permissions"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message=f"You do not have the necessary permissions to delete this material.",
                )
            material_ids = data.material_ids
            files = []
            for material_id in material_ids:
                existing_material_response = await self.material_repository.find_one(
                    Material.id == material_id
                )
                if not existing_material_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=existing_material_response.code,
                        data=None,
                        message=existing_material_response.message,
                    )
                existing_material = existing_material_response.data
                if not existing_material:
                    await self.logger.log(
                        action="DeleteMany",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Material with ID {material_id} not found",
                        details={"error": "Material not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Material with ID {material_id} not found",
                    )
                verify_restricted_access_response = (
                    await self.helper_service.verify_restricted_access(
                        subject_id=existing_material.subject_id
                    )
                )
                if not verify_restricted_access_response.success:
                    await self.logger.log(
                        action="DeleteMany",
                        entity="Material",
                        level="error",
                        code=verify_restricted_access_response.code or 500,
                        message=f"Failed to verify restricted access for user {logged_in_user.id} on subject {existing_material.subject_id}: {verify_restricted_access_response.message}",
                        details={"error": verify_restricted_access_response.error},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=verify_restricted_access_response.code,
                        data=None,
                        message=verify_restricted_access_response.message,
                    )
                if existing_material.author_id != logged_in_user.id:
                    if "Manage All Materials" not in logged_in_user_permissions:
                        await self.logger.log(
                            action="DeleteMany",
                            entity="Material",
                            level="error",
                            code=403,
                            message=f"User {logged_in_user.id} is not authorized to delete material {existing_material.id}",
                            details={
                                "error": "User not authorized to delete this material"
                            },
                            source="MaterialService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=403,
                            data=None,
                            message=f"You are not authorized to delete this material.",
                        )
                delete_response = await self._recursive_delete(material_id, files)
                if not delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_response.code,
                        data=None,
                        message=delete_response.message,
                    )
            await self._remove_files(files)
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Materials deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="DeleteMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while deleting materials",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting materials",
            )

    async def get_parents(self, material_id):
        try:
            parents = []
            parents_response = await self._recursive_get_parents(material_id, parents)
            if not parents_response.success:
                return BaseResponseDto(
                    success=False,
                    code=parents_response.code,
                    data=None,
                    message=parents_response.message,
                )
            parents = parents_response.data
            return BaseResponseDto(
                success=True,
                code=200,
                data=parents,
                message="Parent materials fetched successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="GetParents",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while fetching parent materials",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching parent materials",
            )

    async def move_many(self, data):
        try:
            material_ids = data.material_ids
            destination_id = data.destination_id
            destination_material_response = await self.material_repository.find_one(
                Material.id == destination_id
            )
            if not destination_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=destination_material_response.code,
                    data=None,
                    message=destination_material_response.message,
                )
            destination_material = destination_material_response.data
            if not destination_material:
                await self.logger.log(
                    action="MoveMany",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Destination material with ID {destination_id} not found",
                    details={"error": "Destination material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Destination material with ID {destination_id} not found",
                )
            if destination_material.material_type != "folder":
                await self.logger.log(
                    action="MoveMany",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Destination material with ID {destination_id} is not a folder",
                    details={"error": "Destination material is not a folder"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Destination must be a folder. Material with ID {destination_id} is not a folder.",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="MoveMany",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    action="MoveMany",
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=destination_material.subject_id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="MoveMany",
                    entity="Material",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access : {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            for material_id in material_ids:
                existing_material_response = await self.material_repository.find_one(
                    Material.id == material_id
                )
                if not existing_material_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=existing_material_response.code,
                        data=None,
                        message=existing_material_response.message,
                    )
                existing_material = existing_material_response.data
                if not existing_material:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Material with ID {material_id} not found",
                        details={"error": "Material not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Material with ID {material_id} not found",
                    )
                verify_restricted_access_response = (
                    await self.helper_service.verify_restricted_access(
                        subject_id=existing_material.subject_id
                    )
                )
                if not verify_restricted_access_response.success:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=verify_restricted_access_response.code or 500,
                        message=f"Failed to verify restricted access for material {material_id}: {verify_restricted_access_response.message}",
                        details={"error": verify_restricted_access_response.error},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=verify_restricted_access_response.code,
                        data=None,
                        message=verify_restricted_access_response.message,
                    )
                if existing_material.parent_id == destination_material.id:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Material {material_id} is already in the destination folder {destination_id}",
                        details={
                            "error": "Material is already in the destination folder"
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Material '{existing_material.name}' is already in the destination folder '{destination_material.name}'.",
                    )
                if existing_material.id == destination_material.id:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Cannot move material {material_id} into itself",
                        details={"error": "Cannot move material into itself"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Cannot move material '{existing_material.name}' into itself.",
                    )
                existing_material.parent_id = destination_material.id
                update_response = await self.material_repository.update(
                    existing_material, ["parent_id"]
                )
                if not update_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_response.code,
                        data=None,
                        message=update_response.message,
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Materials moved successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="MoveMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while moving materials",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while moving materials",
            )

    async def copy_many(self, data):
        try:
            material_ids = data.material_ids
            destination_id = data.destination_id
            destination_material_response = await self.material_repository.find_one(
                Material.id == destination_id
            )
            if not destination_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=destination_material_response.code,
                    data=None,
                    message=destination_material_response.message,
                )
            destination_material = destination_material_response.data
            if not destination_material:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Destination material with ID {destination_id} not found",
                    details={"error": "Destination material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Destination material with ID {destination_id} not found",
                )
            if destination_material.material_type != "folder":
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Destination material with ID {destination_id} is not a folder",
                    details={"error": "Destination material is not a folder"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Destination material with ID {destination_id} is not a folder",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=400,
                    message="Failed to retrieve logged-in user",
                    details={"error": "Failed to retrieve logged-in user"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Failed to retrieve logged-in user",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=401,
                    message="Logged-in user not found",
                    details={"error": "Logged-in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message="Logged-in user not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=destination_material.subject_id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user {logged_in_user.id} on subject {destination_material.subject_id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            author_id = logged_in_user.id
            access_token_response = await self.helper_service.get_google_access_token(
                logged_in_user.google_refresh_token
            )
            if not access_token_response.success:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=access_token_response.code or 500,
                    message="Failed to retrieve Google access token",
                    details={"error": access_token_response.message},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=access_token_response.code,
                    data=None,
                    message=access_token_response.message,
                )
            access_token = access_token_response.data
            if not access_token:
                await self.logger.log(
                    action="CopyMany",
                    entity="Material",
                    level="error",
                    code=500,
                    message="Google access token is None",
                    details={"error": "Google access token is None"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to retrieve Google access token",
                )
            for material_id in material_ids:
                copy_response = await self._recursive_copy(
                    material_id,
                    destination_material.id,
                    author_id,
                    access_token,
                )
                if not copy_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=copy_response.code,
                        data=None,
                        message=copy_response.message,
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Files copied successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="CopyMany",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while copying materials",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while copying materials",
            )

    async def fetch_materials_from_drive(self, data):
        try:
            url = data.url
            subject_id = data.subject_id
            parent_id = data.parent_id
            file_id = self.helper_service.get_file_id_from_url(url)
            if not file_id:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Invalid URL format: {url}",
                    details={"error": "Could not extract file ID from URL"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid URL format: {url}",
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Subject, ["user_subject_links.user"]
            )
            subject_response = await self.subject_repository.find_one(
                Subject.id == subject_id, dynamic_includes
            )
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )
            subject = subject_response.data
            if not subject:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Subject with ID {subject_id} not found",
                    details={"error": "Subject not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Subject with ID {subject_id} not found",
                )
            user_ids = [user.id for user in subject.users] if subject.users else []
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            verify_restricted_access_response = (
                await self.helper_service.verify_restricted_access(
                    subject_id=subject_id
                )
            )
            if not verify_restricted_access_response.success:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=verify_restricted_access_response.code or 500,
                    message=f"Failed to verify restricted access for user {logged_in_user.id} on subject {subject_id}: {verify_restricted_access_response.message}",
                    details={"error": verify_restricted_access_response.error},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=verify_restricted_access_response.code,
                    data=None,
                    message=verify_restricted_access_response.message,
                )
            parent = None
            if parent_id:
                parent_response = await self.material_repository.find_one(
                    Material.id == parent_id
                )
                if not parent_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=parent_response.code,
                        data=None,
                        message=parent_response.message,
                    )
                parent = parent_response.data
                if not parent:
                    await self.logger.log(
                        action="FetchMaterialsFromDrive",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Parent material with ID {parent_id} not found",
                        details={"error": "Parent material not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Parent material with ID {parent_id} not found",
                    )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=logged_in_user_response.code or 500,
                    message=f"Failed to get logged in user",
                    details={"error": logged_in_user_response.message},
                    source="MaterialService",
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
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=401,
                    message=f"Logged in user not found",
                    details={"error": "Logged in user not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=None,
                    message=f"Logged in user not found",
                )
            author_id = logged_in_user.id
            fetched_data_response = await self.helper_service.fetch_from_drive(file_id)
            if not fetched_data_response.success:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=fetched_data_response.code or 500,
                    message=f"Failed to fetch data from Google Drive for file ID {file_id}",
                    details={"error": fetched_data_response.message},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=fetched_data_response.code,
                    data=None,
                    message=fetched_data_response.message,
                )
            fetched_data = fetched_data_response.data
            if not fetched_data:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to fetch data from Google Drive for file ID {file_id}",
                    details={"error": "No data returned from Google Drive"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to fetch data from Google Drive, please try again later.",
                )
            create_response = await self._recursive_create_from_drive(
                fetched_data, subject_id, parent_id, author_id
            )
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_data = create_response.data
            if not created_data:
                await self.logger.log(
                    action="FetchMaterialsFromDrive",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to create materials from Google Drive data for file ID {file_id}",
                    details={"error": "No data returned after creating materials"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to create materials from Google Drive data, please try again later.",
                )
            share_link = f"/user/materials/{subject_id}"
            if parent_id:
                share_link += f"/{parent_id}"
            if len(fetched_data.children) == 0:
                share_link += f"?material_id={created_data.id}"
            await self.helper_service.send_notification(
                notification_type=Notification.NotificationType.MATERIAL,
                parent_id=created_data.id,
                user_ids=user_ids,
                content=f"New material '{created_data.name}' has been fetched from drive to subject '{subject.name}'",
                url=share_link,
            )
            await self.logger.log(
                action="FetchMaterialsFromDrive",
                entity="Material",
                level="info",
                code=200,
                message=f"Materials fetched and created successfully from Google Drive for file ID {file_id}",
                details={},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Materials fetched and created successfully from Google Drive",
            )
        except Exception as ex:
            await self.logger.log(
                action="FetchMaterialsFromDrive",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while fetching materials from Google Drive",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching materials from Google Drive",
            )

    # Material Specific Functions
    async def _generate_unique_name(
        self, name: str | None, subject_id: int | None, parent_id: int | None
    ) -> BaseResponseDto[str]:
        try:
            if not name:
                name = "Untitled"
            name = name.strip()
            if (
                name.endswith(")")
                or name.rfind("(") != -1
                and Validator.is_int(name[name.rfind("(") + 1 : -1])
            ):
                name = name[: name.rfind("(")].strip()
            while True:
                existing_material_response = await self.material_repository.find_one(
                    and_(
                        Material.name == name,
                        Material.subject_id == subject_id,
                        Material.parent_id == parent_id,
                    )
                )
                if not existing_material_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=existing_material_response.code,
                        data=None,
                        message=existing_material_response.message,
                    )
                existing_material = existing_material_response.data
                if not existing_material:
                    return BaseResponseDto(
                        success=True,
                        code=200,
                        data=name,
                        message="Unique name generated successfully",
                    )
                if name.endswith(")"):
                    base_name = name[: name.rfind("(")].strip()
                    count_str = name[name.rfind("(") + 1 : -1]
                    if Validator.is_int(count_str):
                        count = int(count_str) + 1
                    else:
                        count = 1
                else:
                    base_name = name
                    count = 1
                name = f"{base_name} ({count})"
        except Exception as ex:
            await self.logger.log(
                action="GenerateUniqueName",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while generating unique name for material",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while generating unique name for material",
            )

    async def _remove_files(self, files: list) -> None:
        try:
            for file in files:
                user_id = file.get("user_id")
                file_id = file.get("file_id")
                if not user_id or not file_id:
                    await self.logger.log(
                        action="RemoveFiles",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Invalid file data: {file}",
                        details={"error": "Invalid file data"},
                        source="MaterialService",
                    )
                    return
                user_response = await self.user_repository.find_one(User.id == user_id)
                if not user_response.success:
                    return
                user = user_response.data
                if not user:
                    await self.logger.log(
                        action="RemoveFiles",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"User with ID {user_id} not found",
                        details={"error": "User not found"},
                        source="MaterialService",
                    )
                    return
                access_token_response = (
                    await self.helper_service.get_google_access_token(
                        user.google_refresh_token
                    )
                )
                if not access_token_response.success:
                    return
                access_token = access_token_response.data
                if not access_token:
                    await self.logger.log(
                        action="RemoveFiles",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to retrieve Google access token for user with ID {user_id}",
                        details={"error": "Failed to retrieve Google access token"},
                        source="MaterialService",
                    )
                    return
                delete_file_response = await self.helper_service.delete_file_from_drive(
                    access_token, file_id
                )
                if not delete_file_response.success:
                    await self.logger.log(
                        action="RemoveFiles",
                        entity="Material",
                        level="error",
                        code=delete_file_response.code or 500,
                        message=delete_file_response.message or "",
                        details={"error": delete_file_response.error},
                        source="MaterialService",
                    )
        except Exception as ex:
            await self.logger.log(
                action="RemoveFiles",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while removing files",
                details={"error": repr(ex)},
                source="MaterialService",
            )

    async def _recursive_delete(
        self, material_id: int, files: list
    ) -> BaseResponseDto[bool]:
        try:
            existing_material_response = await self.material_repository.find_one(
                Material.id == material_id
            )
            if not existing_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_material_response.code,
                    data=None,
                    message=existing_material_response.message,
                )
            existing_material = existing_material_response.data
            if not existing_material:
                await self.logger.log(
                    action="RecursiveDelete",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Material with ID {material_id} not found",
                    details={"error": "Material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Material with ID {material_id} not found",
                )
            if (
                existing_material.material_type == "file"
                and not existing_material.details.get("fetched")
            ):
                files.append(
                    {
                        "user_id": existing_material.author_id,
                        "file_id": self.helper_service.get_file_id_from_url(
                            existing_material.url or ""
                        ),
                    }
                )
            child_materials_response = await self.material_repository.find(
                Material.parent_id == material_id
            )
            if not child_materials_response.success:
                return BaseResponseDto(
                    success=False,
                    code=child_materials_response.code,
                    data=None,
                    message=child_materials_response.message,
                )
            child_materials = child_materials_response.data
            for child in child_materials or []:
                recursive_delete_response = await self._recursive_delete(
                    child.id, files
                )
                if not recursive_delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=recursive_delete_response.code,
                        data=None,
                        message=recursive_delete_response.message,
                    )
            delete_response = await self.material_repository.delete(existing_material)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Material deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="RecursiveDelete",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while recursively deleting material with ID {material_id}",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while trying to delete material with ID {material_id}",
            )

    async def _recursive_get_parents(
        self, material_id: int, parents: list[Material]
    ) -> BaseResponseDto[list[Material]]:
        try:
            existing_material_response = await self.material_repository.find_one(
                Material.id == material_id
            )
            if not existing_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_material_response.code,
                    data=None,
                    message=existing_material_response.message,
                )
            existing_material = existing_material_response.data
            if not existing_material:
                await self.logger.log(
                    action="RecursiveGetParents",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Material with ID {material_id} not found",
                    details={"error": "Material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Material with ID {material_id} not found",
                )
            parents.append(existing_material)
            if existing_material.parent_id:
                return await self._recursive_get_parents(
                    existing_material.parent_id, parents
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=parents[::-1],
                message="Parent materials fetched successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="RecursiveGetParents",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while recursively fetching parent materials for material with ID {material_id}",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while trying to fetch parent materials for material with ID {material_id}",
            )

    async def _recursive_copy(
        self,
        material_id: int,
        destination_id: int,
        author_id: int,
        access_token: str,
    ) -> BaseResponseDto[bool]:
        try:
            existing_material_response = await self.material_repository.find_one(
                Material.id == material_id
            )
            if not existing_material_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_material_response.code,
                    data=None,
                    message=existing_material_response.message,
                )
            existing_material = existing_material_response.data
            if not existing_material:
                await self.logger.log(
                    action="RecursiveCopy",
                    entity="Material",
                    level="error",
                    code=404,
                    message=f"Material with ID {material_id} not found",
                    details={"error": "Material not found"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"Material with ID {material_id} not found",
                )
            new_material = Material(
                name=existing_material.name,
                material_type=existing_material.material_type,
                url=existing_material.url,
                details=existing_material.details,
                subject_id=existing_material.subject_id,
                parent_id=destination_id,
                author_id=author_id,
            )
            unique_name_response = await self._generate_unique_name(
                new_material.name, new_material.subject_id, new_material.parent_id
            )
            if not unique_name_response.success:
                return BaseResponseDto(
                    success=False,
                    code=unique_name_response.code,
                    data=None,
                    message=unique_name_response.message,
                )
            new_material.name = unique_name_response.data
            if existing_material.material_type == "file":
                file_id = self.helper_service.get_file_id_from_url(
                    existing_material.url or ""
                )
                if not file_id:
                    await self.logger.log(
                        action="RecursiveCopy",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Invalid file URL for material with ID {material_id}",
                        details={"error": "Invalid file URL"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Invalid file URL for material with ID {material_id}",
                    )
                copy_file_response = await self.helper_service.copy_file_on_drive(
                    access_token, file_id
                )
                if not copy_file_response.success:
                    await self.logger.log(
                        action="RecursiveCopy",
                        entity="Material",
                        level="error",
                        code=copy_file_response.code or 500,
                        message=copy_file_response.message or "",
                        details={"error": copy_file_response.error},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=copy_file_response.code,
                        data=None,
                        message=copy_file_response.message,
                    )
                copied_file = copy_file_response.data
                if not copied_file:
                    await self.logger.log(
                        action="RecursiveCopy",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to copy file for material with ID {material_id}",
                        details={"error": "No data returned from copy_file_on_drive"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to copy file for material with ID {material_id}",
                    )
                new_material.url = self.helper_service.get_file_url_from_id(
                    copied_file.id
                )
                new_material.details["fetched"] = False
                new_material.details["file_data"] = copied_file.model_dump(mode="json")
            create_response = await self.material_repository.create(new_material)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_material = create_response.data
            if not created_material:
                await self.logger.log(
                    action="RecursiveCopy",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to create new material during recursive copy",
                    details={"error": "No data returned from repository"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to create new material during recursive copy",
                )
            child_materials_response = await self.material_repository.find(
                Material.parent_id == material_id
            )
            if not child_materials_response.success:
                return BaseResponseDto(
                    success=False,
                    code=child_materials_response.code,
                    data=None,
                    message=child_materials_response.message,
                )
            child_materials = child_materials_response.data
            for child in child_materials or []:
                recursive_copy_response = await self._recursive_copy(
                    child.id,
                    created_material.id,
                    author_id,
                    access_token,
                )
                if not recursive_copy_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=recursive_copy_response.code,
                        data=None,
                        message=recursive_copy_response.message,
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Material copied successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="RecursiveCopy",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while recursively copying material with ID {material_id}",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while trying to copy material with ID {material_id}",
            )

    async def _recursive_create_from_drive(
        self,
        fetched_data: FetchedModel,
        subject_id: int | None,
        parent_id: int | None,
        author_id: int,
    ) -> BaseResponseDto[Material]:
        try:
            fetched_file = fetched_data.data
            fetched_file_type = "file" if len(fetched_data.children) < 1 else "folder"
            new_material = Material(
                name=fetched_file.name,
                material_type=fetched_file_type,
                subject_id=subject_id,
                parent_id=parent_id,
                author_id=author_id,
            )
            if fetched_file_type == "file":
                new_material.url = self.helper_service.get_file_url_from_id(
                    fetched_file.id
                )
                new_material.details = {
                    "fetched": True,
                    "file_data": fetched_file.model_dump(mode="json"),
                }
            unique_name_response = await self._generate_unique_name(
                new_material.name, new_material.subject_id, new_material.parent_id
            )
            if not unique_name_response.success:
                return BaseResponseDto(
                    success=False,
                    code=unique_name_response.code,
                    data=None,
                    message=unique_name_response.message,
                )
            new_material.name = unique_name_response.data
            create_response = await self.material_repository.create(new_material)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_material = create_response.data
            if not created_material:
                await self.logger.log(
                    action="RecursiveCreateFromDrive",
                    entity="Material",
                    level="error",
                    code=500,
                    message=f"Failed to create new material from Drive for file ID {fetched_file.id}",
                    details={"error": "No data returned from repository"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to create new material from Drive",
                )
            for child in fetched_data.children or []:
                recursive_create_response = await self._recursive_create_from_drive(
                    child, subject_id, created_material.id, author_id
                )
                if not recursive_create_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=recursive_create_response.code,
                        data=None,
                        message=recursive_create_response.message,
                    )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_material,
                message=f"Successfully created material from Drive",
            )
        except Exception as ex:
            await self.logger.log(
                action="RecursiveCreateFromDrive",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while recursively creating material from Drive with file ID {fetched_data.data.id}",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while trying to create material from Drive",
            )
