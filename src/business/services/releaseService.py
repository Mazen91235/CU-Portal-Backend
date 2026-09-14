from sqlalchemy import func
from core.iServices.iReleaseService import IReleaseService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.release import Release
from core.entities.version import Version
from core.entities.releaseItem import ReleaseItem
from core.dtos.baseDtos import BaseResponseDto


class ReleaseService(IReleaseService):
    def __init__(
        self,
        release_repository: IBaseRepository[Release],
        version_repository: IBaseRepository[Version],
        release_item_repository: IBaseRepository[ReleaseItem],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.release_repository = release_repository
        self.version_repository = version_repository
        self.release_item_repository = release_item_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.release_repository.begin_transaction()

    async def commit_transaction(self):
        await self.release_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.release_repository.rollback_transaction()

    async def find_versions(self):
        try:
            result = await self.version_repository.find_distinct(
                column=Version.version_number
            )
            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )
            return BaseResponseDto(success=True, data=sorted(result.data or []))
        except Exception as ex:
            await self.logger.log(
                action="FindVersions",
                entity="Version",
                level="error",
                code=500,
                message="An error occurred while finding versions",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding versions",
            )

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
                Release,
                data,
                ["release_number", "title"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Release, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Release", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Release", order_by
            )
            result = await self.release_repository.find_one(
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
            release = result.data
            return BaseResponseDto(success=True, data=release)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while finding release",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding release",
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
                Release,
                data,
                ["release_number", "title"],
                is_and,
                starts_with,
                is_exact,
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Release, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Release", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Release", order_by
            )
            result = await self.release_repository.find(
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
            releases = result.data
            return BaseResponseDto(
                success=True, data=releases, next_page=result.next_page
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while finding releases",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding releases",
            )

    async def create(self, data):
        try:
            version_number = int(data.release_number.split(".")[0])
            version_response = await self.version_repository.find_one(
                Version.version_number == version_number
            )
            if not version_response.success:
                return BaseResponseDto(
                    success=False,
                    code=version_response.code,
                    data=None,
                    message=version_response.message,
                )
            version = version_response.data
            if not version:
                version = Version(version_number=version_number)
                create_version_response = await self.version_repository.create(version)
                if not create_version_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_version_response.code,
                        data=None,
                        message=create_version_response.message,
                    )
                version = create_version_response.data
                if not version:
                    await self.logger.log(
                        action="Create",
                        entity="Version",
                        level="error",
                        code=500,
                        message="Failed to create version without a specific error",
                        source="ReleaseService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating version",
                    )
            existing_release_response = await self.release_repository.find_one(
                Release.release_number == data.release_number
            )
            if not existing_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_release_response.code,
                    data=None,
                    message=existing_release_response.message,
                )
            existing_release = existing_release_response.data
            if existing_release:
                await self.logger.log(
                    action="Create",
                    entity="Release",
                    level="warning",
                    code=400,
                    message="Release with the same release number already exists",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Release with the same release number already exists",
                )
            release = Release(
                release_number=data.release_number,
                title=data.title,
                date=data.date,
                details=data.details,
                release_version=version,
                release_items=set(
                    ReleaseItem(
                        item_type=item.item_type,
                        content=item.content,
                    )
                    for item in data.release_items
                ),
            )
            create_release_response = await self.release_repository.create(release)
            if not create_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_release_response.code,
                    data=None,
                    message=create_release_response.message,
                )
            created_release = create_release_response.data
            if not created_release:
                await self.logger.log(
                    action="Create",
                    entity="Release",
                    level="error",
                    code=500,
                    message="Failed to create release without a specific error",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating release",
                )
            await self.logger.log(
                action="Create",
                entity="Release",
                level="info",
                code=201,
                message="Release created successfully",
                source="ReleaseService",
            )
            return BaseResponseDto(success=True, code=201, data=created_release)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while creating release",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating release",
            )

    async def update(self, data):
        try:
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Release, ["release_items"]
            )
            target_release_response = await self.release_repository.find_one(
                Release.id == data.id, includes=dynamic_includes
            )
            if not target_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_release_response.code,
                    data=None,
                    message=target_release_response.message,
                )
            target_release = target_release_response.data
            if not target_release:
                await self.logger.log(
                    action="Update",
                    entity="Release",
                    level="info",
                    code=404,
                    message="Release not found",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Release not found",
                )
            old_version_number = int(target_release.release_number.split(".")[0])
            version_number = int(data.release_number.split(".")[0])
            version_response = await self.version_repository.find_one(
                Version.version_number == version_number
            )
            if not version_response.success:
                return BaseResponseDto(
                    success=False,
                    code=version_response.code,
                    data=None,
                    message=version_response.message,
                )
            version = version_response.data
            if not version:
                version = Version(version_number=version_number)
                create_version_response = await self.version_repository.create(version)
                if not create_version_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_version_response.code,
                        data=None,
                        message=create_version_response.message,
                    )
                version = create_version_response.data
                if not version:
                    await self.logger.log(
                        action="Update",
                        entity="Version",
                        level="error",
                        code=500,
                        message="Failed to create version without a specific error",
                        source="ReleaseService",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=None,
                        message="An error occurred while creating version",
                    )
            existing_release_response = await self.release_repository.find_one(
                Release.release_number == data.release_number,
            )
            if not existing_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_release_response.code,
                    data=None,
                    message=existing_release_response.message,
                )
            existing_release = existing_release_response.data
            if existing_release and existing_release.id != data.id:
                await self.logger.log(
                    action="Update",
                    entity="Release",
                    level="warning",
                    code=400,
                    message="Release with the same release number already exists",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Release with the same release number already exists",
                )
            target_release.release_number = data.release_number
            target_release.title = data.title
            target_release.date = data.date
            target_release.details = data.details
            target_release.release_version = version
            target_release.release_items.update(
                set(
                    ReleaseItem(
                        item_type=item.item_type,
                        content=item.content,
                    )
                    for item in data.release_items
                )
            )
            update_release_response = await self.release_repository.update(
                target_release
            )
            if not update_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_release_response.code,
                    data=None,
                    message=update_release_response.message,
                )
            updated_release = update_release_response.data
            if not updated_release:
                await self.logger.log(
                    action="Update",
                    entity="Release",
                    level="error",
                    code=500,
                    message="Failed to update release without a specific error",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating release",
                )
            if old_version_number != version_number:
                dynamic_includes = self.helper_service.generate_dynamic_includes(
                    Version, ["releases"]
                )
                old_version_response = await self.version_repository.find_one(
                    Version.version_number == old_version_number, dynamic_includes
                )
                if not old_version_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=old_version_response.code,
                        data=None,
                        message=old_version_response.message,
                    )
                old_version = old_version_response.data
                if old_version and len(old_version.releases) < 1:
                    delete_old_version_response = await self.version_repository.delete(
                        old_version
                    )
                    if not delete_old_version_response.success:
                        return BaseResponseDto(
                            success=False,
                            code=delete_old_version_response.code,
                            data=None,
                            message=delete_old_version_response.message,
                        )
            await self.logger.log(
                action="Update",
                entity="Release",
                level="info",
                code=200,
                message="Release updated successfully",
                source="ReleaseService",
            )
            return BaseResponseDto(success=True, code=200, data=updated_release)
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while updating release",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating release",
            )

    async def delete(self, data):
        try:
            target_release_response = await self.release_repository.find_one(
                Release.id == data.id
            )
            if not target_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_release_response.code,
                    data=None,
                    message=target_release_response.message,
                )
            target_release = target_release_response.data
            if not target_release:
                await self.logger.log(
                    action="Delete",
                    entity="Release",
                    level="info",
                    code=404,
                    message="Release not found",
                    source="ReleaseService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Release not found",
                )
            old_version_number = int(target_release.release_number.split(".")[0])
            delete_release_response = await self.release_repository.delete(
                target_release
            )
            if not delete_release_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_release_response.code,
                    data=None,
                    message=delete_release_response.message,
                )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Version, ["releases"]
            )
            old_version_response = await self.version_repository.find_one(
                Version.version_number == old_version_number, dynamic_includes
            )
            if not old_version_response.success:
                return BaseResponseDto(
                    success=False,
                    code=old_version_response.code,
                    data=None,
                    message=old_version_response.message,
                )
            old_version = old_version_response.data
            if old_version and len(old_version.releases) < 1:
                delete_old_version_response = await self.version_repository.delete(
                    old_version
                )
                if not delete_old_version_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_old_version_response.code,
                        data=None,
                        message=delete_old_version_response.message,
                    )
            await self.logger.log(
                action="Delete",
                entity="Release",
                level="info",
                code=200,
                message="Release deleted successfully",
                source="ReleaseService",
            )
            return BaseResponseDto(success=True, code=200, data=None)
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Release",
                level="error",
                code=500,
                message="An error occurred while deleting release",
                details={"error": repr(ex)},
                source="ReleaseService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting release",
            )
