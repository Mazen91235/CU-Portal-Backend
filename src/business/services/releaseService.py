from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from core.iServices.iReleaseService import IReleaseService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.release import Release
from core.entities.version import Version
from core.entities.releaseItem import ReleaseItem
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.releaseDtos import ReleaseCreateDto, ReleaseUpdateDto, ReleaseSearchDto
from core.models.queryModel import QueryModel
from core.utils.timezoneHandler import TimezoneHandler


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

    # Generic Interfaces
    async def find_one(self, predicate=None, includes=None, selects=None, order_by=None, descending=False):
        return await self.release_repository.find_one(predicate, includes, selects, order_by, descending)

    async def find(self, predicate=None, includes=None, selects=None, order_by=None, descending=False, page=1, limit=50):
        return await self.release_repository.find(predicate, includes, selects, order_by, descending, page, limit)

    async def count(self, predicate=None):
        return await self.release_repository.count(predicate)

    async def create(self, entity: Release):
        return await self.release_repository.create(entity)

    async def update(self, entity: Release, updates=None):
        return await self.release_repository.update(entity, updates)

    async def delete(self, entity: Release):
        return await self.release_repository.delete(entity)

    # Helper Function: Ensure Version exists
    async def _ensure_version(self, release_number: str) -> BaseResponseDto[Version]:
        try:
            major_version_num = int(release_number.split(".")[0])
            version_response = await self.version_repository.find_one(Version.version_number == major_version_num)
            
            if version_response.success and version_response.data:
                return BaseResponseDto(success=True, data=version_response.data)

            # Create if it doesn't exist
            new_version = Version(version_number=major_version_num)
            return await self.version_repository.create(new_version)
        except Exception as e:
            return BaseResponseDto(success=False, code=500, message="Failed to process version resolution.")

    # Helper Function: Cleanup Orphaned Versions
    async def _cleanup_orphaned_version(self, version_id: int):
        try:
            count_response = await self.release_repository.count(Release.version_id == version_id)
            if count_response.success and count_response.data == 0:
                version_to_delete = (await self.version_repository.find_one(Version.id == version_id)).data
                if version_to_delete:
                    await self.version_repository.delete(version_to_delete)
        except Exception as e:
            await self.logger.log("Cleanup", "Version", "error", 500, "Failed to cleanup version", "ReleaseService", {"error": str(e)})

    # Specific Feature Logic
    async def create_release(self, data: ReleaseCreateDto) -> BaseResponseDto[Release]:
        try:
            # Uniqueness check
            existing_release = await self.release_repository.find_one(Release.release_number == data.release_number)
            if existing_release.success and existing_release.data:
                return BaseResponseDto(success=False, code=400, message=f"Release {data.release_number} already exists.")

            # Version handling
            version_response = await self._ensure_version(data.release_number)
            if not version_response.success:
                return BaseResponseDto(success=False, code=500, message="Failed to map release to a version.")
            version_id = version_response.data.id

            # Build entity graph
            new_release = Release(
                release_number=data.release_number,
                title=data.title,
                date=TimezoneHandler.from_isoformat(data.date),
                version_id=version_id,
                release_items=[
                    ReleaseItem(item_type=item.item_type, content=item.content) for item in data.release_items
                ]
            )

            result = await self.release_repository.create(new_release)
            if not result.success:
                return result

            await self.logger.log("Create", "Release", "info", 201, "Release created successfully", "ReleaseService")
            return BaseResponseDto(success=True, code=201, data=result.data, message="Release created successfully.")
        except Exception as ex:
            await self.logger.log("Create", "Release", "error", 500, "Error creating release", "ReleaseService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while creating the release.")

    async def update_release(self, release_id: int, data: ReleaseUpdateDto) -> BaseResponseDto[Release]:
        try:
            # Fetch existing
            existing_response = await self.release_repository.find_one(
                Release.id == release_id, 
                includes=[selectinload(Release.release_items)]
            )
            if not existing_response.success or not existing_response.data:
                return BaseResponseDto(success=False, code=404, message="Release not found.")
            
            release = existing_response.data
            old_version_id = release.version_id

            # Uniqueness check (if changed)
            if release.release_number != data.release_number:
                dup_check = await self.release_repository.find_one(Release.release_number == data.release_number)
                if dup_check.success and dup_check.data:
                    return BaseResponseDto(success=False, code=400, message=f"Release {data.release_number} already exists.")

                # Ensure new version exists
                version_response = await self._ensure_version(data.release_number)
                if not version_response.success:
                    return BaseResponseDto(success=False, code=500, message="Failed to map new release version.")
                release.version_id = version_response.data.id

            # Update properties
            release.release_number = data.release_number
            release.title = data.title
            release.date = TimezoneHandler.from_isoformat(data.date)

            # Handle Items (Replace all items to ensure exact match with DTO state)
            for old_item in release.release_items:
                await self.release_item_repository.delete(old_item)
            
            release.release_items = [
                ReleaseItem(item_type=item.item_type, content=item.content) for item in data.release_items
            ]

            update_result = await self.release_repository.update(release)
            if not update_result.success:
                return update_result

            # Cleanup Old Version if necessary
            if old_version_id != release.version_id:
                await self._cleanup_orphaned_version(old_version_id)

            await self.logger.log("Update", "Release", "info", 200, "Release updated successfully", "ReleaseService")
            return BaseResponseDto(success=True, code=200, data=update_result.data, message="Release updated successfully.")

        except Exception as ex:
            await self.logger.log("Update", "Release", "error", 500, "Error updating release", "ReleaseService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while updating the release.")

    async def delete_release(self, release_id: int) -> BaseResponseDto[bool]:
        try:
            existing_response = await self.release_repository.find_one(Release.id == release_id)
            if not existing_response.success or not existing_response.data:
                return BaseResponseDto(success=False, code=404, message="Release not found.")
            
            release = existing_response.data
            version_id_to_check = release.version_id

            # Delete the release (Cascade should handle release_items) 
            delete_result = await self.release_repository.delete(release)
            if not delete_result.success:
                return delete_result

            # Check and delete orphaned version
            await self._cleanup_orphaned_version(version_id_to_check)

            await self.logger.log("Delete", "Release", "info", 200, "Release deleted successfully", "ReleaseService")
            return BaseResponseDto(success=True, code=200, data=True, message="Release deleted successfully.")

        except Exception as ex:
            await self.logger.log("Delete", "Release", "error", 500, "Error deleting release", "ReleaseService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while deleting the release.")

    async def get_releases(self, query: QueryModel[ReleaseSearchDto]) -> BaseResponseDto[list[Release]]:
        try:
            predicate = self.helper_service.generate_dynamic_predicate(
                Release, query.data, ["title", "release_number"], query.is_and, query.starts_with, query.is_exact
            )
            includes = self.helper_service.generate_dynamic_includes(Release, query.includes)
            
            if not includes:
                includes = [selectinload(Release.release_items), selectinload(Release.version)]

            order_by = self.helper_service.generate_dynamic_order_by("Release", query.order_by)
            if not order_by:
                order_by = [Release.date]
                query.descending = True  # Newest releases first

            result = await self.release_repository.find(
                predicate=predicate,
                includes=includes,
                order_by=order_by,
                descending=query.descending,
                page=query.page,
                limit=query.limit,
            )

            if not result.success:
                return result

            return BaseResponseDto(success=True, code=200, data=result.data, message="Releases retrieved successfully.")

        except Exception as ex:
            await self.logger.log("Get", "Release", "error", 500, "Error getting releases", "ReleaseService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching releases.")

    async def get_release(self, release_id: int) -> BaseResponseDto[Release]:
        try:
            includes = [selectinload(Release.release_items), selectinload(Release.version)]
            result = await self.release_repository.find_one(Release.id == release_id, includes=includes)
            
            if not result.success or not result.data:
                return BaseResponseDto(success=False, code=404, message="Release not found.")
                
            return BaseResponseDto(success=True, code=200, data=result.data, message="Release retrieved successfully.")
        except Exception as ex:
            await self.logger.log("Get", "Release", "error", 500, "Error getting release", "ReleaseService", {"error": str(ex)})
            return BaseResponseDto(success=False, code=500, message="An error occurred while fetching the release.")