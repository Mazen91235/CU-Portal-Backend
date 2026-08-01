import os
import aiohttp
from aiohttp import ClientResponse
import asyncio
import json
from typing import TypeVar, cast
from sqlalchemy import and_, func, or_
from aiosmtplib import SMTP
from email.message import EmailMessage
from sqlalchemy.orm import selectinload
from business.contextVars.requestContext import request_context
from business.contextVars.userContext import user_context
from core.iServices.iHelperService import IHelperService
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.user import User
from core.entities.notification import Notification
from core.entities.userNotification import UserNotification
from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import FetchedModel, DownloadedFileModel, FileModel
from core.utils.entitiesHandler import EntitiesHandler
from core.utils.fernetHandler import FernetHandler

U = TypeVar("U")  # EntitySearchDto Type


class HelperService(IHelperService[U]):
    def __init__(
        self,
        notification_repository: IBaseRepository[Notification],
        user_notification_repository: IBaseRepository[UserNotification],
    ):
        self.notification_repository = notification_repository
        self.user_notification_repository = user_notification_repository

    def _get_column_type(self, column):
        column_property = getattr(column, "property", None)
        columns = getattr(column_property, "columns", None)
        if not columns:
            return None
        return getattr(columns[0], "type", None)

    def _is_string_column(self, column):
        column_type = self._get_column_type(column)
        if not column_type:
            return False

        try:
            if column_type.python_type is str:
                return True
        except Exception:
            pass

        type_name = type(column_type).__name__.lower()
        return (
            "char" in type_name
            or "string" in type_name
            or "text" in type_name
            or "unicode" in type_name
        )

    async def get_ip_address(self):
        try:
            request = request_context.get(None)
            ip_address = request.client.host if request and request.client else None
            return BaseResponseDto(success=True, data=ip_address)
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching IP address",
                error=str(ex),
            )

    async def get_logged_in_user(self):
        try:
            user = user_context.get(None)
            if user:
                return BaseResponseDto[User | None](success=True, data=user)
            else:
                return BaseResponseDto[User | None](
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in user found",
                )
        except Exception as ex:
            return BaseResponseDto[User | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching logged-in user",
                error=str(ex),
            )

    async def send_email(self, to_email, subject, body):
        try:
            if os.environ.get("TESTING", "false").lower() == "true":
                # In testing mode, we won't actually send an email.
                return BaseResponseDto(success=True, data=True)
            smtp_host = os.environ.get("SMTP_HOST")
            smtp_port = int(os.environ.get("SMTP_PORT") or 587)
            smtp_user = os.environ.get("SMTP_USER", "")
            smtp_password = os.environ.get("SMTP_PASSWORD", "")
            smtp_from = os.environ.get("SMTP_FROM") or smtp_user

            async with SMTP(
                hostname=smtp_host,
                port=smtp_port,
            ) as smtp:
                await smtp.login(smtp_user, smtp_password)
                email_message = EmailMessage()
                email_message["From"] = smtp_from
                email_message["To"] = to_email
                email_message["Subject"] = subject
                email_message.set_content(body, subtype="html")
                await smtp.send_message(email_message)
                return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while sending the email",
                error=str(ex),
            )

    def generate_dynamic_includes(self, cls, includes):
        if not includes:
            return []

        includes_arr = []
        for include in includes:
            if not isinstance(include, str) or not include.strip():
                continue

            include_path = [item for item in include.split(".") if item]
            if not include_path:
                continue

            # Accept both "User.tokens" and "tokens" forms.
            if (
                include_path[0].lower() == cls.__name__.lower()
                and len(include_path) > 1
            ):
                include_path = include_path[1:]

            include_attr = getattr(cls, include_path[0], None)
            current_mapper = getattr(
                getattr(include_attr, "property", None), "mapper", None
            )
            if not include_attr or not current_mapper:
                continue

            include_item = selectinload(include_attr)

            for item in include_path[1:]:
                nested_attr = getattr(current_mapper.class_, item, None)
                if not nested_attr:
                    break
                current_mapper = getattr(
                    getattr(nested_attr, "property", None), "mapper", None
                )
                if not current_mapper:
                    break
                include_item = include_item.selectinload(nested_attr)

            includes_arr.append(include_item)
        return includes_arr

    def generate_dynamic_selects(self, entity_name, selects):
        if not selects:
            return []

        selects_arr = []
        for select in selects:
            if not isinstance(select, str) or not select.strip():
                continue

            entity = entity_name if "." not in select else select.split(".")[0]
            property_name = select if "." not in select else select.split(".")[1]
            select_item = EntitiesHandler.get_property(entity, property_name)
            if select_item:
                selects_arr.append(select_item)
        return selects_arr

    def generate_dynamic_order_by(self, entity_name, order_by):
        if not order_by:
            return []

        order_by_arr = []
        for order in order_by:
            if not isinstance(order, str) or not order.strip():
                continue

            entity = entity_name if "." not in order else order.split(".")[0]
            property_name = order if "." not in order else order.split(".")[1]
            order_item = EntitiesHandler.get_property(entity, property_name)
            if order_item:
                order_by_arr.append(order_item)
        return order_by_arr

    def generate_dynamic_predicate(
        self, cls, data, query_fields, is_and, starts_with, is_exact
    ):
        if not data or not cls:
            return None
        if not query_fields:
            query_fields = []
        to_dict = getattr(data, "model_dump", None)
        if callable(to_dict):
            data_dict = cast(dict, to_dict())
        elif isinstance(data, dict):
            data_dict = data
        else:
            return None

        conditions = []
        for key, value in data_dict.items():
            if value is None:
                continue
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue

            is_range_key = key.endswith("_from") or key.endswith("_to")
            field_name = key.rsplit("_", 1)[0] if is_range_key else key
            if field_name == "query" and len(query_fields) > 0:
                for query_field in query_fields:
                    column = getattr(cls, query_field, None)
                    if not column:
                        continue
                    if starts_with:
                        conditions.append(
                            func.lower(column).ilike(func.lower(f"{value}%"))
                        )
                    elif is_exact:
                        conditions.append(column == value)
                    else:
                        conditions.append(
                            func.lower(column).ilike(func.lower(f"%{value}%"))
                        )
                continue
            column = getattr(cls, field_name, None)
            if not column:
                continue

            if key.endswith("_from"):
                conditions.append(column >= value)
            elif key.endswith("_to"):
                conditions.append(column <= value)
            elif isinstance(value, str):
                if not self._is_string_column(column):
                    conditions.append(column == value)
                elif starts_with:
                    conditions.append(func.lower(column).ilike(func.lower(f"{value}%")))
                elif is_exact:
                    conditions.append(column == value)
                else:
                    conditions.append(
                        func.lower(column).ilike(func.lower(f"%{value}%"))
                    )
            else:
                conditions.append(column == value)

        if not conditions:
            return None

        return and_(*conditions) if is_and else or_(*conditions)

    # Notification Functions
    async def send_notification(
        self, notification_type, parent_id, user_ids, content, url=None
    ):
        try:
            notification = Notification(
                content=content,
                type=notification_type,
                parent_id=parent_id,
                url=url,
            )
            create_notification_response = await self.notification_repository.create(
                notification
            )
            if not create_notification_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_notification_response.code,
                    data=False,
                    message=create_notification_response.message,
                )
            created_notification = create_notification_response.data
            if not created_notification:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="Failed to create notification",
                )
            for user_id in user_ids or []:
                user_notification = UserNotification(
                    user_id=user_id, notification_id=created_notification.id
                )
                create_user_notification_response = (
                    await self.user_notification_repository.create(user_notification)
                )
                if not create_user_notification_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=create_user_notification_response.code,
                        data=False,
                        message=create_user_notification_response.message,
                    )
                created_user_notification = create_user_notification_response.data
                if not created_user_notification:
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=False,
                        message="Failed to create user notification",
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Notification sent successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while sending the notification",
                error=str(ex),
            )

    # File Functions
    async def _request_with_retries(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        data: aiohttp.FormData | None = None,
        json_data: dict | None = None,
        max_retries=6,
    ) -> BaseResponseDto[ClientResponse]:
        RATE_LIMIT_REASONS = [
            "userRateLimitExceeded",
            "rateLimitExceeded",
            "quotaExceeded",
        ]
        errors = []
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        data=data,
                        json=json_data,
                    ) as response:
                        json_response = await response.json()
                        if response.status == 429:  # Too Many Requests
                            retry_after = int(response.headers.get("Retry-After", 1))
                            await asyncio.sleep(retry_after)
                            continue
                        if response.status == 403:  # Forbidden
                            reason = (
                                json_response.get("error", {})
                                .get("errors", [{}])[0]
                                .get("reason", "")
                            )
                            if any(x in reason for x in RATE_LIMIT_REASONS):
                                retry_after = int(
                                    response.headers.get("Retry-After", 1)
                                )
                                await asyncio.sleep(retry_after)
                                continue
                        if response.status != 200:
                            return BaseResponseDto(
                                success=False,
                                code=response.status,
                                data=None,
                                message=f"Request failed with status {response.status}",
                                error=f"Request for {url} with method {method} failed with status {response.status} and response: {json.dumps(json_response)}",
                            )
                        return BaseResponseDto(
                            success=True,
                            code=response.status,
                            data=response,
                            message="Request successful",
                        )
            except Exception as ex:
                errors.append(str(ex))
                await asyncio.sleep(2**attempt)  # Exponential backoff
                continue
        return BaseResponseDto(
            success=False,
            code=500,
            data=None,
            message="Max retries exceeded for the request",
            error=f"Max retries exceeded for {url} with method {method}, errors: {json.dumps(errors)}",
        )

    def _format_file_model(self, metadata: dict) -> FileModel:
        return FileModel(
            id=metadata.get("id", ""),
            name=metadata.get("name", ""),
            mime_type=metadata.get("mimeType", ""),
            size=self._format_size(metadata.get("size", "0")),
            web_content_link=metadata.get("webContentLink", ""),
            web_view_link=metadata.get("webViewLink", ""),
            file_type=self.get_file_type(metadata.get("mimeType", "")),
        )

    def _format_size(self, size_in_bytes: str) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        if not size_in_bytes or not size_in_bytes.isdigit():
            return (
                "Unknown"
                if not any(x in size_in_bytes for x in units)
                else size_in_bytes
            )
        size = int(size_in_bytes)
        for unit in units:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def get_file_id_from_url(self, url):
        if not url:
            return None
        url = url.strip()
        if "drive.google.com" not in url:
            return None
        if "/file/d/" in url:
            parts = url.split("/file/d/")
            if len(parts) > 1:
                file_id_part = parts[1].split("/")[0]
                return file_id_part
        if "/folders/" in url:
            parts = url.split("/folders/")
            if len(parts) > 1:
                folder_id_part = parts[1].split("/")[0]
                return folder_id_part
        elif "id=" in url:
            parts = url.split("id=")
            if len(parts) > 1:
                file_id_part = parts[1].split("&")[0]
                return file_id_part
        return None

    def get_file_url_from_id(self, file_id):
        if not file_id:
            return None
        file_id = file_id.strip()
        if not file_id:
            return None
        return f"https://drive.google.com/uc?export=view&id={file_id}"

    def get_file_type(self, mime_type):
        mime_type = mime_type.strip().lower()
        file_types = [
            "image",
            "pdf",
            "doc",
            "sheet",
            "ppt",
            "video",
            "audio",
            "text",
            "archive",
            "gdrive",
            "folder",
        ]
        for file_type in file_types:
            if self.verify_file_type(mime_type, file_type):
                return file_type
        return "unknown"

    def verify_file_type(self, mime_type, expected_type):
        mime_type = mime_type.strip().lower()
        expected_type = expected_type.strip().lower()

        if expected_type == "image":
            return mime_type.startswith("image/")
        elif expected_type == "pdf":
            return "pdf" in mime_type
        elif expected_type in ["doc", "docx", "docs"]:
            return (
                "msword" in mime_type
                or "wordprocessingml" in mime_type
                or "vnd.openxmlformats-officedocument.wordprocessingml" in mime_type
                or "vnd.google-apps.document" in mime_type
            )
        elif expected_type in ["sheet", "xlsx", "xls", "excel"]:
            return (
                "spreadsheet" in mime_type
                or "excel" in mime_type
                or "vnd.ms-excel" in mime_type
                or "vnd.google-apps.spreadsheet" in mime_type
            )
        elif expected_type in ["ppt", "pptx", "powerpoint", "presentation"]:
            return (
                "presentation" in mime_type
                or "powerpoint" in mime_type
                or "vnd.ms-powerpoint" in mime_type
                or "vnd.google-apps.presentation" in mime_type
            )
        elif expected_type == "video":
            return mime_type.startswith("video/")
        elif expected_type == "audio":
            return mime_type.startswith("audio/")
        elif expected_type in ["text", "json", "xml", "csv", "html", "css", "js"]:
            return mime_type.startswith("text/") or any(
                ext in mime_type
                for ext in ["json", "xml", "csv", "html", "css", "javascript"]
            )
        elif expected_type in [
            "archive",
            "zip",
            "rar",
            "tar",
            "gzip",
            "7z",
            "bzip",
            "octet-stream",
            "compressed",
        ]:
            return any(
                ext in mime_type
                for ext in [
                    "zip",
                    "rar",
                    "tar",
                    "gzip",
                    "7z",
                    "bzip",
                    "octet-stream",
                    "compressed",
                ]
            ) or mime_type.startswith("application/x-")
        elif expected_type == "gdrive":
            return "vnd.google-apps" in mime_type
        elif expected_type == "folder":
            return mime_type == "application/vnd.google-apps.folder"
        else:
            return False

    def verify_file_size(self, file_size, max_size_in_bytes):
        units = ["B", "KB", "MB", "GB", "TB"]
        if not file_size or not file_size.isdigit():
            return False
        for unit in units:
            if file_size.endswith(unit):
                size_value = float(file_size[: -len(unit)].strip())
                size_in_bytes = size_value * (1024 ** units.index(unit))
                return size_in_bytes <= max_size_in_bytes
        return False

    async def fetch_from_drive(
        self,
        file_id,
        visited=None,
        max_retries=6,
    ) -> BaseResponseDto[FetchedModel]:
        try:
            if not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="File ID is required",
                    error="No file ID provided for fetching from Google Drive",
                )
            if not visited:
                visited = set()
            if file_id in visited:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Circular reference detected",
                    error=f"Circular reference detected for file ID: {file_id}",
                )
            visited.add(file_id)
            api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")
            params = {
                "fields": "id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails",
                "key": api_key,
            }
            response = await self._request_with_retries(
                method="GET",
                url=f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params=params,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error="Empty response data for file ID: {file_id}",
                )
            metadata = await response_data.json()
            if not metadata:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error="Empty metadata for file ID: {file_id}",
                )
            if metadata.get("shortcutDetails") and metadata["shortcutDetails"].get(
                "targetId"
            ):
                target_id = metadata["shortcutDetails"]["targetId"]
                result = await self.fetch_from_drive(
                    file_id=target_id, visited=visited, max_retries=max_retries
                )
                if result and result.data and result.data.data:
                    result.data.data.name = metadata.get("name", result.data.data.name)
                return result
            fetched_file = self._format_file_model(metadata)
            fetched_response = FetchedModel(data=fetched_file)
            if not self.verify_file_type(fetched_file.mime_type, "folder"):
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=fetched_response,
                    message="File fetched successfully",
                )
            queue = [
                (fetched_file.id, fetched_response.children)
            ]  # to get the children by reference
            while queue and len(queue) > 0:
                parent_id, children_list = queue.pop(0)
                page_token = None
                while True:
                    params = {
                        "q": f"'{parent_id}' in parents and trashed = false",
                        "fields": "nextPageToken, files(id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails)",
                        "key": api_key,
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    response = await self._request_with_retries(
                        method="GET",
                        url="https://www.googleapis.com/drive/v3/files",
                        params=params,
                        max_retries=max_retries,
                    )
                    if not response.success:
                        return BaseResponseDto(
                            success=False,
                            code=response.code,
                            data=None,
                            message=response.message,
                            error=response.error,
                        )
                    response_data = response.data
                    if not response_data:
                        break
                    json_response = await response_data.json()
                    if not json_response:
                        return BaseResponseDto(
                            success=False,
                            code=500,
                            data=None,
                            message="Bad Response from Google Drive API, please try again later",
                            error=f"Empty JSON response while fetching children for parent ID: {parent_id}",
                        )
                    for item in json_response.get("files", []):
                        child_model = FileModel(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            mime_type=item.get("mimeType", ""),
                            size=self._format_size(item.get("size", "0")),
                            web_content_link=item.get("webContentLink", ""),
                            web_view_link=item.get("webViewLink", ""),
                            file_type=self.get_file_type(item.get("mimeType", "")),
                        )
                        result_data = FetchedModel(data=child_model)
                        if item.get("shortcutDetails") and item["shortcutDetails"].get(
                            "targetId"
                        ):
                            target_id = item["shortcutDetails"]["targetId"]
                            result = await self.fetch_from_drive(
                                file_id=target_id,
                                visited=visited,
                                max_retries=max_retries,
                            )
                            if not result.success:
                                return BaseResponseDto(
                                    success=False,
                                    code=result.code,
                                    data=None,
                                    message=result.message,
                                    error=result.error,
                                )
                            result_data = result.data
                            if not result_data or not result_data.data:
                                return BaseResponseDto(
                                    success=False,
                                    code=500,
                                    data=None,
                                    message="Bad Response from Google Drive API, please try again later",
                                    error=f"Empty data for shortcut target ID: {target_id}",
                                )
                            result_data.data.name = item.get(
                                "name", result_data.data.name
                            )
                        children_list.append(result_data)
                        if self.verify_file_type(result_data.data.mime_type, "folder"):
                            if result_data.data.id not in visited:
                                visited.add(result_data.data.id)
                                queue.append(
                                    (result_data.data.id, result_data.children)
                                )
                    page_token = json_response.get("nextPageToken")
                    if not page_token:
                        break
            return BaseResponseDto(
                success=True,
                code=200,
                data=fetched_response,
                message="File and its children fetched successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching the file from Google Drive",
                error=str(ex),
            )

    async def get_google_access_token(
        self, user_refresh_token, max_retries=6
    ) -> BaseResponseDto[str]:
        try:
            if not user_refresh_token:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Bad Request, Please try again later",
                    error="No user refresh token provided for fetching Google access token",
                )
            client_id = os.environ.get("GOOGLE_CLIENT_ID")
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": FernetHandler.decrypt(user_refresh_token),
                "grant_type": "refresh_token",
            }
            response = await self._request_with_retries(
                method="POST",
                url="https://oauth2.googleapis.com/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                json_data=data,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google OAuth API, please try again later",
                    error="Empty response data while fetching Google access token",
                )
            json_response = await response_data.json()
            if not json_response or "access_token" not in json_response:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google OAuth API, please try again later",
                    error=f"Invalid JSON response while fetching Google access token: {json.dumps(json_response)}",
                )
            access_token = json_response["access_token"]
            return BaseResponseDto(
                success=True,
                code=200,
                data=access_token,
                message="Access token fetched successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching Connecting with Google API, please try again later",
                error=str(ex),
            )

    async def download_file_from_drive(
        self, file_id, max_retries=6
    ) -> BaseResponseDto[DownloadedFileModel]:
        try:
            if not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="File ID is required",
                    error="No file ID provided for downloading from Google Drive",
                )
            api_key = os.environ.get("GOOGLE_TOKEN_API_KEY")
            metadata_response = await self.fetch_from_drive(
                file_id=file_id, max_retries=max_retries
            )
            if not metadata_response.success:
                return BaseResponseDto(
                    success=False,
                    code=metadata_response.code,
                    data=None,
                    message=metadata_response.message,
                    error=metadata_response.error,
                )
            if not metadata_response.data or not metadata_response.data.data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty metadata for file ID: {file_id}",
                )
            file_metadata = metadata_response.data.data
            if not file_metadata.web_content_link:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="File cannot be downloaded directly from Google Drive",
                    error=f"No web content link for file ID: {file_id}",
                )
            download_url = f"{file_metadata.web_content_link}&key={api_key}"
            response = await self._request_with_retries(
                method="GET",
                url=download_url,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty response data while downloading file for file ID: {file_id}",
                )
            content = await response_data.read()
            downloaded_file = DownloadedFileModel(
                name=file_metadata.name,
                size=file_metadata.size,
                content=content,
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=downloaded_file,
                message="File downloaded successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while downloading the file from Google Drive",
                error=str(ex),
            )

    async def set_file_public_on_drive(
        self,
        access_token,
        file_id,
        max_retries=6,
    ) -> BaseResponseDto[bool]:
        try:
            if not access_token or not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Access token and file ID are required",
                    error="Missing required parameters for setting file public on Google Drive",
                )
            permission_url = (
                f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            permission_data = {
                "role": "reader",
                "type": "anyone",
            }
            response = await self._request_with_retries(
                method="POST",
                url=permission_url,
                headers=headers,
                json_data=permission_data,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty response data while setting file public for file ID: {file_id}",
                )
            json_response = await response_data.json()
            if not json_response or "id" not in json_response:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Invalid JSON response while setting file public for file ID: {file_id}, response: {json.dumps(json_response)}",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="File set to public successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while setting the file public on Google Drive",
                error=str(ex),
            )

    async def upload_file_to_drive(
        self,
        access_token,
        name,
        content,
        size=None,
        max_retries=6,
    ) -> BaseResponseDto[FileModel]:
        try:
            if not access_token or not name or not content:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Access token, file name, and content are required",
                    error="Missing required parameters for uploading to Google Drive",
                )
            upload_url = (
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
            )
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            metadata = {
                "name": name,
            }
            multipart_data = aiohttp.FormData()
            multipart_data.add_field(
                "metadata",
                json.dumps(metadata),
                content_type="application/json; charset=UTF-8",
            )
            multipart_data.add_field(
                "file",
                content,
                filename=name,
                content_type="application/octet-stream",
            )
            response = await self._request_with_retries(
                method="POST",
                url=upload_url,
                headers=headers,
                data=multipart_data,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            response_data = response.data
            if not response_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty response data while uploading file: {name}",
                )
            json_response = await response_data.json()
            if not json_response or "id" not in json_response:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Invalid JSON response while uploading file: {name}, response: {json.dumps(json_response)}",
                )
            json_response["size"] = size if size else str(len(content))
            uploaded_file = self._format_file_model(json_response)
            public_response = await self.set_file_public_on_drive(
                access_token=access_token,
                file_id=uploaded_file.id,
                max_retries=max_retries,
            )
            if not public_response.success:
                return BaseResponseDto(
                    success=False,
                    code=public_response.code,
                    data=None,
                    message=public_response.message,
                    error=public_response.error,
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=uploaded_file,
                message="File uploaded successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while uploading the file to Google Drive",
                error=str(ex),
            )

    async def delete_file_from_drive(
        self,
        access_token,
        file_id,
        max_retries=6,
    ) -> BaseResponseDto[bool]:
        try:
            if not access_token or not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Access token and file ID are required",
                    error="Missing required parameters for deleting file from Google Drive",
                )
            delete_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            response = await self._request_with_retries(
                method="DELETE",
                url=delete_url,
                headers=headers,
                max_retries=max_retries,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="File deleted successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting the file from Google Drive",
                error=str(ex),
            )

    async def copy_file_on_drive(
        self,
        access_token,
        file_id,
        new_name=None,
        max_retries=6,
    ) -> BaseResponseDto[FileModel]:
        try:
            if not access_token or not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Access token and file ID are required",
                    error="Missing required parameters for copying file on Google Drive",
                )
            downloaded_file_response = await self.download_file_from_drive(
                file_id=file_id, max_retries=max_retries
            )
            if not downloaded_file_response.success:
                return BaseResponseDto(
                    success=False,
                    code=downloaded_file_response.code,
                    data=None,
                    message=downloaded_file_response.message,
                    error=downloaded_file_response.error,
                )
            if not downloaded_file_response.data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty data while downloading file for file ID: {file_id}",
                )
            downloaded_file = downloaded_file_response.data
            upload_name = new_name if new_name else downloaded_file.name
            upload_response = await self.upload_file_to_drive(
                access_token=access_token,
                name=upload_name,
                content=downloaded_file.content,
                size=downloaded_file.size,
                max_retries=max_retries,
            )
            if not upload_response.success:
                return BaseResponseDto(
                    success=False,
                    code=upload_response.code,
                    data=None,
                    message=upload_response.message,
                    error=upload_response.error,
                )
            if not upload_response.data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Empty data while uploading copied file for original file ID: {file_id}",
                )
            uploaded_file = upload_response.data
            return BaseResponseDto(
                success=True,
                code=200,
                data=uploaded_file,
                message="File copied successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while copying the file on Google Drive",
                error=str(ex),
            )
