from core.iControllers.iAttachmentController import IAttachmentController
from core.iServices.iAttachmentService import IAttachmentService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler


class AttachmentController(IAttachmentController):
    def __init__(self, attachment_service: IAttachmentService, logger: IBaseLogger):
        self.attachment_service = attachment_service
        self.logger = logger

    # File Specific Functions
    async def seed(self, request):
        try:
            await self.attachment_service.begin_transaction()
            seed_response = await self.attachment_service.seed()
            if not seed_response.success:
                await self.attachment_service.rollback_transaction()
                return ResponseHandler.generate_response(
                    success=False,
                    code=seed_response.code,
                    data=None,
                    message=seed_response.message,
                )
            await self.attachment_service.commit_transaction()
            return ResponseHandler.generate_response(
                success=True,
                code=200,
                message="Attachment seeding completed successfully",
            )
        except Exception as e:
            await self.attachment_service.rollback_transaction()
            await self.logger.log(
                action="Seed",
                entity="Attachment",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="AttachmentController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                data=None,
                message="An error occurred while processing the request",
            )

    async def validate(self, request, start_idx: int):
        raise NotImplementedError("The 'validate' method is not implemented yet.")
