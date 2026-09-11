import os
import aiohttp
from aiohttp import FormData
import asyncio
import json
from collections.abc import AsyncIterable
from typing import TypeVar, cast
from sqlalchemy import and_, func, or_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from business.contextVars.requestContext import request_context
from business.contextVars.userContext import user_context
from business.contextVars.permissionsContext import permissions_context
from core.iServices.iHelperService import IHelperService
from core.iRepositories.iBaseRepository import IBaseRepository
from core.entities.user import User
from core.entities.role import Role
from core.entities.faculty import Faculty
from core.entities.department import Department
from core.entities.year import Year
from core.entities.subject import Subject
from core.entities.userSubjectLink import UserSubjectLink
from core.entities.notification import Notification
from core.entities.userNotification import UserNotification
from core.entities.attachment import Attachment
from core.entities.log import Log
from core.entities.event import Event
from core.entities.eventOrganizer import EventOrganizer
from core.dtos.baseDtos import BaseResponseDto
from core.models.fileModels import (
    RequestResponseModel,
    FetchedModel,
    DownloadedFileModel,
    FileModel,
)
from core.utils.entitiesHandler import EntitiesHandler
from core.utils.fernetHandler import FernetHandler
from core.utils.timezoneHandler import TimezoneHandler
from core.utils.validator import Validator
from core.utils.firebaseHandler import FirebaseHandler

U = TypeVar("U")  # EntitySearchDto Type


class HelperService(IHelperService[U]):
    def __init__(
        self,
        notification_repository: IBaseRepository[Notification],
        user_notification_repository: IBaseRepository[UserNotification],
        user_repository: IBaseRepository[User],
        role_repository: IBaseRepository[Role],
        faculty_repository: IBaseRepository[Faculty],
        department_repository: IBaseRepository[Department],
        year_repository: IBaseRepository[Year],
        subject_repository: IBaseRepository[Subject],
        attachment_repository: IBaseRepository[Attachment],
        log_repository: IBaseRepository[Log],
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.notification_repository = notification_repository
        self.user_notification_repository = user_notification_repository
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.faculty_repository = faculty_repository
        self.department_repository = department_repository
        self.year_repository = year_repository
        self.subject_repository = subject_repository
        self.attachment_repository = attachment_repository
        self.log_repository = log_repository
        self.smtp_name = os.environ.get("SMTP_FROM_NAME", "")
        self.smtp_email = os.environ.get("SMTP_FROM_EMAIL", "")
        self.brevo_api_url = os.environ.get("BREVO_API_URL", "")
        self.brevo_api_key = os.environ.get("BREVO_API_KEY", "")
        self.session_factory = session_factory

    async def _log(
        self,
        action: str,
        entity: str,
        level: str,
        code: int,
        message: str,
        details: dict | None = None,
    ):
        try:
            ip_address_response = await self.get_ip_address()
            ip_address = (
                ip_address_response.data if ip_address_response.success else None
            )
            logged_in_user_response = await self.get_logged_in_user()
            logged_in_user_id = (
                logged_in_user_response.data.id
                if logged_in_user_response.success and logged_in_user_response.data
                else None
            )

            request = request_context.get(None)
            route = request.url.path if request else None

            formatted_details = (
                json.dumps(details, default=str) if details is not None else None
            )

            await self.log_repository.execute_sql(
                f"INSERT INTO {EntitiesHandler.TABLES.get('Log')} (action, entity, level, response_code, message, details, source, route, ip, user_id, created_at, updated_at) VALUES (:action, :entity, :level, :response_code, :message, :details, :source, :route, :ip, :user_id, :created_at, :updated_at)",
                {
                    "action": action,
                    "entity": entity,
                    "level": level,
                    "response_code": code,
                    "message": message,
                    "details": formatted_details,
                    "source": "HelperService",
                    "route": route,
                    "ip": ip_address,
                    "user_id": logged_in_user_id,
                    "created_at": TimezoneHandler.now("UTC"),
                    "updated_at": TimezoneHandler.now("UTC"),
                },
            )
        except Exception as ex:
            print(f"Failed to log message: {repr(ex)}")
            return

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
                error=repr(ex),
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
                error=repr(ex),
            )

    async def get_logged_in_user_permissions(self):
        try:
            permissions = permissions_context.get(None)
            return BaseResponseDto(success=True, data=permissions)
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while fetching logged-in user permissions",
                error=repr(ex),
            )

    async def verify_restricted_access(
        self, faculty_id=None, department_id=None, year_id=None, subject_id=None
    ):
        try:
            user_response = await self.get_logged_in_user()
            if not user_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_response.code,
                    data=False,
                    message=user_response.message,
                )
            user = user_response.data
            if not user:
                return BaseResponseDto(
                    success=False,
                    code=401,
                    data=False,
                    message="No logged-in user found",
                )
            user_permissions_response = await self.get_logged_in_user_permissions()
            if not user_permissions_response.success:
                return BaseResponseDto(
                    success=False,
                    code=user_permissions_response.code,
                    data=False,
                    message=user_permissions_response.message,
                )
            user_permissions = user_permissions_response.data
            if not user_permissions:
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="User has no permissions assigned",
                )
            if (
                faculty_id
                and user.faculty_id != faculty_id
                and "Access All Faculties" not in user_permissions
            ):
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="User does not have access to the specified faculty",
                )
            if faculty_id:
                faculty_response = await self.faculty_repository.find_one(
                    Faculty.id == faculty_id
                )
                if not faculty_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=faculty_response.code,
                        data=False,
                        message=faculty_response.message,
                    )
                faculty = faculty_response.data
                if not faculty:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Faculty with ID {faculty_id} not found",
                    )
            if (
                department_id
                and user.department_id != department_id
                and "Access All Departments" not in user_permissions
            ):
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="User does not have access to the specified department",
                )
            if department_id and not faculty_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Department ID specified without corresponding Faculty ID",
                )
            if department_id:
                department_response = await self.department_repository.find_one(
                    Department.id == department_id
                )
                if not department_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=department_response.code,
                        data=False,
                        message=department_response.message,
                    )
                department = department_response.data
                if not department:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Department with ID {department_id} not found",
                    )
                if faculty_id and department.faculty_id != faculty_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Department does not belong to the specified faculty",
                    )
                if (
                    department.faculty_id != user.faculty_id
                    and "Access All Faculties" not in user_permissions
                ):
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=False,
                        message="User does not have access to the faculty of the specified department",
                    )
            if (
                year_id
                and user.year_id != year_id
                and "Access All Years" not in user_permissions
            ):
                return BaseResponseDto(
                    success=False,
                    code=403,
                    data=False,
                    message="User does not have access to the specified year",
                )
            if year_id:
                year_response = await self.year_repository.find_one(Year.id == year_id)
                if not year_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=year_response.code,
                        data=False,
                        message=year_response.message,
                    )
                year = year_response.data
                if not year:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Year with ID {year_id} not found",
                    )
            if subject_id:
                dynamic_includes = self.generate_dynamic_includes(
                    Subject, ["user_subject_links.user"]
                )
                subject_response = await self.subject_repository.find_one(
                    Subject.id == subject_id, dynamic_includes
                )
                if not subject_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=subject_response.code,
                        data=False,
                        message=subject_response.message,
                    )
                subject = subject_response.data
                if not subject:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Subject with ID {subject_id} not found",
                    )
                if faculty_id and subject.faculty_id != faculty_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified faculty",
                    )
                if department_id and subject.department_id != department_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified department",
                    )
                if year_id and subject.year_id != year_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified year",
                    )
                user_ids = [user.id for user in subject.users] if subject.users else []
                if (
                    user.id not in user_ids
                    and "Access All Courses" not in user_permissions
                ):
                    return BaseResponseDto(
                        success=False,
                        code=403,
                        data=False,
                        message="User does not have access to the specified subject",
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="User has access to the specified faculty, department, and year",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while verifying restricted access",
                error=repr(ex),
            )

    async def verify_academic_data(
        self, faculty_id=None, department_id=None, year_id=None, subject_id=None
    ):
        try:
            if faculty_id:
                faculty_response = await self.faculty_repository.find_one(
                    Faculty.id == faculty_id
                )
                if not faculty_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=faculty_response.code,
                        data=False,
                        message=faculty_response.message,
                    )
                faculty = faculty_response.data
                if not faculty:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Faculty with ID {faculty_id} not found",
                    )
            if department_id and not faculty_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=False,
                    message="Department ID specified without corresponding Faculty ID",
                )
            if department_id:
                department_response = await self.department_repository.find_one(
                    Department.id == department_id
                )
                if not department_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=department_response.code,
                        data=False,
                        message=department_response.message,
                    )
                department = department_response.data
                if not department:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Department with ID {department_id} not found",
                    )
                if faculty_id and department.faculty_id != faculty_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Department does not belong to the specified faculty",
                    )
            if year_id:
                year_response = await self.year_repository.find_one(Year.id == year_id)
                if not year_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=year_response.code,
                        data=False,
                        message=year_response.message,
                    )
                year = year_response.data
                if not year:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Year with ID {year_id} not found",
                    )
            if subject_id:
                subject_response = await self.subject_repository.find_one(
                    Subject.id == subject_id
                )
                if not subject_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=subject_response.code,
                        data=False,
                        message=subject_response.message,
                    )
                subject = subject_response.data
                if not subject:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"Subject with ID {subject_id} not found",
                    )
                if faculty_id and subject.faculty_id != faculty_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified faculty",
                    )
                if department_id and subject.department_id != department_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified department",
                    )
                if year_id and subject.year_id != year_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Subject does not belong to the specified year",
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Academic data is valid and consistent",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while verifying academic data",
                error=repr(ex),
            )

    async def send_email(self, to_email, subject, body):
        try:
            if os.environ.get("TESTING", "false").lower() == "true":
                # In testing mode, we won't actually send an email.
                return BaseResponseDto(success=True, data=True)
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    self.brevo_api_url,
                    headers={
                        "accept": "application/json",
                        "api-key": self.brevo_api_key,
                        "content-type": "application/json",
                    },
                    json={
                        "sender": {"name": self.smtp_name, "email": self.smtp_email},
                        "to": [{"email": to_email}],
                        "subject": subject,
                        "htmlContent": body,
                    },
                )
                if response.status != 201:
                    return BaseResponseDto(
                        success=False,
                        code=response.status,
                        data=False,
                        message=f"Failed to send email. Please try again later.",
                        error=f"Code: {response.status}, Response: {await response.text()}",
                    )
            return BaseResponseDto(success=True, data=True)
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while sending the email",
                error=repr(ex),
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
        self, cls, data, query_fields, is_and, starts_with, is_exact, allow_nulls=False
    ):
        if not cls:
            return None
        if not query_fields:
            query_fields = []
        if not data:
            data = {}
        to_dict = getattr(data, "model_dump", None)
        if callable(to_dict):
            data_dict = cast(dict, to_dict(exclude_unset=True, exclude_none=False))
        elif isinstance(data, dict):
            data_dict = data
        else:
            return None

        conditions = []
        for key, value in data_dict.items():
            is_range_key = key.endswith("_from") or key.endswith("_to")
            field_name = key.rsplit("_", 1)[0] if is_range_key else key

            if value is None:
                conditions.append(getattr(cls, field_name).is_(None))
                continue

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    continue

            if field_name == "query" and len(query_fields) > 0:
                query_conditions = []
                for query_field in query_fields:
                    column = getattr(cls, query_field, None)
                    if not column:
                        continue
                    if starts_with:
                        query_conditions.append(
                            func.lower(column).ilike(func.lower(f"{value}%"))
                        )
                    elif is_exact:
                        query_conditions.append(column == value)
                    else:
                        query_conditions.append(
                            func.lower(column).ilike(func.lower(f"%{value}%"))
                        )
                if len(query_conditions) > 0:
                    conditions.append(or_(*query_conditions))
                continue

            column = getattr(cls, field_name, None)

            if not column:
                continue

            if key.endswith("_from"):
                if allow_nulls:
                    conditions.append(
                        (column.is_(None))
                        | (column >= TimezoneHandler.from_isoformat(value))
                    )
                else:
                    conditions.append(
                        column.isnot(None)
                        & (column >= TimezoneHandler.from_isoformat(value))
                    )
            elif key.endswith("_to"):
                if allow_nulls:
                    conditions.append(
                        (column.is_(None))
                        | (column <= TimezoneHandler.from_isoformat(value)),
                    )
                else:
                    conditions.append(
                        column.isnot(None)
                        & (column <= TimezoneHandler.from_isoformat(value))
                    )
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

        result = None

        if conditions:
            result = and_(*conditions) if is_and else or_(*conditions)

        request = request_context.get(None)
        user = user_context.get(None)

        if not request or not user:
            return result

        if hasattr(cls, "subject_id"):
            if request.state.restrict_courses:
                user_subjects_subquery = (
                    select(UserSubjectLink.subject_id)
                    .where(UserSubjectLink.user_id == user.id)
                    .scalar_subquery()
                )
                if result is not None:
                    result = and_(
                        result,
                        or_(
                            getattr(cls, "subject_id").is_(None),
                            getattr(cls, "subject_id").in_(user_subjects_subquery),
                        ),
                    )
                else:
                    result = or_(
                        getattr(cls, "subject_id").is_(None),
                        getattr(cls, "subject_id").in_(user_subjects_subquery),
                    )
        else:
            if hasattr(cls, "faculty_id") and request.state.restrict_faculties:
                if result is not None:
                    result = and_(
                        result,
                        or_(
                            getattr(cls, "faculty_id").is_(None),
                            getattr(cls, "faculty_id") == user.faculty_id,
                        ),
                    )
                else:
                    result = or_(
                        getattr(cls, "faculty_id").is_(None),
                        getattr(cls, "faculty_id") == user.faculty_id,
                    )
            if hasattr(cls, "department_id") and request.state.restrict_departments:
                if result is not None:
                    result = and_(
                        result,
                        or_(
                            getattr(cls, "department_id").is_(None),
                            getattr(cls, "department_id") == user.department_id,
                        ),
                    )
                else:
                    result = or_(
                        getattr(cls, "department_id").is_(None),
                        getattr(cls, "department_id") == user.department_id,
                    )
            if hasattr(cls, "year_id") and request.state.restrict_years:
                if result is not None:
                    result = and_(
                        result,
                        or_(
                            getattr(cls, "year_id").is_(None),
                            getattr(cls, "year_id") == user.year_id,
                        ),
                    )
                else:
                    result = or_(
                        getattr(cls, "year_id").is_(None),
                        getattr(cls, "year_id") == user.year_id,
                    )

        return result

    # Notification Functions
    async def _send_notification(
        self,
        notification_type,
        parent_id,
        content,
        url=None,
        faculty_id=None,
        department_id=None,
        year_id=None,
        subject_id=None,
    ):
        if not self.session_factory:
            await self._log(
                action="SendNotification",
                entity="Notification",
                level="error",
                code=500,
                message="Session factory is not initialized",
                details={},
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="Session factory is not initialized",
            )
        return_response = None
        user_ids = set()
        async with self.session_factory() as session:
            try:
                await session.begin()  # Start a transaction
                if (
                    not faculty_id
                    and not department_id
                    and not year_id
                    and not subject_id
                ):
                    users_response = await self.user_repository.find(
                        limit=int(1e6), session=session
                    )
                    if not users_response.success:
                        return_response = BaseResponseDto(
                            success=False,
                            code=users_response.code,
                            data=False,
                            message=users_response.message,
                        )
                        return return_response
                    users = users_response.data
                    user_ids.update([user.id for user in (users or [])])
                else:
                    if faculty_id:
                        dynamic_includes = self.generate_dynamic_includes(
                            Faculty, ["users"]
                        )
                        faculty_response = await self.faculty_repository.find_one(
                            Faculty.id == faculty_id, dynamic_includes, session=session
                        )
                        if not faculty_response.success:
                            return_response = BaseResponseDto(
                                success=False,
                                code=faculty_response.code,
                                data=False,
                                message=faculty_response.message,
                            )
                            return return_response
                        faculty = faculty_response.data
                        if not faculty:
                            return_response = BaseResponseDto(
                                success=False,
                                code=404,
                                data=False,
                                message=f"Faculty with ID {faculty_id} not found",
                            )
                            return return_response
                        if len(user_ids) < 1:
                            user_ids.update([user.id for user in (faculty.users or [])])
                        else:
                            user_ids.intersection_update(
                                [user.id for user in (faculty.users or [])]
                            )
                    if department_id:
                        dynamic_includes = self.generate_dynamic_includes(
                            Department, ["users"]
                        )
                        department_response = await self.department_repository.find_one(
                            Department.id == department_id,
                            dynamic_includes,
                            session=session,
                        )
                        if not department_response.success:
                            return_response = BaseResponseDto(
                                success=False,
                                code=department_response.code,
                                data=False,
                                message=department_response.message,
                            )
                            return return_response
                        department = department_response.data
                        if not department:
                            return_response = BaseResponseDto(
                                success=False,
                                code=404,
                                data=False,
                                message=f"Department with ID {department_id} not found",
                            )
                            return return_response
                        if len(user_ids) < 1:
                            user_ids.update(
                                [user.id for user in (department.users or [])]
                            )
                        else:
                            user_ids.intersection_update(
                                [user.id for user in (department.users or [])]
                            )
                    if year_id:
                        dynamic_includes = self.generate_dynamic_includes(
                            Year, ["users"]
                        )
                        year_response = await self.year_repository.find_one(
                            Year.id == year_id, dynamic_includes, session=session
                        )
                        if not year_response.success:
                            return_response = BaseResponseDto(
                                success=False,
                                code=year_response.code,
                                data=False,
                                message=year_response.message,
                            )
                            return return_response
                        year = year_response.data
                        if not year:
                            return_response = BaseResponseDto(
                                success=False,
                                code=404,
                                data=False,
                                message=f"Year with ID {year_id} not found",
                            )
                            return return_response
                        if len(user_ids) < 1:
                            user_ids.update([user.id for user in (year.users or [])])
                        else:
                            user_ids.intersection_update(
                                [user.id for user in (year.users or [])]
                            )
                    if subject_id:
                        dynamic_includes = self.generate_dynamic_includes(
                            Subject, ["user_subject_links.user"]
                        )
                        subject_response = await self.subject_repository.find_one(
                            Subject.id == subject_id, dynamic_includes, session=session
                        )
                        if not subject_response.success:
                            return_response = BaseResponseDto(
                                success=False,
                                code=subject_response.code,
                                data=False,
                                message=subject_response.message,
                            )
                            return return_response
                        subject = subject_response.data
                        if not subject:
                            return_response = BaseResponseDto(
                                success=False,
                                code=404,
                                data=False,
                                message=f"Subject with ID {subject_id} not found",
                            )
                            return return_response
                        if len(user_ids) < 1:
                            user_ids.update([user.id for user in (subject.users or [])])
                        else:
                            user_ids.intersection_update(
                                [user.id for user in (subject.users or [])]
                            )
                if len(user_ids) < 1:
                    return_response = BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message="No users found for the specified criteria",
                    )
                    return return_response
                notification = Notification(
                    content=content,
                    notification_type=notification_type,
                    parent_id=parent_id,
                    url=url,
                    user_notifications=set(
                        UserNotification(user_id=user_id)
                        for user_id in (user_ids or [])
                    ),
                )
                create_notification_response = (
                    await self.notification_repository.create(
                        notification, session=session
                    )
                )
                if not create_notification_response.success:
                    return_response = BaseResponseDto(
                        success=False,
                        code=create_notification_response.code,
                        data=False,
                        message=create_notification_response.message,
                    )
                    return return_response
                created_notification = create_notification_response.data
                if not created_notification:
                    return_response = BaseResponseDto(
                        success=False,
                        code=500,
                        data=False,
                        message="Failed to create notification",
                    )
                    return return_response
                await self._send_push_notifications(
                    session,
                    user_ids,
                    created_notification.id,
                    notification_type,
                    content,
                    url=url,
                )
                await session.commit()  # Commit the transaction
                return_response = BaseResponseDto(
                    success=True,
                    code=200,
                    data=True,
                    message="Notification sent successfully",
                )
                return return_response
            except Exception as ex:
                await session.rollback()  # Rollback the transaction on error
                await self._log(
                    action="SendNotification",
                    entity="Notification",
                    level="error",
                    code=500,
                    message="An error occurred while sending the notification",
                    details={"error": repr(ex)},
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="An error occurred while sending the notification",
                    error=repr(ex),
                )
            finally:
                if return_response is not None:
                    await self._log(
                        action="SendNotification",
                        entity="Notification",
                        level=(
                            "info"
                            if return_response.success
                            else (
                                "warning"
                                if (return_response.code or 500) < 500
                                else "error"
                            )
                        ),
                        code=return_response.code or 500,
                        message=return_response.message
                        or "Notification processing completed",
                        details=(
                            {"error": return_response.error}
                            if return_response.error
                            else {}
                        ),
                    )
                await session.close()  # Ensure the session is closed

    async def _send_push_notifications(
        self, session, user_ids, notification_id, notification_type, body, url=None
    ):
        try:
            title = "New Notification"
            if "new" in body.lower():
                if notification_type.lower() == "announcement":
                    title = "New Announcement has been posted"
                elif notification_type.lower() == "task":
                    title = "New Task has been assigned"
                elif notification_type.lower() == "exam":
                    title = "New Exam has been scheduled"
                elif notification_type.lower() == "event":
                    title = "New Event has been created"
            elif "updated" in body.lower():
                if notification_type.lower() == "announcement":
                    title = "Announcement has been updated"
                elif notification_type.lower() == "task":
                    title = "Task has been updated"
                elif notification_type.lower() == "exam":
                    title = "Exam has been updated"
                elif notification_type.lower() == "event":
                    title = "Event has been updated"
            for user_id in user_ids:
                user_response = await self.user_repository.find_one(User.id == user_id)
                if not user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=user_response.code,
                        data=False,
                        message=user_response.message,
                    )
                user = user_response.data
                if not user:
                    await self._log(
                        action="SendPushNotifications",
                        entity="Notification",
                        level="error",
                        code=404,
                        message=f"User with ID {user_id} not found while sending push notifications",
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"User with ID {user_id} not found",
                    )
                should_update_devices = False
                for device_token in user.devices or []:
                    if not device_token or not device_token.strip():
                        continue
                    send_response = FirebaseHandler.send_notification(
                        device_token=device_token,
                        title=title,
                        body=body,
                        url=url,
                        notification_id=notification_id,
                    )
                    if not send_response.success and send_response.code == 404:
                        user.devices.remove(device_token)
                        should_update_devices = True
                    if not send_response.success:
                        await self._log(
                            action="SendPushNotifications",
                            entity="Notification",
                            level="error",
                            code=send_response.code or 500,
                            message=f"Failed to send push notification to user {user_id} for device token {device_token}",
                            details={"error": send_response.error},
                        )
                if should_update_devices:
                    await self.user_repository.update(
                        user, ["devices"], session=session
                    )
            await self._log(
                action="SendPushNotifications",
                entity="Notification",
                level="info",
                code=200,
                message=f"Push notifications sent successfully to {len(user_ids)} users",
            )
        except Exception as ex:
            await self._log(
                action="SendPushNotifications",
                entity="Notification",
                level="error",
                code=500,
                message="An error occurred while sending push notifications",
                details={"error": repr(ex)},
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while sending push notifications",
                error=repr(ex),
            )

    async def _send_notification_to_background_worker(
        self,
        notification_type,
        parent_id,
        content,
        url=None,
        faculty_id=None,
        department_id=None,
        year_id=None,
        subject_id=None,
    ):
        try:
            if not os.environ.get("BACKGROUND_WORKER_URL") or not os.environ.get(
                "API_KEY"
            ):
                await self._log(
                    action="SendNotificationToBackgroundWorker",
                    entity="Notification",
                    level="error",
                    code=500,
                    message="Background worker URL or API key is not configured",
                    details={
                        "background_worker_url": (
                            os.environ.get("BACKGROUND_WORKER_URL") is not None
                        ),
                        "api_key": (os.environ.get("API_KEY") is not None),
                    },
                )
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=False,
                    message="Background worker URL or API key is not configured",
                )
            response = await self._request_with_retries(
                method="POST",
                url=f"{os.environ.get('BACKGROUND_WORKER_URL', 'http://localhost:3000')}/notifications",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": os.environ.get("API_KEY", ""),
                },
                json_data={
                    "notification_type": notification_type,
                    "parent_id": parent_id,
                    "content": content,
                    "url": url,
                    "faculty_id": faculty_id,
                    "department_id": department_id,
                    "year_id": year_id,
                    "subject_id": subject_id,
                },
            )
            if not response.success:
                await self._log(
                    action="SendNotificationToBackgroundWorker",
                    entity="Notification",
                    level="error",
                    code=response.code or 500,
                    message=f"Failed to send notification to background worker: {response.message}",
                    details={"error": response.error},
                )
        except Exception as ex:
            await self._log(
                action="SendNotificationToBackgroundWorker",
                entity="Notification",
                level="error",
                code=500,
                message="An error occurred while sending notification to background worker",
                details={"error": repr(ex)},
            )

    async def send_notification(
        self,
        notification_type,
        parent_id,
        content,
        url=None,
        faculty_id=None,
        department_id=None,
        year_id=None,
        subject_id=None,
    ):
        request = request_context.get(None)
        if not request:
            await self._log(
                action="SendNotification",
                entity="Notification",
                level="error",
                code=500,
                message="Request context is not available",
                details={},
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="Request context is not available",
            )
        hostname = request.url.hostname
        if not hostname:
            await self._log(
                action="SendNotification",
                entity="Notification",
                level="error",
                code=500,
                message="Hostname is not available in the request context",
                details={},
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="Hostname is not available in the request context",
            )
        if Validator.validate_hostname_is_background_worker(hostname):
            asyncio.create_task(
                self._send_notification(
                    notification_type,
                    parent_id,
                    content,
                    url,
                    faculty_id,
                    department_id,
                    year_id,
                    subject_id,
                )
            )
        else:
            asyncio.create_task(
                self._send_notification_to_background_worker(
                    notification_type=notification_type,
                    parent_id=parent_id,
                    content=content,
                    url=url,
                    faculty_id=faculty_id,
                    department_id=department_id,
                    year_id=year_id,
                    subject_id=subject_id,
                )
            )
        return BaseResponseDto(
            success=True,
            code=200,
            data=True,
            message="Notification sent successfully",
        )

    # File Functions
    async def _stream_aiohttp_response(
        self,
        session: aiohttp.ClientSession,
        response: aiohttp.ClientResponse,
    ) -> AsyncIterable[bytes]:
        try:
            async for chunk in response.content.iter_chunked(1024 * 1024):
                if chunk:
                    yield chunk
        finally:
            response.release()
            await session.close()
            
    async def _request_with_retries(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        data: aiohttp.FormData | None = None,
        json_data: dict | None = None,
        max_retries=6,
        stream_response: bool = False,
    ) -> BaseResponseDto[RequestResponseModel]:
        RATE_LIMIT_REASONS = [
            "userRateLimitExceeded",
            "rateLimitExceeded",
            "quotaExceeded",
        ]
        errors = []

        for attempt in range(max_retries):
            session = aiohttp.ClientSession()
            try:
                response = await session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                )

                json_response = {}
                if not stream_response or response.status in {403, 429}:
                    try:
                        json_response = await response.json()
                    except Exception:
                        pass

                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get("Retry-After", 1))
                    response.release()
                    await session.close()
                    await asyncio.sleep(retry_after)
                    continue

                if response.status == 403:  # Forbidden
                    reason = (
                        json_response.get("error", {})
                        .get("errors", [{}])[0]
                        .get("reason", "")
                    )
                    if any(x in reason for x in RATE_LIMIT_REASONS):
                        retry_after = int(response.headers.get("Retry-After", 1))
                        response.release()
                        await session.close()
                        await asyncio.sleep(retry_after)
                        continue

                if str(response.status)[0] != "2":  # Not a 2xx response
                    try:
                        if not json_response:
                            json_response = await response.json()
                    except Exception:
                        pass
                    response.release()
                    await session.close()
                    return BaseResponseDto(
                        success=False,
                        code=response.status,
                        data=None,
                        message=f"Request failed with status {response.status}",
                        error=f"Request for {url} with method {method} failed with status {response.status} and response: {json.dumps(json_response)}",
                    )

                if stream_response:
                    return BaseResponseDto(
                        success=True,
                        code=response.status,
                        data=RequestResponseModel(
                            json_response=json_response,
                            content=self._stream_aiohttp_response(session, response),
                        ),
                        message="Request successful",
                    )

                response_model = RequestResponseModel(json_response=json_response)
                response.release()
                await session.close()
                return BaseResponseDto(
                    success=True,
                    code=response.status,
                    data=response_model,
                    message="Request successful",
                )
            except Exception as ex:
                errors.append(repr(ex))
                await session.close()
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                break

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
            web_content_link=metadata.get(
                "webContentLink",
                f"https://drive.google.com/uc?export=download&id={metadata.get('id', '')}",
            ),
            web_view_link=metadata.get(
                "webViewLink",
                f"https://drive.google.com/uc?export=view&id={metadata.get('id', '')}",
            ),
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
        if not file_size:
            return False
        for unit in units:
            if file_size.endswith(unit):
                try:
                    size_value = float(file_size[: -len(unit)].strip())
                    size_in_bytes = size_value * (1024 ** units.index(unit))
                    return size_in_bytes <= max_size_in_bytes
                except ValueError:
                    continue
        return False

    async def verify_file_exists_on_drive(self, url):
        try:
            file_id = self.get_file_id_from_url(url)
            if not file_id:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid URL format: {url}",
                )
            file_response = await self.fetch_from_drive(file_id)
            if not file_response.success:
                return BaseResponseDto(
                    success=False,
                    code=file_response.code,
                    data=None,
                    message=file_response.message,
                    error=file_response.error,
                )
            file_data = file_response.data
            if not file_data:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message=f"Failed to fetch file data from Google Drive, please try again later.",
                    error="No data returned from Google Drive",
                )
            file = file_data.data
            if not file:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message=f"File not found on Google Drive for URL: {url}",
                    error="No file data returned from Google Drive",
                )
            if len(file_data.children) > 0:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"The provided URL points to a folder, not a file: {url}",
                    error="URL points to a folder instead of a file",
                )
            return BaseResponseDto(
                success=True,
                code=200,
                data=file,
                message="File found on Google Drive",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while verifying file existence on Google Drive",
                error=repr(ex),
            )

    async def remove_files_from_drive(self, files):
        try:
            for file in files:
                user_id = file.get("user_id")
                file_id = file.get("file_id")
                if not user_id or not file_id:
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=False,
                        message="Couldn't remove files from Google Drive",
                        error="Missing user_id or file_id in the provided files list",
                    )
                user_response = await self.user_repository.find_one(User.id == user_id)
                if not user_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=user_response.code,
                        data=False,
                        message=user_response.message,
                        error=user_response.message,
                    )
                user = user_response.data
                if not user:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=False,
                        message=f"User with ID {user_id} not found",
                        error=f"User with ID {user_id} not found in the database",
                    )
                access_token_response = await self.get_google_access_token(
                    user.google_refresh_token
                )
                if not access_token_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=access_token_response.code,
                        data=False,
                        message=access_token_response.message,
                        error=access_token_response.error,
                    )
                access_token = access_token_response.data
                if not access_token:
                    return BaseResponseDto(
                        success=False,
                        code=500,
                        data=False,
                        message="Failed to retrieve Google access token",
                        error="Access token is None after decryption and retrieval",
                    )
                delete_file_response = await self.delete_file_from_drive(
                    access_token, file_id
                )
                if not delete_file_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=delete_file_response.code,
                        data=False,
                        message=delete_file_response.message,
                        error=delete_file_response.error,
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                data=True,
                message="Files removed from Google Drive successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=False,
                message="An error occurred while removing files from Google Drive",
                error=repr(ex),
            )

    async def fetch_from_drive(
        self,
        file_id,
        visited=None,
        max_retries=6,
    ):
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
            metadata = response_data.json_response
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
                    json_response = response_data.json_response
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
                error=repr(ex),
            )

    async def get_google_access_token(
        self, user_refresh_token, max_retries=6
    ):
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
                data=FormData(data),
                max_retries=max_retries,
            )
            if not response.success:
                print(response)
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
            json_response = response_data.json_response
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
                message="An error occurred while Connecting with Google API, please try again later",
                error=repr(ex),
            )

    async def download_file_from_drive(
        self, file_id, max_retries=6
    ):
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
                stream_response=True,
            )
            if not response.success:
                return BaseResponseDto(
                    success=False,
                    code=response.code,
                    data=None,
                    message=response.message,
                    error=response.error,
                )
            if not response.data or response.data.content is None:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"No download stream returned for file ID: {file_id}",
                )

            downloaded_file = DownloadedFileModel(
                name=file_metadata.name,
                size=file_metadata.size,
                content=response.data.content,
            )
            return BaseResponseDto(
                success=True,
                code=200,
                data=downloaded_file,
                message="File download stream created successfully",
            )
        except Exception as ex:
            print(f"Error creating download stream from Google Drive: {repr(ex)}")
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating the download stream from Google Drive",
                error=repr(ex),
            )

    async def set_file_public_on_drive(
        self,
        access_token,
        file_id,
        max_retries=6,
    ):
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
            json_response = response_data.json_response
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
                error=repr(ex),
            )

    async def upload_file_to_drive(
        self,
        access_token,
        name,
        content,
        size=None,
        max_retries=6,
    ):
        try:
            if not access_token or not name or content is None:
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
                max_retries=1,
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
            json_response = response_data.json_response
            if not json_response or "id" not in json_response:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Bad Response from Google Drive API, please try again later",
                    error=f"Invalid JSON response while uploading file: {name}, response: {json.dumps(json_response)}",
                )
            json_response["size"] = size if size else "0 B"
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
                error=repr(ex),
            )

    async def delete_file_from_drive(
        self,
        access_token,
        file_id,
        max_retries=6,
    ):
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
                error=repr(ex),
            )

    async def copy_file_on_drive(
        self,
        access_token,
        file_id,
        new_name=None,
        max_retries=6,
    ):
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
                    error=f"Empty data while creating download stream for file ID: {file_id}",
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
                    error=f"Empty response data while uploading copied file for original file ID: {file_id}",
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
                error=repr(ex),
            )

    # Attachment Functions
    async def create_attachment(
        self,
        is_file,
        url,
        author_id,
        source_name,
        source_id,
        link_title=None,
        fetched=None,
    ):
        custom_sources = {
            "user_id": lambda: Attachment.user.has(User.id == source_id),
            "event_logo_id": lambda: Attachment.event_logo.has(Event.id == source_id),
            "event_organizer_logo_id": lambda: Attachment.event_organizer_logo.has(
                EventOrganizer.id == source_id
            ),
        }
        try:
            if not url:
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="URL is required",
                    error="No URL provided for creating attachment",
                )
            if source_name not in custom_sources and not hasattr(
                Attachment, source_name
            ):
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message=f"Invalid source name: {source_name}",
                    error=f"Attachment entity does not have a field named '{source_name}'",
                )
            author_response = await self.user_repository.find_one(User.id == author_id)
            if not author_response.success:
                return BaseResponseDto(
                    success=False,
                    code=author_response.code,
                    data=None,
                    message=author_response.message,
                )
            author = author_response.data
            if not author:
                return BaseResponseDto(
                    success=False,
                    code=404,
                    data=None,
                    message="Author not found",
                )
            if source_name in custom_sources:
                existing_attachment_predicate = custom_sources[source_name]()
            else:
                existing_attachment_predicate = (
                    getattr(Attachment, source_name) == source_id
                )
            existing_attachment_response = await self.attachment_repository.find_one(
                and_(
                    Attachment.author_id == author_id,
                    existing_attachment_predicate,
                    Attachment.url == url,
                )
            )
            if not existing_attachment_response.success:
                return BaseResponseDto(
                    success=False,
                    code=existing_attachment_response.code,
                    data=None,
                    message=existing_attachment_response.message,
                )
            existing_attachment = existing_attachment_response.data
            if existing_attachment:
                return BaseResponseDto(
                    success=True,
                    code=200,
                    data=existing_attachment,
                    message="Attachment already exists",
                )
            details = {}
            if is_file:
                if not Validator.is_valid_drive_url(url):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid Google Drive URL",
                        error=f"Provided URL is not a valid Google Drive URL: {url}",
                    )
                file_exists_response = await self.verify_file_exists_on_drive(url)
                if not file_exists_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=file_exists_response.code,
                        data=None,
                        message=file_exists_response.message,
                        error=file_exists_response.error,
                    )
                file_exists = file_exists_response.data
                if not file_exists:
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="File not found on Google Drive",
                        error=f"File at URL {url} does not exist on Google Drive",
                    )
                details["file_data"] = file_exists.model_dump(mode="json")
                if fetched is not None:
                    details["fetched"] = fetched
            else:
                if not Validator.is_valid_external_url(url):
                    return BaseResponseDto(
                        success=False,
                        code=400,
                        data=None,
                        message="Invalid URL",
                        error=f"Invalid URL: {url}",
                    )
                link_title = link_title or ""
                details["link_title"] = link_title
            attachment = Attachment(
                is_file=is_file,
                url=url,
                details=details,
                author_google_refresh_token=author.google_refresh_token,
                author_id=author_id,
            )
            if source_name not in custom_sources:
                setattr(attachment, source_name, source_id)
            create_attachment_response = await self.attachment_repository.create(
                attachment
            )
            if not create_attachment_response.success:
                return BaseResponseDto(
                    success=False,
                    code=create_attachment_response.code,
                    data=None,
                    message=create_attachment_response.message,
                )
            created_attachment = create_attachment_response.data
            if not created_attachment:
                return BaseResponseDto(
                    success=False,
                    code=500,
                    data=None,
                    message="Failed to create attachment",
                    error="Attachment creation returned no data",
                )
            return BaseResponseDto(
                success=True,
                code=201,
                data=created_attachment,
                message="Attachment created successfully",
            )
        except Exception as ex:
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while creating the attachment, please try again later",
                error=repr(ex),
            )

    async def delete_attachment(
        self,
        attachment_id=None,
        attachment=None,
    ):
        try:
            if not attachment_id and not attachment:
                await self._log(
                    action="DeleteAttachment",
                    entity="Attachment",
                    level="warning",
                    code=400,
                    message="Attachment ID or Attachment object is required for deletion",
                    details={
                        "attachment_id": attachment_id,
                    },
                )
                return BaseResponseDto(
                    success=False,
                    code=400,
                    data=None,
                    message="Attachment ID or Attachment object is required",
                    error="No attachment ID or object provided for deletion",
                )
            if not attachment:
                attachment_response = await self.attachment_repository.find_one(
                    Attachment.id == attachment_id
                )
                if not attachment_response.success:
                    return BaseResponseDto(
                        success=False,
                        code=attachment_response.code,
                        data=None,
                        message=attachment_response.message,
                        error=attachment_response.error,
                    )
                attachment = attachment_response.data
                if not attachment:
                    await self._log(
                        action="DeleteAttachment",
                        entity="Attachment",
                        level="warning",
                        code=404,
                        message="Attachment not found for deletion",
                        details={
                            "attachment_id": attachment_id,
                        },
                    )
                    return BaseResponseDto(
                        success=False,
                        code=404,
                        data=None,
                        message="Attachment not found",
                        error=f"Attachment with ID {attachment_id} does not exist",
                    )
            to_be_removed = (
                attachment.url
                if attachment.is_file and not attachment.details.get("fetched", False)
                else None
            )
            delete_response = await self.attachment_repository.delete(attachment)
            if not delete_response.success:
                return BaseResponseDto(
                    success=False,
                    code=delete_response.code,
                    data=None,
                    message=delete_response.message,
                )
            if to_be_removed:
                access_token_response = await self.get_google_access_token(
                    attachment.author_google_refresh_token or ""
                )
                if not access_token_response.success or not access_token_response.data:
                    return BaseResponseDto(
                        success=True,
                        code=200,
                    )
                access_token = access_token_response.data
                file_id = self.get_file_id_from_url(to_be_removed)
                if not file_id:
                    return BaseResponseDto(
                        success=True,
                        code=200,
                    )
                delete_file_response = await self.delete_file_from_drive(
                    access_token, file_id
                )
                if not delete_file_response.success:
                    await self._log(
                        action="DeleteAttachment",
                        entity="Attachment",
                        level="warning",
                        code=delete_file_response.code or 500,
                        message="Failed to delete file from Google Drive after attachment deletion",
                        details={
                            "attachment_id": attachment.id,
                            "file_id": file_id,
                            "error": delete_file_response.error,
                        },
                    )
                    return BaseResponseDto(
                        success=True,
                        code=200,
                    )
            return BaseResponseDto(
                success=True,
                code=200,
                message="Attachment deleted successfully",
            )
        except Exception as ex:
            await self._log(
                action="DeleteAttachment",
                entity="Attachment",
                level="error",
                code=500,
                message="An error occurred while deleting the attachment",
                details={
                    "attachment_id": attachment_id,
                    "error": repr(ex),
                },
            )
            return BaseResponseDto(
                success=False,
                code=500,
                data=None,
                message="An error occurred while deleting the attachment, please try again later",
                error=repr(ex),
            )
