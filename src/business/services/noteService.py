import os
import math
from datetime import datetime
from typing import cast
from fastapi import Request
from core.iServices.iNoteService import INoteService
from core.iServices.bases.iQueryableService import IQueryableService
from core.iServices.bases.iUpdatableService import IUpdatableService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository

from core.entities.note import Note
from core.entities.user import User
from core.entities.subject import Subject
from core.entities.role import Role
from core.dtos.baseDtos import BaseResponseDto
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.validator import Validator
from core.utils.mapper import Mapper


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
                Note, data, ["content"], is_and, starts_with, is_exact
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
            return BaseResponseDto(success=True, code=200, data=result.data)

        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Note",
                level="error",
                code=500,
                message="Error finding note",
                details={"error": str(ex)},
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
                Note, data, ["content"], is_and, starts_with, is_exact
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

            return BaseResponseDto(success=True, code=200, data=result.data)

        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while finding notes",
                details={"error": str(ex)},
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

            create_res = await self.note_repository.create(data)

            created_note = create_res.data

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
            )

        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while creating note",
                details={"error": str(ex)},
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
            target_res = await self.note_repository.find_one(Note.id == data.id)

            if not target_res.success:
                return BaseResponseDto(
                    success=False,
                    code=target_res.code,
                    data=None,
                    message=target_res.message,
                )

            target_note = target_res.data
            if not target_note:
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Note not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Note not found",
                )

            if data.content is not None:
                target_note.content = data.content
            if data.date is not None:
                target_note.date = data.date

            update_res = await self.note_repository.update(target_note)

            if not update_res.success:
                return BaseResponseDto(
                    success=False,
                    code=update_res.code,
                    data=None,
                    message=update_res.message,
                )

            updated_note = update_res.data

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
            )

        except Exception as ex:
            await self.logger.log(
                action="Update",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while updating note",
                details={"error": str(ex)},
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
            if not data:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="warning",
                    code=400,
                    message="No data provided for note deletion.",
                    details={},
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    message="No data provided for deletion",
                )
            result = await self.note_repository.find_one(predicate=(Note.id == data.id))

            if not result.success:
                return BaseResponseDto(
                    success=False,
                    code=result.code,
                    data=None,
                    message=result.message,
                )

            note = result.data
            if not note:
                await self.logger.log(
                    action="Delete",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Note not found",
                    source="NoteService",
                )
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Note not found",
                )

            delete_res = await self.Note_repository.delete(note)

            if not delete_res.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_res.code,
                    data=None,
                    message=delete_res.message,
                )

            await self.logger.log(
                action="Delete",
                entity="Note",
                level="info",
                code=200,
                message="Note deleted successfully",
                source="NoteService",
            )
            return BaseResponseDto(success=True, code=200, data=True)

        except Exception as ex:
            await self.logger.log(
                action="Delete",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while deleting note",
                details={"error": str(ex)},
                source="NoteService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting note",
            )
