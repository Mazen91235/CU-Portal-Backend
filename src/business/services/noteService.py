from sqlalchemy import and_, func
from core.iServices.iNoteService import INoteService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.note import Note
from core.dtos.baseDtos import BaseResponseDto


class NoteService(INoteService):
    def __init__(
        self,
        note_repository: IBaseRepository[Note],
        logger: IBaseLogger,
        helper_service: IHelperService,
    ):
        self.note_repository = note_repository
        self.logger = logger
        self.helper_service = helper_service

    # Transaction Functions
    async def begin_transaction(self):
        await self.note_repository.begin_transaction()

    async def commit_transaction(self):
        await self.note_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.note_repository.rollback_transaction()

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
                Note, data, ["title", "content"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Note, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Note", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Note", order_by
            )

            result = await self.note_repository.find_one(
                predicate,
                dynamic_includes,
                dynamic_selects,
                dynamic_order_by,
                descending,
            )

            if not result.success:
                return BaseResponseDto(
                    success=False, code=result.code, data=None, message=result.message
                )
            note = result.data
            return BaseResponseDto(success=True, code=200, data=note)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Note",
                level="error",
                code=500,
                message="Error finding note",
                details={"error": repr(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding the note",
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
                Note, data, ["title", "content"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Note, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Note", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Note", order_by
            )

            result = await self.note_repository.find(
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
                    success=False, code=result.code, data=None, message=result.message
                )
            notes = result.data
            return BaseResponseDto(success=True, code=200, data=notes)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while finding notes",
                details={"error": repr(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding notes",
            )

    async def create(self, data):
        try:
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Create",
                    entity="Note",
                    level="warning",
                    code=401,
                    message="User not logged in for note creation",
                    details={},
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    message="User not logged in",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Create",
                    entity="Note",
                    level="warning",
                    code=401,
                    message="User not logged in for note creation",
                    details={},
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=401,
                    message="User not logged in",
                )
            data.author_id = logged_in_user.id
            existing_note_response = await self.note_repository.find_one(
                and_(
                    func.lower(Note.title) == func.lower(data.title),
                    Note.author_id == logged_in_user.id,
                    func.lower(Note.content) == func.lower(data.content),
                    Note.date.is_not_distinct_from(data.date),
                )
            )
            if not existing_note_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_note_response.code,
                    data=None,
                    message=existing_note_response.message,
                )
            existing_note = existing_note_response.data
            if existing_note:
                await self.logger.log(
                    action="Create",
                    entity="Note",
                    level="info",
                    code=409,
                    message="Note already exists for the user",
                    details={},
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=409,
                    data=None,
                    message="Note already exists for the user",
                )
            create_response = await self.note_repository.create(data)
            if not create_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_response.code,
                    data=None,
                    message=create_response.message,
                )
            created_note = create_response.data
            if not created_note:
                await self.logger.log(
                    action="Create",
                    entity="Note",
                    level="error",
                    code=500,
                    message="Failed to create note without a specific error",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while creating note",
                )
            await self.logger.log(
                action="Create",
                entity="Note",
                level="info",
                code=201,
                message="Note created successfully",
                source="NoteService",
            )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_note,
                message="Note created successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while creating note",
                details={"error": repr(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating note",
            )

    async def update(self, data):
        try:
            target_note_response = await self.note_repository.find_one(
                Note.id == data.id
            )
            if not target_note_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_note_response.code,
                    data=None,
                    message=target_note_response.message,
                )
            target_note = target_note_response.data
            if not target_note:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Note not found for update",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Note not found for update",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Logged-in user not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged-in user not found",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Logged-in user not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged-in user not found",
                )
            if target_note.author_id != logged_in_user.id:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="warning",
                    code=403,
                    message="User not authorized to update this note",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="User not authorized to update this note",
                )
            existing_note_response = await self.note_repository.find_one(
                and_(
                    func.lower(Note.title) == func.lower(data.title),
                    Note.author_id == logged_in_user.id,
                    func.lower(Note.content) == func.lower(data.content),
                    Note.date.is_not_distinct_from(data.date),
                )
            )
            if not existing_note_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_note_response.code,
                    data=None,
                    message=existing_note_response.message,
                )
            existing_note = existing_note_response.data
            if existing_note and existing_note.id != target_note.id:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="info",
                    code=409,
                    message="Another note with the same title and content already exists for the user",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=409,
                    data=None,
                    message="Another note with the same details already exists for the user",
                )
            target_note.title = data.title
            target_note.content = data.content
            target_note.date = data.date
            update_response = await self.note_repository.update(target_note)
            if not update_response.success:
                return BaseResponseDto(
                    success=False,
                    code=update_response.code,
                    data=None,
                    message=update_response.message,
                )
            updated_note = update_response.data
            if not updated_note:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="error",
                    code=500,
                    message="Failed to update note without a specific error",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="An error occurred while updating note",
                )
            await self.logger.log(
                action="Update",
                entity="Note",
                level="info",
                code=200,
                message="Note updated successfully",
                source="NoteService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=updated_note,
                message="Note updated successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while updating note",
                details={"error": repr(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while updating note",
            )

    async def delete(self, data):
        try:
            target_note_response = await self.note_repository.find_one(
                Note.id == data.id
            )
            if not target_note_response.success:
                return BaseResponseDto(
                    success=False,
                    code=target_note_response.code,
                    data=None,
                    message=target_note_response.message,
                )
            target_note = target_note_response.data
            if not target_note:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Note not found for deletion",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Note not found for deletion",
                )
            logged_in_user_response = await self.helper_service.get_logged_in_user()
            if not logged_in_user_response.success:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Logged-in user not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged-in user not found",
                )
            logged_in_user = logged_in_user_response.data
            if not logged_in_user:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Logged-in user not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Logged-in user not found",
                )
            if target_note.author_id != logged_in_user.id:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="warning",
                    code=403,
                    message="User not authorized to delete this note",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=None,
                    message="User not authorized to delete this note",
                )
            delete_response = await self.note_repository.delete(target_note)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            await self.logger.log(
                action="Delete",
                entity="Note",
                level="info",
                code=200,
                message="Note deleted successfully",
                source="NoteService",
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=None,
                message="Note deleted successfully",
            )
        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while deleting note",
                details={"error": repr(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting note",
            )
