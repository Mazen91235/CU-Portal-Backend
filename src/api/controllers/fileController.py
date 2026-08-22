from urllib.parse import quote
from fastapi import Response

from core.iControllers.iFileController import IFileController
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.attachment import Attachment
from core.utils.responseHandler import ResponseHandler


class FileController(IFileController):
    def __init__(
        self,
        attachment_repository: IBaseRepository[Attachment],
        helper_service: IHelperService,
        logger: IBaseLogger,
    ):
        self.attachment_repository = attachment_repository
        self.helper_service = helper_service
        self.logger = logger

    async def download_file(self, request):
        try:
            attachment_id = request.path_params.get("attachment_id")
            if not attachment_id:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Attachment ID is required",
                )
            try:
                attachment_id = int(attachment_id)
            except (TypeError, ValueError):
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="Attachment ID must be a valid integer",
                )
            attachment_response = await self.attachment_repository.find_one(
                Attachment.id == attachment_id
            )
            if not attachment_response.success:
                return ResponseHandler.generate_response(
                    success=False,
                    code=attachment_response.code,
                    message=attachment_response.message,
                )
            attachment = attachment_response.data
            if not attachment:
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="Attachment not found",
                )
            if not attachment.is_file:
                return ResponseHandler.generate_response(
                    success=False,
                    code=400,
                    message="This attachment is an external link, not a downloadable file",
                )

            file_exists_response = await self.helper_service.verify_file_exists_on_drive(
                attachment.url
            )
            if not file_exists_response.success or not file_exists_response.data:
                await self.attachment_repository.delete(attachment)
                await self.logger.log(
                    action="DownloadFile",
                    entity="Attachment",
                    level="info",
                    code=404,
                    message="Attachment file no longer exists on Google Drive; attachment removed",
                    details={"attachment_id": attachment.id, "url": attachment.url},
                    source="FileController",
                )
                return ResponseHandler.generate_response(
                    success=False,
                    code=404,
                    message="This file no longer exists on Google Drive and has been removed.",
                )

            file_id = self.helper_service.get_file_id_from_url(attachment.url)
            downloaded_response = await self.helper_service.download_file_from_drive(
                file_id
            )
            if not downloaded_response.success or not downloaded_response.data:
                return ResponseHandler.generate_response(
                    success=False,
                    code=downloaded_response.code or 500,
                    message=downloaded_response.message
                    or "Failed to download file from Google Drive",
                )
            downloaded_file = downloaded_response.data
            quoted_name = quote(downloaded_file.name)
            return Response(
                content=downloaded_file.content,
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_name}",
                    "Content-Length": str(len(downloaded_file.content)),
                },
            )
        except Exception as e:
            await self.logger.log(
                action="DownloadFile",
                entity="Attachment",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": str(e)},
                source="FileController",
            )
            return ResponseHandler.generate_response(
                success=False,
                code=500,
                message="An error occurred while processing the request, please try again later",
            )
