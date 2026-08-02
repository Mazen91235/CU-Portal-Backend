import datetime
import random
import aiosmtplib
import aiofiles
from email.message import EmailMessage
from typing import Dict, Any
from fastapi.params import Depends
import os
from time import sleep
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import Select, Delete
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse
import asyncio
from models import (
    User,
    Token,
    Log,
    Role,
    ExactRole,
    Notification,
    Task,
    Subject,
    Announcement,
    Material,
    Grade,
)
from extensions import fernet, async_session, cairo_tz
import jwt

templates = {
    "reset_password": {
        "subject": "CU Portal - Reset Password",
        "content": """
            <html>
            <body>
            <h1>Hello [name]</h1>
            <p>To Reset your password, please click the link below:</p>
            <a href="[link]">[link]</a>
            <p>This link will expire in 1 hour.</p>
            </body>
            </html>
            """,
    },
    "verify_email": {
        "subject": "CU Portal - Verify Email",
        "content": """
            <html>
            <body>
            <h2>Hello [name]</h2>
            <p>That's the Verification Code to Verify Your Email:</p>
            <h1>[code]</h1>
            <p>This code will expire in 1 hour.</p>
            </body>
            </html>
            """,
    },
    "new_message": {
        "subject": "CU Portal - New Message Received",
        "content": """
            <html>
            <body>
            <h2>Hello [name]</h2>
            <p>A new message was received on CU - Portal.</p>
            </body>
            </html>
            """,
    },
}


async def send_email(request: Request, to_address, template_name, data):
    if template_name not in templates:
        await log(
            request,
            "Send",
            "Email",
            404,
            "error",
            "Template Not Found",
            {"template_name": template_name, "data": data, "to_address": to_address},
        )
        return JSONResponse({"status": "error", "message": "Template not found"}, 404)
    try:
        # Render template
        template = templates[template_name].get("content", "")
        for key, value in data.items():
            template = template.replace(f"[{key}]", str(value))
        email_body = template

        # Create email message
        message = EmailMessage()
        message["From"] = os.environ.get("MAIL_APP_EMAIL")
        message["To"] = to_address
        message["Subject"] = templates[template_name].get("subject", "CU - Portal")
        message.set_content(email_body, subtype="html")

        # Async SMTP connection
        async with aiosmtplib.SMTP(
            hostname=os.environ.get("MAIL_APP_PROVIDER", "mail.cu-portal.com"),
            port=os.environ.get("MAIL_APP_PORT", 587),
        ) as smtp:
            await smtp.login(
                os.environ.get("MAIL_APP_USER"), os.environ.get("MAIL_APP_PASSWORD")
            )
            await smtp.send_message(message)

        await log(
            request,
            "Send",
            "Email",
            200,
            "info",
            "Email Sent Successfully",
            {
                "template_name": template_name,
                "data": data,
                "to_address": to_address,
                "msg": template,
            },
        )
        return JSONResponse(
            {"status": "success", "message": "Email sent successfully"}, 200
        )
    except Exception as e:
        await log(
            request,
            "Send",
            "Email",
            500,
            "error",
            "An Error Occurred While Trying to Send an Email",
            {
                "template_name": template_name,
                "data": data,
                "to_address": to_address,
                "error": str(e),
            },
        )
        return JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while trying to send an email",
            },
            500,
        )


alphabets = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_random_string(length=10):
    time = datetime.datetime.now(cairo_tz).strftime(
        "%Y%m%d%H%M%S%f"
    )  # Unique time-based string
    random_str = "".join([random.choice(alphabets) for _ in range(length)]) + str(time)
    random_str = list(random_str)
    random.shuffle(random_str)
    return "".join(random_str)


def generate_random_number(length=6):
    numbers = "0123456789"
    return "".join([random.choice(numbers) for _ in range(length)])


async def generate_unique_token(length=10, token_table=True, request: Request = None):
    try:
        async with async_session() as session:
            while True:
                token = generate_random_string(length)
                if (
                    token_table
                    and not (
                        await session.execute(Select(Token).where(Token.token == token))
                    ).scalar_one_or_none()
                ):
                    return token
                elif (
                    not token_table
                    and not (
                        await session.execute(
                            Select(User).where(User.refresh_token == token)
                        )
                    ).scalar_one_or_none()
                ):
                    return token
    except Exception as e:
        await log(
            request,
            "Generate",
            "Token",
            500,
            "error",
            "An Error Occurred While Trying to Generate a Unique Token",
            {"error": str(e)},
        )
        return None


async def updated_roles(request: Request = None):
    # required_roles = ['access_admins','access_site_admins', 'delete_site_admins','access_representatives',
    #                    'delete_representatives',
    #                   'access_admin','access_years',
    #                   'access_faculties','access_departments','access_courses','access_users','access_roles']
    required_roles = [
        "View Admin Panel",
        "View Admin Links",
        "Is Admin",
        "Add Faculties",
        "Edit Faculties",
        "Delete Faculties",
        "View Faculties",
        "Access All Faculties",
        "Add Departments",
        "Edit Departments",
        "Delete Departments",
        "View Departments",
        "Access All Departments",
        "Add Years",
        "Edit Years",
        "Delete Years",
        "View Years",
        "Access All Years",
        "Add Users",
        "View Users",
        "Manage Users",
        "Assign Roles",
        "Add Roles",
        "Edit Roles",
        "Delete Roles",
        "View Roles",
        "Add Courses",
        "Edit Courses",
        "Delete Courses",
        "View Courses",
        "Access All Courses",
        "Add Course Maps",
        "Edit Course Maps",
        "Delete Course Maps",
        "View Course Maps",
        "Add Materials",
        "Edit Materials",
        "Delete Materials",
        "View Materials",
        "Manage All Materials",
        "Add Grades",
        "Edit Grades",
        "Delete Grades",
        "View Grades",
        "Manage All Grades",
        "Add Tasks",
        "Edit Tasks",
        "Delete Tasks",
        "View Tasks",
        "Manage All Tasks",
        "Add Exams",
        "Edit Exams",
        "Delete Exams",
        "View Exams",
        "Manage All Exams",
        "Add Announcements",
        "Edit Announcements",
        "Delete Announcements",
        "View Announcements",
        "Manage All Announcements",
        "View Logs",
        "View Messages",
    ]
    async with async_session() as session:
        await session.begin()
        try:
            existing_roles = (
                (await session.execute(Select(ExactRole.name))).scalars().all()
            )
            unneeded_roles = [
                role for role in existing_roles if role not in required_roles
            ]
            for role in unneeded_roles:
                await session.execute(Delete(ExactRole).where(ExactRole.name == role))
            needed_roles = [
                role for role in required_roles if role not in existing_roles
            ]
            for role in needed_roles:
                new_role = ExactRole(name=role)
                session.add(new_role)
            roles = {
                "admin": [],
                "site admin": [
                    "View Admin Panel",
                    "Is Admin",
                    "View Logs",
                    "View Messages",
                ],
                "representative": [
                    "View Admin Panel",
                    "Is Admin",
                    "View Logs",
                    "View Messages",
                    "View Faculties",
                    "Add Faculties",
                    "Edit Faculties",
                    "Delete Faculties",
                    "Access All Faculties",
                    "View Departments",
                    "Add Departments",
                    "Edit Departments",
                    "Delete Departments",
                    "Access All Departments",
                    "View Years",
                    "Add Years",
                    "Edit Years",
                    "Delete Years",
                    "Access All Years",
                ],
            }
            if not (
                await session.execute(Select(Role).where(Role.name == "user"))
            ).scalar_one_or_none():
                session.add(Role(name="user", level=4))
            for role, non_authorized in roles.items():
                current_role = (
                    await session.execute(
                        Select(Role)
                        .where(Role.name == role)
                        .options(selectinload(Role.exact_roles))
                    )
                ).scalar_one_or_none()
                if not current_role:
                    level = 1 if role == "admin" else 2
                    current_role = Role(name=role, level=level, exact_roles=[])
                    session.add(current_role)
                for unneeded_role in non_authorized:
                    unneeded_role_role = (
                        await session.execute(
                            Select(ExactRole).where(ExactRole.name == unneeded_role)
                        )
                    ).scalar_one_or_none()
                    if unneeded_role_role in current_role.exact_roles:
                        current_role.exact_roles.remove(unneeded_role_role)
                existing_roles = (
                    (await session.execute(Select(ExactRole))).scalars().all()
                )
                needed_roles = [
                    exact_role
                    for exact_role in existing_roles
                    if exact_role.name not in non_authorized
                    and exact_role not in current_role.exact_roles
                ]
                current_role.exact_roles.extend(needed_roles)
                await session.commit()
        except Exception as e:
            await log(
                request,
                "Update",
                "Roles",
                500,
                "error",
                "An Error Occurred While Trying to Update Roles",
                {"error": str(e)},
            )
            await session.rollback()


async def file_log(
    ip,
    action,
    entity,
    code,
    level,
    message,
    route=None,
    details=None,
    user_id=None,
    error=None,
):
    """
    Logs the message to a file.
    :param ip: The IP address of the user.
    :param action: The action being performed (e.g., 'Add', 'Edit', 'Delete', 'Get', 'Get One').
    :param entity: The entity being acted upon (e.g., 'User', 'Course').
    :param code: The response code (e.g., 200, 404).
    :param level: The log level (e.g., 'info', 'error').
    :param message: The log message.
    :param route: The route or endpoint being accessed.
    :param details: Additional details about the log.
    :param user_id: The ID of the user associated with the log.
    :param error: Optional error object to log.
    """
    try:
        details_txt = ""
        for key, value in details.items():
            if isinstance(value, dict):
                details_txt += (
                    f"{key}: {', '.join([f'{k}={v}' for k, v in value.items()])}\n"
                )
            else:
                details_txt += f"{key}: {value}\n"
        async with aiofiles.open("logs.txt", "a") as f:
            await f.write(
                f"{datetime.datetime.now(cairo_tz)} - {ip} - {action} - {entity} - {code} - {level.lower()} -"
                f" {route} -"
                f" {message} -"
                f" {details_txt} - User "
                f"ID:"
                f" {user_id}\n"
            )
            if error:
                await f.write(f"A Log Error Occurred: {error}\n")
    except Exception as e:
        return False
    else:
        return True
        # print(f"Failed to write to log file: {e}")


async def log(
    request: Request,
    action,
    entity,
    code,
    level,
    message,
    details=None,
    user_id=None,
    trials=0,
):
    asyncio.create_task(
        log_async(request, action, entity, code, level, message, details, user_id)
    )
    return True


async def log_async(
    request: Request,
    action,
    entity,
    code,
    level,
    message,
    details=None,
    user_id=None,
    trials=0,
):
    ip = request.client.host if request else None
    try:
        async with async_session() as session:
            await session.begin()
            logged = Log(
                ip=ip,
                response_code=code,
                level=level.lower(),
                action=action.strip().title(),
                entity=entity.strip().title(),
                message=message,
                details=details,
                route=request.url.path if request else None,
                user=(
                    (
                        await session.execute(Select(User).where(User.id == user_id))
                    ).scalar_one_or_none()
                    if user_id
                    else None
                ),
            )
            session.add(logged)
            await session.commit()
    except Exception as e:
        await session.rollback()
        sleep(1)
        return (
            await log(
                request,
                action,
                entity,
                code,
                level,
                message,
                details,
                user_id,
                trials + 1,
            )
            if trials < 3
            else await file_log(
                ip,
                action,
                entity,
                code,
                level,
                message,
                request.url.path if request else None,
                details,
                user_id,
                e,
            )
        )  # Retry up to 3 times
    else:
        return True


async def create_notification(request: Request, type, parent_id, content, url=None):
    """
    Creates a notification and associates it with users based on the parent entity.
    :param request: The request object.
    :param type: The type of notification (e.g., 'task', 'exam', 'announcement').
    :param parent_id: The ID of the parent entity (e.g., task ID, exam ID).
    :param content: The content of the notification.
    :param url: The URL associated with the notification.
    :return: None
    """
    try:
        async with async_session() as session:
            await session.begin()
            notification = Notification(
                type=type, parent_id=parent_id, content=content, url=url, users=[]
            )
            session.add(notification)
            if type in ["task", "exam"]:
                parent = (
                    await session.execute(
                        Select(Task)
                        .where(Task.id == parent_id)
                        .options(selectinload(Task.subject).selectinload(Subject.users))
                    )
                ).scalar_one_or_none()
                if not parent:
                    await log(
                        request,
                        "Create",
                        "Notification",
                        404,
                        "error",
                        f"Parent {type} Not Found",
                        {
                            "type": type,
                            "parent_id": parent_id,
                            "content": content,
                            "url": url,
                        },
                    )
                    await session.rollback()
                    return
                parent_type = "exam" if parent.type == "exam" else "task"
                if type != parent_type:
                    await log(
                        request,
                        "Create",
                        "Notification",
                        400,
                        "error",
                        f"Parent Task/Exam Type Mismatch",
                        {
                            "type": type,
                            "parent_id": parent_id,
                            "content": content,
                            "url": url,
                        },
                    )
                    await session.rollback()
                    return
                notification.users.extend(
                    [u for u in parent.subject.users if u.id != parent.author_id]
                )
            elif type == "announcement":
                parent = (
                    await session.execute(
                        Select(Announcement)
                        .where(Announcement.id == parent_id)
                        .options(
                            selectinload(Announcement.subject).selectinload(
                                Subject.users
                            )
                        )
                    )
                ).scalar_one_or_none()
                if not parent:
                    await log(
                        request,
                        "Create",
                        "Notification",
                        404,
                        "error",
                        f"Parent Announcement Not Found",
                        {
                            "type": type,
                            "parent_id": parent_id,
                            "content": content,
                            "url": url,
                        },
                    )
                    await session.rollback()
                    return
                notification.users.extend(
                    [u for u in parent.subject.users if u.id != parent.author_id]
                )
            elif type == "material":
                parent = (
                    await session.execute(
                        Select(Material)
                        .where(Material.id == parent_id)
                        .options(
                            selectinload(Material.subject).selectinload(Subject.users)
                        )
                    )
                ).scalar_one_or_none()
                if not parent:
                    await log(
                        request,
                        "Create",
                        "Notification",
                        404,
                        "error",
                        f"Parent Material Not Found",
                        {
                            "type": type,
                            "parent_id": parent_id,
                            "content": content,
                            "url": url,
                        },
                    )
                    await session.rollback()
                    return
                notification.users.extend(
                    [u for u in parent.subject.users if u.id != parent.author_id]
                )
            elif type == "grade":
                parent = (
                    await session.execute(
                        Select(Grade)
                        .where(Grade.id == parent_id)
                        .options(
                            selectinload(Grade.subject).selectinload(Subject.users)
                        )
                    )
                ).scalar_one_or_none()
                if not parent:
                    await log(
                        request,
                        "Create",
                        "Notification",
                        404,
                        "error",
                        f"Parent Grade Not Found",
                        {
                            "type": type,
                            "parent_id": parent_id,
                            "content": content,
                            "url": url,
                        },
                    )
                    await session.rollback()
                    return
                notification.users.extend(
                    [u for u in parent.subject.users if u.id != parent.author_id]
                )
            await session.commit()
            await log(
                request,
                "Create",
                "Notification",
                201,
                "info",
                "Notification Created Successfully",
                {
                    "type": type,
                    "parent_id": parent_id,
                    "content": content,
                    "url": url,
                    "notified_users": [user.id for user in notification.users],
                },
            )
    except Exception as e:
        await log(
            request,
            "Create",
            "Notification",
            500,
            "error",
            "An Error Occurred While Trying to Create a Notification",
            {
                "type": type,
                "parent_id": parent_id,
                "content": content,
                "url": url,
                "error": str(e),
            },
        )
        await session.rollback()


def encrypt_data(data):
    """
    Encrypts the given data using the Fernet key.
    :param data: The data to encrypt.
    :return: The encrypted data.
    """
    return fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data):
    """
    Decrypts the given encrypted data using the Fernet key.
    :param encrypted_data: The encrypted data to decrypt.
    :return: The decrypted data.
    """
    return fernet.decrypt(encrypted_data.encode()).decode() if encrypted_data else None


def get_user_if_exists(request: Request):
    """
    Retrieves the user from the request cookies if it exists.
    :return: The user object if found, otherwise None.
    """
    try:
        token = request.cookies.get("access_token")
        refresh_token = request.cookies.get("refresh_token")
        if not token and not refresh_token:
            return None
        data = (
            jwt.decode(
                token, os.environ.get("ACCESS_TOKEN_SECRET_KEY"), algorithms=["HS256"]
            )
            if token
            else (
                jwt.decode(
                    refresh_token,
                    os.environ.get("REFRESH_TOKEN_SECRET_KEY"),
                    algorithms=["HS256"],
                )
                if refresh_token
                else None
            )
        )
        if not data:
            return None
        user = User.query.get(data.get("id"))
        if not user:
            return None
    except Exception as e:
        return None
    else:
        return user


security = HTTPBasic()


def verify_notification_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
):
    correct_username = credentials.username == "admin"
    correct_password = credentials.password == os.environ.get("DRIVE_AUTH_PASSWORD")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": 'Basic realm="Login Required"'},
        )
    return credentials.username


def finalize_request(response):
    """
    Finalizes the request by handling the response and returning it.
    :param response: The response to finalize.
    :return: The finalized response.
    """
    return response
