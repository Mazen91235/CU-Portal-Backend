from core.iControllers.iFileController import IFileController
from core.iServices.iHelperService import IHelperService
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.responseHandler import ResponseHandler


class FileController(IFileController):
    def __init__(self, helper_service: IHelperService, logger: IBaseLogger):
        self.helper_service = helper_service
        self.logger = logger

    # File Specific Functions
    async def download(self, request, id):
        try:
            download_response = await self.helper_service.download_file_from_drive(id)
            if not download_response.success:
                await self.logger.log(
                    action="Download",
                    entity="File",
                    level="error",
                    code=download_response.code or 500,
                    message=f"Failed to download file with id {id} from Google Drive : {download_response.message}",
                    details={"error": download_response.error},
                    source="FileController",
                )
                raise Exception(
                    f":Failed to download file from Google Drive : {download_response.message}"
                )
            downloaded_file = download_response.data
            if not downloaded_file:
                await self.logger.log(
                    action="Download",
                    entity="File",
                    level="error",
                    code=404,
                    message=f"File with id {id} not found in Google Drive",
                    details={},
                    source="FileController",
                )
                raise Exception(f":File not found in Google Drive")
            return ResponseHandler.generate_streaming_response(
                downloaded_file.content, downloaded_file.name
            )
        except Exception as e:
            await self.logger.log(
                action="Download",
                entity="File",
                level="error",
                code=500,
                message="An error occurred while processing the request",
                details={"error": repr(e)},
                source="FileController",
            )
            if repr(e).startswith(":"):
                raise Exception(repr(e)[1:])
            raise Exception(
                "An error occurred while processing the request, please try again later"
            )
