# FastAPI & Python Built-ins
from fastapi import Request
from pydantic import ValidationError
from datetime import datetime
import json

# Interfaces
from core.iControllers.iNoteController import INoteController
from core.iServices.iNoteService import INoteService
from core.iLoggers.iBaseLogger import IBaseLogger

# Utilities & Handlers
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.utils.parser import Parser

# Entities, DTOs & Models
from core.entities.note import Note
from core.dtos.noteDtos import (
    NoteSearchDto,
    NoteCreateDto,
    NoteResponseDto,
    NoteUpdateDto,
    NoteDeleteDto,
)
from core.models.queryModel import QueryModel


class NoteController(INoteController):
    def __init__(self, note_service: INoteService, logger: IBaseLogger):
        self.note_service = note_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request):
        try:
            note_id = request.path_params.get("note_id")
            if not note_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Note ID is required",
                )

            entity_search_dto = Generator[NoteSearchDto].generate(
                NoteSearchDto, {"id": note_id}
            )

            response = await self.note_service.find_one(
                entity_search_dto,
                [
                    "content",
                    "author_id",
                ],
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
                details={"error": str(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request: Request):
        try:
            query = Parser.parse_query(
                request.query_params.get("query", "{}"),
                QueryModel[NoteSearchDto],
            )
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

            if not notes:
                await self.logger.log(
                    action="Find",
                    entity="Note",
                    level="info",
                    code=404,
                    message="Notes not found",
                    source="NoteController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="notes not found",
                )

            notes_mapped = Mapper[Note, NoteResponseDto].map_list(
                notes, NoteResponseDto, True
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
                details={"error": str(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request: Request):
        try:
            await self.note_service.begin_transaction()
            payload = await request.json()
            data = Generator[NoteCreateDto].generate(NoteCreateDto, payload)
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
                details={"error": str(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def update(self, request: Request):
        try:
            await self.note_service.begin_transaction()

            note_id = request.path_params.get("note_id")

            if not note_id:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Note ID is required",
                )

            payload = await request.json()
            data = Generator[NoteUpdateDto].generate(NoteUpdateDto, payload)
            note = Mapper[NoteUpdateDto, Note].map(data, Note)
            note.id = int(note_id)

            response = await self.note_service.update(note)

            if not response.success:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            updated_note = response.data
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
                details={"error": str(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def delete(self, request: Request):
        try:
            await self.note_service.begin_transaction()

            note_id = request.path_params.get("note_id")

            if not note_id:
                await self.note_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Note ID is required",
                )

            data = Generator[NoteDeleteDto].generate(
                NoteDeleteDto, {"id": int(note_id)}
            )
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
                details={"error": str(e)},
                source="NoteController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
