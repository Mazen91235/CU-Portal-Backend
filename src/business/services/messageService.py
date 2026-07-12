from core.iServices.iMessageService import IMessageService
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.message import Message
from core.dtos.baseDtos import BaseResponseDto
from core.dtos.messageDtos import MessageSearchDto
from core.utils.validator import Validator


class MessageService(IMessageService):
    def __init__(
        self,
        message_repository: IBaseRepository,
        helper_service: IHelperService,
        logger: IBaseLogger,
    ):
        self.message_repository = message_repository
        self.helper_service = helper_service
        self.logger = logger

    # Transaction Functions
    async def begin_transaction(self):
        await self.message_repository.begin_transaction()

    async def commit_transaction(self):
        await self.message_repository.commit_transaction()

    async def rollback_transaction(self):
        await self.message_repository.rollback_transaction()

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
                Message, data, ["name", "email", "phone"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Message, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Message", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Message", order_by
            )
            result = await self.message_repository.find_one(
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
            message = result.data
            return BaseResponseDto(success=True, data=message)
        except Exception as ex:
            await self.logger.log(
                action="FindOne",
                entity="Message",
                level="error",
                code=500,
                message=f"An error occurred while finding message",
                details={"error": str(ex)},
                source="MessageService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding message",
            )

    async def find(
        self,
        data: MessageSearchDto | None = None,
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
                Message, data, ["name", "email", "phone"], is_and, starts_with, is_exact
            )
            dynamic_includes = self.helper_service.generate_dynamic_includes(
                Message, includes
            )
            dynamic_selects = self.helper_service.generate_dynamic_selects(
                "Message", selects
            )
            dynamic_order_by = self.helper_service.generate_dynamic_order_by(
                "Message", order_by
            )
            result = await self.message_repository.find(
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
            messages = result.data
            return BaseResponseDto(success=True, data=messages)
        except Exception as ex:
            await self.logger.log(
                action="Find",
                entity="Message",
                level="error",
                code=500,
                message=f"An error occurred while finding messages",
                details={"error": str(ex)},
                source="MessageService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while finding messages",
            )

    async def create(self, data: Message) -> BaseResponseDto[Message]:
        try:
            validate_email_result = Validator.validate_email(data.email, True)
            if not validate_email_result.success:
                await self.logger.log(
                    action="Create",
                    entity="Message",
                    level="error",
                    code=400,
                    message="Invalid email address provided",
                    details={"error": validate_email_result.error},
                    source="MessageService",
                )
                return BaseResponseDto(
                    success=False,
                    code=validate_email_result.code,
                    data=None,
                    message=validate_email_result.message,
                )

            validated_email = validate_email_result.data
            if not validated_email:
                await self.logger.log(
                    action="Create",
                    entity="Message",
                    level="error",
                    code=400,
                    message="Email validation failed without a specific error",
                    source="MessageService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Email validation failed, please check the email format.",
                )
            data.email = validated_email.normalized.lower()

            if not Validator.is_valid_phone_number(data.phone):
                await self.logger.log(
                    action="Create",
                    entity="Message",
                    level="error",
                    code=400,
                    message="Invalid phone number provided",
                    source="MessageService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Invalid phone number format, please provide a valid phone number.",
                )

            message_exists_response = await self.message_repository.find_one(
                Message.email == data.email
            )
            if not message_exists_response.success:
                return BaseResponseDto(
                    success=False,
                    code=message_exists_response.code,
                    data=None,
                    message=message_exists_response.message,
                )
            message_exists = message_exists_response.data
            if message_exists:
                await self.logger.log(
                    action="Create",
                    entity="Message",
                    level="warning",
                    code=400,
                    message="A message from this email already exists",
                    source="MessageService",
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="A message from this email already exists",
                )

            created_message_response = await self.message_repository.create(data)
            if not created_message_response.success:
                return BaseResponseDto(
                    success=False,
                    code=created_message_response.code,
                    data=None,
                    message=created_message_response.message,
                )
            created_message = created_message_response.data

            await self.logger.log(
                action="Create",
                entity="Message",
                level="info",
                code=201,
                message="Message created successfully",
                source="MessageService",
            )
            return BaseResponseDto(success=True, code=201, data=created_message)
        except Exception as ex:
            await self.logger.log(
                action="Create",
                entity="Message",
                level="error",
                code=500,
                message="An error occurred while creating message",
                details={"error": str(ex)},
                source="MessageService",
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating message",
            )