import os
from pathlib import Path
from typing import TypeVar, cast
from fastapi import UploadFile
from sqlalchemy import and_, or_
from aiosmtplib import SMTP
from email.message import EmailMessage
from sqlalchemy.orm import selectinload
from pgvector import Vector
from core.iServices.iHelperService import IHelperService
from core.dtos.baseDtos import BaseResponseDto
from core.entities.user import User
from core.entities.patient import Patient
from business.contextVars.requestContext import request_context
from business.contextVars.userContext import user_context
from business.contextVars.patientContext import patient_context
from core.utils.fileHandler import FileHandler
from core.utils.stringHandler import StringHandler
from core.utils.entitiesHandler import EntitiesHandler
from core.utils.aiHandler import AIHandler


U = TypeVar("U")  # EntitySearchDto Type


class HelperService(IHelperService[U]):
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}

    def _get_column_type(self, column):
        column_property = getattr(column, "property", None)
        columns = getattr(column_property, "columns", None)
        if not columns:
            return None
        return getattr(columns[0], "type", None)

    def _is_vector_column(self, column):
        column_type = self._get_column_type(column)
        if not column_type:
            return False
        type_name = type(column_type).__name__.lower()
        module_name = type(column_type).__module__.lower()
        return "vector" in type_name or "pgvector" in module_name

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

    def _coerce_vector_value(self, value):
        if isinstance(value, Vector):
            to_list = getattr(value, "to_list", None)
            if callable(to_list):
                return to_list()
            return value

        if isinstance(value, (list, tuple)):
            try:
                return [float(item) for item in value]
            except (TypeError, ValueError):
                return None

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return None
            if raw_value.startswith("[") and raw_value.endswith("]"):
                raw_value = raw_value[1:-1]
            if not raw_value:
                return []

            try:
                return [
                    float(item.strip()) for item in raw_value.split(",") if item.strip()
                ]
            except ValueError:
                return None

        return None

    async def get_ip_address(self):
        try:
            request = request_context.get(None)
            ip_address = request.client.host if request and request.client else None
            return BaseResponseDto[str | None](success=True, data=ip_address)
        except Exception as ex:
            return BaseResponseDto[str | None](
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

    async def get_logged_in_patient(self):
        try:
            patient = patient_context.get(None)
            if patient:
                return BaseResponseDto[Patient | None](success=True, data=patient)
            else:
                return BaseResponseDto[Patient | None](
                    success=False,
                    code=401,
                    data=None,
                    message="No logged-in patient found",
                )
        except Exception as ex:
            return BaseResponseDto[Patient | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching logged-in patient",
                error=str(ex),
            )

    async def store_file(self, file):
        try:
            await file.seek(0)
            extension = FileHandler.get_file_extension(file)
            random_filename = StringHandler.generate_random_string(32) + extension
            path = FileHandler.generate_file_path(random_filename)
            await file.seek(0)
            with open(path, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    buffer.write(chunk)

            await file.seek(0)
            return BaseResponseDto[str | None](
                success=True,
                data=f"/uploads/{random_filename}",
            )
        except Exception as ex:
            return BaseResponseDto[str | None](
                success=False,
                code=500,
                data=None,
                message="An error occurred while storing the file",
                error=str(ex),
            )

    def validate_image_file(self, file: UploadFile) -> BaseResponseDto[bool]:
        try:
            extension = FileHandler.get_file_extension(file)
        except Exception as ex:
            return BaseResponseDto[bool](
                success=False,
                code=400,
                data=False,
                message=f"Invalid image file - {str(ex)}",
                error=str(ex),
            )

        if extension not in self.IMAGE_EXTENSIONS:
            return BaseResponseDto[bool](
                success=False,
                code=400,
                data=False,
                message="The provided file is not a supported image format",
            )

        return BaseResponseDto[bool](success=True, data=True)

    def resolve_voice_and_image_files(
        self, files: list[UploadFile]
    ) -> BaseResponseDto[tuple[UploadFile, UploadFile] | None]:
        voice_file = None
        image_file = None

        for current_file in files or []:
            try:
                extension = FileHandler.get_file_extension(current_file)
            except Exception:
                continue

            if extension in self.AUDIO_EXTENSIONS and voice_file is None:
                voice_file = current_file
            elif extension in self.IMAGE_EXTENSIONS and image_file is None:
                image_file = current_file

            if voice_file and image_file:
                break

        if not voice_file or not image_file:
            return BaseResponseDto[tuple[UploadFile, UploadFile] | None](
                success=False,
                code=400,
                data=None,
                message="Expected one voice file and one image file for patient user registration",
            )

        return BaseResponseDto[tuple[UploadFile, UploadFile] | None](
            success=True,
            code=200,
            data=(voice_file, image_file),
        )

    async def delete_file(self, file_path):
        try:
            path = FileHandler.retrieve_file_path(file_path)
            if path.exists():
                path.unlink()
                return BaseResponseDto(success=True, data=True)
            else:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=False,
                    message="File not found for deletion",
                )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while deleting the file",
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

    def generate_dynamic_predicate(self, cls, data, is_and, starts_with, is_exact):
        if not data or not cls:
            return None

        to_dict = getattr(data, "to_dict", None)
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
            column = getattr(cls, field_name, None)
            if not column:
                continue

            if self._is_vector_column(column):
                vector_value = self._coerce_vector_value(value)
                if vector_value is None:
                    continue
                conditions.append(
                    column.cosine_distance(vector_value) <= (1 - AIHandler.THRESHOLD)
                )
                continue

            if key.endswith("_from"):
                conditions.append(column >= value)
            elif key.endswith("_to"):
                conditions.append(column <= value)
            elif isinstance(value, str):
                if not self._is_string_column(column):
                    conditions.append(column == value)
                elif starts_with:
                    conditions.append(column.ilike(f"{value}%"))
                elif is_exact:
                    conditions.append(column == value)
                else:
                    conditions.append(column.ilike(f"%{value}%"))
            else:
                conditions.append(column == value)

        if not conditions:
            return None

        return and_(*conditions) if is_and else or_(*conditions)
