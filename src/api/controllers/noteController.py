from typing import cast
from core.iControllers.iNoteController import INoteController
from core.iServices.iNoteService import INoteService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler

# Entities & DTOs
from core.entities.note import Note
from core.dtos.noteDtos import (
    NoteCreateDto,
    NoteResponseDto,
    NoteUpdateDto,
    NoteSearchDto,
    NoteDeleteDto,
)


class NoteController(INoteController):
    def __init__(self, note_service: INoteService, logger: IBaseLogger):
        self.note_service = note_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[NoteSearchDto].generate(
                NoteSearchDto, {"id": id}
            )

            response = await self.note_service.find_one(
                entity_search_dto,
                ["author"],
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            note = response.data

            if not note:
                await self.logger.log(
                    action="FindOne",
                    entity="Note",
                    level="info",
                    code=404,
                    message="note not found",
                    source="NoteController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Note not found",
                )

            note_mapped = Mapper[Note, NoteResponseDto].map(note, NoteResponseDto, True)

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=note_mapped,
            )

        except Exception as e:
            await self.logger.log(
                action="FindOne",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[NoteSearchDto].generate_from_query(
                NoteSearchDto, query
            )

            includes = query.includes
            selects = query.selects
            is_and = query.is_and
            starts_with = query.starts_with
            is_exact = query.is_exact
            order_by = query.order_by
            descending = query.descending
            page = query.page or 1
            limit = query.limit or 50

            response = await self.note_service.find(
                entity_search_dto,
                includes,
                selects,
                is_and,
                starts_with,
                is_exact,
                order_by,
                descending,
                page,
                limit,
            )

            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            notes = response.data

            notes_mapped = Mapper[Note, NoteResponseDto].map_list(
                notes or [], NoteResponseDto, True
            )

            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=notes_mapped,
            )

        except Exception as e:
            await self.logger.log(
                action="Find",
                entity="Notes",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.note_service.begin_transaction()
            note = Mapper[NoteCreateDto, Note].map(data, Note)

            response = await self.note_service.create(note)

            if not response.success:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            created_note = response.data
            if not created_note:
                await self.note_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Note",
                    level="error",
                    code=500,
                    message="Failed to create note",
                    source="NoteController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create note",
                )
            note_mapped = Mapper[Note, NoteResponseDto].map(
                created_note, NoteResponseDto, True
            )

            await self.note_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=note_mapped,
                message="Note created successfully",
            )

        except Exception as e:
            await self.note_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request, id, data):
        try:
            await self.note_service.begin_transaction()
            note = cast(Note, Mapper[NoteUpdateDto, Note].map(data, Note))
            note.id = id

            response = await self.note_service.update(note)

            if not response.success:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_note = response.data
            if not updated_note:
                await self.note_service.rollback_transaction()
                await self.logger.log(
                    action="Update",
                    entity="Note",
                    level="error",
                    code=500,
                    message="Failed to update note",
                    source="NoteController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to update note, please try again later",
                )
            note_mapped = Mapper[Note, NoteResponseDto].map(
                updated_note, NoteResponseDto, True
            )

            await self.note_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=note_mapped,
                message="Note updated successfully",
            )

        except Exception as e:
            await self.note_service.rollback_transaction()
            await self.logger.log(
                action="Update",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request, id):
        try:
            await self.note_service.begin_transaction()
            data = Generator[NoteDeleteDto].generate(NoteDeleteDto, {"id": id})
            entity = Mapper[NoteDeleteDto, Note].map(data, Note)

            response = await self.note_service.delete(entity)

            if not response.success:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            await self.note_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Note deleted successfully",
            )

        except Exception as e:
            await self.note_service.rollback_transaction()
            await self.logger.log(
                action="Delete",
                entity="Note",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
