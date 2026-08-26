from core.iControllers.iMessageController import IMessageController
from core.iServices.iMessageService import IMessageService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.mapper import Mapper
from core.utils.generator import Generator
from core.utils.responseHandler import ResponseHandler
from core.entities.message import Message
from core.dtos.messageDtos import MessageCreateDto, MessageResponseDto, MessageSearchDto
from core.models.queryModel import QueryModel


class MessageController(IMessageController):
    def __init__(self, message_service: IMessageService, logger: IBaseLogger):
        self.message_service = message_service
        self.logger = logger

    # CRUD Functions
    async def find_one(self, request, id):
        try:
            entity_search_dto = Generator[MessageSearchDto].generate(
                MessageSearchDto, {"id": id}
            )
            response = await self.message_service.find_one(entity_search_dto)
            if not response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            message = response.data
            if not message:
                await self.logger.log(
                    action="FindOne",
                    entity="Message",
                    level="info",
                    code=404,
                    message="Message not found",
                    source="MessageController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Message not found",
                )

            message_mapped = Mapper[Message, MessageResponseDto].map(
                message, MessageResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=message_mapped,
            )
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Message",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="MessageController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def find(self, request, query):
        try:
            entity_search_dto = Generator[MessageSearchDto].generate_from_query(
                MessageSearchDto, query
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

            response = await self.message_service.find(
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

            messages = response.data
            if not messages:
                await self.logger.log(
                    action="Find",
                    entity="Message",
                    level="info",
                    code=404,
                    message="Messages not found",
                    source="MessageController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Messages not found",
                )

            messages_mapped = Mapper[Message, MessageResponseDto].map_list(
                messages, MessageResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                data=messages_mapped,
                next_page=response.next_page,
            )
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Message",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="MessageController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )

    async def create(self, request, data):
        try:
            await self.message_service.begin_transaction()
            message = Mapper[MessageCreateDto, Message].map(data, Message)
            response = await self.message_service.create(message)
            if not response.success:
                await self.message_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=response.code,
                    message=response.message,
                )

            message = response.data
            if not message:
                await self.message_service.rollback_transaction()
                await self.logger.log(
                    action="Create",
                    entity="Message",
                    level="error",
                    code=500,
                    message="Failed to create message",
                    source="MessageController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=500,
                    message="Failed to create message, please try again later",
                )
            await self.message_service.commit_transaction()
            message_mapped = Mapper[Message, MessageResponseDto].map(
                message, MessageResponseDto, True
            )
            return ResponseHandler.generate_response(
                success=True,
                code=201,
                data=message_mapped,
                message="Message created successfully",
            )
        except Exception as ex:
            await self.message_service.rollback_transaction()
            await self.logger.log(
                action="Create",
                entity="Message",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(ex)},
                source="MessageController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
