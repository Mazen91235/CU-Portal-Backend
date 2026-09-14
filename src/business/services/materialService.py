from sqlalchemy import and_
import re
from datetime import datetime, timezone
from collections.abc import AsyncGenerator
from stat import S_IFDIR, S_IFREG
import struct
import zlib
from core.iServices.iMaterialService import IMaterialService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.material import Material
from core.entities.subject import Subject
from core.entities.user import User
from core.entities.week import Week
from core.entities.notification import Notification
from core.entities.attachment import Attachment
from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import FetchedModel
from core.utils.validator import Validator


class MaterialService(IMaterialService):
    def __init__(
        self,
        material_repository: IBaseRepository[Material],
        subject_repository: IBaseRepository[Subject],
        user_repository: IBaseRepository[User],
        week_repository: IBaseRepository[Week],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.material_repository = material_repository
        self.subject_repository = subject_repository
        self.user_repository = user_repository
        self.week_repository = week_repository
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
            if data.material_type != "folder" and not data.details.get("url"):
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
                    data.details.get("url", ""), data.material_type
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
            subject_response = await self.subject_repository.find_one(
                Subject.id == data.subject_id,
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
            if data.week_id:
                if data.material_type == "folder":
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Week ID should not be provided for folder type materials",
                        details={"error": "Week ID is not applicable for folders"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Week ID should not be provided for folder type materials",
                    )
                week_response = await self.week_repository.find_one(
                    Week.id == data.week_id
                )
                if not week_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=week_response.code,
                        data=None,
                        message=week_response.message,
                    )
                week = week_response.data
                if not week:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Week with ID {data.week_id} not found",
                        details={"error": "Week not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Week with ID {data.week_id} not found",
                    )
                if (
                    week.faculty_id != subject.faculty_id
                    or week.department_id != subject.department_id
                    or week.year_id != subject.year_id
                ):
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Week with ID {data.week_id} does not belong to the same faculty, department, or year as the subject {subject.id}",
                        details={
                            "error": "Week does not match subject's faculty, department, or year"
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Week with ID {data.week_id} does not belong to the same faculty, department, or year as the subject {subject.id}",
                    )
            data.author_id = logged_in_user.id
            data.details = data.details or {}
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
            url = data.details.get("url")
            data.details.pop("url", None)
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
            if data.material_type != "folder":
                if data.material_type == "file":
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=True,
                        url=url or "",
                        author_id=logged_in_user.id,
                        source_name="material_id",
                        source_id=created_material.id,
                    )
                else:
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=False,
                        url=url or "",
                        author_id=logged_in_user.id,
                        source_name="material_id",
                        source_id=created_material.id,
                        link_title=created_material.name,
                    )

                if not attachment_response.success:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=attachment_response.code or 500,
                        message=f"Failed to create attachment for material {created_material.id}: {attachment_response.message}",
                        details={"error": attachment_response.error},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=f"Failed to create attachment for material, please try again later.",
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for material {created_material.id}, no data returned from repository",
                        details={"error": "No data returned from repository"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to create attachment for material, please try again later.",
                    )
                created_material.attachment = attachment
            share_link = f"/user/materials/{subject_id}"
            if parent_id:
                share_link += f"/{parent_id}"
            if data.material_type == "file":
                share_link += f"?material_id={created_material.id}"
            elif data.material_type != "folder":
                share_link = created_material.attachment.url
            await self.helper_service.send_notification(
                Notification.NotificationType.MATERIAL,
                created_material.id,
                f"New material '{created_material.name}' has been created for subject {subject.name}.",
                share_link,
                subject_id=created_material.subject_id,
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
            if data.material_type != "folder" and not data.details.get("url"):
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
                    data.details.get("url") or "", data.material_type
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
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, ["attachment"]
            )
            existing_material_response = await self.material_repository.find_one(
                Material.id == data.id, dynamic_includes
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
            if data.week_id:
                if (
                    data.material_type == "folder"
                    or existing_material.material_type == "folder"
                ):
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Week ID should not be provided for folder type materials",
                        details={"error": "Week ID is not applicable for folders"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Week ID should not be provided for folder type materials",
                    )
                week_response = await self.week_repository.find_one(
                    Week.id == data.week_id
                )
                if not week_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=week_response.code,
                        data=None,
                        message=week_response.message,
                    )
                week = week_response.data
                if not week:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Week with ID {data.week_id} not found",
                        details={"error": "Week not found"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Week with ID {data.week_id} not found",
                    )
                if (
                    week.faculty_id != subject.faculty_id
                    or week.department_id != subject.department_id
                    or week.year_id != subject.year_id
                ):
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Week with ID {data.week_id} does not belong to the same faculty, department, or year as the subject {subject.id}",
                        details={
                            "error": "Week does not match subject's faculty, department, or year"
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=f"Week with ID {data.week_id} does not belong to the same faculty, department, or year as the subject {subject.id}",
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
            to_be_removed = None
            url = data.details.get("url")
            data.details.pop("url", None)
            if (
                data.material_type != "folder"
                and existing_material.material_type != "folder"
                and url != existing_material.attachment.url
            ):
                to_be_removed = existing_material.attachment
            data.author_id = logged_in_user.id
            updated_material_response = await self.material_repository.update(
                data, ["name", "material_type", "details", "author_id"]
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
                await self.helper_service.delete_attachment(attachment=to_be_removed)
                if updated_material.material_type == "file":
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=True,
                        url=url or "",
                        author_id=logged_in_user.id,
                        source_name="material_id",
                        source_id=updated_material.id,
                    )
                else:
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=False,
                        url=url or "",
                        author_id=logged_in_user.id,
                        source_name="material_id",
                        source_id=updated_material.id,
                        link_title=updated_material.name,
                    )
                if not attachment_response.success:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=attachment_response.code or 500,
                        message=f"Failed to create attachment for material {updated_material.id}: {attachment_response.message}",
                        details={"error": attachment_response.error},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=f"Failed to create attachment for material, please try again later.",
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for material {updated_material.id}, no data returned from repository",
                        details={"error": "No data returned from repository"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to create attachment for material, please try again later.",
                    )
                updated_material.attachment = attachment
            user_ids = [user.id for user in subject.users] if subject.users else []
            share_link = f"/user/materials/{updated_material.subject_id}"
            if updated_material.parent_id:
                share_link += f"/{updated_material.parent_id}"
            if updated_material.material_type == "file":
                share_link += f"?material_id={updated_material.id}"
            elif updated_material.material_type != "folder":
                share_link = updated_material.attachment.url
            await self.helper_service.send_notification(
                Notification.NotificationType.MATERIAL,
                updated_material.id,
                f"Material '{updated_material.name}' has been updated for subject {subject.name}.",
                share_link,
                subject_id=updated_material.subject_id,
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
            attachment_ids = []
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
                delete_response = await self._recursive_delete(
                    material_id, attachment_ids
                )
                if not delete_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_response.code,
                        data=None,
                        message=delete_response.message,
                    )
            for attachment_id in attachment_ids:
                await self.helper_service.delete_attachment(attachment_id=attachment_id)
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
            subject_id = data.subject_id
            destination_id = data.destination_id
            destination_material = None
            if destination_id is not None:
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
                if destination_material.subject_id != subject_id:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=400,
                        message="Destination material does not belong to the provided subject",
                        details={"error": "Destination subject mismatch"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Destination material must belong to the provided subject",
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
                    subject_id=subject_id
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
                if existing_material.subject_id != subject_id:
                    await self.logger.log(
                        action="MoveMany",
                        entity="Material",
                        level="error",
                        code=400,
                        message=f"Material {material_id} does not belong to the provided subject",
                        details={"error": "Material subject mismatch"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="All materials must belong to the provided subject",
                    )
                if destination_material and existing_material.parent_id == destination_material.id:
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
                if destination_material and existing_material.id == destination_material.id:
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
                existing_material.parent_id = destination_id
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
            subject_id = data.subject_id
            destination_id = data.destination_id
            subject_response = await self.subject_repository.find_one(
                Subject.id == subject_id
            )
            if not subject_response.success:
                return BaseResponseDto(
                    success=False,
                    code=subject_response.code,
                    data=None,
                    message=subject_response.message,
                )
            if not subject_response.data:
                await self.logger.log(
                    action="CopyMany",
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
            destination_material = None
            if destination_id is not None:
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
                if destination_material.subject_id != subject_id:
                    await self.logger.log(
                        action="CopyMany",
                        entity="Material",
                        level="error",
                        code=400,
                        message="Destination material does not belong to the provided subject",
                        details={"error": "Destination subject mismatch"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Destination material must belong to the provided subject",
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
                    destination_id,
                    author_id,
                    access_token,
                    subject_id,
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
            subject_response = await self.subject_repository.find_one(
                Subject.id == subject_id
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
                content=f"New material '{created_data.name}' has been fetched from drive to subject '{subject.name}'",
                url=share_link,
                subject_id=created_data.subject_id,
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

    async def download_many(self, data):
        try:
            material_ids = data.material_ids
            selected_material_ids = set(material_ids)
            roots = []

            for material_id in material_ids:
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Material, ["attachment"]
                )
                material_response = await self.material_repository.find_one(
                    Material.id == material_id, dynamic_includes
                )
                if not material_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=material_response.code,
                        data=None,
                        message=material_response.message,
                    )

                material = material_response.data
                if not material:
                    await self.logger.log(
                        action="DownloadMany",
                        entity="Material",
                        level="error",
                        code=404,
                        message=f"Material with ID {material_id} not found",
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message=f"Material with ID {material_id} not found",
                    )

                if await self._has_selected_ancestor(material, selected_material_ids):
                    continue

                tree_response = await self._build_download_tree(material)
                if not tree_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=tree_response.code,
                        data=None,
                        message=tree_response.message,
                    )
                roots.append(tree_response.data)

            if not roots:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="No materials available for download",
                )

            return BaseResponseDto(
                success=True,
                code=200,
                data={
                    "stream": self._stream_download_zip(roots),
                    "filename": "archive.zip",
                },
                message="Materials download prepared successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="DownloadMany",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while preparing materials download",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while processing the request",
                error=repr(ex),
            )

    # Helper Functions
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

    async def _recursive_delete(
        self, material_id: int, attachment_ids: list[int]
    ) -> BaseResponseDto[bool]:
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, ["attachment"]
            )
            existing_material_response = await self.material_repository.find_one(
                Material.id == material_id, dynamic_includes
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
            if existing_material.material_type != "folder":
                attachment_ids.append(existing_material.attachment.id)
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
                    child.id, attachment_ids
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
        destination_id: int | None,
        author_id: int,
        access_token: str,
        subject_id: int,
    ) -> BaseResponseDto[bool]:
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, ["attachment"]
            )
            existing_material_response = await self.material_repository.find_one(
                Material.id == material_id, dynamic_includes
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
            if existing_material.subject_id != subject_id:
                await self.logger.log(
                    action="RecursiveCopy",
                    entity="Material",
                    level="error",
                    code=400,
                    message=f"Material with ID {material_id} does not belong to subject with ID {subject_id}",
                    details={"error": "Material does not belong to the provided subject"},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Material with ID {material_id} does not belong to subject with ID {subject_id}",
                )
            new_material = Material(
                name=existing_material.name,
                material_type=existing_material.material_type,
                details=existing_material.details,
                subject_id=subject_id,
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
            if existing_material.material_type != "folder":
                if existing_material.material_type == "file":
                    file_id = self.helper_service.get_file_id_from_url(
                        existing_material.attachment.url or ""
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
                            details={
                                "error": "No data returned from copy_file_on_drive"
                            },
                            source="MaterialService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=500,
                            data=None,
                            message=f"Failed to copy file for material with ID {material_id}",
                        )
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=True,
                        url=self.helper_service.get_file_url_from_id(copied_file.id)
                        or "",
                        author_id=author_id,
                        source_name="material_id",
                        source_id=created_material.id,
                    )
                else:
                    attachment_response = await self.helper_service.create_attachment(
                        is_file=False,
                        url=existing_material.attachment.url or "",
                        author_id=author_id,
                        source_name="material_id",
                        source_id=created_material.id,
                        link_title=(
                            existing_material.attachment.details.get("link_title")
                            if existing_material.attachment.details
                            else None
                        ),
                    )
                if not attachment_response.success:
                    await self.logger.log(
                        action="RecursiveCopy",
                        entity="Material",
                        level="error",
                        code=attachment_response.code or 500,
                        message=attachment_response.message or "",
                        details={"error": attachment_response.error},
                        source="MaterialService",
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
                        action="RecursiveCopy",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for copied file for material with ID {material_id}",
                        details={"error": "No data returned from create_attachment"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to create attachment for copied file for material with ID {material_id}",
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
                    subject_id,
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
            if fetched_file_type == "file":
                attachment_response = await self.helper_service.create_attachment(
                    is_file=True,
                    url=self.helper_service.get_file_url_from_id(fetched_file.id) or "",
                    author_id=author_id,
                    source_name="material_id",
                    source_id=created_material.id,
                    fetched=True,
                )
                if not attachment_response.success:
                    await self.logger.log(
                        action="RecursiveCreateFromDrive",
                        entity="Material",
                        level="error",
                        code=attachment_response.code or 500,
                        message=attachment_response.message or "",
                        details={"error": attachment_response.error},
                        source="MaterialService",
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
                        action="RecursiveCreateFromDrive",
                        entity="Material",
                        level="error",
                        code=500,
                        message=f"Failed to create attachment for material from Drive for file ID {fetched_file.id}",
                        details={"error": "No data returned from create_attachment"},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to create attachment for material from Drive",
                    )
                created_material.attachment = attachment
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

    async def _iter_download_zip_members(
        self, roots: list[dict]
    ) -> AsyncGenerator[tuple[str, datetime, int, AsyncGenerator], None]:
        root_links = []

        for root in roots:
            material = root["material"]
            if material.material_type in {"youtube", "drive", "external"}:
                root_links.append(material)
                continue

            async for member in self._iter_download_members(root):
                yield member

        if root_links:
            yield (
                "links.txt",
                datetime.now(timezone.utc),
                S_IFREG | 0o644,
                self._iter_links_content(root_links),
            )

    @staticmethod
    def _zip_dos_datetime(modified_at: datetime) -> tuple[int, int]:
        if modified_at.tzinfo is not None:
            modified_at = modified_at.astimezone(timezone.utc)

        year = max(1980, min(modified_at.year, 2107))
        dos_time = (
            (modified_at.hour << 11)
            | (modified_at.minute << 5)
            | (modified_at.second // 2)
        )
        dos_date = ((year - 1980) << 9) | (modified_at.month << 5) | modified_at.day
        return dos_time, dos_date

    async def _stream_download_zip(
        self, roots: list[dict]
    ) -> AsyncGenerator[bytes, None]:
        offset = 0
        central_directory = []

        async for name, modified_at, mode, chunks in self._iter_download_zip_members(
            roots
        ):
            name_bytes = name.encode("utf-8")
            if len(name_bytes) > 0xFFFF:
                raise ValueError(f"ZIP member name is too long: {name}")

            dos_time, dos_date = self._zip_dos_datetime(modified_at)
            is_directory = bool(mode & S_IFDIR)
            flags = 0x0800  # UTF-8 names.
            compression = 0 if is_directory else 8  # Store directories, deflate files.
            external_attr = (mode << 16) | (0x10 if name_bytes.endswith(b"/") else 0)

            local_header_extra = b""
            if not is_directory:
                # ZIP64 local extra field. Actual sizes are written in the
                # trailing ZIP64 data descriptor after the streamed member.
                local_header_extra = struct.pack(
                    "<HHQQ",
                    0x0001,
                    16,
                    0,
                    0,
                )
                flags |= 0x0008  # Data descriptor follows member data.

            if is_directory:
                member_offset = offset
                local_header = struct.pack(
                    "<4sHHHHHIIIHH",
                    b"PK\x03\x04",
                    45,
                    flags,
                    compression,
                    dos_time,
                    dos_date,
                    0,
                    0,
                    0,
                    len(name_bytes),
                    len(local_header_extra),
                )
                local_header += name_bytes + local_header_extra

                yield local_header
                offset += len(local_header)

                central_directory.append(
                    (
                        name_bytes,
                        dos_time,
                        dos_date,
                        45,
                        flags,
                        compression,
                        0,
                        0,
                        0,
                        external_attr,
                        member_offset,
                    )
                )
                continue

            local_header = struct.pack(
                "<4sHHHHHIIIHH",
                b"PK\x03\x04",
                45,
                flags,
                compression,
                dos_time,
                dos_date,
                0,
                0xFFFFFFFF,
                0xFFFFFFFF,
                len(name_bytes),
                len(local_header_extra),
            )
            local_header += name_bytes + local_header_extra

            member_offset = offset
            yield local_header
            offset += len(local_header)

            stats = {
                "uncompressed_size": 0,
                "compressed_size": 0,
                "crc32": 0,
            }
            compressor = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)

            # Keep consuming the source stream until EOF. The ZIP member is
            # not complete until every source chunk has been processed.
            async for chunk in chunks:
                if not chunk:
                    continue

                stats["uncompressed_size"] += len(chunk)
                stats["crc32"] = zlib.crc32(chunk, stats["crc32"])

                compressed_chunk = compressor.compress(chunk)
                if compressed_chunk:
                    stats["compressed_size"] += len(compressed_chunk)
                    yield compressed_chunk
                    offset += len(compressed_chunk)

            compressed_chunk = compressor.flush()
            if compressed_chunk:
                stats["compressed_size"] += len(compressed_chunk)
                yield compressed_chunk
                offset += len(compressed_chunk)

            descriptor = struct.pack(
                "<4sIQQ",
                b"PK\x07\x08",
                stats["crc32"] & 0xFFFFFFFF,
                stats["compressed_size"],
                stats["uncompressed_size"],
            )
            yield descriptor
            offset += len(descriptor)

            central_directory.append(
                (
                    name_bytes,
                    dos_time,
                    dos_date,
                    45,
                    flags,
                    compression,
                    stats["crc32"] & 0xFFFFFFFF,
                    stats["compressed_size"],
                    stats["uncompressed_size"],
                    external_attr,
                    member_offset,
                )
            )

        central_directory_offset = offset

        for entry in central_directory:
            (
                name_bytes,
                dos_time,
                dos_date,
                version,
                flags,
                compression,
                crc32,
                compressed_size,
                uncompressed_size,
                external_attr,
                member_offset,
            ) = entry

            central_extra = struct.pack(
                "<HHQQQ",
                0x0001,
                24,
                uncompressed_size,
                compressed_size,
                member_offset,
            )

            central_header = struct.pack(
                "<4sHHHHHHIIIHHHHHII",
                b"PK\x01\x02",
                (3 << 8) | 45,
                version,
                flags,
                compression,
                dos_time,
                dos_date,
                crc32,
                0xFFFFFFFF,
                0xFFFFFFFF,
                len(name_bytes),
                len(central_extra),
                0,
                0,
                0,
                external_attr,
                0xFFFFFFFF,
            )
            central_header += name_bytes + central_extra

            yield central_header
            offset += len(central_header)

        central_directory_size = offset - central_directory_offset
        entry_count = len(central_directory)

        zip64_end_offset = offset
        zip64_end = struct.pack(
            "<4sQHHIIQQQQ",
            b"PK\x06\x06",
            44,
            45,
            45,
            0,
            0,
            entry_count,
            entry_count,
            central_directory_size,
            central_directory_offset,
        )
        yield zip64_end
        offset += len(zip64_end)

        zip64_locator = struct.pack(
            "<4sIQI",
            b"PK\x06\x07",
            0,
            zip64_end_offset,
            1,
        )
        yield zip64_locator
        offset += len(zip64_locator)

        end_of_central_directory = struct.pack(
            "<4sHHHHIIH",
            b"PK\x05\x06",
            0xFFFF,
            0xFFFF,
            0xFFFF,
            0xFFFF,
            0xFFFFFFFF,
            0xFFFFFFFF,
            0,
        )
        yield end_of_central_directory

    async def _iter_links_content(
        self, materials: list[Material]
    ) -> AsyncGenerator[bytes, None]:
        for material in materials:
            attachment = material.attachment
            if not attachment or not attachment.url:
                continue
            details = attachment.details or {}
            link_title = details.get("link_title") or material.name or ""
            yield f"{link_title}: {attachment.url}\n".encode("utf-8")

    async def _has_selected_ancestor(
        self, material: Material, selected_material_ids: set[int]
    ) -> bool:
        parent_id = material.parent_id
        visited = set()

        while parent_id:
            if parent_id in selected_material_ids:
                return True
            if parent_id in visited:
                return False
            visited.add(parent_id)

            parent_response = await self.material_repository.find_one(
                Material.id == parent_id
            )
            if not parent_response.success or not parent_response.data:
                return False
            parent = parent_response.data
            parent_id = parent.parent_id

        return False

    async def _build_download_tree(self, material: Material) -> BaseResponseDto[dict]:
        try:
            node = {
                "material": material,
                "children": [],
            }

            if material.material_type != "folder":
                if material.material_type not in {
                    "file",
                    "youtube",
                    "drive",
                    "external",
                }:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=(
                            f"Material with ID {material.id} has an unsupported "
                            f"material type: {material.material_type}"
                        ),
                    )

                if not material.attachment or not material.attachment.url:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message=(
                            f"Material with ID {material.id} does not have a "
                            "downloadable attachment"
                        ),
                    )

                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=node,
                )

            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Material, ["attachment"]
            )
            children_response = await self.material_repository.find(
                Material.parent_id == material.id,
                dynamic_includes,
                limit=int(1e6),
            )
            if not children_response.success:
                return BaseResponseDto(
                    success=False,
                    code=children_response.code,
                    data=None,
                    message=children_response.message,
                )

            for child in children_response.data or []:
                child_response = await self._build_download_tree(child)
                if not child_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=child_response.code,
                        data=None,
                        message=child_response.message,
                    )
                child_data = child_response.data
                if not child_data:
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message=f"Failed to build download tree for child material with ID {child.id}",
                    )
                node["children"].append(child_data)

            return BaseResponseDto(
                success=True,
                code=200,
                data=node,
            )
        except Exception as ex:
            await self.logger.log(
                action="BuildDownloadTree",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while preparing material with ID {material.id}",
                details={"error": repr(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message=f"An error occurred while preparing material with ID {material.id}",
                error=repr(ex),
            )

    async def _iter_download_members(
        self, node: dict, parent_path=""
    ) -> AsyncGenerator:
        material = node["material"]
        children = node["children"] or []
        safe_name = self._sanitize_zip_name(material.name or f"material-{material.id}")
        current_path = f"{parent_path}/{safe_name}" if parent_path else safe_name
        modified_at = (
            material.updated_at or material.created_at or datetime.now(timezone.utc)
        )

        if material.material_type == "folder":
            yield (
                f"{current_path}/",
                modified_at,
                S_IFDIR | 0o755,
                (),
            )

            link_materials = []
            for child in children:
                if child["material"].material_type in {"youtube", "drive", "external"}:
                    link_materials.append(child["material"])

            for child in children:
                if child["material"].material_type not in {
                    "youtube",
                    "drive",
                    "external",
                }:
                    async for member in self._iter_download_members(
                        child, current_path
                    ):
                        yield member

            if link_materials:
                yield (
                    f"{current_path}/links.txt",
                    modified_at,
                    S_IFREG | 0o644,
                    self._iter_links_content(link_materials),
                )
            return

        if material.material_type in {"youtube", "drive", "external"}:
            return

        attachment = material.attachment
        if not attachment or not attachment.url:
            raise ValueError(
                f"Material with ID {material.id} does not have a downloadable attachment"
            )

        file_name = self._get_attachment_file_name(material, attachment)
        file_path = f"{parent_path}/{file_name}" if parent_path else file_name

        yield (
            file_path,
            modified_at,
            S_IFREG | 0o644,
            self._stream_attachment_file(attachment),
        )

    async def _stream_attachment_file(
        self, attachment: Attachment
    ) -> AsyncGenerator[bytes, None]:
        details = attachment.details or {}
        file_data = details.get("file_data") or {}

        file_id = file_data.get("id") or self.helper_service.get_file_id_from_url(
            attachment.url
        )
        if not file_id:
            raise ValueError(
                f"Could not determine Google Drive file ID for attachment {attachment.id}"
            )

        download_response = await self.helper_service.download_file_from_drive(file_id)
        if not download_response.success:
            raise ValueError(
                download_response.error
                or download_response.message
                or f"Failed to download Google Drive file {file_id}"
            )

        downloaded_file = download_response.data
        if not downloaded_file or downloaded_file.content is None:
            raise ValueError(
                f"No download stream returned for Google Drive file {file_id}"
            )

        # Keep the returned async iterable alive and consume it directly in
        # this generator. The ZIP writer above awaits every chunk until EOF
        # before it writes the data descriptor and moves to the next member.
        async for chunk in downloaded_file.content:
            if chunk:
                yield chunk

    def _get_attachment_file_name(
        self, material: Material, attachment: Attachment
    ) -> str:
        details = attachment.details or {}
        file_data = details.get("file_data") or {}
        file_name = file_data.get("name") or material.name or f"material-{material.id}"
        return self._sanitize_zip_name(file_name)

    @staticmethod
    def _sanitize_zip_name(name: str) -> str:
        safe_name = re.sub(r'[\\\\/:*?"<>|]+', "_", str(name)).strip(" .")
        return safe_name or "unnamed"
