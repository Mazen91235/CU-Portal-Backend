import os
from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from core.iServices.iMaterialService import IMaterialService
from core.iServices.iUserService import IUserService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.material import Material
from core.entities.subject import Subject
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.userDtos import UserHasPermissionsDto
from core.utils.validator import Validator
from core.dtos.materialDtos import (
    MaterialUpdateDto,
    MaterialResponseDto,
    MaterialMinimalResponseDto,
)


class MaterialOperationError(Exception):
    def __init__(self, message: str, code: int = 500):
        super().__init__(message)
        self.code = code


class MaterialService(IMaterialService):
    def __init__(
        self,
        material_repository: IBaseRepository[Material],
        subject_repository: IBaseRepository[Subject],
        user_service: IUserService,
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.material_repository = material_repository
        self.subject_repository = subject_repository
        self.user_service = user_service
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.material_repository.begin_transaction()

    async def commit_transaction(self):
        await self.material_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.material_repository.rollback_transaction()

    # Private Helpers
    async def _generate_unique_name(
        self,
        subject_id: int,
        parent_id: int | None,
        material_type: str,
        base_name: str,
        exclude_id: int | None = None,
    ) -> str:
        if not base_name or base_name == "":
            base_name = "Untitled"
        base_name = base_name.strip()
        if (
            base_name.endswith(")")
            and base_name.rfind("(") != -1
            and base_name[base_name.rfind("(") + 1 : -1].isdigit()
        ):
            base_name = base_name[: base_name.rfind("(")].strip()

        unique_name = base_name
        counter = 1
        while True:
            conditions = [
                Material.subject_id == subject_id,
                Material.parent_id == parent_id,
                Material.type == material_type,
                Material.name == unique_name,
            ]
            if exclude_id is not None:
                conditions.append(Material.id != exclude_id)
            predicate = and_(*conditions)
            existing_response = await self.material_repository.find_one(predicate)
            if not existing_response.success or not existing_response.data:
                return unique_name
            unique_name = f"{base_name} ({counter})"
            counter += 1

    async def _count_descendants(
        self, material_id: int, count_files: bool = True
    ) -> int:

        # BaseRepository.find() enforces pagination via offset/limit with no way to disable it.
        # The limit=10000 used here is a hard cap, not optional — folders exceeding this size
        # will return incomplete results.

        count = 0
        material_response = await self.material_repository.find_one(
            Material.id == material_id
        )
        if not material_response.success:
            raise Exception(material_response.message)
        material = material_response.data
        if not material:
            return 0
        if material.type == "folder":
            children_response = await self.material_repository.find(
                Material.parent_id == material.id, limit=10000
            )
            if not children_response.success:
                raise Exception(children_response.message)
            children = children_response.data or []
            for child in children:
                count += (
                    1
                    if count_files
                    and child.type != "folder"
                    or not count_files
                    and child.type == "folder"
                    else 0
                )
                count += await self._count_descendants(child.id, count_files)
        return count

    async def _fetch_parents(self, material_id: int) -> list[dict]:
        parents = []
        current_id = material_id
        while current_id:
            material_response = await self.material_repository.find_one(
                Material.id == current_id
            )
            if not material_response.success:
                raise Exception(material_response.message)
            material = material_response.data
            if material:
                parents.append(material.min_to_dict())
                current_id = material.parent_id
            else:
                current_id = None
        parents.reverse()
        return parents

    async def _create_from_fetched_tree(
        self,
        fetched,
        subject_id: int,
        parent_id: int | None,
        author_id: int,
    ) -> Material:

        is_folder = self.helper_service.verify_file_type(
            fetched.data.mime_type, "folder"
        )
        material_type = "folder" if is_folder else "file"
        unique_name = await self._generate_unique_name(
            subject_id=subject_id,
            parent_id=parent_id,
            material_type=material_type,
            base_name=fetched.data.name,
        )

        material = Material(
            name=unique_name,
            subject_id=subject_id,
            parent_id=parent_id,
            author_id=author_id,
            type=material_type,
            url=None if is_folder else fetched.data.web_view_link,
            details=None if is_folder else {"file_data": fetched.data, "fetched": True},
        )
        create_response = await self.material_repository.create(material)
        if not create_response.success:
            raise Exception(create_response.message)
        created_material = create_response.data
        if not created_material:
            raise Exception(
                "Failed to create material while importing from Google Drive"
            )

        if is_folder:
            for child in fetched.children or []:
                await self._create_from_fetched_tree(
                    child, subject_id, created_material.id, author_id
                )

        return created_material

    async def _delete_recursive(self, material_id: int) -> None:
        material_response = await self.material_repository.find_one(
            Material.id == material_id,
            includes=[selectinload(Material.author)],
        )
        if not material_response.success:
            raise Exception(material_response.message)
        material = material_response.data
        if not material:
            return  # Already gone — matches old "consider it deleted"

        if material.type == "file" and not material.details.get("fetched", False):
            access_token_response = await self.helper_service.get_google_access_token(
                material.author.google_refresh_token or ""
            )
            if not access_token_response.success or not access_token_response.data:
                raise Exception(
                    f"Failed to delete material {material.name}. Please try again later."
                )
            access_token = access_token_response.data
            file_id = self.helper_service.get_file_id_from_url(material.url)
            removed_response = await self.helper_service.delete_file_from_drive(
                access_token, file_id
            )
            if not removed_response.success or not removed_response.data:
                raise Exception(
                    f"Failed to delete material {material.name}. Please try again later."
                )

        if material.type == "folder":
            children_response = await self.material_repository.find(
                Material.parent_id == material.id, limit=10000
            )
            if not children_response.success:
                raise Exception(children_response.message)
            for child in children_response.data or []:
                await self._delete_recursive(child.id)

        delete_response = await self.material_repository.delete(material)
        if not delete_response.success:
            raise Exception(
                f"Failed to delete material {material.name}. Please try again later."
            )

    async def _copy_recursive(
        self,
        material_id: int,
        subject_id: int,
        parent_id: int | None,
        author_id: int,
    ) -> Material:
        material_response = await self.material_repository.find_one(
            Material.id == material_id,
            includes=[selectinload(Material.author)],
        )
        if not material_response.success:
            raise Exception(material_response.message)
        material = material_response.data
        if not material:
            raise Exception("Material not found")

        new_name = await self._generate_unique_name(
            subject_id=subject_id,
            parent_id=parent_id,
            material_type=material.type,
            base_name=material.name,
        )

        new_url = material.url
        details = dict(material.details) if material.details else {}

        if material.type == "file":
            file_id = self.helper_service.get_file_id_from_url(material.url)
            if not file_id:
                raise MaterialOperationError("Invalid Request.", code=400)
            access_token_response = await self.helper_service.get_google_access_token(
                material.author.google_refresh_token or ""
            )
            if not access_token_response.success or not access_token_response.data:
                raise Exception("Failed to copy material(s).")
            access_token = access_token_response.data
            copied_file_response = await self.helper_service.copy_file_on_drive(
                access_token, file_id
            )
            if not copied_file_response.success or not copied_file_response.data:
                raise Exception("Failed to copy material(s).")
            copied_file = copied_file_response.data
            new_url = copied_file.web_view_link
            details["file_data"] = copied_file

        children = []
        if material.type == "folder":
            children_response = await self.material_repository.find(
                Material.parent_id == material.id, limit=10000
            )
            if not children_response.success:
                raise Exception(children_response.message)
            children = children_response.data or []

        new_material = Material(
            name=new_name,
            type=material.type,
            subject_id=subject_id,
            parent_id=parent_id,
            author_id=author_id,
            url=new_url,
            details=details,
        )
        create_response = await self.material_repository.create(new_material)
        if not create_response.success:
            raise Exception(create_response.message)
        created_material = create_response.data
        if not created_material:
            raise Exception("Failed to copy material(s).")

        for child in children:
            await self._copy_recursive(
                child.id, subject_id, created_material.id, author_id
            )

        return created_material

    # CRUD Functions
    async def update(self, data: MaterialUpdateDto):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            material_response = await self.material_repository.find_one(
                Material.id == data.id,
                includes=[
                    selectinload(Material.subject),
                    selectinload(Material.author),
                ],
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
                    action="Update",
                    entity="Material",
                    level="warning",
                    code=404,
                    message="Material not found with this ID",
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Material not found"
                )

            if material.author_id != current_user_id:
                has_permission_response = await self.user_service.has_permissions(
                    UserHasPermissionsDto(required_permissions=["Manage All Materials"])
                )
                if (
                    not has_permission_response.success
                    or not has_permission_response.data
                ):
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="warning",
                        code=403,
                        message="Unauthorized material update attempt by non-author user",
                        details={
                            "material_id": material.id,
                            "author_id": material.author_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=None,
                        message="You are not authorized to update this material",
                    )

            name = data.name
            description = data.description
            url = data.url
            file = None
            to_be_removed = False

            if name and name != "":
                material.name = await self._generate_unique_name(
                    subject_id=material.subject_id,
                    parent_id=material.parent_id,
                    material_type=material.type,
                    base_name=name,
                    exclude_id=material.id,
                )

            if description and description != "":
                material.details["description"] = description

            if material.type == "file" and url and url != material.url:
                file_id = self.helper_service.get_file_id_from_url(url)
                if not file_id:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid file URL provided for material update",
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid file provided",
                    )
                file_response = await self.helper_service.fetch_from_drive(file_id)
                if not file_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=file_response.code,
                        data=None,
                        message=file_response.message,
                    )
                file = file_response.data
                if not file:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="File not found",
                    )
                to_be_removed = not material.details.get("fetched", False)
                material.url = (
                    url if material.details.get("fetched", False) else material.url
                )
                material.details["file_data"] = file
                material.details["fetched"] = False

            if (
                material.type in ["youtube", "drive", "external"]
                and url
                and url != ""
                and url != material.url
            ):
                if material.type == "youtube" and not Validator.is_youtube_url(url):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid YouTube URL provided",
                    )
                if material.type == "drive" and not Validator.is_drive_url(url):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid Google Drive URL provided",
                    )
                if material.type == "external" and not Validator.is_valid_url(url):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid external URL provided",
                    )
                material.url = url

            if to_be_removed:
                access_token_response = (
                    await self.helper_service.get_google_access_token(
                        material.author.google_refresh_token or ""
                    )
                )
                if not access_token_response.success or not access_token_response.data:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=500,
                        message="Failed to get Google access token for removing old file",
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="Failed to update material. Please try again later.",
                    )
                access_token = access_token_response.data
                old_file_id = self.helper_service.get_file_id_from_url(material.url)
                removed_response = await self.helper_service.delete_file_from_drive(
                    access_token, old_file_id
                )
                if not removed_response.success or not removed_response.data:
                    await self.logger.log(
                        action="Update",
                        entity="Material",
                        level="error",
                        code=500,
                        message="Failed to remove old file from Drive during material update",
                        details={
                            "material_id": material.id,
                            "old_url": material.url,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="Failed to update material. Please try again later.",
                    )
                material.url = url
                material.details["file_data"] = file
                material.details["fetched"] = False

            material.author_id = current_user_id

            update_response = await self.material_repository.update(
                material, ["name", "details", "url", "author_id"]
            )
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_material = update_response.data
            if not updated_material:
                await self.logger.log(
                    action="Update",
                    entity="Material",
                    level="error",
                    code=500,
                    message="Failed to update material, no material returned after update",
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating material, please try again.",
                )
            is_file = updated_material.type != "folder"

            await self.logger.log(
                action="Update",
                entity="Material",
                level="info",
                code=200,
                message="Material updated successfully",
                source="MaterialService",
            )

            if is_file:
                subject_name = (
                    updated_material.subject.name if updated_material.subject else "N/A"
                )
                if updated_material.type == "file":
                    share_link = (
                        f"{os.environ.get('FRONTEND_URL')}/user/materials"
                        f"?subject_id={updated_material.subject_id}"
                        f"&parent_id={updated_material.parent_id if updated_material.parent_id else ''}"
                        f"&material_id={updated_material.id}"
                    )
                else:
                    share_link = updated_material.url
                await self.helper_service.send_notification(
                    "material",
                    updated_material.id,
                    f'Material "{updated_material.name}" has been updated for subject "{subject_name}".',
                    share_link,
                )

            return BaseResponseDto(success=True, data=updated_material)

        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while updating material",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating material",
            )

    async def get_by_id(self, material_id: int):
        try:
            material_response = await self.material_repository.find_one(
                Material.id == material_id,
                includes=[
                    selectinload(Material.author),
                    selectinload(Material.subject),
                    selectinload(Material.parent),
                ],
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
                    action="Get",
                    entity="Material",
                    level="warning",
                    code=404,
                    message="Material not found with this ID",
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Material not found"
                )

            material_dict = material.to_dict()
            material_dict["details"]["files_count"] = await self._count_descendants(
                material.id
            )
            material_dict["details"]["folders_count"] = await self._count_descendants(
                material.id, False
            )

            await self.logger.log(
                action="Get",
                entity="Material",
                level="info",
                code=200,
                message="Material retrieved successfully",
                details={"material": material_dict},
                source="MaterialService",
            )

            response_data = MaterialResponseDto(**material_dict)
            return BaseResponseDto(success=True, code=200, data=response_data)
        except Exception as ex:
            await self.logger.log(
                action="Get",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while getting material by ID",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting material by ID",
            )

    async def get_detail(self, material_id: int):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            material_response = await self.material_repository.find_one(
                Material.id == material_id,
                includes=[selectinload(Material.subject).selectinload(Subject.users)],
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
                    action="Get",
                    entity="Material",
                    level="warning",
                    code=404,
                    message="Material not found with this ID",
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Material not found"
                )

            if not any(user.id == current_user_id for user in material.subject.users):
                await self.logger.log(
                    action="Get",
                    entity="Material",
                    level="warning",
                    code=403,
                    message="User tried to get material of a subject they are not enrolled in",
                    details={
                        "material_id": material_id,
                        "subject_id": material.subject.id,
                    },
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="You are not enrolled in this subject",
                )

            await self.logger.log(
                action="Get",
                entity="Material",
                level="info",
                code=200,
                message="Material detail retrieved successfully",
                details={"material_id": material_id},
                source="MaterialService",
            )

            response_data = MaterialResponseDto(**material.user_to_dict())
            return BaseResponseDto(success=True, code=200, data=response_data)
        except Exception as ex:
            await self.logger.log(
                action="Get",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while getting material detail",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while retrieving material detail",
            )

    async def get_parents(self, material_id: int):
        try:
            material_response = await self.material_repository.find_one(
                Material.id == material_id
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
                    action="Get",
                    entity="Material Parents",
                    level="warning",
                    code=404,
                    message="Material not found for fetching parents",
                    details={"material_id": material_id},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Material not found"
                )

            parents = await self._fetch_parents(material.id)
            response_data = [MaterialMinimalResponseDto(**p) for p in parents]

            await self.logger.log(
                action="Get",
                entity="Material Parents",
                level="info",
                code=200,
                message="Material parents retrieved successfully",
                details={
                    "material_id": material_id,
                    "parents": [p["id"] for p in parents],
                },
                source="MaterialService",
            )
            return BaseResponseDto(success=True, code=200, data=response_data)
        except Exception as ex:
            await self.logger.log(
                action="Get",
                entity="Material Parents",
                level="error",
                code=500,
                message="An error occurred while getting material parents",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while getting material parents",
            )

    async def create(self, data):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            name = data.get("name", "").strip()
            description = data.get("description", "").strip()
            url = data.get("url", "").strip()
            type = (
                data.get("type", "").strip().lower()
            )  # File or Folder or YouTube or Drive or External
            parent_id = data.get("parent_id", None)  # Parent Folder ID
            subject_id = data.get("subject_id", None)  # Subject ID

            if not type or type not in [
                "file",
                "folder",
                "youtube",
                "drive",
                "external",
            ]:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=400,
                    message="Invalid or Missing Material Type Provided for Material Creation",
                    details=None,
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Material type must be one of the available types",
                )
            if parent_id and int(parent_id) < 1:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=404,
                    message="Invalid Parent ID Provided for Material Creation",
                    details=None,
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Invalid parent ID provided",
                )
            if not subject_id or int(subject_id) < 1:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="error",
                    code=404,
                    message="Invalid Subject ID Provided for Material Creation",
                    details=None,
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Invalid subject ID provided",
                )

            file = None
            if type == "folder":
                if not name or name == "":
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Missing Required Fields for Folder Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Folder Name is required",
                    )
            elif type in ["youtube", "drive", "external"]:
                if not name or name == "" or not url or url == "":
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Missing Required Fields for Link Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Name and URL are required",
                    )
                if type == "youtube" and not Validator.is_youtube_url(url):
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid YouTube URL Provided for Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid YouTube URL provided",
                    )
                if type == "drive" and not Validator.is_drive_url(url):
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid Google Drive URL Provided for Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid Google Drive URL provided",
                    )
                if type == "external" and not Validator.is_valid_url(url):
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid External URL Provided for Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid External URL provided",
                    )
            else:  # "file"
                if not url or url == "":
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Missing Required Fields for File Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="File is required",
                    )
                file_id = self.helper_service.get_file_id_from_url(url)
                if not file_id:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid File URL Provided for Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid File Provided.",
                    )
                file_response = await self.helper_service.fetch_from_drive(file_id)
                if not file_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=file_response.code,
                        data=None,
                        message=file_response.message,
                    )
                file = file_response.data
                if not file or not file.data:
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid File URL Provided for Material Creation",
                        details={"data": data},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid File Provided.",
                    )

            if name and name != "" and len(name) > 200:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Material Name Exceeds Maximum Length for Material Creation",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Material name exceeds maximum length of 200 characters",
                )
            if url and url != "" and len(url) > 200:
                await self.logger.log(
                    action="Create",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Material URL Exceeds Maximum Length for Material Creation",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Material URL exceeds maximum length of 200 characters",
                )

            parent = None
            if parent_id:
                parent_response = await self.material_repository.find_one(
                    Material.id == int(parent_id)
                )
                if not parent_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=parent_response.code,
                        data=None,
                        message=parent_response.message,
                    )
                parent = parent_response.data
                if not parent or parent.type != "folder":
                    await self.logger.log(
                        action="Create",
                        entity="Material",
                        level="warning",
                        code=404,
                        message="Parent Folder Not Found for Material Creation",
                        details={"parent_id": parent_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Parent folder not found",
                    )

            subject_response = await self.subject_repository.find_one(
                Subject.id == int(subject_id)
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
                    level="warning",
                    code=404,
                    message="Subject Not Found for Material Creation",
                    details={"subject_id": subject_id},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Subject not found",
                )

            material_name_input = name if name and name != "" else file.data.name
            unique_name = await self._generate_unique_name(
                subject_id=subject.id,
                parent_id=parent.id if parent_id else None,
                material_type=type,
                base_name=material_name_input,
            )

            material = Material(
                name=unique_name,
                type=type,
                url=url if url and url != "" else None,
                subject_id=subject.id,
                author_id=current_user_id,
                parent_id=parent.id if parent_id else None,
                details={
                    "description": (
                        description if description and description != "" else None
                    ),
                    "file_data": file.data if file else None,
                    "fetched": False,
                },
            )

            create_response = await self.material_repository.create(material)
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
                    action="Create",
                    entity="Material",
                    level="error",
                    code=500,
                    message="Failed to create material, no material returned after creation",
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating material, please try again.",
                )

            is_file = created_material.type != "folder"

            await self.logger.log(
                action="Create",
                entity="Material",
                level="info",
                code=201,
                message="Material Created Successfully",
                details={"material": created_material.min_to_dict()},
                source="MaterialService",
            )

            if is_file:
                if created_material.type == "file":
                    share_link = (
                        f"{os.environ.get('FRONTEND_URL')}/user/materials"
                        f"?subject_id={subject.id}"
                        f"&parent_id={parent.id if parent_id else ''}"
                        f"&material_id={created_material.id}"
                    )
                else:
                    share_link = created_material.url
                await self.helper_service.send_notification(
                    "material",
                    created_material.id,
                    f'New material "{created_material.name}" has been '
                    f'uploaded for subject "{subject.name}".',
                    share_link,
                )

            return BaseResponseDto(success=True, code=201, data=created_material)

        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Material",
                level="error",
                code=500,
                message=f"An error occurred while creating material",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating material",
            )

    async def fetch_materials_from_drive(self, data):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            drive_url = data.get("drive_url", "").strip()
            subject_id = data.get("subject_id", None)
            parent_id = data.get("parent_id", None)

            if (
                not drive_url
                or drive_url == ""
                or not Validator.is_drive_url(drive_url)
            ):
                await self.logger.log(
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid or Missing Google Drive URL Provided for Fetching Materials",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Google Drive URL provided",
                )
            if not subject_id or int(subject_id) < 1:
                await self.logger.log(
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid or Missing Subject ID Provided for Fetching Materials",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid subject was provided.",
                )
            if parent_id and int(parent_id) < 1:
                await self.logger.log(
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Parent ID Provided for Fetching Materials",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid parent ID provided",
                )

            subject_response = await self.subject_repository.find_one(
                Subject.id == int(subject_id)
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
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=404,
                    message="Subject Not Found for Fetching Materials",
                    details={"subject_id": subject_id},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=404, data=None, message="Subject not found"
                )

            parent = None
            if parent_id:
                parent_response = await self.material_repository.find_one(
                    Material.id == int(parent_id)
                )
                if not parent_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=parent_response.code,
                        data=None,
                        message=parent_response.message,
                    )
                parent = parent_response.data
                if not parent or parent.type != "folder":
                    await self.logger.log(
                        action="Import",
                        entity="Material",
                        level="warning",
                        code=404,
                        message="Parent Folder Not Found for Fetching Materials",
                        details={"parent_id": parent_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Parent folder not found",
                    )

            file_id = Validator.get_drive_file_id(drive_url)
            if not file_id:
                await self.logger.log(
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Google Drive URL Provided for Fetching Materials",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Google Drive URL provided",
                )

            fetched_response = await self.helper_service.fetch_from_drive(file_id)
            if not fetched_response.success:
                return BaseResponseDto(
                    success=False,
                    code=fetched_response.code,
                    data=None,
                    message=fetched_response.message,
                )
            fetched = fetched_response.data
            if not fetched or not fetched.data:
                await self.logger.log(
                    action="Import",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Fetched Data From Google Drive",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Fetched Data From Google Drive.",
                )

            root_material = await self._create_from_fetched_tree(
                fetched,
                subject.id,
                parent.id if parent_id else None,
                current_user_id,
            )

            await self.logger.log(
                action="Import",
                entity="Material",
                level="info",
                code=201,
                message="Materials Fetched from Google Drive and Created Successfully",
                details={
                    "subject_id": subject.id,
                    "parent_id": parent.id if parent_id else None,
                },
                source="MaterialService",
            )

            share_link = (
                f"{os.environ.get('FRONTEND_URL')}/user/materials"
                f"?subject_id={subject.id}"
                f"&parent_id={parent.id if parent_id else ''}"
            )
            await self.helper_service.send_notification(
                "material",
                parent.id if parent_id else None,
                f'New materials have been fetched from Google Drive for subject "{subject.name}".',
                share_link,
            )

            return BaseResponseDto(success=True, code=201, data=root_material)

        except Exception as ex:
            await self.logger.log(
                action="Import",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while fetching materials from google drive",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching materials from google drive",
            )

    async def fetch_one_material_from_drive(self, data):
        try:
            drive_url = data.get("drive_url", "").strip()
            if (
                not drive_url
                or drive_url == ""
                or not Validator.is_drive_url(drive_url)
            ):
                await self.logger.log(
                    action="Preview",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid or Missing Google Drive URL Provided for Fetching Material",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Google Drive URL provided",
                )

            file_id = Validator.get_drive_file_id(drive_url)
            if not file_id:
                await self.logger.log(
                    action="Preview",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Failed to Extract File ID from Google Drive URL",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Google Drive URL provided",
                )

            fetched_response = await self.helper_service.fetch_from_drive(file_id)
            if not fetched_response.success:
                await self.logger.log(
                    action="Preview",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Failed to Fetch Material from Google Drive",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Failed to fetch material from Google Drive",
                )

            fetched = fetched_response.data
            if not fetched or not fetched.data:
                await self.logger.log(
                    action="Preview",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Fetched Data From Google Drive",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid Fetched Data From Google Drive.",
                )

            await self.logger.log(
                action="Preview",
                entity="Material",
                level="info",
                code=200,
                message="Material Fetched from Google Drive Successfully",
                details={"file_data": fetched.model_dump()},
                source="MaterialService",
            )

            return BaseResponseDto(success=True, code=200, data=fetched)

        except Exception as ex:
            await self.logger.log(
                action="Preview",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while fetching material from Google Drive",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching material from Google Drive",
            )

    async def delete_many(self, ids: list[int]):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            for material_id in ids:
                material_response = await self.material_repository.find_one(
                    Material.id == material_id,
                    includes=[selectinload(Material.author)],
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
                        action="Delete",
                        entity="Material",
                        level="warning",
                        code=404,
                        message="Material not found for deletion",
                        details={"material_id": material_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Material(s) not found",
                    )

                if material.author_id != current_user_id:
                    has_permission_response = await self.user_service.has_permissions(
                        UserHasPermissionsDto(
                            required_permissions=["Manage All Materials"]
                        )
                    )
                    if (
                        not has_permission_response.success
                        or not has_permission_response.data
                    ):
                        await self.logger.log(
                            action="Delete",
                            entity="Material",
                            level="warning",
                            code=403,
                            message="Unauthorized material deletion attempt by non-author user",
                            details={
                                "material_id": material_id,
                                "author_id": material.author_id,
                            },
                            source="MaterialService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=403,
                            data=None,
                            message=f"You are not authorized to delete this material {material.name}",
                        )

                await self._delete_recursive(material_id)

            await self.logger.log(
                action="Delete",
                entity="Material",
                level="info",
                code=200,
                message="Material(s) deleted successfully",
                details={"material_ids": ids},
                source="MaterialService",
            )
            return BaseResponseDto(success=True, code=200, data=True)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while deleting material(s)",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting material(s)",
            )

    async def copy_many(self, data):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            material_ids = data.get("material_ids", [])
            destination_id = data.get("destination_id", None)

            if not material_ids:
                await self.logger.log(
                    action="Copy",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="No Material IDs Provided for Copying",
                    details=None,
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            if destination_id and int(destination_id) < 1:
                await self.logger.log(
                    action="Copy",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Destination ID Provided for Copying Materials",
                    details={"destination_id": destination_id},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            if not isinstance(material_ids, list) or any(
                int(id) < 1 for id in material_ids
            ):
                await self.logger.log(
                    action="Copy",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Material IDs Provided for Copying",
                    details={"material_ids": material_ids},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            if any(material_ids.count(id) > 1 for id in material_ids):
                await self.logger.log(
                    action="Copy",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Duplicate Material IDs Provided for Copying",
                    details={"material_ids": material_ids},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )

            material_ids = [int(id) for id in material_ids]
            destination_id = int(destination_id) if destination_id else None

            if destination_id:
                destination_response = await self.material_repository.find_one(
                    Material.id == destination_id
                )
                if not destination_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=destination_response.code,
                        data=None,
                        message=destination_response.message,
                    )
                destination = destination_response.data
                if not destination or destination.type != "folder":
                    await self.logger.log(
                        action="Copy",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid Destination ID Provided for Copying Materials",
                        details={"destination_id": destination_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid destination provided",
                    )

            subject_id = None
            parent_id = None
            for material_id in material_ids:
                material_response = await self.material_repository.find_one(
                    Material.id == material_id,
                    includes=[selectinload(Material.author)],
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
                        action="Copy",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid Material ID Provided for Copying",
                        details={"material_id": material_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Material(s) not found",
                    )

                if material.author_id != current_user_id:
                    has_permission_response = await self.user_service.has_permissions(
                        UserHasPermissionsDto(
                            required_permissions=["Manage All Materials"]
                        )
                    )
                    if (
                        not has_permission_response.success
                        or not has_permission_response.data
                    ):
                        await self.logger.log(
                            action="Copy",
                            entity="Material",
                            level="warning",
                            code=403,
                            message="Unauthorized material copy attempt by non-author user",
                            details={
                                "material_id": material_id,
                                "author_id": material.author_id,
                            },
                            source="MaterialService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=403,
                            data=None,
                            message="You are not authorized to copy this/these material(s).",
                        )

                if not subject_id:
                    subject_id = material.subject_id
                elif subject_id != material.subject_id:
                    await self.logger.log(
                        action="Copy",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Materials from Different Subjects Provided for Copying",
                        details={
                            "material_id": material_id,
                            "subject_id": material.subject_id,
                            "expected_subject_id": subject_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials from different subjects cannot be copied together",
                    )

                if not parent_id:
                    parent_id = material.parent_id
                elif parent_id != material.parent_id:
                    await self.logger.log(
                        action="Copy",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Materials from Different Parent Folders Provided for Copying",
                        details={
                            "material_id": material_id,
                            "parent_id": material.parent_id,
                            "expected_parent_id": parent_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials from different parent folders cannot be copied together",
                    )

                await self._copy_recursive(
                    material.id, subject_id, destination_id, current_user_id
                )

            await self.logger.log(
                action="Copy",
                entity="Material",
                level="info",
                code=201,
                message="Material(s) Copied Successfully",
                details={
                    "material_ids": material_ids,
                    "destination_id": destination_id,
                },
                source="MaterialService",
            )
            return BaseResponseDto(success=True, code=201, data=True)

        except MaterialOperationError as ex:
            await self.logger.log(
                action="Copy",
                entity="Material",
                level="warning" if ex.code < 500 else "error",
                code=ex.code,
                message=str(ex),
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False, code=ex.code, data=None, message=str(ex)
            )
        except Exception as ex:
            await self.logger.log(
                action="Copy",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while copying material(s)",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while copying material(s)",
            )

    async def move_many(self, data):
        try:
            current_user_id_response = await self.user_service.get_current_user_id()
            if not current_user_id_response.success:
                return BaseResponseDto(
                    success=False,
                    code=current_user_id_response.code,
                    data=None,
                    message=current_user_id_response.message,
                )
            current_user_id = current_user_id_response.data

            material_ids = data.get("material_ids", [])
            destination_id = data.get("destination_id", None)

            if not material_ids:
                await self.logger.log(
                    action="Move",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Data Provided in The Request Body for Moving Materials",
                    details={"data": data},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            if not isinstance(material_ids, list) or any(
                int(id) < 1 for id in material_ids
            ):
                await self.logger.log(
                    action="Move",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Material IDs Provided for Moving Materials",
                    details={"material_ids": material_ids},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            if any(material_ids.count(id) > 1 for id in material_ids):
                await self.logger.log(
                    action="Move",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Duplicate Material IDs Provided for Moving Materials",
                    details={"material_ids": material_ids},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            material_ids = [int(id) for id in material_ids]
            if destination_id and int(destination_id) < 1:
                await self.logger.log(
                    action="Move",
                    entity="Material",
                    level="warning",
                    code=400,
                    message="Invalid Destination ID Provided for Moving Materials",
                    details={"destination_id": destination_id},
                    source="MaterialService",
                )
                return BaseResponseDto(
                    success=False, code=400, data=None, message="Invalid Request."
                )
            destination_id = int(destination_id) if destination_id else None

            if destination_id:
                destination_response = await self.material_repository.find_one(
                    Material.id == destination_id
                )
                if not destination_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=destination_response.code,
                        data=None,
                        message=destination_response.message,
                    )
                destination = destination_response.data
                if not destination or destination.type != "folder":
                    await self.logger.log(
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid Destination ID Provided for Moving Materials",
                        details={"destination_id": destination_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False, code=400, data=None, message="Invalid Request."
                    )

            subject_id = None
            parent_id = None
            for material_id in material_ids:
                material_response = await self.material_repository.find_one(
                    Material.id == material_id
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
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Invalid Material ID Provided for Moving Materials",
                        details={"material_id": material_id},
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False, code=400, data=None, message="Invalid Request."
                    )

                if material.author_id != current_user_id:
                    has_permission_response = await self.user_service.has_permissions(
                        UserHasPermissionsDto(
                            required_permissions=["Manage All Materials"]
                        )
                    )
                    if (
                        not has_permission_response.success
                        or not has_permission_response.data
                    ):
                        await self.logger.log(
                            action="Move",
                            entity="Material",
                            level="warning",
                            code=403,
                            message="Unauthorized material move attempt by non-author user",
                            details={
                                "material_id": material_id,
                                "author_id": material.author_id,
                            },
                            source="MaterialService",
                        )
                        return BaseResponseDto(
                            success=False,
                            code=403,
                            data=None,
                            message="You are not authorized to move this/these material(s).",
                        )

                if not subject_id:
                    subject_id = material.subject_id
                elif subject_id != material.subject_id:
                    await self.logger.log(
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Materials from Different Subjects Provided for Moving",
                        details={
                            "material_id": material_id,
                            "subject_id": material.subject_id,
                            "expected_subject_id": subject_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials from different subjects cannot be moved together",
                    )

                if not parent_id:
                    parent_id = material.parent_id
                elif parent_id != material.parent_id:
                    await self.logger.log(
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Materials from Different Parent Folders Provided for Moving",
                        details={
                            "material_id": material_id,
                            "parent_id": material.parent_id,
                            "expected_parent_id": parent_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials from different folders cannot be moved together",
                    )

                if (
                    destination_id
                    and parent_id
                    and parent_id == destination_id
                    or not destination_id
                    and not parent_id
                ):
                    await self.logger.log(
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Destination Folder is Same as Source Parent Folder for Moving Materials",
                        details={
                            "material_id": material_id,
                            "parent_id": parent_id,
                            "destination_id": destination_id,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials can't be moved to the same folder they are in",
                    )

                material.name = await self._generate_unique_name(
                    subject_id=subject_id,
                    parent_id=destination_id,
                    material_type=material.type,
                    base_name=material.name,
                )

                parent_chain = (
                    await self._fetch_parents(destination_id) if destination_id else []
                )
                parent_ids = [p["id"] for p in parent_chain]
                if material.id in parent_ids:
                    await self.logger.log(
                        action="Move",
                        entity="Material",
                        level="warning",
                        code=400,
                        message="Cannot Move Material Inside Its Own Subfolder",
                        details={
                            "material_id": material_id,
                            "destination_id": destination_id,
                            "parent_ids": parent_ids,
                        },
                        source="MaterialService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Materials can't be moved to a subfolder of themselves",
                    )

                material.parent_id = destination_id
                material.author_id = current_user_id

                update_response = await self.material_repository.update(
                    material, ["name", "parent_id", "author_id"]
                )
                if not update_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=update_response.code,
                        data=None,
                        message=update_response.message,
                    )

            await self.logger.log(
                action="Move",
                entity="Material",
                level="info",
                code=200,
                message="Material(s) Moved Successfully",
                details={
                    "material_ids": material_ids,
                    "destination_id": destination_id,
                },
                source="MaterialService",
            )
            return BaseResponseDto(success=True, code=200, data=True)

        except Exception as ex:
            await self.logger.log(
                action="Move",
                entity="Material",
                level="error",
                code=500,
                message="An error occurred while moving material(s)",
                details={"error": str(ex)},
                source="MaterialService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while moving material(s)",
            )
