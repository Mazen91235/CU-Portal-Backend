import asyncio
import aiohttp
import json
import math
import random
from user_agents import parse
import jwt
from sqlalchemy import (
    Select,
    Delete,
    exists,
    func,
    not_,
    not_,
    or_,
    case,
    literal,
    cast,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload
import re
from models import *
from extensions import (
    load_dotenv,
    oauth,
    google,
    async_session,
    cairo_tz,
    os,
    convert_to_utc,
    utc_tz,
    access_token_expire_time,
    refresh_token_expire_time,
    google_token_expire_time,
    user_token_expire_time,
    stored_state_expire_time,
)
from settings import (
    send_email,
    generate_unique_token,
    log,
    encrypt_data,
    decrypt_data,
    finalize_request,
    get_user_if_exists,
    updated_roles,
    generate_random_number,
    create_notification,
    verify_notification_credentials,
    generate_random_string,
)
from urllib.parse import urlparse, parse_qs, quote
from fastapi import APIRouter, Request, Depends
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from authlib.integrations.httpx_client import AsyncOAuth2Client
from wrappers import (
    is_logged_in,
    is_not_logged_in,
    rate_limit,
    is_authorized,
    is_ready,
    is_logged_in_web,
    is_not_logged_in_web,
    is_authorized_web,
    is_ready_web,
    has_cookies,
    has_cookies_web,
    has_valid_id_web,
    has_registered_subjects,
    has_registered_subjects_web,
)
import uvicorn

# Load environment variables first
load_dotenv()

# Configure Blueprints
v1 = APIRouter(prefix="/v1", tags=["v1"])
auth = APIRouter(prefix="/auth", tags=["auth"])
user_prefix = APIRouter(prefix="/user", tags=["user"])
admin_prefix = APIRouter(prefix="/admin", tags=["admin"])


# Helper functions
async def generate_refresh_token(user_id, request: Request = None):
    async with async_session() as session:
        await session.begin()
        try:
            user = (
                await session.execute(Select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if not user:
                return None
            refresh_token = user.refresh_token
            if (
                not refresh_token
                or not user.refresh_expire_at
                or user.refresh_expire_at <= datetime.now(utc_tz)
            ):
                refresh_token = await generate_unique_token(40, False)
            user.refresh_token = refresh_token
            user.refresh_expire_at = datetime.now(utc_tz) + timedelta(
                days=refresh_token_expire_time
            )
            await session.commit()
            return refresh_token
        except Exception as e:
            await log(
                request,
                "Generate",
                "Refresh Token",
                500,
                "error",
                "An error occurred while generating refresh token.",
                {"error": str(e)},
                user_id,
            )
            await session.rollback()
            return None


async def remove_file_from_drive(
    drive_url, user_refresh_token, request: Request = None, max_retries=6
):
    current_user = (
        request.state.current_user
        if request and hasattr(request.state, "current_user")
        else None
    )
    # Ensure user is authenticated
    if not current_user and (
        "user/" in request.url.path or "admin/" in request.url.path
    ):
        await log(
            request,
            "Delete",
            "File",
            401,
            "warning",
            "Unauthorized user tried to delete file from Google Drive.",
            {},
        )
        return False
    if not current_user:
        current_user = User(id=None)
    try:
        # Refresh access token
        async with AsyncOAuth2Client(
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        ) as client:
            new_token = await client.refresh_token(
                url="https://oauth2.googleapis.com/token",
                refresh_token=decrypt_data(user_refresh_token),
            )

        access_token = new_token["access_token"]

        url = urlparse(drive_url)
        url_params = parse_qs(url.query)
        file_id = url_params.get("id", [None])[0]

        if not file_id:
            await log(
                request,
                "Delete",
                "File",
                400,
                "warning",
                "Could not extract file_id from the provided Google Drive URL.",
                {"drive_url": drive_url},
                current_user.id,
            )
            # return False
            return True  # Until Thinking of Proper Logic

        # Delete file
        async with AsyncOAuth2Client(
            token={"access_token": access_token, "token_type": "Bearer"}
        ) as client:
            response = await client.delete(
                f"https://www.googleapis.com/drive/v3/files/{file_id}"
            )

            if response.status_code == 403 and any(
                x
                for x in ["userRateLimitExceeded", "rateLimitExceeded", "quotaExceeded"]
                if x
                in response.json().get("error", {}).get("errors", [{}])[0].get("reason")
            ):
                if max_retries < 1:
                    await log(
                        request,
                        "Delete",
                        "File",
                        429,
                        "warning",
                        "Exceeded maximum retries due to rate limiting when deleting file from Google Drive.",
                        {"file_id": file_id},
                        current_user.id,
                    )
                    # return False
                    return True  # Until Thinking of Proper Logic
                await asyncio.sleep(
                    2 ** (6 - max_retries) + random.randint(1, 5)
                )  # Wait before retrying
                return await remove_file_from_drive(
                    drive_url, user_refresh_token, request, max_retries - 1
                )

            if str(response.status_code)[0] == "2":
                await log(
                    request,
                    "Delete",
                    "File",
                    200,
                    "info",
                    "File deleted from Google Drive successfully.",
                    {"file_id": file_id},
                    current_user.id,
                )
                return True
            else:
                body = await response.aread()
                decoded = json.loads(body.decode())
                if (
                    decoded
                    and decoded.get("error")
                    and decoded["error"].get("errors")
                    and decoded["error"]["errors"][0].get("reason") == "notFound"
                ):
                    return True
                await log(
                    request,
                    "Delete",
                    "File",
                    400,
                    "warning",
                    "Failed to delete file from Google Drive.",
                    {
                        "status_code": response.status_code,
                        "response": body.decode(),
                        "file_id": file_id,
                    },
                    current_user.id,
                )
                # return False
                return True  # Until Thinking of Proper Logic

    except Exception as e:
        await log(
            request,
            "Delete",
            "File",
            500,
            "error",
            "An error occurred while deleting file from Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        # return False
        return True  # Until Thinking of Proper Logic


def format_size(bytes_str: str) -> str:
    if not bytes_str:
        return "Unknown"
    size = int(bytes_str)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def verify_file_type(mimetype: str, type: str) -> bool:
    """
    Flexibly verifies if the given mimetype matches the expected file type.
    :param mimetype: File MIME type returned by Drive API
    :param type: Expected file category (image, pdf, doc, sheet, ppt, video, audio, text, archive, etc.)
    :return: True if matches, False otherwise
    """
    type = type.strip().lower()
    mimetype = mimetype.strip().lower()

    if type == "image":
        return mimetype.startswith("image/")

    elif type == "pdf":
        return "pdf" in mimetype

    elif type in ["doc", "docx", "docs"]:
        return (
            "msword" in mimetype
            or "wordprocessingml" in mimetype
            or "vnd.google-apps.document" in mimetype
        )

    elif type in ["sheet", "xlsx", "xls", "excel"]:
        return (
            "spreadsheet" in mimetype
            or "excel" in mimetype
            or "vnd.ms-excel" in mimetype
        )

    elif type in ["ppt", "pptx", "presentation"]:
        return (
            "presentation" in mimetype
            or "powerpoint" in mimetype
            or "vnd.google-apps.presentation" in mimetype
        )

    elif type == "video":
        return mimetype.startswith("video/")

    elif type == "audio":
        return mimetype.startswith("audio/")

    elif type in ["text", "json", "xml", "csv", "html", "css", "js"]:
        # Covers plain text and common structured/text formats
        return (
            mimetype.startswith("text/")
            or "json" in mimetype
            or "xml" in mimetype
            or "csv" in mimetype
            or "javascript" in mimetype
        )

    elif type in ["archive", "compressed"]:
        # Covers zip, rar, 7z, gzip, tar, bzip and generic octet-stream
        return any(
            x in mimetype
            for x in ["zip", "rar", "7z", "gzip", "tar", "bzip", "octet-stream"]
        )

    elif type == "folder":
        return mimetype == "application/vnd.google-apps.folder"

    elif type == "gdrive":
        return mimetype.startswith("application/vnd.google-apps")

    else:
        return False


def get_file_type(mimetype: str) -> str:
    """
    Determines the general file type based on the MIME type.
    :param mimetype: File MIME type returned by Drive API
    :return: General file type (image, pdf, doc, sheet, ppt, video, audio, text, archive, gdrive, unknown)
    """
    mimetype = mimetype.strip().lower()
    if verify_file_type(mimetype, "image"):
        return "image"
    elif verify_file_type(mimetype, "pdf"):
        return "pdf"
    elif verify_file_type(mimetype, "doc"):
        return "doc"
    elif verify_file_type(mimetype, "sheet"):
        return "sheet"
    elif verify_file_type(mimetype, "ppt"):
        return "ppt"
    elif verify_file_type(mimetype, "video"):
        return "video"
    elif verify_file_type(mimetype, "audio"):
        return "audio"
    elif verify_file_type(mimetype, "text"):
        return "text"
    elif verify_file_type(mimetype, "archive"):
        return "archive"
    elif verify_file_type(mimetype, "folder"):
        return "folder"
    elif verify_file_type(mimetype, "gdrive"):
        return "gdrive"
    else:
        return "unknown"


def get_file_data(drive_file: dict) -> dict:
    """
    Extracts and formats relevant file data from the Google Drive file metadata.
    :param drive_file: File metadata dictionary returned by Drive API
    :return: Formatted file data dictionary
    """
    if not drive_file or not isinstance(drive_file, dict):
        return {}

    file_id = drive_file.get("id")
    name = drive_file.get("name")
    mimeType = drive_file.get("mimeType")
    size = (
        format_size(drive_file.get("size"))
        if drive_file.get("size") and is_float(drive_file.get("size"))
        else "Unknown"
    )
    webContentLink = drive_file.get("webContentLink")
    webViewLink = drive_file.get("webViewLink")
    file_type = get_file_type(mimeType) if mimeType else "unknown"
    if not webContentLink:
        webContentLink = f"https://drive.google.com/uc?id={file_id}&export=download"
    if not webViewLink:
        webViewLink = f"https://drive.google.com/uc?export=view&id={file_id}"
    return {
        "id": file_id,
        "name": name,
        "mimeType": mimeType,
        "type": file_type,
        "size": size,
        "webContentLink": webContentLink,
        "webViewLink": webViewLink,
    }


def get_drive_id(drive_url: str) -> str | None:
    try:
        if "id=" in drive_url:
            # Format: ...?id=FILE_ID
            url = urlparse(drive_url)
            url_params = parse_qs(url.query)
            return url_params.get("id", [None])[0]

        if "/folders/" in drive_url:
            # Format: .../folders/FOLDER_ID
            file_id = drive_url.split("/folders/")[1]
            return file_id.split("?")[0] if "?" in file_id else file_id

        if "/file/d/" in drive_url:
            # Format: .../file/d/FILE_ID/...
            file_id = drive_url.split("/file/d/")[1]
            return file_id.split("/")[0] if "/" in file_id else file_id

        return None
    except Exception:
        return None


def get_drive_url(file_id: str) -> str:
    return f"https://drive.google.com/uc?export=view&id={file_id}"


async def fetch_from_drive(
    id: str,
    api_key: str,
    request: Request = None,
    visited: set[str] | None = None,
    max_retries: int = 6,
) -> dict | None:
    current_user = getattr(request.state, "current_user", None) if request else None
    if (
        not current_user
        and request
        and ("user/" in request.url.path or "admin/" in request.url.path)
    ):
        await log(
            request,
            "Fetch From Drive",
            "File",
            401,
            "warning",
            "Unauthorized user tried to fetch files from Google Drive.",
            {},
        )
        return None
    if not current_user:
        current_user = User(id=None)

    if not id:
        await log(
            request,
            "Fetch From Drive",
            "File",
            400,
            "warning",
            "No file ID provided to fetch from Google Drive.",
            {},
            current_user.id,
        )
        return None

    if visited is None:
        visited = set()
    if id in visited:
        # Prevent cycles
        return None
    visited.add(id)

    try:
        node = {}

        # Fetch metadata
        async with aiohttp.ClientSession() as client:
            resp = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{id}",
                params={
                    "fields": "id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails"
                },
            )

            if resp.status_code == 403 and any(
                x
                for x in ["userRateLimitExceeded", "rateLimitExceeded", "quotaExceeded"]
                if x
                in resp.json().get("error", {}).get("errors", [{}])[0].get("reason")
            ):
                if max_retries < 1:
                    await log(
                        request,
                        "Fetch From Drive",
                        "File",
                        429,
                        "warning",
                        "Exceeded maximum retries due to rate limiting when fetching file from Google Drive.",
                        {"file_id": id},
                        current_user.id,
                    )
                    return False
                await asyncio.sleep(
                    2 ** (6 - max_retries) + random.randint(1, 5)
                )  # Wait before retrying
                return await fetch_from_drive(
                    id, api_key, request, visited, max_retries - 1
                )

            if resp.status_code // 100 != 2:
                data = await resp.json()
                await log(
                    request,
                    "Fetch From Drive",
                    "File",
                    400,
                    "warning",
                    "Failed to fetch folder metadata from Google Drive.",
                    {"status_code": resp.status_code, "response": data, "file_id": id},
                    current_user.id,
                )
                return None

            metadata = await resp.json()
            if not metadata:
                return None
            if metadata.get("shortcutDetails") and metadata["shortcutDetails"].get(
                "targetId"
            ):
                # If it's a shortcut, fetch the target file instead
                return await fetch_from_drive(
                    metadata["shortcutDetails"]["targetId"],
                    access_token,
                    request,
                    visited,
                )
            node["data"] = get_file_data(metadata)

            # If not a folder → return just the node
            if not verify_file_type(metadata.get("mimeType", ""), "folder"):
                return node

            node["children"] = []

            # Paginated children fetch
            page_token = None
            while True:
                params = {
                    "q": f"'{id}' in parents",
                    "fields": "nextPageToken, files(id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails)",
                }
                if page_token:
                    params["pageToken"] = page_token

                resp = await client.get(
                    "https://www.googleapis.com/drive/v3/files", params=params
                )

                if resp.status_code == 403 and any(
                    x
                    for x in [
                        "userRateLimitExceeded",
                        "rateLimitExceeded",
                        "quotaExceeded",
                    ]
                    if x
                    in resp.json().get("error", {}).get("errors", [{}])[0].get("reason")
                ):
                    if max_retries < 1:
                        await log(
                            request,
                            "Fetch From Drive",
                            "File",
                            429,
                            "warning",
                            "Exceeded maximum retries due to rate limiting when fetching files from Google Drive.",
                            {"file_id": id},
                            current_user.id,
                        )
                        return None
                    await asyncio.sleep(
                        2 ** (6 - max_retries) + random.randint(1, 5)
                    )  # Wait before retrying
                    return await fetch_from_drive(
                        id, api_key, request, visited, max_retries - 1
                    )

                if resp.status_code // 100 != 2:
                    data = await resp.json()
                    await log(
                        request,
                        "Fetch From Drive",
                        "File",
                        400,
                        "warning",
                        "Failed to fetch files from Google Drive.",
                        {
                            "status_code": resp.status_code,
                            "response": data,
                            "file_id": id,
                        },
                        current_user.id,
                    )
                    return None

                data = await resp.json()
                for f in data.get("files", []):
                    if f.get("shortcutDetails") and f["shortcutDetails"].get(
                        "targetId"
                    ):
                        # If it's a shortcut, fetch the target file instead
                        child = await fetch_from_drive(
                            f["shortcutDetails"]["targetId"],
                            access_token,
                            request,
                            visited,
                        )
                        if child:
                            node["children"].append(child)
                        continue
                    if verify_file_type(f.get("mimeType", ""), "folder"):
                        child = await fetch_from_drive(
                            f["id"], access_token, request, visited
                        )
                        if child:
                            node["children"].append(child)
                    else:
                        node["children"].append(get_file_data(f))

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return node

    except Exception as e:
        await log(
            request,
            "Fetch From Drive",
            "File",
            500,
            "error",
            "An error occurred while fetching files from Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        return None


async def fetch_public_drive(
    id: str,
    api_key: str,
    request: Request = None,
    visited: set[str] | None = None,
    max_retries: int = 6,
) -> dict | None:
    current_user = getattr(request.state, "current_user", None) if request else None
    if (
        not current_user
        and request
        and ("user/" in request.url.path or "admin/" in request.url.path)
    ):
        await log(
            request,
            "Fetch From Drive",
            "File",
            401,
            "warning",
            "Unauthorized user tried to fetch public files from Google Drive.",
            {},
        )
        return None
    if not current_user:
        current_user = User(id=None)

    if not id:
        await log(
            request,
            "Fetch From Drive",
            "File",
            400,
            "warning",
            "No file ID provided to fetch from Google Drive.",
            {},
            current_user.id,
        )
        return None

    if visited is None:
        visited = set()
    if id in visited:
        # Prevent cycles
        return None
    visited.add(id)

    try:
        async with aiohttp.ClientSession() as session:
            # Helper to handle retries and error parsing efficiently
            async def _get_with_retries(url, params, retries):
                for attempt in range(retries):
                    async with session.get(url, params=params) as resp:
                        if resp.status == 403:
                            data = await resp.json()
                            reason = (
                                data.get("error", {})
                                .get("errors", [{}])[0]
                                .get("reason")
                            )
                            if reason and any(
                                x in reason
                                for x in [
                                    "userRateLimitExceeded",
                                    "rateLimitExceeded",
                                    "quotaExceeded",
                                ]
                            ):
                                if attempt == retries - 1:
                                    await log(
                                        request,
                                        "Fetch From Drive",
                                        "File",
                                        429,
                                        "warning",
                                        "Exceeded maximum retries due to rate limiting when fetching files from Google Drive.",
                                        {"file_id": id},
                                        current_user.id,
                                    )
                                    return None, None
                                await asyncio.sleep(2**attempt + random.randint(1, 5))
                                continue
                        if resp.status != 200:
                            data = await resp.json()
                            await log(
                                request,
                                "Fetch From Drive",
                                "File",
                                400,
                                "warning",
                                "Failed to fetch files from Google Drive.",
                                {
                                    "status_code": resp.status,
                                    "response": data,
                                    "file_id": id,
                                },
                                current_user.id,
                            )
                            return None, None
                        return await resp.json(), resp
                return None, None

            # Fetch metadata
            meta_params = {
                "fields": "id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails",
                "key": api_key,
            }
            metadata, _ = await _get_with_retries(
                f"https://www.googleapis.com/drive/v3/files/{id}",
                meta_params,
                max_retries,
            )
            if not metadata:
                return None
            if metadata.get("shortcutDetails") and metadata["shortcutDetails"].get(
                "targetId"
            ):
                # If it's a shortcut, fetch the target file instead
                node = await fetch_public_drive(
                    metadata["shortcutDetails"]["targetId"],
                    api_key,
                    request,
                    visited,
                    max_retries,
                )
                if node:
                    node["data"]["name"] = metadata.get(
                        "name", node["data"].get("name")
                    )
                return node

            node = {"data": get_file_data(metadata)}
            await log(
                request,
                "Fetch From Drive",
                "File",
                200,
                "info",
                "Successfully fetched file metadata from Google Drive.",
                {"file_id": id, "data": node["data"]},
                current_user.id,
            )
            # If not a folder → return just the node
            if not verify_file_type(metadata.get("mimeType", ""), "folder"):
                return node

            # Use a queue for iterative traversal to avoid deep recursion and reduce stack/memory usage
            node["children"] = []
            queue = [(id, node["children"])]
            while queue and len(queue) > 0:
                parent_id, children_list = queue.pop()
                page_token = None
                while True:
                    params = {
                        "q": f"'{parent_id}' in parents",
                        "fields": "nextPageToken, files(id, name, mimeType, size, webContentLink, webViewLink, shortcutDetails)",
                        "key": api_key,
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    data, _ = await _get_with_retries(
                        "https://www.googleapis.com/drive/v3/files", params, max_retries
                    )
                    if not data:
                        break
                    for f in data.get("files", []):
                        if f.get("shortcutDetails") and f["shortcutDetails"].get(
                            "targetId"
                        ):
                            # If it's a shortcut, fetch the target file instead
                            if f["shortcutDetails"]["targetId"] not in visited:
                                child = await fetch_public_drive(
                                    f["shortcutDetails"]["targetId"],
                                    api_key,
                                    request,
                                    visited,
                                    max_retries,
                                )
                                if child:
                                    child["data"]["name"] = f.get(
                                        "name", child["data"].get("name")
                                    )
                                    children_list.append(child)
                            continue
                        if verify_file_type(f.get("mimeType", ""), "folder"):
                            if f["id"] in visited:
                                continue
                            visited.add(f["id"])
                            folder_node = {"data": get_file_data(f), "children": []}
                            children_list.append(folder_node)
                            queue.append((f["id"], folder_node["children"]))
                        else:
                            children_list.append({"data": get_file_data(f)})
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
            return node
    except Exception as e:
        await log(
            request,
            "Fetch From Drive",
            "File",
            500,
            "error",
            "An error occurred while fetching files from Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        return None


def is_allowed_file_type(mimetype: str, excluded_types: list = []) -> bool:
    """
    Checks if the given mimetype is not in the excluded types.
    :param mimetype: File MIME type returned by Drive API
    :param excluded_types: List of excluded file categories (image, pdf, doc, sheet, ppt, video, audio, text, archive, etc.)
    :return: True if not excluded, False otherwise
    """
    allowed_file_types = [
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
    ]
    excluded_types = [type.strip().lower() for type in excluded_types]
    allowed_file_types = [
        type.strip().lower()
        for type in allowed_file_types
        if type.strip().lower() not in excluded_types
    ]

    mimetype = mimetype.strip().lower()
    if mimetype not in allowed_file_types:
        return False
    return True


async def get_file_from_drive(
    drive_url, user_refresh_token, request: Request = None, max_retries=6
) -> dict | None:
    current_user = (
        request.state.current_user
        if request and hasattr(request.state, "current_user")
        else None
    )
    # Ensure user is authenticated
    if not current_user and (
        "user/" in request.url.path or "admin/" in request.url.path
    ):
        await log(
            request,
            "Get",
            "File",
            401,
            "warning",
            "Unauthorized user tried to access file from Google Drive.",
            {},
        )
        return None
    if not current_user:
        current_user = User(id=None)
    try:
        # Refresh access token
        async with AsyncOAuth2Client(
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        ) as client:
            new_token = await client.refresh_token(
                url="https://oauth2.googleapis.com/token",
                refresh_token=decrypt_data(user_refresh_token),
            )

        access_token = new_token["access_token"]

        url = urlparse(drive_url)
        url_params = parse_qs(url.query)
        file_id = url_params.get("id", [None])[0]

        if not file_id:
            await log(
                request,
                "Get",
                "File",
                400,
                "warning",
                "Could not extract file_id from the provided Google Drive URL.",
                {"drive_url": drive_url},
                current_user.id,
            )
            return None

        # Get file metadata
        async with AsyncOAuth2Client(
            token={"access_token": access_token, "token_type": "Bearer"}
        ) as client:
            response = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={
                    "fields": "id, name, mimeType, size, webContentLink, webViewLink"
                },
            )

            if response.status_code == 403 and any(
                x
                for x in ["userRateLimitExceeded", "rateLimitExceeded", "quotaExceeded"]
                if x
                in response.json().get("error", {}).get("errors", [{}])[0].get("reason")
            ):
                if max_retries < 1:
                    await log(
                        request,
                        "Get",
                        "File",
                        429,
                        "warning",
                        "Exceeded maximum retries due to rate limiting when fetching file metadata from Google Drive.",
                        {"file_id": file_id},
                        current_user.id,
                    )
                    return None
                await asyncio.sleep(
                    2 ** (6 - max_retries) + random.randint(1, 5)
                )  # Wait before retrying
                return await get_file_from_drive(
                    drive_url, user_refresh_token, request, max_retries - 1
                )

            if str(response.status_code)[0] == "2":
                body = await response.aread()
                decoded = json.loads(body.decode())
                await log(
                    request,
                    "Get",
                    "File",
                    200,
                    "info",
                    "File metadata retrieved from Google Drive successfully.",
                    {"file_id": file_id},
                    current_user.id,
                )
                return decoded
            else:
                body = await response.aread()
                decoded = json.loads(body.decode())
                if (
                    decoded
                    and decoded.get("error")
                    and decoded["error"].get("errors")
                    and decoded["error"]["errors"][0].get("reason") == "notFound"
                ):
                    return None
                await log(
                    request,
                    "Get",
                    "File",
                    400,
                    "warning",
                    "Failed to get file metadata from Google Drive.",
                    {
                        "status_code": response.status_code,
                        "response": body.decode(),
                        "file_id": file_id,
                    },
                    current_user.id,
                )
                return None

    except Exception as e:
        await log(
            request,
            "Get",
            "File",
            500,
            "error",
            "An error occurred while retrieving file metadata from Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        return None


async def get_google_drive_access_token(
    user_refresh_token, request: Request = None
) -> str | None:
    current_user = (
        request.state.current_user
        if request and hasattr(request.state, "current_user")
        else None
    )
    # Ensure user is authenticated
    if not current_user and (
        "user/" in request.url.path or "admin/" in request.url.path
    ):
        await log(
            request,
            "Get",
            "Google Drive Access Token",
            401,
            "warning",
            "Unauthorized user tried to get Google Drive access token.",
            {},
        )
        return None
    if not current_user:
        current_user = User(id=None)
    try:
        # Refresh access token
        async with AsyncOAuth2Client(
            client_id=os.environ["GOOGLE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        ) as client:
            new_token = await client.refresh_token(
                url="https://oauth2.googleapis.com/token",
                refresh_token=decrypt_data(user_refresh_token),
            )
        access_token = new_token["access_token"]
        await log(
            request,
            "Get",
            "Google Drive Access Token",
            200,
            "info",
            "Google Drive access token retrieved successfully.",
            {},
            current_user.id,
        )
        return access_token
    except Exception as e:
        await log(
            request,
            "Get",
            "Google Drive Access Token",
            500,
            "error",
            "An error occurred while retrieving Google Drive access token.",
            {"error": str(e)},
            current_user.id,
        )
        return None


async def import_file_in_drive(
    file_id, user_refresh_token, request: Request = None, max_retries=6
) -> dict | None:
    current_user = (
        request.state.current_user
        if request and hasattr(request.state, "current_user")
        else None
    )
    # Ensure user is authenticated
    if not current_user and (
        "user/" in request.url.path or "admin/" in request.url.path
    ):
        await log(
            request,
            "Import",
            "File",
            401,
            "warning",
            "Unauthorized user tried to import file in Google Drive.",
            {},
        )
        return None
    if not current_user:
        current_user = User(id=None)
    try:
        access_token = await get_google_drive_access_token(user_refresh_token, request)
        if not access_token:
            await log(
                request,
                "Import",
                "File",
                401,
                "warning",
                "Failed to retrieve Google Drive access token.",
                {},
                current_user.id,
            )
            return None
        file_content = None
        data = {}
        file_name = generate_random_string(10)
        size = "Unknown"
        # Fetch File
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                params={
                    "key": os.environ.get("GOOGLE_TOKEN_API_KEY"),
                    "fields": "id,name,size,mimeType,webViewLink,webContentLink",
                },
            ) as resp:
                error_data = await resp.json()
                errors = error_data.get("error", {}).get("errors", [{}])
                reason = errors[0].get("reason", "")
                if resp.status == 403 and reason in [
                    "userRateLimitExceeded",
                    "rateLimitExceeded",
                    "quotaExceeded",
                ]:
                    if max_retries < 1:
                        await log(
                            request,
                            "Import",
                            "File",
                            429,
                            "warning",
                            "Exceeded maximum retries due to rate limiting when fetching file metadata from Google Drive.",
                            {"file_id": file_id},
                            current_user.id,
                        )
                        return None
                    await asyncio.sleep(
                        2 ** (6 - max_retries) + random.randint(1, 5)
                    )  # Wait before retrying
                    return await import_file_in_drive(
                        file_id, user_refresh_token, request, max_retries - 1
                    )

                data = await resp.json()
                if resp.status != 200:
                    await log(
                        request,
                        "Import",
                        "File",
                        400,
                        "warning",
                        "Failed to fetch file metadata from Google Drive.",
                        {
                            "status_code": resp.status,
                            "response": data,
                            "file_id": file_id,
                        },
                        current_user.id,
                    )
                    return None
                file_name = data.get("name", file_name)
                size = (
                    data.get("size", size)
                    if data.get("size") and is_float(data.get("size"))
                    else "Unknown"
                )
        # Download File
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
                params={"key": os.environ.get("GOOGLE_TOKEN_API_KEY")},
            ) as file_resp:

                if file_resp.status != 200:
                    error_data = await file_resp.text()
                    await log(
                        request,
                        "Import",
                        "File",
                        400,
                        "warning",
                        "Failed to fetch file from Google Drive.",
                        {
                            "status_code": file_resp.status,
                            "response": error_data,
                            "file_id": file_id,
                        },
                        current_user.id,
                    )
                    return None
                file_content = await file_resp.read()
        # Upload File
        upload_url = (
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        metadata = {
            "name": file_name,
        }
        multipart_body = aiohttp.FormData()
        multipart_body.add_field(
            "metadata", json.dumps(metadata), content_type="application/json"
        )
        multipart_body.add_field("file", file_content, filename=metadata["name"])
        result_data = {}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                upload_url, headers=headers, data=multipart_body
            ) as upload_resp:

                upload_data = await upload_resp.json()
                if upload_resp.status != 200:
                    errors = upload_data.get("error", {}).get("errors", [{}])
                    reason = errors[0].get("reason", "")
                    if upload_resp.status == 403 and reason in [
                        "userRateLimitExceeded",
                        "rateLimitExceeded",
                        "quotaExceeded",
                    ]:
                        if max_retries < 1:
                            await log(
                                request,
                                "Import",
                                "File",
                                429,
                                "warning",
                                "Exceeded maximum retries due to rate limiting when uploading file to Google Drive.",
                                {"file_id": file_id},
                                current_user.id,
                            )
                            return None
                        await asyncio.sleep(
                            2 ** (6 - max_retries) + random.randint(1, 5)
                        )  # Wait before retrying
                        return await import_file_in_drive(
                            file_id, user_refresh_token, request, max_retries - 1
                        )
                    await log(
                        request,
                        "Import",
                        "File",
                        400,
                        "warning",
                        "Failed to upload file to Google Drive.",
                        {
                            "status_code": upload_resp.status,
                            "response": upload_data,
                            "file_id": file_id,
                        },
                        current_user.id,
                    )
                    return None
                result_data = upload_data
        # Change file permissions to anyone with the link can view
        permission_url = f"https://www.googleapis.com/drive/v3/files/{upload_data.get('id')}/permissions"
        permission_body = {"role": "reader", "type": "anyone"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                permission_url, headers=headers, json=permission_body
            ) as perm_resp:

                error_data = await perm_resp.json()
                errors = error_data.get("error", {}).get("errors", [{}])
                reason = errors[0].get("reason", "")
                if perm_resp.status == 403 and reason in [
                    "userRateLimitExceeded",
                    "rateLimitExceeded",
                    "quotaExceeded",
                ]:
                    if max_retries < 1:
                        await log(
                            request,
                            "Import",
                            "File",
                            429,
                            "warning",
                            "Exceeded maximum retries due to rate limiting when setting file permissions in Google Drive.",
                            {"file_id": upload_data.get("id")},
                            current_user.id,
                        )
                        return None
                    await asyncio.sleep(
                        2 ** (6 - max_retries) + random.randint(1, 5)
                    )  # Wait before retrying
                    return await import_file_in_drive(
                        file_id, user_refresh_token, request, max_retries - 1
                    )

                perm_data = await perm_resp.json()
                if perm_resp.status != 200:
                    await log(
                        request,
                        "Import",
                        "File",
                        400,
                        "warning",
                        "Failed to set file permissions in Google Drive.",
                        {
                            "status_code": perm_resp.status,
                            "response": perm_data,
                            "file_id": upload_data.get("id"),
                        },
                        current_user.id,
                    )
        result_data["size"] = size
        result_data = get_file_data(result_data)
        # Return the uploaded file data
        await log(
            request,
            "Import",
            "File",
            200,
            "info",
            "File imported to Google Drive successfully.",
            {"file_id": upload_data.get("id")},
            current_user.id,
        )
        return result_data
    except Exception as e:
        await log(
            request,
            "Copy",
            "File",
            500,
            "error",
            "An error occurred while copying file in Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        return None


def user_agent_parser(user_agent: str) -> str:
    """
    Parses the user agent string to extract device information and returns a formatted string.
    :param user_agent: User agent string from the request headers
    :return: Formatted string like 'Apple iPhone', 'Samsung Tablet', 'Desktop', etc.
    """
    if not user_agent or not isinstance(user_agent, str):
        return "Unknown Device"

    try:
        ua = parse(user_agent)

        # Check for bots first
        if ua.is_bot:
            return "Bot/Crawler"

        # Check for tablets
        if ua.is_tablet:
            if ua.device.brand and ua.device.brand != "Unknown":
                return f"{ua.device.brand.strip().title()} Tablet"
            else:
                return "Unknown Tablet"

        # Check for mobile phones
        if ua.is_mobile:
            if ua.device.brand and ua.device.brand != "Unknown":
                return f"{ua.device.brand.strip().title()} Phone"
            else:
                return "Unknown Phone"

        # Check for desktop computers
        if ua.is_pc:
            return "Desktop"

        # Check for smart TVs, gaming consoles, etc.
        if ua.device.brand and ua.device.brand != "Unknown":
            return f"{ua.device.brand.strip().title()} Device"

        # Fallback for any other device type
        return "Unknown Device"

    except Exception as e:
        # In case of any parsing errors, return Unknown Device
        return "Unknown Device"


async def get_device_details(ip: str, user_agent: str, request: Request = None) -> dict:
    """
    Fetches device details based on the provided IP address using the ipgeolocation.io API.
    :param ip: IP address to fetch details for
    :param user_agent: User agent string from the request headers
    :param request: FastAPI Request object (for logging purposes)
    :return: Dictionary containing device details (city, country, device) or empty dict on failure
    """
    if not ip or not isinstance(ip, str):
        return {}
    try:
        api_key = os.environ.get("IPGEOLOCATION_API_KEY")
        if not api_key:
            await log(
                request,
                "Get",
                "Device",
                500,
                "error",
                "IPGeolocation API key is not set in environment variables.",
                {},
            )
            return {}
        async with AsyncOAuth2Client() as client:
            data = {
                "city": "Unknown",
                "country": "Unknown",
                "device": (
                    user_agent_parser(user_agent) if user_agent else "Unknown Device"
                ),
            }
            response = await client.get(
                f"https://api.ipgeolocation.io/v2/ipgeo?apiKey={api_key}&ip={ip}"
            )
            if str(response.status_code)[0] == "2":
                body = await response.aread()
                decoded = json.loads(body.decode())
                location = decoded.get("location", {})
                data["city"] = location.get("city", "Unknown")
                data["country"] = location.get("country_name", "Unknown")
                await log(
                    request,
                    "Get",
                    "Device",
                    200,
                    "info",
                    "Geolocation details fetched from IPGeolocation API successfully.",
                    {"ip": ip, "data": data},
                )
                return data
            else:
                body = await response.aread()
                await log(
                    request,
                    "Get",
                    "Device",
                    400,
                    "warning",
                    "Failed to fetch geolocation details from IPGeolocation API.",
                    {
                        "status_code": response.status_code,
                        "response": body.decode(),
                        "ip": ip,
                    },
                )
                return {}
    except Exception as e:
        await log(
            request,
            "Get",
            "Device",
            500,
            "error",
            "An error occurred while fetching device details.",
            {"error": str(e), "ip": ip},
        )
        return {}


def is_int(value) -> bool:
    """
    Helper function to check if a value is an integer.
    """
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_float(value) -> bool:
    """
    Helper function to check if a value is a float.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_sanitized(data) -> bool:
    """
    Checks if the given data is sanitized.

    Rules:
    - str: Must be either:
        1. A phone number starting with '+' followed by digits only (e.g. '+20151511'), OR
        2. Only letters (a-zA-Z), digits (0-9), hyphens (-), underscores (_), @, dots (.), colons (:), parentheses (()), ampersands (&), and spaces, OR
    - dict: All keys and values must be sanitized recursively.
    - list: All elements must be sanitized recursively.
    - Other types: Considered safe (returns True).
    """
    # for now skip this step
    return True
    if not data:
        return True
    if isinstance(data, str):
        # Phone number format: + followed by digits
        if re.fullmatch(r"\+\d+", data):
            return True
        # Allowed chars: letters, digits, hyphen, underscore, @, dot, colon, brackets, ampersand, space
        if re.fullmatch(r"[a-zA-Z0-9\-_@.:%()& ]+", data):
            return True
        if is_valid_url(data):
            return True
        return False

    elif isinstance(data, dict):
        return all(is_sanitized(k) and is_sanitized(v) for k, v in data.items())

    elif isinstance(data, list):
        return all(is_sanitized(item) for item in data)

    return True


def is_drive_url(url: str) -> bool:
    """
    Validates if the provided URL is a valid Google Drive URL.
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match various Google Drive URL formats
    drive_url_pattern = re.compile(
        r"^(https?://)?(www\.)?(drive\.google\.com|docs\.google\.com|forms\.google\.com|slides\.google\.com|sheets\.google\.com|sites\.google\.com)/.*$"
    )

    return bool(drive_url_pattern.match(url.strip()))


def is_youtube_url(url: str) -> bool:
    """
    Validates if the provided URL is a valid YouTube URL.
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match various YouTube URL formats including yt music
    youtube_url_pattern = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.*$"
    )

    return bool(youtube_url_pattern.match(url.strip()))


def is_valid_url(url: str) -> bool:
    """
    Validates if the provided string is a well-formed URL (Public Url only).
    """
    if not url or not isinstance(url, str):
        return False

    # Regular expression to match well-formed URLs (excluding localhost, IP addresses, and port)
    url_pattern = re.compile(
        r"^(https?://)"  # http:// or https://
        r"(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})"  # Domain name only
        r"(/[A-Za-z0-9\-._~:/?#[\]@!$&\'()*+,;=]*)?$"  # Path and query string
    )

    return bool(url_pattern.match(url.strip()))


def is_date(date_str: str) -> bool:
    """
    Validates if the provided string is a valid date in YYYY-MM-DD format.
    """
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_phone_number(phone: str) -> bool:
    """
    Validates if the provided string is a valid phone number.
    Accepts formats like +201234567890 or 01234567890
    """
    if not phone or not isinstance(phone, str):
        return False
    phone = phone.strip().lower()
    if "+" in phone and phone[0] != "+":
        return False
    had_code = True if phone.startswith("+") else False
    phone = phone.replace("+", "")
    if not phone.isdigit():
        return False
    if len(phone) < 10 or len(phone) > 12:
        return False
    if len(phone) != 11 and not had_code:
        return False
    if len(phone) == 11 and phone[0] != "0" and not had_code:
        return False
    if len(phone) < 12 and had_code:
        return False
    if len(phone) == 12 and phone[0:2] != "20":
        return False
    return True


# Authentication routes
@auth.post("/refresh")
@is_not_logged_in
@rate_limit
async def refresh(request: Request):
    try:
        authentication_type = os.environ.get("AUTHENTICATION")
        if authentication_type == "cookies":
            data = request.cookies
        else:
            data = await request.json()
        if not data:
            await log(
                request,
                "Refresh",
                "Token",
                400,
                "warning",
                "No Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "No data provided"}, 400
            )
            return finalize_request(response)
        if authentication_type == "cookies":
            refresh_token = data.get("refresh_token_backend", None) if data else None
        else:
            refresh_token = data.get("refresh_token", None) if data else None
        if not refresh_token:
            await log(
                request,
                "Refresh",
                "Token",
                400,
                "warning",
                "No Refresh Token Found in The Request Cookies.",
                {},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You are not logged in. Please log in again.",
                },
                400,
            )
            return finalize_request(response)
        if not is_sanitized(refresh_token):
            await log(
                request,
                "Refresh",
                "Token",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {"refresh_token": refresh_token},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
    except json.JSONDecodeError as e:
        await log(
            request,
            "Refresh",
            "Token",
            400,
            "warning",
            "Invalid JSON in Request Body.",
            {"error": str(e)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid JSON. Please provide a valid JSON body.",
            },
            400,
        )
        return finalize_request(response)
    try:
        async with async_session() as session:
            user = (
                await session.execute(
                    Select(User).where(
                        User.refresh_token == refresh_token,
                        User.refresh_expire_at > datetime.now(utc_tz),
                    )
                )
            ).scalar_one_or_none()
            if not user:
                await log(
                    request,
                    "Refresh",
                    "Token",
                    404,
                    "warning",
                    "User Not Found.",
                    {"refresh_token": refresh_token},
                )
                response = JSONResponse(
                    {"status": "error", "message": "User not found"}, 404
                )
                return finalize_request(response)
            expire_date = convert_from_utc(user.refresh_expire_at)
            payload = {
                "id": user.id,
                "expire_date": (
                    datetime.now(cairo_tz) + timedelta(minutes=access_token_expire_time)
                ).isoformat(),
            }
            access_token = jwt.encode(
                payload, os.environ.get("ACCESS_TOKEN_SECRET_KEY"), algorithm="HS256"
            )
            if (
                expire_date - datetime.now(cairo_tz)
            ).days < 7:  # If the refresh token is about to expire in less than 7 days
                await log(
                    request,
                    "Refresh",
                    "Token",
                    200,
                    "info",
                    "Refreshing Refresh Token for User.",
                    {},
                    user.id,
                )
                refresh_token = await generate_refresh_token(user.id)
                if not refresh_token:
                    await log(
                        request,
                        "Refresh",
                        "Token",
                        500,
                        "error",
                        "An error occurred while generating refresh token for user.",
                        {},
                        user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "An error occurred while generating refresh token",
                        },
                        500,
                    )
                    return finalize_request(response)
                expire_date = convert_from_utc(user.refresh_expire_at)
            await log(
                request,
                "Refresh",
                "Token",
                200,
                "info",
                "Successfully refreshed tokens for user.",
                {},
                user.id,
            )
            if authentication_type == "cookies":
                response = JSONResponse(
                    {
                        "status": "success",
                        "message": "Token refreshed successfully",
                    },
                    200,
                )
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=access_token_expire_time * 60,  # in seconds
                    path="/",
                )
                response.set_cookie(
                    key="refresh_token",
                    value=refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="lax",
                    max_age=refresh_token_expire_time * 24 * 60 * 60,  # in seconds
                    path="/",
                )
                return finalize_request(response)
            else:
                response_payload = {
                    "access_token": access_token,
                    "access_expires_in": int(
                        timedelta(minutes=access_token_expire_time).total_seconds()
                    ),  # seconds until expiration
                    "refresh_token": refresh_token,
                    "refresh_expires_in": int(
                        (expire_date - datetime.now(cairo_tz)).total_seconds()
                    ),  # seconds until expiration
                }
                response = JSONResponse(
                    {
                        "status": "success",
                        "message": "Token refreshed successfully",
                        "data": response_payload,
                    },
                    200,
                )
                return finalize_request(response)
    except jwt.ExpiredSignatureError as e:
        await log(
            request,
            "Refresh",
            "Token",
            407,
            "warning",
            "Refresh Token Expired.",
            {"error": str(e), "refresh_token": refresh_token},
        )
        response = JSONResponse({"status": "error", "message": str(e)}, 407)
        return finalize_request(response)
    except jwt.InvalidTokenError as e:
        await log(
            request,
            "Refresh",
            "Token",
            401,
            "warning",
            "Invalid Refresh Token Provided.",
            {"error": str(e), "refresh_token": refresh_token},
        )
        response = JSONResponse({"status": "error", "message": str(e)}, 401)
        return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Refresh",
            "Token",
            500,
            "error",
            "An error occurred while refreshing tokens.",
            {"error": str(e)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An Error Occurred. Please Try Again Later.",
            },
            500,
        )
        return finalize_request(response)


@auth.post("/signup")
@is_not_logged_in
@rate_limit
async def signup(request: Request):
    data = await request.json()
    if not data:
        await log(
            request,
            "Create",
            "Profile",
            400,
            "warning",
            "No Data Provided for SignUp.",
            {},
        )
        response = JSONResponse({"status": "error", "message": "No data provided"}, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Create",
            "Profile",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    gender = data.get("gender", "").strip()
    agreed = data.get("agreed", "")
    early_access = data.get("early_access", False)
    if not agreed:
        await log(
            request,
            "Create",
            "Profile",
            400,
            "warning",
            "User did not agree to the terms and conditions.",
            {"data": dict(data)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "You must agree to the terms and conditions to sign up",
            },
            400,
        )
        return finalize_request(response)
    manages = {}
    details = {}
    google_details_token = (
        data.get("google_details_token").strip()
        if data.get("google_details_token")
        else None
    )
    if not google_details_token:
        await log(
            request,
            "Create",
            "Profile",
            400,
            "warning",
            "UnAuthorized User With Google Tried to SignUp.",
            {"data": dict(data)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "You Must Authorize Google Account to Proceed.",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            google_details_token = (
                await session.execute(
                    Select(Token).where(
                        Token.token == google_details_token,
                        Token.expire_at > datetime.now(utc_tz),
                    )
                )
            ).scalar_one_or_none()
            if not google_details_token or not google_details_token.details:
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "UnAuthorized User With Google Tried to SignUp.",
                    {"data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You Must Authorize Google Account to Proceed.",
                    },
                    400,
                )
                return finalize_request(response)
            google_details_token.expire_at = datetime.now(utc_tz) + timedelta(
                minutes=-1
            )  # Invalidate the token
            google_details_token = google_details_token.details
            if (
                not name
                or name == ""
                or not email
                or email == ""
                or not phone
                or phone == ""
                or not gender
                or gender == "gender"
                or gender == ""
            ):
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "Missing Required Fields for SignUp.",
                    {"data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Please make sure to fill all the required fields",
                    },
                    400,
                )
                return finalize_request(response)
            if (
                await session.execute(Select(User).where(User.email == email))
            ).scalar_one_or_none():
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "User Tried to SignUp with Email Already Existing.",
                    {"email": email, "data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Email already exists"}, 400
                )
                return finalize_request(response)
            if (
                await session.execute(Select(User).where(User.phone == phone))
            ).scalar_one_or_none():
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "User Tried to SignUp with Phone Number Already Existing.",
                    {"phone": phone, "data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "A user with this phone number already exists",
                    },
                    400,
                )
                return finalize_request(response)
            try:
                email_info = validate_email(email, check_deliverability=True)
            except EmailNotValidError as e:
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "Invalid Email Address Provided for SignUp.",
                    {"email": email, "data": dict(data), "error": str(e)},
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Invalid email address provided"},
                    400,
                )
                return finalize_request(response)
            if not is_phone_number(phone):
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "Invalid Phone Number Provided for SignUp.",
                    {"phone": phone, "data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Invalid phone number provided"}, 400
                )
                return finalize_request(response)
            domain = email_info.domain
            url = None
            allowed_domains = ["cu.edu.eg", "stud.cu.edu.eg"]
            if domain not in allowed_domains and not any(
                d for d in allowed_domains if d in domain
            ):
                url = data.get("url", None).strip() if data.get("url") else None
                if not url:
                    await log(
                        request,
                        "Create",
                        "Profile",
                        400,
                        "warning",
                        "User Did not use University email and did not provide approval image for SignUp.",
                        {"email": email, "data": dict(data)},
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You must Upload Your Approval Image or Use Your University Email (stud.cu.edu.eg) to "
                            "SignUp.",
                        },
                        400,
                    )
                    return finalize_request(response)
            status = url is None
            google_user_details = jwt.decode(
                google_details_token,
                os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not google_user_details:
                await log(
                    request,
                    "Create",
                    "Profile",
                    400,
                    "warning",
                    "UnAuthorized User With Google Tried to SignUp.",
                    {"data": dict(data)},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You Must Authorize Google Account to Proceed.",
                    },
                    400,
                )
                return finalize_request(response)
            google_user_details = google_user_details.get("google_user_details")
            if url:
                drive_file = await get_file_from_drive(
                    url, google_user_details.get("google_refresh_token"), request
                )
                if not drive_file:
                    await log(
                        request,
                        "Create",
                        "Profile",
                        400,
                        "warning",
                        "Invalid Google Drive URL Provided for Approval Image.",
                        {"data": dict(data)},
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Invalid Image Uploaded. Please try again.",
                        },
                        400,
                    )
                    return finalize_request(response)
                if not verify_file_type(drive_file.get("mimeType", ""), "image"):
                    await log(
                        request,
                        "Create",
                        "Profile",
                        400,
                        "warning",
                        "Non Image File Provided as Approval Image.",
                        {
                            "data": dict(data),
                            "file_mimeType": drive_file.get("mimeType", ""),
                        },
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "The Uploaded File Must Be an Image. Please try again.",
                        },
                        400,
                    )
                    return finalize_request(response)
                if (
                    drive_file.get("size")
                    and int(drive_file.get("size")) > 10 * 1024 * 1024
                ):
                    await log(
                        request,
                        "Create",
                        "Profile",
                        400,
                        "warning",
                        "Image Provided as Approval Image Exceeds Size Limit.",
                        {"data": dict(data), "file_size": drive_file.get("size")},
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "The Uploaded Image Must Not Exceed 10MB in Size. Please try again.",
                        },
                        400,
                    )
                    return finalize_request(response)
            # token = await generate_unique_token(40)
            code = generate_random_number(6)
            payload = {
                "user": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "gender": gender,
                    "role": "user",
                    "manages": manages,
                    "details": details,
                    "status": status,
                    "google_id": google_user_details.get("google_id"),
                    "google_name": google_user_details.get("google_name"),
                    "google_email": google_user_details.get("google_email"),
                    "google_avatar": google_user_details.get("google_avatar"),
                    "google_refresh_token": google_user_details.get(
                        "google_refresh_token"
                    ),
                    "early_access": early_access,
                }
            }
            if not status:
                payload["pending_user"] = {"url": url}
            token_user = jwt.encode(
                payload, os.environ.get("USER_TOKEN_SECRET_KEY"), algorithm="HS256"
            )
            token_db = Token(
                token=code,
                details=token_user,
                is_valid=True,
                expire_at=datetime.now(utc_tz)
                + timedelta(minutes=user_token_expire_time),
                type=1,  # 1 for User signup token
            )
            session.add(token_db)
            await session.commit()
            email_sent = await send_email(
                request,
                email,
                "verify_email",
                {
                    "name": name,
                    # 'link': 'https://' + request.url.hostname + f"/verify-email?token={token}",
                    "code": code,
                },
            )
            if email_sent.status_code != 200:
                await session.delete(token_db)
                await session.commit()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An Error Occurred While Trying to SignUp Please Try Again Later.",
                    },
                    500,
                )
                return finalize_request(response)
            can_resend_after_date = datetime.now(cairo_tz) + timedelta(minutes=1)
            code_details = {
                "code": code,
                "can_resend_after": (can_resend_after_date).isoformat(),
            }
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Successfully Created Your Profile. Please Check Your Email to Verify Your Account.",
                    "data": {
                        "can_resend_after": (
                            math.ceil(
                                (
                                    can_resend_after_date - datetime.now(cairo_tz)
                                ).total_seconds()
                            )
                            if can_resend_after_date > datetime.now(cairo_tz)
                            else 0
                        )
                    },
                },
                201,
            )
            response.set_cookie(
                key="code_details",
                value=json.dumps(code_details),
                httponly=True,
                secure=True,
                samesite="none",
                max_age=user_token_expire_time * 60,  # in seconds
                path="/",
            )
            await log(
                request,
                "Create",
                "Profile",
                201,
                "info",
                "User Signed Up Successfully.",
                {"data": dict(data), "user": payload.get("user")},
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Create",
                "Profile",
                500,
                "error",
                "An error occurred while signing up user.",
                {"error": str(e), "data": dict(data)},
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An Error Occurred While Trying to SignUp Please Try Again Later.",
                },
                500,
            )
            return finalize_request(response)


@auth.get("/logout")
@is_logged_in
@rate_limit
async def logout(request: Request):
    """
    This route is used to log out the user.
    It will clear the session and cookies.
    """
    async with async_session() as session:
        await session.begin()
        try:
            current_user = await session.merge(request.state.current_user)
            current_user.refresh_token = None  # Clear the refresh token
            current_user.refresh_expire_at = datetime.now(utc_tz) + timedelta(
                minutes=-1
            )
            await session.commit()
            response = JSONResponse(
                {"status": "success", "message": "You have logged out successfully."}
            )
            response.set_cookie(
                key="success",
                value="You have logged out successfully.",
                httponly=False,
                secure=True,
                samesite="lax",
                path="/",  # Cookie is valid for the entire site
            )
            response.delete_cookie("access_token_backend", path="/")
            response.delete_cookie("refresh_token_backend", path="/")
            response.delete_cookie("google_details_token_backend", path="/")
            response.delete_cookie("oauth_state_backend", path="/")
            response.delete_cookie("access_token", path="/")
            response.delete_cookie("refresh_token", path="/")
            response.delete_cookie("google_details_token", path="/")
            response.delete_cookie("oauth_state", path="/")
            await log(
                request,
                "Logout",
                "User",
                200,
                "info",
                "User logged out successfully.",
                {},
                current_user.id,
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Logout",
                "User",
                500,
                "error",
                "An error occurred while logging out user.",
                {"error": str(e)},
                current_user.id if current_user else None,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An Error Occurred While Trying to Logout Please Try Again Later.",
                },
                500,
            )
            return finalize_request(response)


# @app.get('/verify-email')
# @rate_limit
# @is_not_logged_in_web
# async def verify_email(request: Request):
#     authentication_type = os.environ.get("AUTHENTICATION")
#     token = request.query_params.get('token')
#     if not token:
#         await log(request, "Verify", "Email", 400, 'warning', 'No Token Provided for Email Verification.')
#         response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#         response.set_cookie(
#             key="error",
#             value="Invalid Request. Please try to SignUp Again.",
#             httponly=False,
#             secure=True,
#             samesite='lax',
#             path="/" # Cookie is valid for the entire site
#         )
#         return finalize_request(response)
#     if not is_sanitized(token):
#         await log(request, "Verify", "Email", 400, 'warning', 'Un Sanitized Token Provided for Email Verification.', {'token': token})
#         response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#         response.set_cookie(
#             key="error",
#             value="Invalid Request. Please try to SignUp Again.",
#             httponly=False,
#             secure=True,
#             samesite='lax',
#             path="/" # Cookie is valid for the entire site
#         )
#         return finalize_request(response)
#     async with async_session() as session:
#         await session.begin()
#         try:
#             token_db = (await session.execute(Select(Token).where(Token.token == token, Token.expire_at > datetime.now(
#                 cairo_tz)))).scalar_one_or_none()
#             if not token_db or not token_db.details:
#                 await log(request, "Verify", "Email", 400, 'warning', 'Invalid or Expired Token Provided for Email Verification.', {'token': token})
#                 await session.rollback()
#                 response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#                 response.set_cookie(
#                     key="error",
#                     value="Invalid or Expired Token. Please Try to SignUp Again.",
#                     httponly=False,
#                     secure=True,
#                     samesite='lax',
#                     path="/" # Cookie is valid for the entire site
#                 )
#                 return finalize_request(response)
#             payload = jwt.decode(token_db.details, os.environ.get('USER_TOKEN_SECRET_KEY'), algorithms=['HS256'])
#             user = payload.get('user')
#             if not user:
#                 await log(request, "Verify", "Email", 400, 'warning', 'Invalid User Data in Token Provided for Email Verification.', {'token': token})
#                 await session.rollback()
#                 response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#                 response.set_cookie(
#                     key="error",
#                     value="Invalid Token Data. Please Try to SignUp Again.",
#                     httponly=False,
#                     secure=True,
#                     samesite='lax',
#                     path="/" # Cookie is valid for the entire site
#                 )
#                 return finalize_request(response)
#             user_db = User(
#                 name=user.get('name'),
#                 email=user.get('email'),
#                 phone=user.get('phone'),
#                 gender=user.get('gender'),
#                 role=(await session.execute(Select(Role).where(Role.name == 'user'))).scalar_one_or_none(),
#                 manages=user.get('manages'),
#                 details=user.get('details'),
#                 status=user.get('status'),
#                 google_id=user.get('google_id'),
#                 google_name=user.get('google_name'),
#                 google_email=user.get('google_email'),
#                 google_avatar=user.get('google_avatar'),
#                 google_refresh_token=user.get('google_refresh_token'),
#                 ips = [request.client.host]  # Store the IP address of the user
#             )
#             pending_user = payload.get('pending_user')
#             pending_user_db = PendingUser(
#                 url=pending_user.get('url') if pending_user else None,
#             )
#             session.add(user_db)
#             if pending_user:
#                 pending_user_db.user = user_db
#                 session.add(pending_user_db)
#             token_db.expire_at = datetime.now(cairo_tz) - timedelta(minutes=1)  # Invalidate the token
#             await session.commit()
#             refresh_token = await generate_refresh_token(user_db.id)
#             if not refresh_token:
#                 await log(request, "Verify", "Email", 500, 'error', 'An error occurred while generating refresh token for user.', {}, user_db.id)
#                 await session.delete(user_db)
#                 await session.commit()
#                 response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#                 response.set_cookie(
#                     key="error",
#                     value="An Error Occurred While Trying to SignUp Please Try Again Later.",
#                     httponly=False,
#                     secure=True,
#                     samesite='lax',
#                     path="/" # Cookie is valid for the entire site
#                 )
#                 return finalize_request(response)
#             access_token = jwt.encode({
#                 'id': user_db.id,
#                 'expire_date': (datetime.now(cairo_tz) + timedelta(minutes=access_token_expire_time)).isoformat()
#             }, os.environ.get('ACCESS_TOKEN_SECRET_KEY'), algorithm='HS256')
#             if authentication_type == "cookies":
#                 response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#                 response.set_cookie(
#                     key="access_token_backend",
#                     value=access_token,
#                     httponly=True,
#                     secure=True,
#                     samesite='lax',
#                     max_age=access_token_expire_time * 60,  # in seconds
#                     path="/" # Cookie is valid for the entire domain
#                 )
#                 response.set_cookie(
#                     key="refresh_token_backend",
#                     value=refresh_token,
#                     httponly=True,
#                     secure=True,
#                     samesite='lax',
#                     max_age=refresh_token_expire_time * 24 * 60 * 60,  # in seconds
#                     path="/" # Cookie is valid for the entire domain
#                 )
#             else:
#                 response_payload = {
#                     'access_token': access_token,
#                     'access_expires_in': int(timedelta(minutes=access_token_expire_time).total_seconds()), # seconds until expiration
#                     'refresh_token': refresh_token,
#                     'refresh_expires_in': int(timedelta(days=refresh_token_expire_time).total_seconds()), # seconds until expiration
#                 }
#                 response = RedirectResponse(
#                     f"{os.environ.get('FRONTEND_URL')}/login?token="
#                     f"{response_payload.get('access_token')}___{response_payload.get('access_expires_in')}___"
#                     f"{response_payload.get('refresh_token')}___{response_payload.get('refresh_expires_in')}")
#             response.set_cookie(
#                 key="success",
#                 value="Your Email Has Been Verified Successfully. You Can Now Login to Your Account.",
#                 httponly=False,
#                 secure=True,
#                 samesite='lax',
#                 path="/" # Cookie is valid for the entire site
#             )
#             await log(request, "Verify", "Email", 200, 'info', 'User Email Verified and Created Account Successfully.',
#                       {}, user_db.id)
#             return finalize_request(response)
#         except jwt.ExpiredSignatureError as e:
#             await log(request, "Verify", "Email", 400, 'warning', 'Expired Token Provided for Email Verification.', {'error': str(e), 'token': token})
#             response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#             response.set_cookie(
#                 key="error",
#                 value="Expired Token. Please Try to SignUp Again.",
#                 httponly=False,
#                 secure=True,
#                 samesite='lax',
#                 path="/" # Cookie is valid for the entire site
#             )
#             await session.rollback()
#             return finalize_request(response)
#         except jwt.InvalidTokenError as e:
#             await log(request, "Verify", "Email", 400, 'warning', 'Invalid Token Provided for Email Verification.', {'error': str(e), 'token': token})
#             response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#             response.set_cookie(
#                 key="error",
#                 value="Invalid Token. Please Try to SignUp Again.",
#                 httponly=False,
#                 secure=True,
#                 samesite='lax',
#                 path="/" # Cookie is valid for the entire site
#             )
#             await session.rollback()
#             return finalize_request(response)
#         except Exception as e:
#             await log(request, "Verify", "Email", 500, 'error', 'An error occurred while verifying user email.', {'error': str(e)})
#             await session.rollback()
#             response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
#             response.set_cookie(
#                 key="error",
#                 value="An Error Occurred While Trying to SignUp Please Try Again Later.",
#                 httponly=False,
#                 secure=True,
#                 samesite='lax',
#                 path="/" # Cookie is valid for the entire site
#             )
#             return finalize_request(response)
#


@auth.post("/verify-email")
@is_not_logged_in
@rate_limit
# @has_cookies_web(["code_details"])
async def verify_email(request: Request):
    authentication_type = os.environ.get("AUTHENTICATION")
    data = await request.json()
    if not data:
        await log(
            request,
            "Verify",
            "Email",
            400,
            "warning",
            "No Data Provided for Email Verification.",
            {},
        )
        response = JSONResponse({"status": "error", "message": "No data provided"}, 400)
        response.delete_cookie("code_details", path="/")
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Verify",
            "Email",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        response.delete_cookie("code_details", path="/")
        return finalize_request(response)
    code = data.get("code", "").strip()
    if not code or code == "":
        await log(
            request,
            "Verify",
            "Email",
            400,
            "warning",
            "No Code Provided for Email Verification.",
            {},
        )
        response = JSONResponse({"status": "error", "message": "No code provided"}, 400)
        return finalize_request(response)
    if len(code) != 6 or not code.isdigit():
        await log(
            request,
            "Verify",
            "Email",
            400,
            "warning",
            "Invalid Code Provided for Email Verification.",
            {"code": code},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid code provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            token_db = (
                await session.execute(
                    Select(Token).where(
                        Token.token == code, Token.expire_at > datetime.now(utc_tz)
                    )
                )
            ).scalar_one_or_none()
            if not token_db or not token_db.details:
                await log(
                    request,
                    "Verify",
                    "Email",
                    400,
                    "warning",
                    "Invalid or Expired Code Provided for Email " "Verification.",
                    {"code": code},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid or Expired code. Please Try to SignUp Again.",
                    },
                    400,
                )
                return finalize_request(response)
            payload = jwt.decode(
                token_db.details,
                os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            user = payload.get("user")
            if not user:
                await log(
                    request,
                    "Verify",
                    "Email",
                    400,
                    "warning",
                    "Invalid User Data in Code Provided for Email " "Verification.",
                    {"code": code},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid Data. Please Try to SignUp Again.",
                    },
                    400,
                )
                return finalize_request(response)
            user_db = User(
                name=user.get("name"),
                email=user.get("email"),
                phone=user.get("phone"),
                gender=user.get("gender"),
                role=(
                    await session.execute(Select(Role).where(Role.name == "user"))
                ).scalar_one_or_none(),
                manages=user.get("manages"),
                details=user.get("details"),
                status=user.get("status"),
                is_early_access=user.get("early_access", False),
                google_id=user.get("google_id"),
                google_name=user.get("google_name"),
                google_email=user.get("google_email"),
                google_avatar=user.get("google_avatar"),
                google_refresh_token=user.get("google_refresh_token"),
                ips=[request.client.host],  # Store the IP address of the user
            )
            pending_user = payload.get("pending_user")
            pending_user_db = PendingUser(
                url=pending_user.get("url") if pending_user else None,
            )
            session.add(user_db)
            await session.flush()  # Ensure user_db.id is populated
            if pending_user:
                pending_user_db.user = user_db
                session.add(pending_user_db)
            token_db.expire_at = datetime.now(utc_tz) - timedelta(
                minutes=1
            )  # Invalidate the token
            await session.commit()
            refresh_token = await generate_refresh_token(user_db.id)
            if not refresh_token:
                await log(
                    request,
                    "Verify",
                    "Email",
                    500,
                    "error",
                    "An error occurred while generating refresh token for user.",
                    {},
                    user_db.id,
                )
                await session.delete(user_db)
                if pending_user:
                    await session.delete(pending_user_db)
                await session.commit()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An Error Occurred While Trying to SignUp Please Try Again Later.",
                    },
                    500,
                )
                response.delete_cookie("code_details", path="/")
                return finalize_request(response)
            access_token = jwt.encode(
                {
                    "id": user_db.id,
                    "expire_date": (
                        datetime.now(cairo_tz)
                        + timedelta(minutes=access_token_expire_time)
                    ).isoformat(),
                },
                os.environ.get("ACCESS_TOKEN_SECRET_KEY"),
                algorithm="HS256",
            )
            if authentication_type == "cookies":
                response = JSONResponse(
                    {
                        "status": "success",
                        "message": "Your Email Has Been Verified Successfully. You Can Now Login to Your Account.",
                    },
                    200,
                )
                response.set_cookie(
                    key="access_token_backend",
                    value=access_token,
                    httponly=True,
                    secure=True,
                    samesite="none",
                    max_age=access_token_expire_time * 60,  # in seconds
                    path="/",  # Cookie is valid for the entire domain
                )
                response.set_cookie(
                    key="refresh_token_backend",
                    value=refresh_token,
                    httponly=True,
                    secure=True,
                    samesite="none",
                    max_age=refresh_token_expire_time * 24 * 60 * 60,  # in seconds
                    path="/",  # Cookie is valid for the entire domain
                )
            else:
                response_payload = {
                    "access_token": access_token,
                    "access_expires_in": int(
                        timedelta(minutes=access_token_expire_time).total_seconds()
                    ),  # seconds until expiration
                    "refresh_token": refresh_token,
                    "refresh_expires_in": int(
                        timedelta(days=refresh_token_expire_time).total_seconds()
                    ),  # seconds until expiration
                }
                response = JSONResponse(
                    {
                        "status": "success",
                        "message": "Your Email Has Been Verified Successfully. You Can Now Login to Your Account.",
                        "data": response_payload,
                    },
                    200,
                )
            response.set_cookie(
                key="success",
                value="Your Email Has Been Verified Successfully. You Can Now Login to Your Account.",
                httponly=False,
                secure=True,
                samesite="lax",
                path="/",  # Cookie is valid for the entire site
            )
            await log(
                request,
                "Verify",
                "Email",
                200,
                "info",
                "User Email Verified and Created Account Successfully.",
                {},
                user_db.id,
            )
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(
                request,
                "Verify",
                "Email",
                400,
                "warning",
                "Expired Code Provided for Email Verification.",
                {"error": str(e), "code": code},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Expired Code. Please Try to SignUp Again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(
                request,
                "Verify",
                "Email",
                400,
                "warning",
                "Invalid Code Provided for Email Verification.",
                {"error": str(e), "code": code},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid Code. Please Try to SignUp Again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Verify",
                "Email",
                500,
                "error",
                "An error occurred while verifying user email.",
                {"error": str(e)},
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An Error Occurred While Trying to SignUp Please Try Again Later.",
                },
                500,
            )
            return finalize_request(response)


@auth.post("/resend-verification-code")
@is_not_logged_in
@rate_limit
# @has_cookies(["code_details"])
async def resend_verification_code(request: Request):
    """
    This route is used to resend the verification code to the user's email.
    """
    code_details = request.cookies.get("code_details", None)
    if not code_details:
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "No Code Details Cookie Provided for Resending Verification Code.",
            {},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "No verification request in progress or expired. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    try:
        code_details = json.loads(code_details)
    except json.JSONDecodeError:
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "Invalid Code Details Cookie Provided for Resending Verification Code.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    code = code_details.get("code", None)
    if not code:
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "No Code in Code Details Cookie Provided for Resending Verification Code.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    if len(code) != 6 or not code.isdigit():
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "Invalid Code in Code Details Cookie Provided for Resending Verification Code.",
            {"code": code},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    can_resend_after = code_details.get("can_resend_after", None)
    if not can_resend_after:
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "Incomplete Code Details Cookie Provided for Resending Verification Code.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    try:
        can_resend_after_date = datetime.fromisoformat(can_resend_after).replace(
            tzinfo=cairo_tz
        )
    except ValueError:
        await log(
            request,
            "Resend",
            "Verification Code",
            400,
            "warning",
            "Invalid Date Format in Code Details Cookie for Resending Verification Code.",
            {"can_resend_after": can_resend_after},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    if can_resend_after_date > datetime.now(cairo_tz):
        await log(
            request,
            "Resend",
            "Verification Code",
            429,
            "warning",
            "User Tried to Resend Verification Code Before Allowed Time.",
            {"code": code, "can_resend_after": can_resend_after},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": f"You can resend the code after "
                f"{math.ceil((can_resend_after_date - datetime.now(cairo_tz)).total_seconds())} seconds.",
            },
            429,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            token_db = (
                await session.execute(
                    Select(Token).where(
                        Token.token == code, Token.expire_at > datetime.now()
                    )
                )
            ).scalar_one_or_none()
            if not token_db or not token_db.details:
                await log(
                    request,
                    "Resend",
                    "Verification Code",
                    400,
                    "warning",
                    "Invalid or Expired Code in Code Details Cookie for Resending Verification Code.",
                    {"code_details": code_details},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "No verification request in progress or expired. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            payload = jwt.decode(
                token_db.details,
                os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            user = payload.get("user")
            if not user:
                await log(
                    request,
                    "Resend",
                    "Verification Code",
                    400,
                    "warning",
                    "Invalid User Data in Code Details Cookie for Resending Verification Code.",
                    {"code_details": code_details},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid verification request. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            email = user.get("email")
            name = user.get("name")
            if not email or not name:
                await log(
                    request,
                    "Resend",
                    "Verification Code",
                    400,
                    "warning",
                    "Incomplete User Data in Code Details Cookie for Resending Verification Code.",
                    {"user": user},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid verification request. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            email_sent = await send_email(
                request,
                email,
                "verify_email",
                {
                    "name": name,
                    # 'link': 'https://' + request.url.hostname + f"/verify-email?token={token}",
                    "code": code,
                },
            )
            if email_sent.status_code != 200:
                await log(
                    request,
                    "Resend",
                    "Verification Code",
                    500,
                    "error",
                    "An Error Occurred while Resending Verification Code Email.",
                    {"email": email},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An Error Occurred. Please try again later.",
                    },
                    500,
                )
                return finalize_request(response)
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Verification code resent successfully. Please check your email.",
                },
                200,
            )
            code_details["can_resend_after"] = (
                datetime.now(cairo_tz) + timedelta(minutes=1)
            ).isoformat()
            response.set_cookie(
                key="code_details",
                value=json.dumps(code_details),
                httponly=True,
                secure=True,
                samesite="lax",
                max_age=user_token_expire_time * 60,  # in seconds
                path="/",
            )
            await log(
                request,
                "Resend",
                "Verification Code",
                200,
                "info",
                "Verification code resent successfully.",
                {"email": email},
            )
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(
                request,
                "Resend",
                "Verification Code",
                400,
                "warning",
                "Expired Code in Code Details Cookie for Resending Verification Code.",
                {"error": str(e), "code_details": code_details},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Expired verification request. Please sign up again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(
                request,
                "Resend",
                "Verification Code",
                400,
                "warning",
                "Invalid Code in Code Details Cookie for Resending Verification Code.",
                {"error": str(e), "code_details": code_details},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid verification request. Please sign up again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Resend",
                "Verification Code",
                500,
                "error",
                "An error occurred while resending verification code.",
                {"error": str(e), "code_details": code_details},
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An Error Occurred. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


@auth.get("/get-verification-details")
@is_not_logged_in
@rate_limit
# @has_cookies(["code_details"])
async def get_verification_details(request: Request):
    """
    This route is used to get the verification details of the user.
    """
    code_details = request.cookies.get("code_details", None)
    if not code_details:
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "No Code Details Cookie Provided for Geting Verification Details.",
            {},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "No verification request in progress or expired. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    try:
        code_details = json.loads(code_details)
    except json.JSONDecodeError:
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "Invalid Code Details Cookie Provided for Geting Verification Details.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    code = code_details.get("code", None)
    if not code:
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "No Code in Code Details Cookie Provided for Geting Verification Details.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    if len(code) != 6 or not code.isdigit():
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "Invalid Code in Code Details Cookie Provided for Geting Verification Details.",
            {"code": code},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    can_resend_after = code_details.get("can_resend_after", None)
    if not can_resend_after:
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "Incomplete Code Details Cookie Provided for Geting Verification Details.",
            {"code_details": code_details},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    try:
        can_resend_after_date = datetime.fromisoformat(can_resend_after).replace(
            tzinfo=cairo_tz
        )
    except ValueError:
        await log(
            request,
            "Get",
            "Verification Details",
            400,
            "warning",
            "Invalid Date Format in Code Details Cookie for Geting Verification Details.",
            {"can_resend_after": can_resend_after},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid verification request. Please sign up again.",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            token_db = (
                await session.execute(
                    Select(Token).where(
                        Token.token == code, Token.expire_at > datetime.now(utc_tz)
                    )
                )
            ).scalar_one_or_none()
            if not token_db or not token_db.details:
                await log(
                    request,
                    "Get",
                    "Verification Details",
                    400,
                    "warning",
                    "Invalid or Expired Code in Code Details Cookie for Geting Verification Details.",
                    {"code_details": code_details},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "No verification request in progress or expired. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            payload = jwt.decode(
                token_db.details,
                os.environ.get("USER_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            user = payload.get("user")
            if not user:
                await log(
                    request,
                    "Get",
                    "Verification Details",
                    400,
                    "warning",
                    "Invalid User Data in Code Details Cookie for Geting Verification Details.",
                    {"code_details": code_details},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid verification request. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            email = user.get("email")
            name = user.get("name")
            if not email or not name:
                await log(
                    request,
                    "Get",
                    "Verification Details",
                    400,
                    "warning",
                    "Incomplete User Data in Code Details Cookie for Geting Verification Details.",
                    {"user": user},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid verification request. Please sign up again.",
                    },
                    400,
                )
                return finalize_request(response)
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Verification details fetched successfully.",
                    "data": {
                        "email": email,
                        "name": name,
                        "can_resend_after": (
                            math.ceil(
                                (
                                    can_resend_after_date - datetime.now(cairo_tz)
                                ).total_seconds()
                            )
                            if can_resend_after_date > datetime.now(cairo_tz)
                            else 0
                        ),
                    },
                },
                200,
            )
            await log(
                request,
                "Get",
                "Verification Details",
                200,
                "info",
                "Verification details fetched successfully.",
                {"email": email},
            )
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(
                request,
                "Get",
                "Verification Details",
                400,
                "warning",
                "Expired Code in Code Details Cookie for Getting Verification Details.",
                {"error": str(e), "code_details": code_details},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Expired verification request. Please sign up again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(
                request,
                "Get",
                "Verification Details",
                400,
                "warning",
                "Invalid Code in Code Details Cookie for Getting Verification Details.",
                {"error": str(e), "code_details": code_details},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid verification request. Please sign up again.",
                },
                400,
            )
            await session.rollback()
            response.delete_cookie("code_details", path="/")
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Get",
                "Verification Details",
                500,
                "error",
                "An error occurred while getting verification details.",
                {"error": str(e), "code_details": code_details},
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An Error Occurred. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


@auth.post("/get-google-stored-token")
@is_not_logged_in
@rate_limit
async def get_google_stored_token(request: Request):
    """
    This route is used to get stored google access token from the session.
    It is used to check if the user is already logged in.
    """
    data = await request.json()
    if not data:
        await log(
            request,
            "Get",
            "Google Access Token",
            400,
            "warning",
            "No Data Provided in The Request Cookies.",
            {},
        )
        response = JSONResponse({"status": "error", "message": "No data provided"}, 400)
        return finalize_request(response)
    google_details_token = data.get("google_details_token", None)
    oauth_state = data.get("oauth_state", None)
    if not oauth_state:
        await log(
            request,
            "Get",
            "Google Access Token",
            400,
            "warning",
            "No OAuth State Provided in the Request Headers.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "MisMatched OAuth State. Please try again."},
            400,
        )
        return finalize_request(response)
    if not google_details_token:
        await log(
            request,
            "Get",
            "Google Access Token",
            401,
            "warning",
            "UnAuthorized User Tried to Get Google Access Token.",
            {},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "You Must Authorize Google Account to Proceed.",
            },
            401,
        )
        return finalize_request(response)
    if not is_sanitized(google_details_token) or not is_sanitized(oauth_state):
        await log(
            request,
            "Get",
            "Google Access Token",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Cookies.",
            {"google_details_token": google_details_token, "oauth_state": oauth_state},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            state_token = (
                await session.execute(
                    Select(Token).where(
                        Token.token == oauth_state,
                        Token.expire_at > datetime.now(utc_tz),
                    )
                )
            ).scalar_one_or_none()
            if not state_token or not state_token.details:
                await log(
                    request,
                    "Get",
                    "Google Access Token",
                    401,
                    "warning",
                    "UnAuthorized User Tried to Get Google Access Token.",
                    {},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You Must Authorize Google Account to Proceed.",
                    },
                    401,
                )
                return finalize_request(response)
            for key, value in state_token.details.get("session").items():
                request.session[key] = value
            for key, value in state_token.details.get("cookies").items():
                request.cookies[key] = value
            token = (
                await session.execute(
                    Select(Token).where(
                        Token.token == google_details_token,
                        Token.expire_at > datetime.now(utc_tz),
                    )
                )
            ).scalar_one_or_none()
            if not token or not token.details:
                await log(
                    request,
                    "Get",
                    "Google Access Token",
                    401,
                    "warning",
                    "UnAuthorized User Tried to Get Google Access Token.",
                    {},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You Must Authorize Google Account to Proceed.",
                    },
                    401,
                )
                return finalize_request(response)
            google_details = jwt.decode(
                token.details,
                os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                algorithms=["HS256"],
            )
            if not google_details or not google_details.get("google_user_details"):
                await log(
                    request,
                    "Get",
                    "Google Access Token",
                    401,
                    "warning",
                    "UnAuthorized User Tried to Get Google Access Token.",
                    {},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You Must Authorize Google Account to Proceed.",
                    },
                    401,
                )
                return finalize_request(response)
            google_details = google_details.get("google_user_details")
            try:
                # Extract the new access token
                async with AsyncOAuth2Client(
                    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
                    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
                ) as client:
                    new_token = await client.refresh_token(
                        url="https://oauth2.googleapis.com/token",
                        refresh_token=decrypt_data(
                            google_details.get("google_refresh_token")
                        ),
                    )
                access_token = new_token["access_token"]
            except Exception as e:
                await log(
                    request,
                    "Get",
                    "Google Access Token",
                    500,
                    "error",
                    "An Error Occurred while Retrieving Google Access Token.",
                    {"error": str(e)},
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An Error Occurred. Please try again later.",
                    },
                    500,
                )
                return finalize_request(response)
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Google access token retrieved successfully",
                    "data": {
                        "access_token": access_token,
                        "expires_in": new_token[
                            "expires_in"
                        ],  # seconds until expiration
                    },
                }
            )
            await session.commit()
            await log(
                request,
                "Get",
                "Google Access Token",
                200,
                "info",
                "Google Access Token Retrieved Successfully.",
                {
                    "google_id": google_details.get("google_id"),
                    "google_name": google_details.get("google_name"),
                    "google_email": google_details.get("google_email"),
                },
            )
            return finalize_request(response)
        except jwt.ExpiredSignatureError as e:
            await log(
                request,
                "Get",
                "Google Access Token",
                401,
                "warning",
                "Expired OAuth State Provided in the Request Headers.",
                {"error": str(e), "oauth_state": oauth_state},
            )
            response = JSONResponse(
                {"status": "error", "message": "Session Expired. Please try again."},
                401,
            )
            await session.rollback()
            return finalize_request(response)
        except jwt.InvalidTokenError as e:
            await log(
                request,
                "Get",
                "Google Access Token",
                401,
                "warning",
                "Invalid OAuth State Provided in the Request Headers.",
                {"error": str(e), "oauth_state": oauth_state},
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "MisMatched OAuth State. Please try again.",
                },
                401,
            )
            await session.rollback()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Get",
                "Google Access Token",
                500,
                "error",
                "An error occurred while getting google stored token.",
                {"error": str(e)},
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred. Please try again."},
                500,
            )
            return finalize_request(response)


@auth.get("/get-google-access-token")
@is_logged_in
@rate_limit
async def get_google_access_token(request: Request):
    """
    This route is used to get the Google access token for the user.
    It is used to access Google Drive and other Google services.
    """
    current_user = request.state.current_user
    try:
        async with AsyncOAuth2Client(
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
        ) as client:
            new_token = await client.refresh_token(
                url="https://oauth2.googleapis.com/token",
                refresh_token=decrypt_data(current_user.google_refresh_token),
            )
        access_token = new_token["access_token"]
        async with async_session() as session:
            if "refresh_token" in new_token:
                current_user.google_refresh_token = encrypt_data(
                    new_token["refresh_token"]
                )
                await session.commit()
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Google access token retrieved successfully",
                    "data": {
                        "access_token": access_token,
                        "expires_in": new_token[
                            "expires_in"
                        ],  # seconds until expiration
                    },
                },
                200,
            )
            await log(
                request,
                "Get",
                "Google Access Token",
                200,
                "info",
                "Google Access Token Retrieved Successfully.",
                {
                    "google_id": current_user.google_id,
                    "google_name": current_user.google_name,
                    "google_email": current_user.google_email,
                },
                current_user.id,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Google Access Token",
            500,
            "error",
            "An Error Occurred while Retrieving Google Access Token.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An Error Occurred. Please try again later.",
            },
            500,
        )
        return finalize_request(response)


@auth.get("/is-logged-in")
@is_logged_in
async def is_logged_in_route(request: Request):
    response = JSONResponse(
        {
            "status": "success",
            "message": "User is logged in.",
        },
        200,
    )
    return finalize_request(response)


@app.get("/login-with-google")
@is_not_logged_in_web
@rate_limit
async def login_with_google(request: Request):
    try:
        is_localhost = request.query_params.get("localhost", "false").lower() == "true"
        redirect_response_url = (
            "https://" + request.url.hostname + "/google-authentication-redirect"
        )
        if is_localhost:
            redirect_response_url += "?localhost=true"
        google_client = oauth.create_client("google")
        state = await generate_unique_token(40)
        nonce = await generate_unique_token(40)
        state_token = Token(
            token=state,
            details={
                "nonce": nonce,
            },
            is_valid=True,
            expire_at=datetime.now(utc_tz) + timedelta(days=stored_state_expire_time),
            type=2,  # 2 for Google OAuth state token
        )
        async with async_session() as session:
            session.add(state_token)
            await session.commit()
        await log(
            request,
            "Login",
            "User",
            200,
            "info",
            "Redirecting user to Google for authentication.",
            {"redirect_response_url": redirect_response_url},
        )
        return await google_client.authorize_redirect(
            request, redirect_response_url, state=state, nonce=nonce
        )
    except Exception as e:
        await log(
            request,
            "Login",
            "User",
            500,
            "error",
            "An error occurred while redirecting to Google for authentication.",
            {"error": str(e)},
        )
        response = RedirectResponse(f"{os.environ.get('FRONTEND_URL')}/login")
        response.set_cookie(
            key="error",
            value="An Error Occurred While Trying to Login with Google. Please Try Again Later.",
            httponly=False,
            secure=True,
            samesite="lax",
            path="/",  # Cookie is valid for the entire site
        )
        return finalize_request(response)


@app.get("/google-authentication-redirect")
@is_not_logged_in_web
@rate_limit
async def google_authentication_redirect_response(request: Request):
    try:
        return_url = os.environ.get("FRONTEND_URL")
        if request.query_params.get("localhost", "false").lower() == "true":
            return_url = os.environ.get("FRONTEND_URL_LOCALHOST")
        authentication_type = os.environ.get("AUTHENTICATION")
        requested_scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            # 'https://www.googleapis.com/auth/drive',
            "https://www.googleapis.com/auth/drive.file",
            # 'https://www.googleapis.com/auth/drive.metadata'
        ]
        details = {
            "cookies": {k: v for k, v in request.cookies.items()},
            "session": {k: v for k, v in request.session.items()},
        }
        oauth_state = request.query_params.get("state")
        async with async_session() as session:
            await session.begin()
            try:
                state_token = (
                    await session.execute(
                        Select(Token).where(
                            Token.token == oauth_state,
                            Token.expire_at > datetime.now(utc_tz),
                        )
                    )
                ).scalar_one_or_none()
                if not state_token:
                    await log(
                        request,
                        "Login",
                        "User",
                        401,
                        "warning",
                        "UnAuthorized User Tried to Authenticate with Google.",
                        {},
                    )
                    response = RedirectResponse(f"{return_url}/login")
                    response.set_cookie(
                        key="error",
                        value="You Must Authorize Google Account to Proceed.",
                        httponly=False,
                        secure=True,
                        samesite="lax",
                        path="/",  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
                details["nonce"] = state_token.details.get("nonce")
                state_token.details = details
                token = await oauth.google.authorize_access_token(
                    request, nonce=state_token.details.get("nonce")
                )
                granted_scopes = token.get("scope")
                un_granted_scopes = [
                    scope for scope in requested_scopes if scope not in granted_scopes
                ]
                if len(un_granted_scopes) > 0:
                    await log(
                        request,
                        "Login",
                        "User",
                        403,
                        "warning",
                        "Google did not grant the requested scopes.",
                        {
                            "un_granted_scopes": un_granted_scopes,
                            "granted_scopes": granted_scopes,
                        },
                    )
                    await session.rollback()
                    un_granted_scopes_short = ", ".join(
                        scope.replace("https://www.googleapis.com/auth/", "")
                        for scope in (un_granted_scopes)
                    )
                    response = RedirectResponse(f"{return_url}/login")
                    response.set_cookie(
                        key="error",
                        value=f"You Must Allow All the Requested Permissions to Proceed.",
                        httponly=False,
                        secure=True,
                        samesite="lax",
                        path="/",  # Cookie is valid for the entire site
                    )
                    return finalize_request(response)
                user = token["userinfo"]
                google_user_details = {
                    "google_id": user.get("sub"),
                    "google_name": user.get("name"),
                    "google_email": user.get("email"),
                    "google_avatar": user.get("picture"),
                    "google_refresh_token": encrypt_data(token.get("refresh_token")),
                }
                user = (
                    await session.execute(
                        Select(User).where(
                            User.google_id == google_user_details.get("google_id")
                        )
                    )
                ).scalar_one_or_none()
                if user:
                    (
                        user.ips.append(request.client.host)
                        if request.client.host not in user.ips
                        else None
                    )
                    # if len(user.ips) > 100:
                    #     await log(request, "Login", "User", 403, 'warning', 'User Tried To Associate More Than 100 IPs to His Account.',
                    #               {'ips': user.ips},
                    #         user.id)
                    #     await session.rollback()
                    #     response = RedirectResponse(f"{return_url}/login")
                    #     response.set_cookie(
                    #         key="error",
                    #         value="You Can\'t Associate More than 100 Devices with Your Account. Please remove one "
                    #               "of your devices from your devices management page and try again.",
                    #         httponly=False,
                    #         secure=True,
                    #         samesite='lax',
                    #         path="/" # Cookie is valid for the entire site
                    #     )
                    #     return finalize_request(response)
                    # user_details = user.details.get("ips", {})
                    # user_agent = request.headers.get('User-Agent', "")
                    # ip = request.client.host
                    # if not user_details.get(ip, None):
                    #     device_details = await get_device_details(ip, user_agent, request)
                    #     user_details[ip] = device_details
                    # user.details["ips"] = user_details
                    user.google_refresh_token = google_user_details.get(
                        "google_refresh_token"
                    )
                    user.google_name = google_user_details.get("google_name")
                    user.google_avatar = google_user_details.get("google_avatar")
                    token = jwt.encode(
                        {
                            "id": user.id,
                            "expire_date": (
                                datetime.now(cairo_tz)
                                + timedelta(minutes=access_token_expire_time)
                            ).isoformat(),
                        },
                        os.environ.get("ACCESS_TOKEN_SECRET_KEY"),
                        algorithm="HS256",
                    )
                    refresh_token = await generate_refresh_token(user.id)
                    if not refresh_token:
                        await log(
                            request,
                            "Login",
                            "User",
                            500,
                            "error",
                            "An error occurred while generating refresh token for user.",
                            {},
                            user.id,
                        )
                        await session.rollback()
                        response = RedirectResponse(f"{return_url}/login")
                        response.set_cookie(
                            key="error",
                            value="An Error Occurred While Logging In. Please Try Again Later.",
                            httponly=False,
                            secure=True,
                            samesite="lax",
                            path="/",  # Cookie is valid for the entire site
                        )
                        return finalize_request(response)
                    if authentication_type == "cookies":
                        response = RedirectResponse(f"{return_url}/user")
                        response.set_cookie(
                            key="access_token_backend",
                            value=token,
                            httponly=True,
                            secure=True,
                            samesite="none",
                            max_age=access_token_expire_time * 60,  # in seconds
                            path="/",  # Cookie is valid for the entire domain
                        )
                        response.set_cookie(
                            key="refresh_token_backend",
                            value=refresh_token,
                            httponly=True,
                            secure=True,
                            samesite="none",
                            max_age=refresh_token_expire_time
                            * 24
                            * 60
                            * 60,  # in seconds
                            path="/",  # Cookie is valid for the entire domain
                        )
                    else:
                        response_payload = {
                            "access_token": token,
                            "access_expires_in": int(
                                timedelta(
                                    minutes=access_token_expire_time
                                ).total_seconds()
                            ),  # seconds until expiration
                            "refresh_token": refresh_token,
                            "refresh_expires_in": int(
                                timedelta(
                                    days=refresh_token_expire_time
                                ).total_seconds()
                            ),  # seconds until expiration
                        }
                        response = RedirectResponse(
                            f"{return_url}/login?token={response_payload.get('access_token')}___"
                            f"{response_payload.get('access_expires_in')}___"
                            f"{response_payload.get('refresh_token')}___{response_payload.get('refresh_expires_in')}"
                        )
                    response.set_cookie(
                        key="success",
                        value="Successfully Logged In to Your Account.",
                        httponly=False,
                        secure=True,
                        samesite="lax",
                        path="/",  # Cookie is valid for the entire site
                    )
                    await session.commit()
                    await log(
                        request,
                        "Login",
                        "User",
                        200,
                        "info",
                        "User logged in successfully using Google.",
                        {"google_id": user.google_id},
                        user.id,
                    )
                    return finalize_request(response)
                new_safe_token = await generate_unique_token(40)
                new_safe_token_db = Token(
                    token=new_safe_token,
                    details=jwt.encode(
                        {
                            "google_user_details": google_user_details,
                            "expire_date": (
                                datetime.now(cairo_tz)
                                + timedelta(minutes=google_token_expire_time)
                            ).isoformat(),
                        },
                        os.environ.get("GOOGLE_TOKEN_SECRET_KEY"),
                        algorithm="HS256",
                    ),
                    is_valid=True,
                    expire_at=datetime.now(utc_tz)
                    + timedelta(minutes=google_token_expire_time),
                    type=0,  # 0 for Google login token
                )
                response = RedirectResponse(
                    f"{return_url}/login-success?state="
                    f"{oauth_state}&token={new_safe_token}___{int(timedelta(minutes=google_token_expire_time).total_seconds())}"
                )
                session.add(new_safe_token_db)
                await session.commit()
                await log(
                    request,
                    "Login",
                    "User",
                    200,
                    "info",
                    "User Authenticated Google Successfully.",
                    {"google_id": google_user_details.get("google_id")},
                )
                return finalize_request(response)
            except Exception as e:
                await log(
                    request,
                    "Login",
                    "User",
                    500,
                    "error",
                    "An Error Occurred while Authenticating with Google.",
                    {"error": str(e)},
                )
                await session.rollback()
                response = RedirectResponse(f"{return_url}/login")
                response.set_cookie(
                    key="error",
                    value="An Error Occurred While Logging In. Please Try Again Later.",
                    httponly=False,
                    secure=True,
                    samesite="lax",
                    path="/",  # Cookie is valid for the entire site
                )
                return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Login",
            "User",
            500,
            "error",
            "An Error Occurred while Authenticating with Google.",
            {"error": str(e)},
        )
        response = RedirectResponse(f"{return_url}/login")
        response.set_cookie(
            key="error",
            value="An Error Occurred While Logging In. Please Try Again Later.",
            httponly=False,
            secure=True,
            samesite="lax",
            path="/",  # Cookie is valid for the entire site
        )
        return finalize_request(response)


# User routes
@user_prefix.get("/data")
@is_logged_in
@rate_limit
async def get_user_data(request: Request):
    current_user = request.state.current_user
    await log(
        request,
        "Get",
        "User",
        200,
        "info",
        "User Data Retrieved Successfully.",
        {},
        current_user.id,
    )
    response = JSONResponse(
        {
            "status": "success",
            "message": "User data retrieved successfully",
            "data": current_user.to_dict(),
        },
        200,
    )
    return finalize_request(response)


@user_prefix.get("/permissions")
@is_logged_in
@rate_limit
async def get_user_permissions(request: Request):
    """
    This route is used to get the permissions of the current user.
    It will return the permissions based on the user's role.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (
                await session.execute(
                    Select(User)
                    .where(User.id == current_user.id)
                    .options(selectinload(User.role).selectinload(Role.exact_roles))
                )
            ).scalar_one_or_none()
            if not user or not user.role:
                await log(
                    request,
                    "Get",
                    "Permissions",
                    404,
                    "warning",
                    "User Not Found or User Role Not Assigned.",
                    {"user_id": current_user.id},
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "User not found or user role not assigned",
                    },
                    404,
                )
                return finalize_request(response)
            permissions = user.role.exact_roles if user.role else []
            await log(
                request,
                "Get",
                "Permissions",
                200,
                "info",
                "User Permissions Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "User permissions retrieved successfully",
                    "data": [permission.name for permission in permissions],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Permissions",
            500,
            "error",
            "An error occurred while getting user permissions.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving user permissions",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.post("/has-permissions")
@is_logged_in
@rate_limit
async def user_has_permissions(request: Request):
    """
    This route is used to check if user has some permissions.
    It will return boolean based on the user's role.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (
                await session.execute(
                    Select(User)
                    .where(User.id == current_user.id)
                    .options(selectinload(User.role).selectinload(Role.exact_roles))
                )
            ).scalar_one_or_none()
            if not user or not user.role:
                await log(
                    request,
                    "Verify",
                    "Permissions",
                    404,
                    "warning",
                    "User Not Found or User Role Not Assigned.",
                    {"user_id": current_user.id},
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "User not found or user role not assigned",
                    },
                    404,
                )
                return finalize_request(response)
            permissions = user.role.exact_roles if user.role else []
            data = await request.json()
            if not is_sanitized(data):
                await log(
                    request,
                    "Verify",
                    "Permissions",
                    400,
                    "warning",
                    "Un Sanitized Data Provided in The Request Body.",
                    {},
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid data provided"}, 400
                )
                return finalize_request(response)
            required_permissions = data.get("permissions", [])
            is_and = data.get("is_and", True)
            if not required_permissions:
                await log(
                    request,
                    "Verify",
                    "Permissions",
                    400,
                    "warning",
                    "No Permissions Provided for Checking.",
                    {},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "No permissions provided"}, 400
                )
                return finalize_request(response)
            if is_and:
                has_permissions = all(
                    permission in [p.name for p in permissions]
                    for permission in required_permissions
                )
            else:
                has_permissions = any(
                    permission in [p.name for p in permissions]
                    for permission in required_permissions
                )
            if not has_permissions:
                await log(
                    request,
                    "Verify",
                    "Permissions",
                    403,
                    "warning",
                    "User Does Not Have Required Permissions.",
                    {},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "User does not have the required permissions",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Verify",
                "Permissions",
                200,
                "info",
                "User has Required Permissions.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "User has the required permissions",
                    "data": has_permissions,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Verify",
            "Permissions",
            500,
            "error",
            "An error occurred while checking user permissions.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while checking user permissions",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/change-google-account")
@is_logged_in
@rate_limit
async def change_google_account(request: Request):
    """
    This route is used to change the Google account associated with the user.
    :param request:
    :return:
    """
    # To be Done in V2
    response = JSONResponse(
        {
            "status": "error",
            "message": "This feature is not available yet. Coming Soon!",
        },
        501,
    )
    return finalize_request(response)


@user_prefix.patch("/")
@is_logged_in
@rate_limit
async def update_user_data(request: Request):
    """
    This route is used to update the user data.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    avatar = current_user.details.get("avatar", current_user.google_avatar)
    existing_avatar_uploaded = current_user.details.get("avatar", None)
    data = await request.json()
    if not data:
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "No Data Provided for Updating User Data.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", current_user.name).strip()
    url = data.get("url", avatar).strip()
    if not name or name == "":
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "No Name Provided for Updating User Data.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Name cannot be empty"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            file = (
                await get_file_from_drive(
                    url, current_user.google_refresh_token, request
                )
                if url and url != avatar
                else None
            )
            if url and url != avatar:
                if not file:
                    await log(
                        request,
                        "Update",
                        "User",
                        400,
                        "warning",
                        "Invalid Avatar URL Provided for Updating User Data.",
                        {"url": url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Invalid Image provided. Please provide a valid Img.",
                        },
                        400,
                    )
                    return finalize_request(response)
                if not verify_file_type(file.get("mimeType", ""), "image"):
                    await log(
                        request,
                        "Update",
                        "User",
                        400,
                        "warning",
                        "Invalid Avatar File Type Provided for Updating User Data.",
                        {"file_type": file.get("mimeType", ""), "url": url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Invalid Image Type. Please provide a valid Img.",
                        },
                        400,
                    )
                    return finalize_request(response)
            current_user = await session.merge(current_user)
            if existing_avatar_uploaded and is_drive_url(existing_avatar_uploaded):
                removed = await remove_file_from_drive(
                    existing_avatar_uploaded, current_user.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Update",
                        "User",
                        500,
                        "error",
                        "An Error Occurred While Removing Old Avatar from Google Drive.",
                        {"old_avatar": existing_avatar_uploaded},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "An Error Occurred While Updating Your Avatar. Please Try Again Later.",
                        },
                        500,
                    )
                    return finalize_request(response)
            current_user.name = name
            current_user.details["avatar"] = url
            await session.flush()
            await log(
                request,
                "Update",
                "User",
                200,
                "info",
                "User Data Updated Successfully.",
                {"updated_data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "User data updated successfully",
                    "data": current_user.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Update",
                "User",
                500,
                "error",
                "An error occurred while updating user data.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating user data",
                },
                500,
            )
            return finalize_request(response)


@user_prefix.patch("/academic-data")
@is_logged_in
@rate_limit
async def update_user_academic_data(request: Request):
    """
    This route is used to update the user academic data.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    if (
        current_user.faculty_id is not None
        or current_user.department_id is not None
        or current_user.year_id is not None
        or current_user.type is not None
        and current_user.type != ""
    ):
        await log(
            request,
            "Update",
            "User",
            403,
            "warning",
            "User Tried to Update Academic Data Again.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "You have already set your academic data. You cannot change it again.",
            },
            403,
        )
        return finalize_request(response)
    data = await request.json()
    if not data:
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "No Data Provided for Updating User Academic Data.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    faculty_id = data.get("faculty_id", None)
    department_id = data.get("department_id", None)
    year_id = data.get("year_id", None)
    study_type = data.get("study_type", "").strip()
    if (
        not faculty_id
        or not is_int(faculty_id)
        or int(faculty_id) < 1
        or not department_id
        or not is_int(department_id)
        or int(department_id) < 1
        or not year_id
        or not is_int(year_id)
        or int(year_id) < 1
        or not study_type
        or study_type == ""
    ):
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "Incomplete Data Provided for Updating User Academic Data.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Faculty, Department, Year and Study Type are required",
            },
            400,
        )
        return finalize_request(response)
    faculty_id = int(faculty_id)
    department_id = int(department_id)
    year_id = int(year_id)
    if study_type not in ["Mainstream", "Credit"]:
        await log(
            request,
            "Update",
            "User",
            400,
            "warning",
            "Invalid Study Type Provided for Updating User Academic Data.",
            {"study_type": study_type},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid Study Type. It should be either 'Mainstream' or 'Credit'",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (
                await session.execute(Select(Faculty).where(Faculty.id == faculty_id))
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Update",
                    "User",
                    404,
                    "warning",
                    "Faculty Not Found for Updating User Academic Data.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == department_id)
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Update",
                    "User",
                    404,
                    "warning",
                    "Department Not Found for Updating User Academic Data.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(
                    request,
                    "Update",
                    "User",
                    400,
                    "warning",
                    "Department Does Not Belong to the Given Faculty for Updating User Academic Data.",
                    {"faculty_id": faculty_id, "department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department does not belong to the given faculty",
                    },
                    400,
                )
                return finalize_request(response)
            if department.study_type.lower() != study_type.lower():
                await log(
                    request,
                    "Update",
                    "User",
                    400,
                    "warning",
                    "Study Type Does Not Match the Given Department for Updating User Academic Data.",
                    {
                        "department_id": department_id,
                        "department_study_type": department.study_type,
                        "provided_study_type": study_type,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": f"Study Type does not match the given department.",
                    },
                    400,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == year_id))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Update",
                    "User",
                    404,
                    "warning",
                    "Year Not Found for Updating User Academic Data.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            current_user = await session.merge(current_user)
            current_user.faculty_id = faculty.id
            current_user.department_id = department.id
            current_user.year_id = year.id
            current_user.type = study_type
            await session.flush()
            await log(
                request,
                "Update",
                "User",
                200,
                "info",
                "User Academic Data Updated Successfully.",
                {"updated_data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "User academic data updated successfully",
                    "data": current_user.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Update",
                "User",
                500,
                "error",
                "An error occurred while updating user academic data.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating user academic data",
                },
                500,
            )
            return finalize_request(response)


@user_prefix.get("/courses/enrolled")
@is_logged_in
@rate_limit
@is_ready
async def get_enrolled_courses(request: Request):
    """
    This route is used to get the courses the user is enrolled in.
    :param request:
    :return:
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            courses = (
                (
                    await session.execute(
                        Select(Subject)
                        .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                        .where(UserSubjectLink.user_id == current_user.id)
                        .options(
                            selectinload(Subject.department),
                            selectinload(Subject.year),
                            selectinload(Subject.faculty),
                        )
                        .order_by(Subject.name)
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Courses",
                200,
                "info",
                "User Enrolled Courses Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Enrolled courses retrieved successfully",
                    "data": [course.user_to_dict() for course in courses],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Courses",
            500,
            "error",
            "An error occurred while getting enrolled courses.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving enrolled courses",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/courses/enrolled/{course_id}")
@is_logged_in
@rate_limit
@is_ready
async def get_enrolled_course(request: Request, course_id: int):
    """
    This route is used to get an enrolled course of the user.
    :param request:
    :return:
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course = (
                await session.execute(
                    Select(Subject)
                    .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                    .where(
                        UserSubjectLink.user_id == current_user.id,
                        Subject.id == course_id,
                    )
                    .options(
                        selectinload(Subject.department),
                        selectinload(Subject.year),
                        selectinload(Subject.faculty),
                    )
                    .order_by(Subject.name)
                )
            ).scalar_one_or_none()
            if not course:
                await log(
                    request,
                    "Get",
                    "Course",
                    404,
                    "warning",
                    "Enrolled Course Not Found for User.",
                    {"course_id": course_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Enrolled course not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Course",
                200,
                "info",
                "User Enrolled Course Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Enrolled course retrieved successfully",
                    "data": course.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Course",
            500,
            "error",
            "An error occurred while getting enrolled course.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving enrolled course",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/courses")
@is_logged_in
@rate_limit
@is_ready
async def get_available_courses(request: Request):
    """
    This route is used to get the courses available for the user to enroll in based on his academic data and that he is not already enrolled in.
    :param request:
    :return:
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Courses",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        async with async_session() as session:
            query = Select(Subject).where(
                Subject.faculty_id == current_user.faculty_id,
                Subject.department_id == current_user.department_id,
                Subject.year_id == current_user.year_id,
            )
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(Subject.name).startswith(query_search),
                        func.lower(Subject.code).startswith(query_search),
                    )
                )
            available_courses = (
                (
                    await session.execute(
                        query.options(
                            selectinload(Subject.department),
                            selectinload(Subject.year),
                            selectinload(Subject.faculty),
                            selectinload(Subject.users),
                        ).order_by(Subject.name)
                    )
                )
                .scalars()
                .all()
            )
            courses = [
                course.user_to_dict()
                for course in available_courses
                if not any(user.id == current_user.id for user in course.users)
            ]
            await log(
                request,
                "Get",
                "Courses",
                200,
                "info",
                "Available Courses for User Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Available courses retrieved successfully",
                    "data": courses,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Courses",
            500,
            "error",
            "An error occurred while getting available courses.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving available courses",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.post("/courses/register")
@is_logged_in
@rate_limit
@is_ready
async def register_course(request: Request):
    """
    This route is used to register the user to a course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Register",
            "Course",
            400,
            "warning",
            "No Data Provided for Course Registration.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Register",
            "Course",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    course_id = data.get("course_id", None)
    if not course_id:
        await log(
            request,
            "Register",
            "Course",
            400,
            "warning",
            "No Course ID Provided for Registration.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Course ID is required"}, 400
        )
        return finalize_request(response)
    if not is_int(course_id) or int(course_id) < 1:
        await log(
            request,
            "Register",
            "Course",
            400,
            "warning",
            "Invalid Course ID Provided for Registration.",
            {"course_id": course_id},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid Course ID provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == course_id)
                    .options(
                        selectinload(Subject.users),
                    )
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Register",
                    "Course",
                    404,
                    "warning",
                    "Course Not Found for Registration.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course not found"}, 404
                )
                return finalize_request(response)
            if (
                subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Register",
                    "Course",
                    400,
                    "warning",
                    "User Tried to Register to a Course Not Belonging to His Academic Data.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You can only register to courses belonging to your academic data",
                    },
                    400,
                )
                return finalize_request(response)
            if current_user in subject.users:
                await log(
                    request,
                    "Register",
                    "Course",
                    400,
                    "warning",
                    "User Tried to Register to a Course He is Already Registered In.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are already registered in this course",
                    },
                    400,
                )
                return finalize_request(response)
            subject.users.append(current_user)
            await session.flush()
            await log(
                request,
                "Register",
                "Course",
                200,
                "info",
                "User Registered to Course Successfully.",
                {"course_id": course_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Registered to course successfully",
                    "data": subject.user_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Register",
                "Course",
                500,
                "error",
                "An error occurred while registering to course.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while registering to course",
                },
                500,
            )
            return finalize_request(response)


@user_prefix.post("/courses/unregister")
@is_logged_in
@rate_limit
@is_ready
async def unregister_course(request: Request):
    """
    This route is used to unregister the user from a course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "UnRegister",
            "Course",
            400,
            "warning",
            "No Data Provided for Course Registration.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "UnRegister",
            "Course",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    course_id = data.get("course_id", None)
    if not course_id:
        await log(
            request,
            "UnRegister",
            "Course",
            400,
            "warning",
            "No Course ID Provided for Registration.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Course ID is required"}, 400
        )
        return finalize_request(response)
    if not is_int(course_id) or int(course_id) < 1:
        await log(
            request,
            "UnRegister",
            "Course",
            400,
            "warning",
            "Invalid Course ID Provided for Registration.",
            {"course_id": course_id},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid Course ID provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == course_id)
                    .options(
                        selectinload(Subject.users),
                        selectinload(Subject.faculty),
                        selectinload(Subject.department),
                        selectinload(Subject.year),
                    )
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "UnRegister",
                    "Course",
                    404,
                    "warning",
                    "Course Not Found for Unregistration.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course not found"}, 404
                )
                return finalize_request(response)
            if not any(user.id == current_user.id for user in subject.users):
                await log(
                    request,
                    "UnRegister",
                    "Course",
                    400,
                    "warning",
                    "User Tried to Unregister from a Course He is Not Registered In.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not registered in this course",
                    },
                    400,
                )
                return finalize_request(response)
            user = [u for u in subject.users if u.id == current_user.id][0]
            subject.users.remove(user)
            await session.flush()
            await log(
                request,
                "UnRegister",
                "Course",
                200,
                "info",
                "User Unregistered from Course Successfully.",
                {"course_id": course_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Unregistered from course successfully",
                    "data": subject.user_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "UnRegister",
                "Course",
                500,
                "error",
                "An error occurred while unregistering from course.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while unregistering from course",
                },
                500,
            )
            return finalize_request(response)


@user_prefix.get("/materials")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_materials(request: Request):
    """
    This route is used to get the materials for the user.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        parent_id = data.get("parent_id", None)  # Parent Material ID for Sub Materials
        if not subject_id:
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "No Subject ID Provided for Getting Materials.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You must choose a subject to fetch its materials.",
                },
                400,
            )
            return finalize_request(response)
        if (
            not is_int(subject_id)
            or int(subject_id) < 1
            or parent_id
            and (not is_int(parent_id) or int(parent_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "Invalid Subject ID or Parent ID Provided for Getting Materials.",
                {"subject_id": subject_id, "parent_id": parent_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        subject_id = int(subject_id) if subject_id else None
        parent_id = int(parent_id) if parent_id else None
        async with async_session() as session:
            subject = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == subject_id)
                    .options(selectinload(Subject.users))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Get",
                    "Materials",
                    404,
                    "warning",
                    "Subject Not Found for Getting Materials.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if not any(user.id == current_user.id for user in subject.users):
                await log(
                    request,
                    "Get",
                    "Materials",
                    403,
                    "warning",
                    "User Tried to Get Materials of a Subject He is Not Enrolled In.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            query = Select(Material).where(Material.subject_id == subject.id)
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Material).where(Material.id == parent_id)
                    )
                ).scalar_one_or_none()
                if (
                    not parent
                    or parent.type != "folder"
                    or parent.subject_id != subject.id
                ):
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Parent Material Not Found or Invalid for Getting Sub Materials.",
                        {"parent_id": parent_id, "subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Parent material not found or invalid",
                        },
                        404,
                    )
                    return finalize_request(response)
            parent_id = int(parent_id) if parent_id else None
            query = query.where(Material.parent_id == parent_id)
            if query_search and query_search != "":
                query = query.where(func.lower(Material.name).contains(query_search))
            sort_order = case(
                (Material.type == "folder", 1),
                (Material.type == "file", 2),
                (Material.type == "drive", 3),
                (Material.type == "youtube", 4),
                (Material.type == "external", 5),
                else_=6,
            )
            materials = (
                (
                    await session.execute(
                        query.options(selectinload(Material.subject)).order_by(
                            sort_order, Material.modified_at.desc()
                        )
                    )
                )
                .scalars()
                .all()
            )
            materials_data = [material.user_to_dict() for material in materials]
            await log(
                request,
                "Get",
                "Materials",
                200,
                "info",
                "Materials for User Retrieved Successfully.",
                {"subject_id": subject_id, "parent_id": parent_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Materials retrieved successfully",
                    "data": materials_data,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Materials",
            500,
            "error",
            "An error occurred while getting materials.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving materials",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/materials/{material_id}/parents")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_material_parents_user(request: Request, material_id: int):
    """
    This route is used to get the parents of a specific material by its ID.
    It will return a list of parent materials.
    """
    try:
        current_user = request.state.current_user
        material = None
        async with async_session() as session:
            material = (
                await session.execute(
                    Select(Material).where(Material.id == material_id)
                )
            ).scalar_one_or_none()
            if not material:
                await log(
                    request,
                    "Get",
                    "Material Parents",
                    404,
                    "warning",
                    "Material Not Found for Fetching Parents.",
                    {"material_id": material_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Material not found"}, 404
                )
                return finalize_request(response)
            parents = await fetch_parents(material.id)
            if not parents or type(parents) != list:
                response = parents
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Material Parents",
                200,
                "info",
                "Material Parents Retrieved Successfully.",
                {"material_id": material_id, "parents": [p["id"] for p in parents]},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material parents retrieved successfully",
                    "data": parents,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Material Parents",
            500,
            "error",
            "An Error Occurred while Getting Material Parents.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting material parents",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/materials/{material_id}")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_material_detail(request: Request, material_id: int):
    """
    This route is used to get the detail of a material for the user.
    """
    try:
        current_user = request.state.current_user
        if not is_int(material_id) or int(material_id) < 1:
            await log(
                request,
                "Get",
                "Material",
                400,
                "warning",
                "Invalid Material ID Provided for Getting Material.",
                {"material_id": material_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            material = (
                await session.execute(
                    Select(Material)
                    .where(Material.id == material_id)
                    .options(selectinload(Material.subject).selectinload(Subject.users))
                )
            ).scalar_one_or_none()
            if not material:
                await log(
                    request,
                    "Get",
                    "Material",
                    404,
                    "warning",
                    "Material Not Found for Getting Material.",
                    {"material_id": material_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Material not found"}, 404
                )
                return finalize_request(response)
            if not any(user.id == current_user.id for user in material.subject.users):
                await log(
                    request,
                    "Get",
                    "Material",
                    403,
                    "warning",
                    "User Tried to Get Material of a Subject He is Not Enrolled In.",
                    {"material_id": material_id, "subject_id": material.subject.id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Material",
                200,
                "info",
                "Material for User Retrieved Successfully.",
                {"material_id": material_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material detail retrieved successfully",
                    "data": material.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Material",
            500,
            "error",
            "An error occurred while getting material detail.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving material detail",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/grades")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_grades(request: Request):
    """
    This route is used to get the grades for the user.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        parent_id = data.get("parent_id", None)  # Parent Grade ID for Sub Grades
        if not subject_id:
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "No Subject ID Provided for Getting Grades.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You must choose a subject to fetch its grades.",
                },
                400,
            )
            return finalize_request(response)
        if (
            not is_int(subject_id)
            or int(subject_id) < 1
            or parent_id
            and (not is_int(parent_id) or int(parent_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "Invalid Subject ID or Parent ID Provided for Getting Grades.",
                {"subject_id": subject_id, "parent_id": parent_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        subject_id = int(subject_id) if subject_id else None
        parent_id = int(parent_id) if parent_id else None
        async with async_session() as session:
            subject = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == subject_id)
                    .options(selectinload(Subject.users))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Get",
                    "Grades",
                    404,
                    "warning",
                    "Subject Not Found for Getting Grades.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if not any(user.id == current_user.id for user in subject.users):
                await log(
                    request,
                    "Get",
                    "Grades",
                    403,
                    "warning",
                    "User Tried to Get Grades of a Subject He is Not Enrolled In.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            query = Select(Grade).where(Grade.subject_id == subject.id)
            if parent_id:
                parent = (
                    await session.execute(Select(Grade).where(Grade.id == parent_id))
                ).scalar_one_or_none()
                if (
                    not parent
                    or parent.type != "folder"
                    or parent.subject_id != subject.id
                ):
                    await log(
                        request,
                        "Get",
                        "Grades",
                        404,
                        "warning",
                        "Parent Grade Not Found or Invalid for Getting Sub Grades.",
                        {"parent_id": parent_id, "subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Parent grade not found or invalid",
                        },
                        404,
                    )
                    return finalize_request(response)
            parent_id = int(parent_id) if parent_id else None
            query = query.where(Grade.parent_id == parent_id)
            if query_search and query_search != "":
                query = query.where(func.lower(Grade.name).contains(query_search))
            sort_order = case(
                (Grade.type == "folder", 1),
                (Grade.type == "file", 2),
                (Grade.type == "drive", 3),
                (Grade.type == "youtube", 4),
                (Grade.type == "external", 5),
                else_=6,
            )
            grades = (
                (
                    await session.execute(
                        query.options(selectinload(Grade.subject)).order_by(
                            sort_order, Grade.modified_at.desc()
                        )
                    )
                )
                .scalars()
                .all()
            )
            grades_data = [grade.user_to_dict() for grade in grades]
            await log(
                request,
                "Get",
                "Grades",
                200,
                "info",
                "Grades for User Retrieved Successfully.",
                {"subject_id": subject_id, "parent_id": parent_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grades retrieved successfully",
                    "data": grades_data,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grades",
            500,
            "error",
            "An error occurred while getting grades.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving grades"},
            500,
        )
        return finalize_request(response)


@user_prefix.get("/grades/{grade_id}/parents")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_grade_parents_user(request: Request, grade_id: int):
    """
    This route is used to get the parents of a specific grade by its ID.
    It will return a list of parent grades.
    """
    try:
        current_user = request.state.current_user
        grade = None
        async with async_session() as session:
            grade = (
                await session.execute(Select(Grade).where(Grade.id == grade_id))
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Get",
                    "Grade Parents",
                    404,
                    "warning",
                    "Grade Not Found for Fetching Parents.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            parents = await fetch_parents(grade.id)
            if not parents or type(parents) != list:
                response = parents
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Grade Parents",
                200,
                "info",
                "Grade Parents Retrieved Successfully.",
                {"grade_id": grade_id, "parents": [p["id"] for p in parents]},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade parents retrieved successfully",
                    "data": parents,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grade Parents",
            500,
            "error",
            "An Error Occurred while Getting Grade Parents.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting grade parents",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/grades/{grade_id}")
@is_logged_in
@rate_limit
@is_ready
async def get_grade_detail(request: Request, grade_id: int):
    """
    This route is used to get the detail of a grade for the user.
    """
    try:
        current_user = request.state.current_user
        if not is_int(grade_id) or int(grade_id) < 1:
            await log(
                request,
                "Get",
                "Grade",
                400,
                "warning",
                "Invalid Grade ID Provided for Getting Grade.",
                {"grade_id": grade_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            grade = (
                await session.execute(
                    Select(Grade)
                    .where(Grade.id == grade_id)
                    .options(selectinload(Grade.subject).selectinload(Subject.users))
                )
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Get",
                    "Grade",
                    404,
                    "warning",
                    "Grade Not Found for Getting Grade.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            if not any(user.id == current_user.id for user in grade.subject.users):
                await log(
                    request,
                    "Get",
                    "Grade",
                    403,
                    "warning",
                    "User Tried to Get Grade of a Subject He is Not Enrolled In.",
                    {"grade_id": grade_id, "subject_id": grade.subject.id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Grade",
                200,
                "info",
                "Grade for User Retrieved Successfully.",
                {"grade_id": grade_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade detail retrieved successfully",
                    "data": grade.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grade",
            500,
            "error",
            "An error occurred while getting grade detail.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving grade detail",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/tasks")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_tasks_user(request: Request):
    """
    This route is used to get the tasks for the user.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Tasks",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        start_date = data.get("start_date", None)  # Start Date
        end_date = data.get("end_date", None)  # End Date
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        if start_date and start_date != "":
            try:
                start_date_obj = (
                    convert_to_utc(datetime.strptime(start_date, "%Y-%m-%d"))
                    if start_date
                    else None
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid Start Date Provided for Getting Tasks.",
                    {"start_date": start_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid start date."}, 400
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = (
                    convert_to_utc(datetime.strptime(end_date, "%Y-%m-%d"))
                    if end_date
                    else None
                )
                if end_date_obj:
                    end_date_obj = end_date_obj + timedelta(days=1, seconds=-1)
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid End Date Provided for Getting Tasks.",
                    {"end_date": end_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid end date."}, 400
                )
                return finalize_request(response)
        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            await log(
                request,
                "Get",
                "Tasks",
                400,
                "warning",
                "Start Date is Greater than End Date for Getting Tasks.",
                {"start_date": start_date, "end_date": end_date},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Start date cannot be greater than end date.",
                },
                400,
            )
            return finalize_request(response)
        if subject_id and (not is_int(subject_id) or int(subject_id) < 1):
            await log(
                request,
                "Get",
                "Tasks",
                400,
                "warning",
                "Invalid Subject ID Provided for Getting Tasks.",
                {"subject_id": subject_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        subject_id = int(subject_id) if subject_id else None
        async with async_session() as session:
            query = (
                Select(Task)
                .where(
                    Task.type != "exam",
                    Task.faculty_id == current_user.faculty_id,
                    Task.department_id == current_user.department_id,
                    Task.year_id == current_user.year_id,
                )
                .options(
                    selectinload(Task.subject),
                    selectinload(Task.author),
                )
                .join(UserSubjectLink, UserSubjectLink.subject_id == Task.subject_id)
                .where(UserSubjectLink.user_id == current_user.id)
            )
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject)
                        .where(Subject.id == subject_id)
                        .options(selectinload(Subject.users))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Subject Not Found for Getting Tasks.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                if not any(u.id == current_user.id for u in subject.users):
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        403,
                        "warning",
                        "User Tried to Get Tasks of a Subject He is Not Enrolled In.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You are not enrolled in this subject",
                        },
                        403,
                    )
                    return finalize_request(response)
                query = query.where(Task.subject_id == subject.id)
            if start_date_obj:
                query = query.where(Task.deadline >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.deadline <= end_date_obj)
            if query_search and query_search != "":
                query = query.where(func.lower(Task.name).contains(query_search))
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Limit Out of Range for Getting Tasks.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Limit must be between 1 and 100."},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(
                            (Task.deadline >= func.now()).desc(), Task.deadline.asc()
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Page Number Out of Range for Getting Tasks.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Invalid page number."}, 400
                )
                return finalize_request(response)
            tasks = result[:limit]
            await log(
                request,
                "Get",
                "Tasks",
                200,
                "info",
                "Tasks for User Retrieved Successfully.",
                {
                    "subject_id": subject_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": page,
                    "limit": limit,
                    "start_date_obj": (
                        start_date_obj.isoformat() if start_date_obj else None
                    ),
                    "end_date_obj": end_date_obj.isoformat() if end_date_obj else None,
                },
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Tasks retrieved successfully",
                    "data": [task.user_to_dict() for task in tasks],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Tasks",
            500,
            "error",
            "An error occurred while getting tasks.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving tasks"},
            500,
        )
        return finalize_request(response)


@user_prefix.get("/tasks/{task_id}")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_task_detail(request: Request, task_id: int):
    """
    This route is used to get the detail of a task for the user.
    """
    try:
        current_user = request.state.current_user
        if not is_int(task_id) or int(task_id) < 1:
            await log(
                request,
                "Get",
                "Task",
                400,
                "warning",
                "Invalid Task ID Provided for Getting Task.",
                {"task_id": task_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            task = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == task_id)
                    .options(
                        selectinload(Task.subject).selectinload(Subject.users),
                        selectinload(Task.author),
                    )
                )
            ).scalar_one_or_none()
            if not task or task.type == "exam":
                await log(
                    request,
                    "Get",
                    "Task",
                    404,
                    "warning",
                    "Task Not Found for Getting Task.",
                    {"task_id": task_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Task not found"}, 404
                )
                return finalize_request(response)
            if not any(u.id == current_user.id for u in task.subject.users):
                await log(
                    request,
                    "Get",
                    "Task",
                    403,
                    "warning",
                    "User Tried to Get Task of a Subject He is Not Enrolled In.",
                    {"task_id": task_id, "subject_id": task.subject.id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Task",
                200,
                "info",
                "Task for User Retrieved Successfully.",
                {"task_id": task_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Task detail retrieved successfully",
                    "data": task.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Task",
            500,
            "error",
            "An error occurred while getting task detail.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving task detail",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/exams")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_exams_user(request: Request):
    """
    This route is used to get the exams for the user.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Exams",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        start_date = data.get("start_date", None)  # Start Date
        end_date = data.get("end_date", None)  # End Date
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        if start_date and start_date != "":
            try:
                start_date_obj = (
                    convert_to_utc(datetime.strptime(start_date, "%Y-%m-%d"))
                    if start_date
                    else None
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid Start Date Provided for Getting Exams.",
                    {"start_date": start_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid start date."}, 400
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = (
                    convert_to_utc(datetime.strptime(end_date, "%Y-%m-%d"))
                    if end_date
                    else None
                )
                if end_date_obj:
                    end_date_obj = end_date_obj + timedelta(days=1, seconds=-1)
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid End Date Provided for Getting Exams.",
                    {"end_date": end_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid end date."}, 400
                )
                return finalize_request(response)
        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            await log(
                request,
                "Get",
                "Exams",
                400,
                "warning",
                "Start Date is Greater than End Date for Getting Exams.",
                {"start_date": start_date, "end_date": end_date},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Start date cannot be greater than end date.",
                },
                400,
            )
            return finalize_request(response)
        if subject_id and (not is_int(subject_id) or int(subject_id) < 1):
            await log(
                request,
                "Get",
                "Exams",
                400,
                "warning",
                "Invalid Subject ID Provided for Getting Exams.",
                {"subject_id": subject_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        subject_id = int(subject_id) if subject_id else None
        async with async_session() as session:
            query = (
                Select(Task)
                .where(
                    Task.type == "exam",
                    Task.faculty_id == current_user.faculty_id,
                    Task.department_id == current_user.department_id,
                    Task.year_id == current_user.year_id,
                )
                .options(
                    selectinload(Task.subject).selectinload(Subject.users),
                    selectinload(Task.author),
                )
                .join(UserSubjectLink, UserSubjectLink.subject_id == Task.subject_id)
                .where(UserSubjectLink.user_id == current_user.id)
            )
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject)
                        .where(Subject.id == subject_id)
                        .options(selectinload(Subject.users))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Subject Not Found for Getting Exams.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                if not any(u.id == current_user.id for u in subject.users):
                    await log(
                        request,
                        "Get",
                        "Exams",
                        403,
                        "warning",
                        "User Tried to Get Exams of a Subject He is Not Enrolled In.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You are not enrolled in this subject",
                        },
                        403,
                    )
                    return finalize_request(response)
                query = query.where(Task.subject_id == subject.id)
            if start_date_obj:
                query = query.where(Task.deadline >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.deadline <= end_date_obj)
            if query_search and query_search != "":
                query = query.where(func.lower(Task.name).contains(query_search))
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Limit Out of Range for Getting Exams.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Limit must be between 1 and 100."},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(
                            (Task.deadline >= func.now()).desc(), Task.deadline.asc()
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Page Number Out of Range for Getting Exams.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Invalid page number."}, 400
                )
                return finalize_request(response)
            exams = result[:limit]
            await log(
                request,
                "Get",
                "Exams",
                200,
                "info",
                "Exams for User Retrieved Successfully.",
                {
                    "subject_id": subject_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": page,
                    "limit": limit,
                },
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exams retrieved successfully",
                    "data": [exam.user_to_dict() for exam in exams],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Exams",
            500,
            "error",
            "An error occurred while getting exams.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving exams"},
            500,
        )
        return finalize_request(response)


@user_prefix.get("/exams/{exam_id}")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_exam_detail(request: Request, exam_id: int):
    """
    This route is used to get the detail of an exam for the user.
    """
    try:
        current_user = request.state.current_user
        if not is_int(exam_id) or int(exam_id) < 1:
            await log(
                request,
                "Get",
                "Exam",
                400,
                "warning",
                "Invalid Exam ID Provided for Getting Exam.",
                {"exam_id": exam_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            exam = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == exam_id)
                    .options(
                        selectinload(Task.subject).selectinload(Subject.users),
                        selectinload(Task.author),
                    )
                )
            ).scalar_one_or_none()
            if not exam or exam.type != "exam":
                await log(
                    request,
                    "Get",
                    "Exam",
                    404,
                    "warning",
                    "Exam Not Found for Getting Exam.",
                    {"exam_id": exam_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Exam not found"}, 404
                )
                return finalize_request(response)
            if not any(u.id == current_user.id for u in exam.subject.users):
                await log(
                    request,
                    "Get",
                    "Exam",
                    403,
                    "warning",
                    "User Tried to Get Exam of a Subject He is Not Enrolled In.",
                    {"exam_id": exam_id, "subject_id": exam.subject.id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Exam",
                200,
                "info",
                "Exam for User Retrieved Successfully.",
                {"exam_id": exam_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exam detail retrieved successfully",
                    "data": exam.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Exam",
            500,
            "error",
            "An error occurred while getting exam detail.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving exam detail",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/announcements")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_announcements_user(request: Request):
    """
    This route is used to get the announcements for the user.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Announcements",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        start_date = data.get("start_date", None)  # Start Date
        end_date = data.get("end_date", None)  # End Date
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        if start_date and start_date != "":
            try:
                start_date_obj = (
                    convert_to_utc(datetime.strptime(start_date, "%Y-%m-%d"))
                    if start_date
                    else None
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid Start Date Provided for Getting Announcements.",
                    {"start_date": start_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid start date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = (
                    convert_to_utc(datetime.strptime(end_date, "%Y-%m-%d"))
                    if end_date
                    else None
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid End Date Provided for Getting Announcements.",
                    {"end_date": end_date},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid end date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if subject_id and (not is_int(subject_id) or int(subject_id) < 1):
            await log(
                request,
                "Get",
                "Announcements",
                400,
                "warning",
                "Invalid Subject ID Provided for Getting Announcements.",
                {"subject_id": subject_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        subject_id = int(subject_id) if subject_id else None
        async with async_session() as session:
            query = (
                Select(Announcement)
                .where(
                    Announcement.faculty_id == current_user.faculty_id,
                    Announcement.department_id == current_user.department_id,
                    Announcement.year_id == current_user.year_id,
                )
                .options(
                    selectinload(Announcement.subject).selectinload(Subject.users),
                    selectinload(Announcement.author),
                )
                .join(Subject, Announcement.subject_id == Subject.id)
                .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                .where(UserSubjectLink.user_id == current_user.id)
            )
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject)
                        .where(Subject.id == subject_id)
                        .options(selectinload(Subject.users))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Subject Not Found for Getting Announcements.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                if not any(u.id == current_user.id for u in subject.users):
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        403,
                        "warning",
                        "User Tried to Get Announcements of a Subject He is Not Enrolled In.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You are not enrolled in this subject",
                        },
                        403,
                    )
                    return finalize_request(response)
                query = query.where(Announcement.subject_id == subject.id)
            if start_date_obj:
                query = query.where(
                    Announcement.date.isnot(None)
                    & (Announcement.date >= start_date_obj)
                )
            if end_date_obj:
                query = query.where(
                    Announcement.date.isnot(None) & (Announcement.date <= end_date_obj)
                )
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(Announcement.title).contains(query_search),
                        func.lower(Announcement.content).contains(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Limit Out of Range for Getting Announcements.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Limit must be between 1 and 100."},
                    400,
                )
                return finalize_request(response)
            announcement_sort_group = case(
                (Announcement.date.is_(None), 2),
                (Announcement.date >= func.now(), 0),
                else_=1,
            )
            future_announcement_date = case(
                (
                    Announcement.date.is_not(None) & (Announcement.date >= func.now()),
                    Announcement.date,
                ),
                else_=None,
            )
            past_announcement_date = case(
                (
                    Announcement.date.is_not(None) & (Announcement.date < func.now()),
                    Announcement.date,
                ),
                else_=None,
            )
            result = (
                (
                    await session.execute(
                        query.order_by(
                            announcement_sort_group.asc(),
                            future_announcement_date.asc(),
                            past_announcement_date.desc(),
                            Announcement.created_at.desc(),
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Page Number Out of Range for Getting Announcements.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Invalid page number."}, 400
                )
                return finalize_request(response)
            announcements = result[:limit]
            await log(
                request,
                "Get",
                "Announcements",
                200,
                "info",
                "Announcements for User Retrieved Successfully.",
                {"subject_id": subject_id, "page": page, "limit": limit},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcements retrieved successfully",
                    "data": [
                        announcement.user_to_dict() for announcement in announcements
                    ],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Announcements",
            500,
            "error",
            "An error occurred while getting announcements.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving announcements",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/announcements/{announcement_id}")
@is_logged_in
@rate_limit
@is_ready
@has_registered_subjects
async def get_announcement_detail(request: Request, announcement_id: int):
    """
    This route is used to get the detail of an announcement for the user.
    """
    try:
        current_user = request.state.current_user
        if not is_int(announcement_id) or int(announcement_id) < 1:
            await log(
                request,
                "Get",
                "Announcement",
                400,
                "warning",
                "Invalid Announcement ID Provided for Getting Announcement.",
                {"announcement_id": announcement_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            announcement = (
                await session.execute(
                    Select(Announcement)
                    .where(Announcement.id == announcement_id)
                    .options(
                        selectinload(Announcement.subject).selectinload(Subject.users),
                        selectinload(Announcement.author),
                    )
                )
            ).scalar_one_or_none()
            if not announcement:
                await log(
                    request,
                    "Get",
                    "Announcement",
                    404,
                    "warning",
                    "Announcement Not Found for Getting Announcement.",
                    {"announcement_id": announcement_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Announcement not found"}, 404
                )
                return finalize_request(response)
            if not any(u.id == current_user.id for u in announcement.subject.users):
                await log(
                    request,
                    "Get",
                    "Announcement",
                    403,
                    "warning",
                    "User Tried to Get Announcement of a Subject He is Not Enrolled In.",
                    {
                        "announcement_id": announcement_id,
                        "subject_id": announcement.subject.id,
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not enrolled in this subject",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Announcement",
                200,
                "info",
                "Announcement for User Retrieved Successfully.",
                {"announcement_id": announcement_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcement detail retrieved successfully",
                    "data": announcement.user_to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Announcement",
            500,
            "error",
            "An error occurred while getting announcement detail.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving announcement detail",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/calendar")
@is_logged_in
@rate_limit
@is_ready
async def get_calendar(request: Request):
    """
    This route is used to get the calendar for the user.
    It will return the calendar data.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Calendar",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        month = data.get("month", None)
        year = data.get("year", None)
        if (
            not month
            or not year
            or not is_int(month)
            or not is_int(year)
            or int(month) < 1
            or int(month) > 12
            or len(year) != 4
            or int(year) < 1970
            or int(year) > 3000
        ):
            await log(
                request,
                "Get",
                "Calendar",
                400,
                "warning",
                "Invalid or Missing Month/Year Provided for Getting Calendar.",
                {"month": month, "year": year},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid month or year provided"}, 400
            )
            return finalize_request(response)
        month = int(month)
        year = int(year)
        start_date = convert_to_utc(datetime(year, month, 1, 0, 0, 0))
        if month == 12:
            end_date = convert_to_utc(datetime(year + 1, 1, 1, 0, 0, 0))
        else:
            end_date = convert_to_utc(datetime(year, month + 1, 1, 0, 0, 0))
        async with async_session() as session:
            tasks = (
                (
                    await session.execute(
                        Select(Task)
                        .where(
                            Task.faculty_id == current_user.faculty_id,
                            Task.department_id == current_user.department_id,
                            Task.year_id == current_user.year_id,
                            Task.due_date >= start_date,
                            Task.due_date < end_date,
                        )
                        .join(
                            UserSubjectLink,
                            UserSubjectLink.subject_id == Task.subject_id,
                        )
                        .where(UserSubjectLink.user_id == current_user.id)
                        .options(
                            selectinload(Task.subject),
                            selectinload(Task.author),
                        )
                        .order_by(Task.due_date.asc())
                    )
                )
                .scalars()
                .all()
            )
            announcements = (
                (
                    await session.execute(
                        Select(Announcement)
                        .where(
                            Announcement.faculty_id == current_user.faculty_id,
                            Announcement.department_id == current_user.department_id,
                            Announcement.year_id == current_user.year_id,
                            Announcement.date.isnot(None),
                            Announcement.date >= start_date,
                            Announcement.date < end_date,
                        )
                        .join(Subject, Announcement.subject_id == Subject.id)
                        .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                        .where(UserSubjectLink.user_id == current_user.id)
                        .options(
                            selectinload(Announcement.subject),
                            selectinload(Announcement.author),
                        )
                        .order_by(Announcement.date.asc())
                    )
                )
                .scalars()
                .all()
            )
            days_dict = {}
            for task in tasks:
                deadline = convert_from_utc(task.deadline)
                date_key = (
                    deadline.date().isoformat()
                    if hasattr(deadline, "date")
                    else str(deadline)
                )
                if date_key not in days_dict:
                    days_dict[date_key] = {
                        "tasks": [],
                        "exams": [],
                        "announcements": [],
                    }
                if task.type == "exam":
                    days_dict[date_key]["exams"].append(task.user_to_dict())
                else:
                    days_dict[date_key]["tasks"].append(task.user_to_dict())
            for announcement in announcements:
                if announcement.date:
                    announcement_date = convert_from_utc(announcement.date)
                    date_key = (
                        announcement_date.date().isoformat()
                        if hasattr(announcement_date, "date")
                        else str(announcement_date)
                    )
                    if date_key not in days_dict:
                        days_dict[date_key] = {
                            "tasks": [],
                            "exams": [],
                            "announcements": [],
                        }
                    days_dict[date_key]["announcements"].append(
                        announcement.user_to_dict()
                    )
            await log(
                request,
                "Get",
                "Calendar",
                200,
                "info",
                "Calendar for User Retrieved Successfully.",
                {"month": month, "year": year},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Calendar retrieved successfully",
                    "data": days_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Calendar",
            500,
            "error",
            "An error occurred while getting calendar.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving calendar",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/notifications")
@is_logged_in
@rate_limit
# @is_ready
async def get_notifications(request: Request):
    """
    This route is used to get the notifications for the user.
    It will return the notifications data.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Notifications",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Params.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        seen = data.get("seen", "false")  # Seen
        if seen.lower() not in ["true", "false"]:
            await log(
                request,
                "Get",
                "Notifications",
                400,
                "warning",
                "Invalid Seen Value Provided for Getting Notifications.",
                {"seen": seen},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        seen = True if seen.lower() == "true" else False
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        async with async_session() as session:
            query = (
                Select(Notification)
                .join(
                    UserNotification,
                    UserNotification.notification_id == Notification.id,
                )
                .where(
                    UserNotification.user_id == current_user.id,
                    UserNotification.seen == seen,
                )
                .order_by(Notification.created_at.desc())
            )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Notifications",
                    400,
                    "warning",
                    "Limit Out of Range for Getting Notifications.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Limit must be between 1 and 100."},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.offset((page - 1) * limit).limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Notifications",
                    400,
                    "warning",
                    "Page Number Out of Range for Getting Notifications.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": f"Invalid page number."}, 400
                )
                return finalize_request(response)
            notifications = result[:limit]
            notifications_result = [
                notification.user_to_dict() for notification in notifications
            ]
            for i in range(len(notifications_result)):
                notifications_result[i]["seen"] = seen
            await log(
                request,
                "Get",
                "Notifications",
                200,
                "info",
                "Notifications for User Retrieved Successfully.",
                {"seen": seen, "page": page, "limit": limit},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Notifications retrieved successfully",
                    "data": notifications_result,
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Notifications",
            500,
            "error",
            "An error occurred while getting notifications.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving notifications",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.patch("/notifications/{notification_id}")
@is_logged_in
@rate_limit
# @is_ready
async def mark_notification_as_seen(request: Request, notification_id: int):
    """
    This route is used to mark a notification as seen for the user.
    """
    current_user = request.state.current_user
    if not is_int(notification_id) or int(notification_id) < 1:
        await log(
            request,
            "Mark",
            "Notification",
            400,
            "warning",
            "Invalid Notification ID Provided for Marking Notification as Seen.",
            {"notification_id": notification_id},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Invalid request."}, 400)
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            user_notification = (
                await session.execute(
                    Select(UserNotification).where(
                        UserNotification.notification_id == notification_id,
                        UserNotification.user_id == current_user.id,
                    )
                )
            ).scalar_one_or_none()
            if not user_notification:
                await log(
                    request,
                    "Mark",
                    "Notification",
                    404,
                    "warning",
                    "Notification Not Found for Marking Notification as Seen.",
                    {"notification_id": notification_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Notification not found"}, 404
                )
                await session.rollback()
                return finalize_request(response)
            # if user_notification.seen:
            #     await log(request, "Mark", "Notification", 400, 'warning', 'Notification Already Marked as Seen.', {'notification_id': notification_id}, current_user.id)
            #     response = JSONResponse({
            #         'status': 'error',
            #         'message': 'Notification is already seen'
            #     }, 400)
            #     await session.rollback()
            #     return finalize_request(response)
            user_notification.seen = True
            await session.flush()
            await log(
                request,
                "Mark",
                "Notification",
                200,
                "info",
                "Notification Marked as Seen Successfully.",
                {"notification_id": notification_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Notification marked as seen successfully",
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await session.rollback()
            await log(
                request,
                "Mark",
                "Notification",
                500,
                "error",
                "An error occurred while marking notification as seen.",
                {"error": str(e)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while marking notification as seen",
                },
                500,
            )
            return finalize_request(response)


@user_prefix.get("/course-map")
@is_logged_in
@rate_limit
@is_ready
async def get_course_map(request: Request):
    """
    This route is used to get the course map for the user.
    It will return the course map data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(
                        Roadmap.status == True,
                        Roadmap.type == 2,
                        Roadmap.faculty_id == current_user.faculty_id,
                        Roadmap.department_id == current_user.department_id,
                        Roadmap.year_id == current_user.year_id,
                    )
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Get",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Getting Course Map.",
                    {},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            courses = (
                (
                    await session.execute(
                        Select(RoadmapCourse)
                        .where(RoadmapCourse.roadmap_id == course_map.id)
                        .order_by(
                            RoadmapCourse.year.asc(),
                            RoadmapCourse.term.asc(),
                            RoadmapCourse.rank.asc(),
                        )
                        .options(
                            selectinload(RoadmapCourse.subject),
                            selectinload(RoadmapCourse.roadmap),
                        )
                    )
                )
                .scalars()
                .all()
            )
            years = [
                [[] for term in range(course_map.details.get("terms", 0))]
                for _ in range(len(course_map.details.get("years", [])))
            ]
            for course in courses:
                if 1 <= course.year <= len(years) and 1 <= course.term <= len(
                    years[course.year - 1]
                ):
                    if not years[course.year - 1][course.term - 1]:
                        years[course.year - 1][course.term - 1] = []
                    years[course.year - 1][course.term - 1].append(course.to_dict())
            await log(
                request,
                "Get",
                "Course Map",
                200,
                "info",
                "Course Map for User Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course map retrieved successfully",
                    "data": {
                        "roadmap": course_map.to_dict(),
                        "courses": years,
                        "courses_count": len(courses),
                    },
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Course Map",
            500,
            "error",
            "An error occurred while getting course map.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving course map",
            },
            500,
        )
        return finalize_request(response)


@user_prefix.get("/download/{file_id}")
@is_logged_in
@rate_limit
async def download_file(request: Request, file_id: str):
    """Endpoint to download a file by its ID from Google Drive"""
    current_user = request.state.current_user
    session = aiohttp.ClientSession()
    try:
        if not file_id or file_id.strip() == "":
            await log(
                request,
                "Download",
                "File",
                400,
                "warning",
                "No file ID provided for file download.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "No file ID provided"}, 400
            )
            return finalize_request(response)
        file_data = None
        stream = None
        async with session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={
                "key": os.environ.get("GOOGLE_TOKEN_API_KEY"),
                "fields": "id,name,mimeType,size",
            },
        ) as meta_resp:
            if meta_resp.status != 200:
                await log(
                    request,
                    "Download",
                    "File",
                    meta_resp.status,
                    "warning",
                    "Failed to retrieve file metadata from Google Drive.",
                    {
                        "file_id": file_id,
                        "response_status": meta_resp.status,
                        "error": await meta_resp.json(),
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "File could not be downloaded"},
                    meta_resp.status,
                )
                return finalize_request(response)
            file_data = await meta_resp.json()
        if (
            not file_data
            or "id" not in file_data
            or "name" not in file_data
            or "mimeType" not in file_data
        ):
            await log(
                request,
                "Download",
                "File",
                404,
                "warning",
                "File Not Found on Google Drive for Download.",
                {"file_id": file_id, "file_data": file_data},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "File could not be downloaded"}, 404
            )
            return finalize_request(response)
        file_resp = await session.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media",
            params={"key": os.environ.get("GOOGLE_TOKEN_API_KEY")},
            allow_redirects=True,
        )
        if file_resp.status != 200:
            await log(
                request,
                "Download",
                "File",
                file_resp.status,
                "warning",
                "Failed to download file from Google Drive.",
                {
                    "file_id": file_id,
                    "response_status": file_resp.status,
                    "error": await file_resp.json(),
                },
                current_user.id,
            )
            await file_resp.release()
            response = JSONResponse(
                {"status": "error", "message": "File could not be downloaded"},
                file_resp.status,
            )
            return finalize_request(response)

        async def clean_resources():
            await file_resp.release()
            await session.close()

        safe_name = file_data.get("name", "Untitled")
        quoted_name = quote(safe_name)
        stream = StreamingResponse(
            file_resp.content.iter_chunked(1024 * 1024),
            media_type=(
                file_data.get("mimeType", "application/octet-stream")
                if file_data.get("mimeType")
                else "application/octet-stream"
            ),
            headers={
                "Content-Disposition": (f"attachment; filename*=UTF-8''{quoted_name}")
            },
            background=BackgroundTask(clean_resources),
        )
        if not stream:
            await log(
                request,
                "Download",
                "File",
                404,
                "warning",
                "File Not Found on Google Drive for Download.",
                {"file_id": file_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "File could not be downloaded"}, 404
            )
            return finalize_request(response)
        await log(
            request,
            "Download",
            "File",
            200,
            "info",
            "File Downloaded Successfully from Google Drive.",
            {"file_id": file_id},
            current_user.id,
        )
        return stream
    except Exception as e:
        await session.close()
        await log(
            request,
            "Download",
            "File",
            500,
            "error",
            "An error occurred while downloading file from Google Drive.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while downloading the file",
            },
            500,
        )
        return finalize_request(response)


# Admin Routes
@admin_prefix.post("/faculties")
@is_logged_in
@rate_limit
@is_authorized(["Add Faculties"])
async def create_faculty(request: Request):
    """
    This route is used to create a new faculty.
    It will return the created faculty data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Faculty",
            400,
            "warning",
            "No Data Provided for Creating Faculty.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Faculty",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name").strip()
    if not name:
        await log(
            request,
            "Add",
            "Faculty",
            400,
            "warning",
            "No Faculty Name Provided for Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Faculty name is required"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            existing_faculty = (
                await session.execute(
                    Select(Faculty).where(func.lower(Faculty.name) == name.lower())
                )
            ).scalar_one_or_none()
            if existing_faculty:
                await log(
                    request,
                    "Add",
                    "Faculty",
                    400,
                    "warning",
                    "Faculty Already Exists.",
                    {"name": name},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty already exists"}, 400
                )
                return finalize_request(response)
            faculty = Faculty(name=name)
            session.add(faculty)
            await session.flush()
            await log(
                request,
                "Add",
                "Faculty",
                201,
                "info",
                "Faculty Created Successfully.",
                {"name": name},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Faculty created successfully",
                    "data": faculty.min_to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Faculty",
                500,
                "error",
                "An Error Occurred while Creating Faculty.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating faculty",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/faculties/{faculty_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Faculties"])
async def update_faculty(request: Request, faculty_id: int):
    """
    This route is used to update an existing faculty.
    It will return the updated faculty data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Faculty",
            400,
            "warning",
            "No Data Provided for Updating Faculty.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Faculty",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name").strip()
    if not name:
        await log(
            request,
            "Edit",
            "Faculty",
            400,
            "warning",
            "No Faculty Name Provided for Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Faculty name is required"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (
                await session.execute(Select(Faculty).where(Faculty.id == faculty_id))
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Edit",
                    "Faculty",
                    404,
                    "warning",
                    "Faculty Not Found for Update.",
                    {"faculty_id": faculty_id, "name": name},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            existing_faculty = (
                await session.execute(
                    Select(Faculty).where(func.lower(Faculty.name) == name.lower())
                )
            ).scalar_one_or_none()
            if existing_faculty and existing_faculty.id != faculty_id:
                await log(
                    request,
                    "Edit",
                    "Faculty",
                    400,
                    "warning",
                    "Faculty Name Already Exists for Update.",
                    {"name": name},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Faculty with this Name already exists",
                    },
                    400,
                )
                return finalize_request(response)
            faculty.name = name
            await session.flush()
            await log(
                request,
                "Edit",
                "Faculty",
                200,
                "info",
                "Faculty Updated Successfully.",
                {"faculty_id": faculty_id, "name": name},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Faculty updated successfully",
                    "data": faculty.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Faculty",
                500,
                "error",
                "An Error Occurred while Updating Faculty.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating faculty",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/faculties/{faculty_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Faculties"])
async def delete_faculty(request: Request, faculty_id: int):
    """
    This route is used to delete an existing faculty.
    It will return a success message if the faculty is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (
                await session.execute(
                    Select(Faculty)
                    .where(Faculty.id == faculty_id)
                    .options(selectinload(Faculty.users))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Delete",
                    "Faculty",
                    404,
                    "warning",
                    "Faculty Not Found for Deletion.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            if faculty.users and len(faculty.users) > 0:
                await log(
                    request,
                    "Delete",
                    "Faculty",
                    400,
                    "warning",
                    "Faculty Cannot Be Deleted Because It Has Users Associated with It.",
                    {"faculty_id": faculty_id, "users_count": len(faculty.users)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Faculty cannot be deleted because it has users associated with it",
                    },
                    400,
                )
                return finalize_request(response)
            await session.delete(faculty)
            await log(
                request,
                "Delete",
                "Faculty",
                200,
                "info",
                "Faculty Deleted Successfully.",
                {"faculty_id": faculty_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Faculty deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Faculty",
                500,
                "error",
                "An Error Occurred while Deleting Faculty.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting faculty",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/faculties")
@is_logged_in
@rate_limit
@is_authorized(["View Faculties"])
async def get_faculties(request: Request):
    """
    This route is used to get all faculties.
    It will return a list of faculties.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Faculties",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip() if data else ""
        async with async_session() as session:
            faculties = (
                (
                    await session.execute(
                        Select(Faculty)
                        .where(
                            func.lower(Faculty.name).startswith(query_search.lower())
                        )
                        .order_by(Faculty.name)
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Faculties",
                200,
                "info",
                "Faculties Retrieved Successfully.",
                {"faculties_count": len(faculties)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Faculties retrieved successfully",
                    "data": [faculty.to_dict() for faculty in faculties],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Faculties",
            500,
            "error",
            "An Error Occurred while Retrieving Faculties.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving faculties",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/faculties/view/{faculty_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Faculties"])
async def get_faculty(request: Request, faculty_id: int):
    """
    This route is used to get a single faculty by its ID.
    It will return the faculty data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            faculty = (
                await session.execute(Select(Faculty).where(Faculty.id == faculty_id))
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Get",
                    "Faculty",
                    404,
                    "warning",
                    "Faculty Not Found.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Faculty",
                200,
                "info",
                "Faculty Retrieved Successfully.",
                {"faculty_id": faculty_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Faculty retrieved successfully",
                    "data": faculty.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Faculty",
            500,
            "error",
            "An Error Occurred while Retrieving Faculty.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving faculty",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/faculties/search")
@is_logged_in
@rate_limit
# @is_authorized(['View Faculties'])
async def search_faculties(request: Request):
    """
    This route is used to search faculties by name.
    It will return a list of faculties matching the search query.
    """
    current_user = request.state.current_user
    try:
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Faculties",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        async with async_session() as session:
            faculties = (
                (
                    await session.execute(
                        Select(Faculty)
                        .where(func.lower(Faculty.name).startswith(query_search))
                        .order_by(Faculty.name)
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Search",
                "Faculties",
                200,
                "info",
                "Faculties Search Completed Successfully.",
                {"query": query_search, "faculties_count": len(faculties)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Faculties search completed successfully",
                    "data": [faculty.min_to_dict() for faculty in faculties],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Faculties",
            500,
            "error",
            "An Error Occurred while Searching Faculties.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while searching faculties",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.post("/departments")
@is_logged_in
@rate_limit
@is_authorized(["Add Departments"])
async def create_department(request: Request):
    """
    This route is used to create a new department.
    It will return the created department data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Department",
            400,
            "warning",
            "No Data Provided for Creating Department.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Department",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name").strip()
    faculty_id = data.get("faculty_id")
    study_type = (
        data.get("study_type", "Mainstream").strip().title()
    )  # Default to 'Mainstream' if not provided
    code = data.get("code", "").strip().upper()  # Required Code Field
    if not name or not faculty_id or not study_type or not code:
        await log(
            request,
            "Add",
            "Department",
            400,
            "warning",
            "No Department Name or Faculty ID or Study Type or Code Provided for Department Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Department name, Study Type, Code, faculty and code are required",
            },
            400,
        )
        return finalize_request(response)
    if study_type not in ["Mainstream", "Credit", "Both"]:
        await log(
            request,
            "Add",
            "Department",
            400,
            "warning",
            "Invalid Study Type Provided for Department Creation.",
            {"study_type": study_type},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid study type provided. Must be one of the options.",
            },
            400,
        )
        return finalize_request(response)
    permissions = json.loads((await get_user_permissions(request)).body)
    if permissions.get("status") != "success":
        await log(
            request,
            "Add",
            "Department",
            403,
            "warning",
            "User Does Not Have Required Permissions for Department Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": permissions.get("message")}, 403
        )
        return finalize_request(response)
    can_access_all_faculties = False
    if permissions.get("data") and "Access All Faculties" in permissions.get("data"):
        can_access_all_faculties = True
    async with async_session() as session:
        await session.begin()
        try:
            if (
                faculty_id != current_user.faculty_id
                and can_access_all_faculties != True
            ):
                await log(
                    request,
                    "Add",
                    "Department",
                    403,
                    "warning",
                    "User Does Not Have Access to Change the Faculty for Department "
                    "Creation.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You do not have access to select faculty rather than your own",
                    },
                    403,
                )
                return finalize_request(response)
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Add",
                    "Department",
                    404,
                    "warning",
                    "Faculty Not Found for Department Creation.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            if study_type != "Both":
                existing_department = (
                    await session.execute(
                        Select(Department).where(
                            Department.faculty_id == faculty.id,
                            func.lower(Department.study_type) == study_type.lower(),
                            func.lower(Department.name) == name.lower(),
                        )
                    )
                ).scalar_one_or_none()
            else:
                existing_department = (
                    await session.execute(
                        Select(Department).where(
                            Department.faculty_id == faculty.id,
                            func.lower(Department.name) == name.lower(),
                        )
                    )
                ).scalar_one_or_none()
            if existing_department:
                await log(
                    request,
                    "Add",
                    "Department",
                    400,
                    "warning",
                    "Department Already Exists with this type for this Faculty.",
                    {"name": name, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department already exists with this type for this faculty",
                    },
                    400,
                )
                return finalize_request(response)
            if study_type != "Both":
                existing_department = (
                    await session.execute(
                        Select(Department).where(
                            Department.faculty_id == faculty.id,
                            func.lower(Department.study_type) == study_type.lower(),
                            func.lower(Department.code) == code.lower(),
                        )
                    )
                ).scalar_one_or_none()
            else:
                existing_department = (
                    await session.execute(
                        Select(Department).where(
                            Department.faculty_id == faculty.id,
                            func.lower(Department.code) == code.lower(),
                        )
                    )
                ).scalar_one_or_none()
            if existing_department:
                await log(
                    request,
                    "Add",
                    "Department",
                    400,
                    "warning",
                    "Department Code Already Exists with this type for this Faculty.",
                    {"code": code, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department with this Code already exists with this type for this faculty",
                    },
                    400,
                )
                return finalize_request(response)
            if study_type != "Both":
                department = Department(
                    name=name,
                    faculty_id=faculty.id,
                    study_type=study_type,
                    code=code.strip().upper(),
                )
                session.add(department)
            else:
                department = Department(
                    name=name,
                    faculty_id=faculty.id,
                    study_type="Mainstream",
                    code=code.strip().upper(),
                )
                session.add(department)
                department = Department(
                    name=name,
                    faculty_id=faculty.id,
                    study_type="Credit",
                    code=code.strip().upper(),
                )
                session.add(department)
            await session.flush()
            await log(
                request,
                "Add",
                "Department",
                201,
                "info",
                "Department Created Successfully.",
                {"name": name, "faculty_id": faculty_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Department created successfully",
                    "data": department.min_to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Department",
                500,
                "error",
                "An Error Occurred while Creating Department.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating department",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/departments/{department_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Departments"])
async def update_department(request: Request, department_id: int):
    """
    This route is used to update an existing department.
    It will return the updated department data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Department",
            400,
            "warning",
            "No Data Provided for Updating Department.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Department",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name").strip()
    faculty_id = data.get("faculty_id")
    study_type = (
        data.get("study_type", "Mainstream").strip().title()
    )  # Default to 'Mainstream' if not provided
    code = data.get("code", "").strip().upper()  # Required Code Field
    if not name or not faculty_id or not study_type or not code:
        await log(
            request,
            "Edit",
            "Department",
            400,
            "warning",
            "No Department Name or Faculty ID or Study Type or Code Provided for Department Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Department name, Study Type, Code, faculty and code are required",
            },
            400,
        )
        return finalize_request(response)
    if study_type not in ["Mainstream", "Credit"]:
        await log(
            request,
            "Edit",
            "Department",
            400,
            "warning",
            "Invalid Study Type Provided for Department Update.",
            {"study_type": study_type},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid study type provided. Must be either 'Mainstream' or 'Credit'.",
            },
            400,
        )
        return finalize_request(response)
    permissions = json.loads((await get_user_permissions(request)).body)
    if permissions.get("status") != "success":
        await log(
            request,
            "Edit",
            "Department",
            403,
            "warning",
            "User Does Not Have Required Permissions for Department Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": permissions.get("message")}, 403
        )
        return finalize_request(response)
    can_access_all_faculties = False
    if permissions.get("data") and "Access All Faculties" in permissions.get("data"):
        can_access_all_faculties = True
    faculty_id = int(faculty_id) if faculty_id else None
    async with async_session() as session:
        await session.begin()
        try:
            if (
                faculty_id != current_user.faculty_id
                and can_access_all_faculties != True
            ):
                await log(
                    request,
                    "Edit",
                    "Department",
                    403,
                    "warning",
                    "User Does Not Have Access to Change the Faculty for Department "
                    "Update.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You do not have access to select faculty rather than your own",
                    },
                    403,
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == department_id)
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Edit",
                    "Department",
                    404,
                    "warning",
                    "Department Not Found for Update.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            existing_department = (
                await session.execute(
                    Select(Department).where(
                        Department.faculty_id == department.faculty_id,
                        func.lower(Department.study_type) == study_type.lower(),
                        func.lower(Department.name) == name.lower(),
                    )
                )
            ).scalar_one_or_none()
            if existing_department and existing_department.id != department_id:
                await log(
                    request,
                    "Edit",
                    "Department",
                    400,
                    "warning",
                    "Department Name Already Exists with this Type for this Faculty.",
                    {"name": name, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department with this Name already exists with this type for this faculty",
                    },
                    400,
                )
                return finalize_request(response)
            existing_department = (
                await session.execute(
                    Select(Department).where(
                        Department.faculty_id == department.faculty_id,
                        func.lower(Department.study_type) == study_type.lower(),
                        func.lower(Department.code) == code.lower(),
                    )
                )
            ).scalar_one_or_none()
            if existing_department and existing_department.id != department_id:
                await log(
                    request,
                    "Edit",
                    "Department",
                    400,
                    "warning",
                    "Department Code Already Exists with this Type for this Faculty.",
                    {"code": code, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department with this Code already exists with this type for this faculty",
                    },
                    400,
                )
                return finalize_request(response)
            faculty = (
                await session.execute(Select(Faculty).where(Faculty.id == faculty_id))
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Edit",
                    "Department",
                    404,
                    "warning",
                    "Faculty Not Found for Department Update.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department.name = name
            department.faculty_id = faculty.id
            department.study_type = study_type
            department.code = code
            await session.flush()
            await log(
                request,
                "Edit",
                "Department",
                200,
                "info",
                "Department Updated Successfully.",
                {
                    "department_id": department_id,
                    "name": name,
                    "faculty_id": faculty_id,
                },
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Department updated successfully",
                    "data": department.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Department",
                500,
                "error",
                "An Error Occurred while Updating Department.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating department",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/departments/{department_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Departments"])
async def delete_department(request: Request, department_id: int):
    """
    This route is used to delete an existing department.
    It will return a success message if the department is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            department = (
                await session.execute(
                    Select(Department)
                    .where(Department.id == department_id)
                    .options(selectinload(Department.users))
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Delete",
                    "Department",
                    404,
                    "warning",
                    "Department Not Found for Deletion.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.users and len(department.users) > 0:
                await log(
                    request,
                    "Delete",
                    "Department",
                    400,
                    "warning",
                    "Department Cannot Be Deleted Because It Has Users Associated with It.",
                    {
                        "department_id": department_id,
                        "users_count": len(department.users),
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department cannot be deleted because it has users associated with it",
                    },
                    400,
                )
                return finalize_request(response)
            await session.delete(department)
            await log(
                request,
                "Delete",
                "Department",
                200,
                "info",
                "Department Deleted Successfully.",
                {"department_id": department_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Department deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Department",
                500,
                "error",
                "An Error Occurred while Deleting Department.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting department",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/departments")
@is_logged_in
@rate_limit
@is_authorized(["View Departments"])
async def get_departments(request: Request):
    """
    This route is used to get all departments.
    It will return a list of departments.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Departments",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip() if data else ""
        faculty_id = data.get("faculty_id") if data else None
        study_type = (
            data.get("study_type", "").strip().title() if data else None
        )  # Default to '' if not provided
        if study_type != "" and study_type not in ["Mainstream", "Credit"]:
            await log(
                request,
                "Get",
                "Departments",
                400,
                "warning",
                "Invalid Study Type Provided for Department Retrieval.",
                {"study_type": study_type},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid study type provided. Must be either 'Mainstream' or 'Credit'.",
                },
                400,
            )
            return finalize_request(response)
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1):
            await log(
                request,
                "Get",
                "Departments",
                400,
                "warning",
                "Invalid Faculty Provided for Department Retrieval.",
                {"faculty_id": faculty_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid faculty provided."}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            query = Select(Department).options(selectinload(Department.faculty))
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Departments",
                        404,
                        "warning",
                        "Faculty Not Found for Department Retrieval.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Department.faculty_id == int(faculty_id))
            if study_type != "":
                query = query.where(Department.study_type == study_type)
            query = query.where(
                func.lower(Department.name).startswith(query_search.lower())
            )
            departments = (
                (await session.execute(query.order_by(Department.name))).scalars().all()
            )
            await log(
                request,
                "Get",
                "Departments",
                200,
                "info",
                "Departments Retrieved Successfully.",
                {"departments_count": len(departments)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Departments retrieved successfully",
                    "data": [department.to_dict() for department in departments],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Departments",
            500,
            "error",
            "An Error Occurred while Retrieving Departments.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving departments",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/departments/view/{department_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Departments"])
async def get_department(request: Request, department_id: int):
    """
    This route is used to get a specific department by its ID.
    It will return the department data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            department = (
                await session.execute(
                    Select(Department)
                    .where(Department.id == department_id)
                    .options(
                        selectinload(Department.faculty),
                        selectinload(Department.users),
                        selectinload(Department.subjects),
                        selectinload(Department.tasks),
                        selectinload(Department.announcements),
                        selectinload(Department.events),
                    )
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Get",
                    "Department",
                    404,
                    "warning",
                    "Department Not Found for Retrieval.",
                    {"department_id": department_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            data = {
                "users": len(department.users),
                "subjects": len(department.subjects),
                "tasks": len(
                    [task for task in department.tasks if task.type.lower() != "exam"]
                ),
                "exams": len(
                    [task for task in department.tasks if task.type.lower() == "exam"]
                ),
                "announcements": len(department.announcements),
                "events": len(department.events),
            }
            await log(
                request,
                "Get",
                "Department",
                200,
                "info",
                "Department Retrieved Successfully.",
                {"department_id": department_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Department retrieved successfully",
                    "data": {"department": department.to_dict(), "summary": data},
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Department",
            500,
            "error",
            "An Error Occurred while Retrieving Department.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving department",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/departments/search")
@is_logged_in
@rate_limit
# @is_authorized(['View Departments'])
async def search_departments(request: Request):
    """
    This route is used to search departments by name.
    It will return a list of departments matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Departments",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        faculty_id = data.get("faculty_id", None) if data else None
        study_type = data.get("study_type", "").strip().title() if data else None
        if study_type != "" and study_type not in ["Mainstream", "Credit"]:
            await log(
                request,
                "Search",
                "Departments",
                400,
                "warning",
                "Invalid Study Type Provided for Department Search.",
                {"study_type": study_type},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid study type provided. Must be either 'Mainstream' or 'Credit'.",
                },
                400,
            )
            return finalize_request(response)
        if faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1):
            await log(
                request,
                "Search",
                "Departments",
                400,
                "warning",
                "Invalid Faculty ID Provided for Department Search.",
                {"faculty_id": faculty_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Faculty ID provided"}, 400
            )
            return finalize_request(response)
        faculty = None
        faculty_id = int(faculty_id) if faculty_id else None
        async with async_session() as session:
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == faculty_id)
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Search",
                        "Departments",
                        404,
                        "warning",
                        "Faculty Not Found for Department Search.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
            query = Select(Department)
            if faculty:
                query = query.where(Department.faculty_id == faculty.id)
            if study_type != "":
                query = query.where(Department.study_type == study_type)
            if query_search != "":
                query = query.where(
                    or_(
                        func.lower(Department.name).startswith(query_search),
                        func.lower(Department.code).startswith(query_search),
                    )
                )
            departments = (
                (await session.execute(query.order_by(Department.name))).scalars().all()
            )
            await log(
                request,
                "Search",
                "Departments",
                200,
                "info",
                "Departments Search Completed Successfully.",
                {"query": query_search, "departments_count": len(departments)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Departments search completed successfully",
                    "data": [department.min_to_dict() for department in departments],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Departments",
            500,
            "error",
            "An Error Occurred while Searching Departments.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while searching departments",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.post("/years")
@is_logged_in
@rate_limit
@is_authorized(["Add Years"])
async def create_year(request: Request):
    """
    This route is used to create a new academic year.
    It will return the created year data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Year",
            400,
            "warning",
            "No Data Provided for Creating Year.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Year",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    year = str(data.get("year")).strip()
    if not year:
        await log(
            request,
            "Add",
            "Year",
            400,
            "warning",
            "No Year Provided for Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Year is required"}, 400)
        return finalize_request(response)
    if "-" in year or not is_int(year) or len(year) != 4:
        await log(
            request,
            "Add",
            "Year",
            400,
            "warning",
            "Invalid Year Provided for Creation.",
            {"year": year},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Year must be a positive 4-digit number"},
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            existing_year = (
                await session.execute(Select(Year).where(Year.year == int(year)))
            ).scalar_one_or_none()
            if existing_year:
                await log(
                    request,
                    "Add",
                    "Year",
                    400,
                    "warning",
                    "Year Already Exists.",
                    {"year": year},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year already exists"}, 400
                )
                return finalize_request(response)
            year_added = Year(year=int(year))
            session.add(year_added)
            await session.flush()
            await log(
                request,
                "Add",
                "Year",
                201,
                "info",
                "Year Created Successfully.",
                {"year": year},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Year created successfully",
                    "data": year_added.min_to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Year",
                500,
                "error",
                "An Error Occurred while Creating Year.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while creating year"},
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/years/{year_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Years"])
async def update_year(request: Request, year_id: int):
    """
    This route is used to update an existing academic year.
    It will return the updated year data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Year",
            400,
            "warning",
            "No Data Provided for Updating Year.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Year",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    year = str(data.get("year")).strip()
    if not year:
        await log(
            request,
            "Edit",
            "Year",
            400,
            "warning",
            "No Year Provided for Update.",
            {},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Year is required"}, 400)
        return finalize_request(response)
    if "-" in year or not is_int(year) or len(year) != 4:
        await log(
            request,
            "Edit",
            "Year",
            400,
            "warning",
            "Invalid Year Provided for Update.",
            {"year": year},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Year must be a positive 4-digit number"},
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            year_obj = (
                await session.execute(Select(Year).where(Year.id == year_id))
            ).scalar_one_or_none()
            if not year_obj:
                await log(
                    request,
                    "Edit",
                    "Year",
                    404,
                    "warning",
                    "Year Not Found for Update.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            existing_year = (
                await session.execute(Select(Year).where(Year.year == int(year)))
            ).scalar_one_or_none()
            if existing_year and existing_year.id != year_id:
                await log(
                    request,
                    "Edit",
                    "Year",
                    400,
                    "warning",
                    "Year Already Exists for Update.",
                    {"year": year},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year already exists"}, 400
                )
                return finalize_request(response)
            year_obj.year = int(year)
            await session.flush()
            await log(
                request,
                "Edit",
                "Year",
                200,
                "info",
                "Year Updated Successfully.",
                {"year_id": year_id, "year": year},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Year updated successfully",
                    "data": year_obj.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Year",
                500,
                "error",
                "An Error Occurred while Updating Year.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while updating year"},
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/years/{year_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Years"])
async def delete_year(request: Request, year_id: int):
    """
    This route is used to delete an existing academic year.
    It will return a success message if the year is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            year = (
                await session.execute(
                    Select(Year)
                    .where(Year.id == year_id)
                    .options(selectinload(Year.users))
                )
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Delete",
                    "Year",
                    404,
                    "warning",
                    "Year Not Found for Deletion.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            if year.users and len(year.users) > 0:
                await log(
                    request,
                    "Delete",
                    "Year",
                    400,
                    "warning",
                    "Year Cannot Be Deleted Because It Has Users Associated with It.",
                    {"year_id": year_id, "users_count": len(year.users)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Year cannot be deleted because it has users associated with it",
                    },
                    400,
                )
                return finalize_request(response)
            await session.delete(year)
            await log(
                request,
                "Delete",
                "Year",
                200,
                "info",
                "Year Deleted Successfully.",
                {"year_id": year_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Year deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Year",
                500,
                "error",
                "An Error Occurred while Deleting Year.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while deleting year"},
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/years")
@is_logged_in
@rate_limit
@is_authorized(["View Years"])
async def get_years(request: Request):
    """
    This route is used to get all academic years.
    It will return a list of years.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Years",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        year = str(data.get("year", "")).strip() if data else ""
        if year and (not is_int(year) or len(year) != 4):
            await log(
                request,
                "Get",
                "Years",
                400,
                "warning",
                "Invalid Year Provided for Retrieval.",
                {"year": year},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Year must be a positive 4-digit number",
                },
                400,
            )
            return finalize_request(response)
        async with async_session() as session:
            query = Select(Year)
            if year:
                query = query.where(Year.year == int(year))
            years = (await session.execute(query.order_by(Year.year))).scalars().all()
            await log(
                request,
                "Get",
                "Years",
                200,
                "info",
                "Years Retrieved Successfully.",
                {"years_count": len(years)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Years retrieved successfully",
                    "data": [year.to_dict() for year in years],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Years",
            500,
            "error",
            "An Error Occurred while Retrieving Years.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving years"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/years/view/{year_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Years"])
async def get_year(request: Request, year_id: int):
    """
    This route is used to get a specific academic year by its ID.
    It will return the year data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            year = (
                await session.execute(Select(Year).where(Year.id == year_id))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Get",
                    "Year",
                    404,
                    "warning",
                    "Year Not Found for Retrieval.",
                    {"year_id": year_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Year",
                200,
                "info",
                "Year Retrieved Successfully.",
                {"year_id": year_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Year retrieved successfully",
                    "data": year.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Year",
            500,
            "error",
            "An Error Occurred while Retrieving Year.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving year"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/years/search")
@is_logged_in
@rate_limit
# @is_authorized(['View Years'])
async def search_years(request: Request):
    """
    This route is used to search academic years by year.
    It will return a list of years matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Years",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip() if data else ""
        if query_search and (not is_int(query_search) or len(query_search) != 4):
            await log(
                request,
                "Search",
                "Years",
                400,
                "warning",
                "Invalid Year Provided for Search.",
                {"query": query_search},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Year must be a positive 4-digit number",
                },
                400,
            )
            return finalize_request(response)
        async with async_session() as session:
            query = Select(Year)
            if query_search:
                query = query.where(Year.year == int(query_search))
            years = (await session.execute(query.order_by(Year.year))).scalars().all()
            await log(
                request,
                "Search",
                "Years",
                200,
                "info",
                "Years Search Completed Successfully.",
                {"query": query_search, "years_count": len(years)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Years search completed successfully",
                    "data": [year.min_to_dict() for year in years],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Years",
            500,
            "error",
            "An Error Occurred while Searching Years.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while searching years"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/users/data")
@is_logged_in
@rate_limit
@is_authorized(["View Users"])
async def get_users_data(request: Request):
    """
    This route is used to get users data.
    It will return a list of data.
    """
    try:
        data = request.query_params
        faculty_id = (
            int(data.get("faculty_id"))
            if data.get("faculty_id") and is_int(data.get("faculty_id"))
            else None
        )
        department_id = (
            int(data.get("department_id"))
            if data.get("department_id") and is_int(data.get("department_id"))
            else None
        )
        year_id = (
            int(data.get("year_id"))
            if data.get("year_id") and is_int(data.get("year_id"))
            else None
        )
        current_user = request.state.current_user
        async with async_session() as session:
            two_hours_ago = datetime.now(utc_tz) - timedelta(hours=2)
            this_month_start = datetime.now(utc_tz).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            users_ids = (
                (
                    await session.execute(
                        Select(User.id).where(
                            User.faculty_id == faculty_id if faculty_id else True,
                            (
                                User.department_id == department_id
                                if department_id
                                else True
                            ),
                            User.year_id == year_id if year_id else True,
                        )
                    )
                )
                .scalars()
                .all()
            )
            users_this_month = await session.scalar(
                Select(func.count(User.id)).where(
                    User.faculty_id == faculty_id if faculty_id else True,
                    User.department_id == department_id if department_id else True,
                    User.year_id == year_id if year_id else True,
                    User.created_at >= this_month_start,
                )
            )
            percentage_increase = (
                (users_this_month / (len(users_ids) - users_this_month)) * 100
                if (len(users_ids) - users_this_month) > 0
                else 0
            )
            active_now = await session.scalar(
                Select(func.count(func.distinct(RequestLimit.user_id))).where(
                    RequestLimit.user_id != None,
                    RequestLimit.user_id.in_(users_ids) if users_ids else False,
                    RequestLimit.created_at >= two_hours_ago,
                )
            )
            last_five_users_active_result = (
                (
                    await session.execute(
                        Select(
                            RequestLimit.user_id,
                            func.max(RequestLimit.created_at).label("max_created_at"),
                        )
                        .where(
                            RequestLimit.user_id != None,
                            RequestLimit.user_id.in_(users_ids) if users_ids else False,
                            RequestLimit.created_at >= two_hours_ago,
                        )
                        .group_by(RequestLimit.user_id)
                        .order_by(func.max(RequestLimit.created_at).desc())
                        .limit(5)
                    )
                )
                .scalars()
                .all()
            )
            last_five_users_active = []
            for row in last_five_users_active_result:
                if not is_int(row):
                    user_id = row[0]
                else:
                    user_id = row
                user = (
                    await session.execute(
                        Select(User.details, User.google_avatar).where(
                            User.id == user_id
                        )
                    )
                ).first()
                if user:
                    avatar = (
                        user.details.get("avatar", None)
                        if user.details.get("avatar", None)
                        else user.google_avatar
                    )
                    last_five_users_active.append(avatar)
            pending_users_count = await session.scalar(
                Select(func.count(PendingUser.id))
                .join(User, User.id == PendingUser.user_id)
                .where(
                    User.faculty_id != None,
                    User.department_id != None,
                    User.year_id != None,
                    User.type != None,
                    User.type != "",
                    User.status == False,
                    User.faculty_id == faculty_id if faculty_id else True,
                    User.department_id == department_id if department_id else True,
                    User.year_id == year_id if year_id else True,
                )
            )
            await log(
                request,
                "Get",
                "Users",
                200,
                "info",
                "Users Data Retrieved Successfully.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Users data retrieved successfully",
                    "data": {
                        "users_count": len(users_ids),
                        "users_this_month": users_this_month,
                        "percentage_increase": math.ceil(percentage_increase),
                        "active_now": active_now,
                        "pending_users_count": pending_users_count,
                        "last_five_users_active": last_five_users_active,
                    },
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Users",
            500,
            "error",
            "An Error Occurred while Retrieving Users Data.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving users data",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/users")
@is_logged_in
@rate_limit
@is_authorized(["View Users"])
async def get_users(request: Request):
    """
    This route is used to get all users.
    It will return a list of users.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Users",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if not data:
            data = {}
        search_query = data.get("query", "").strip().lower()
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        is_active = (
            data.get("is_active").lower() == "true" if data.get("is_active") else True
        )
        page = int(data.get("page", 1)) if data.get("page", "1").isdigit() else 1
        limit = int(data.get("limit", 50)) if data.get("limit", "50").isdigit() else 50
        current_user_permissions = (
            json.loads((await get_user_permissions(request)).body)
        ).get("data", [])
        if (
            faculty_id
            and (not is_int(faculty_id) or int(faculty_id) < 1)
            or department_id
            and (not is_int(department_id) or int(department_id) < 1)
            or year_id
            and (not is_int(year_id) or int(year_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Users",
                400,
                "warning",
                "Invalid IDs Provided for User Retrieval.",
                {
                    "faculty_id": faculty_id,
                    "department_id": department_id,
                    "year_id": year_id,
                },
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Data provided"}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            query = (
                Select(User)
                .where(
                    not_(
                        Select(RoleLink)
                        .where(RoleLink.role_id == User.role_id)
                        .join(ExactRole, RoleLink.exact_role_id == ExactRole.id)
                        .where(ExactRole.name.notin_(current_user_permissions))
                        .exists()
                    )
                )
                .options(
                    selectinload(User.role),
                    selectinload(User.faculty),
                    selectinload(User.department),
                    selectinload(User.year),
                    selectinload(User.pending_user),
                    selectinload(User.notifications),
                    selectinload(User.subjects),
                )
            )
            faculty = None
            if faculty_id:
                faculty_id = int(faculty_id)
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == faculty_id)
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Users",
                        404,
                        "warning",
                        "Faculty Not Found for User Retrieval.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(User.faculty_id == faculty_id)
            if department_id:
                department_id = int(department_id)
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == department_id)
                    )
                ).scalar_one_or_none()
                if not department:
                    await log(
                        request,
                        "Get",
                        "Users",
                        404,
                        "warning",
                        "Department Not Found for User Retrieval.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Department not found"}, 404
                    )
                    return finalize_request(response)
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Users",
                        400,
                        "warning",
                        "Faculty ID Must Be Provided with Department ID for User Retrieval.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Can't choose department without faculty",
                        },
                        400,
                    )
                    return finalize_request(response)
                if department.faculty_id != int(faculty_id):
                    await log(
                        request,
                        "Get",
                        "Users",
                        400,
                        "warning",
                        "Department Does Not Belong to the Specified Faculty for User Retrieval.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department does not belong to the specified faculty",
                        },
                        400,
                    )
                    return finalize_request(response)
                query = query.where(User.department_id == department_id)
            if year_id:
                year_id = int(year_id)
                year = (
                    await session.execute(Select(Year).where(Year.id == year_id))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Get",
                        "Users",
                        404,
                        "warning",
                        "Year Not Found for User Retrieval.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(User.year_id == year_id)
            query = query.where(User.status == is_active)
            if not is_active:
                query = query.where(
                    User.faculty != None,
                    User.department != None,
                    User.year != None,
                    User.type != None,
                    User.type != "",
                )
            if search_query and search_query != "":
                query = query.where(
                    or_(
                        func.lower(User.name).startswith(search_query),
                        func.lower(User.email).startswith(search_query),
                        func.lower(User.phone).startswith(search_query),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Users",
                    400,
                    "warning",
                    "Invalid Limit Provided for User Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(User.name)
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            users = result[:limit]
            if page < 1 or page > 1 and (not users or len(users) < 1):
                await log(
                    request,
                    "Get",
                    "Users",
                    400,
                    "warning",
                    "Invalid Page Number Provided for User Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Users",
                200,
                "info",
                "Users Retrieved Successfully.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Users retrieved successfully",
                    "data": [user.to_dict() for user in users],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Users",
            500,
            "error",
            "An Error Occurred while Retrieving Users.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving users"},
            500,
        )
        return finalize_request(response)


@admin_prefix.patch("/users")
@is_logged_in
@rate_limit
@is_authorized(["Manage Users"])
async def update_users(request: Request):
    """
    This route is used to update multiple users.
    It will return a success message if the users are updated successfully.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Users",
            400,
            "warning",
            "No Data Provided for Users Update.",
            {},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "No data provided"}, 400)
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Users",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    if isinstance(data, dict):
        data_to_update = data.get(
            "data_to_update", []
        )  # each contains {'id': user_id, 'approved': True/False, 'role_id':
        # role_id (optional)}
    elif isinstance(data, list):
        data_to_update = data
    else:
        await log(
            request,
            "Edit",
            "Users",
            400,
            "warning",
            "Invalid Data Format Provided for Users Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data format provided"}, 400
        )
        return finalize_request(response)
    if not data_to_update or not isinstance(data_to_update, list):
        await log(
            request,
            "Edit",
            "Users",
            400,
            "warning",
            "No Users Data Provided for Users Update.",
            {"data": data},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Empty request was sent"}, 400
        )
        return finalize_request(response)
    for record in data_to_update:
        if (
            not record.get("id")
            or not is_int(record.get("id"))
            or "approved" not in record
            or not record.get("approved", True) in [True, False]
            or (record.get("role_id", "1") and not is_int(record.get("role_id", "1")))
            or (record.get("role_id", "1") and int(record.get("role_id", "1")) < 1)
        ):
            await log(
                request,
                "Edit",
                "Users",
                400,
                "warning",
                "Invalid User Data Provided for Users Update.",
                {"record": record},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid request was sent"}, 400
            )
            return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            for record in data_to_update:
                user = (
                    await session.execute(
                        Select(User)
                        .where(User.id == int(record.get("id")))
                        .options(selectinload(User.role).selectinload(Role.exact_roles))
                    )
                ).scalar_one_or_none()
                if not user:
                    await log(
                        request,
                        "Edit",
                        "Users",
                        404,
                        "warning",
                        "User Not Found for Users Update.",
                        {"user_id": record.get("id")},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": f"Invalid request was sent. Users sent contains not found users",
                        },
                        404,
                    )
                    return finalize_request(response)
                if user.id == current_user.id:
                    await log(
                        request,
                        "Edit",
                        "Users",
                        400,
                        "warning",
                        "User Cannot Update Their Own Account via This Endpoint.",
                        {"user_id": user.id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You cannot update your own account using this method",
                        },
                        400,
                    )
                    return finalize_request(response)
                user_permissions = json.loads(
                    (await get_user_permissions(request)).body
                )
                permissions = user_permissions.get("data", [])
                updated_user_permissions = (
                    [permission.name for permission in user.role.exact_roles]
                    if user.role and user.role.exact_roles
                    else []
                )
                missing_permissions = [
                    permission
                    for permission in updated_user_permissions
                    if permission not in permissions
                ]
                if missing_permissions and len(missing_permissions) > 0:
                    await log(
                        request,
                        "Edit",
                        "Users",
                        403,
                        "warning",
                        "User Does Not Have All Required Permissions to Update the Specified User.",
                        {
                            "user_id": user.id,
                            "missing_permissions": missing_permissions,
                        },
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": f"You Cannot update a user having permissions you don't have.",
                        },
                        403,
                    )
                    return finalize_request(response)
                if not bool(record.get("approved")) and user.status:
                    await log(
                        request,
                        "Edit",
                        "Users",
                        400,
                        "warning",
                        "Cannot Un Approve an Already Approved User.",
                        {"user_id": user.id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Cannot un approve an already approved user",
                        },
                        400,
                    )
                    return finalize_request(response)
                if not bool(record.get("approved")):
                    await session.delete(user)
                    # Send email to user notifying them of account deletion (V2)
                    continue
                user.status = True
                pending_user = (
                    await session.execute(
                        Select(PendingUser).where(PendingUser.user_id == user.id)
                    )
                ).scalar_one_or_none()
                if pending_user:
                    await session.delete(pending_user)
                if record.get("role_id", None):
                    role = (
                        await session.execute(
                            Select(Role)
                            .where(Role.id == int(record.get("role_id")))
                            .options(selectinload(Role.exact_roles))
                        )
                    ).scalar_one_or_none()
                    if not role:
                        await log(
                            request,
                            "Edit",
                            "Users",
                            404,
                            "warning",
                            "Role Not Found for User Update.",
                            {"role_id": record.get("role_id")},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": f"Invalid request was sent. Roles sent contained roles not found",
                            },
                            404,
                        )
                        return finalize_request(response)
                    if "Assign Roles" not in permissions:
                        await log(
                            request,
                            "Edit",
                            "Users",
                            403,
                            "warning",
                            "User Does Not Have Required Permissions to Assign Roles for User Update.",
                            {},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "You do not have permissions to assign roles",
                            },
                            403,
                        )
                        return finalize_request(response)
                    missing_permissions = [
                        permission.name
                        for permission in role.exact_roles
                        if permission.name not in permissions
                    ]
                    if missing_permissions and len(missing_permissions) > 0:
                        await log(
                            request,
                            "Edit",
                            "Users",
                            403,
                            "warning",
                            "User Does Not Have All Required Permissions to Assign the Specified Role for User Update.",
                            {
                                "role_id": record.get("role_id"),
                                "missing_permissions": missing_permissions,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": f"You Cannot assign a role having permissions you don't have.",
                            },
                            403,
                        )
                        return finalize_request(response)
                    user.role_id = role.id
                await session.flush()
            await log(
                request,
                "Edit",
                "Users",
                200,
                "info",
                "Users Updated Successfully.",
                {"users_updated_count": len(data_to_update)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Users updated successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Users",
                500,
                "error",
                "An Error Occurred while Updating Users.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating users",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/users/{user_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Users"])
async def get_user(request: Request, user_id: int):
    """
    This route is used to get a specific user by their ID.
    It will return the user data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            user = (
                await session.execute(
                    Select(User)
                    .where(User.id == user_id)
                    .options(
                        selectinload(User.role).selectinload(Role.exact_roles),
                        selectinload(User.faculty),
                        selectinload(User.department),
                        selectinload(User.year),
                        selectinload(User.pending_user),
                        selectinload(User.notifications),
                        selectinload(User.subjects),
                    )
                )
            ).scalar_one_or_none()
            if not user:
                await log(
                    request,
                    "Get",
                    "User",
                    404,
                    "warning",
                    "User Not Found for Retrieval.",
                    {"user_id": user_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "User not found"}, 404
                )
                return finalize_request(response)
            permissions = json.loads((await get_user_permissions(request)).body).get(
                "data", []
            )
            user_permissions = (
                [permission.name for permission in user.role.exact_roles]
                if user.role and user.role.exact_roles
                else []
            )
            missing_permissions = [
                permission
                for permission in user_permissions
                if permission not in permissions
            ]
            if missing_permissions and len(missing_permissions) > 0:
                await log(
                    request,
                    "Get",
                    "User",
                    403,
                    "warning",
                    "User Does Not Have All Required Permissions to View the Specified User.",
                    {"user_id": user.id, "missing_permissions": missing_permissions},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": f"You Cannot view a user having permissions you don't have.",
                    },
                    403,
                )
                return finalize_request(response)
            user_dict = user.to_dict()
            exams_published = (
                (
                    await session.execute(
                        Select(Task)
                        .where(
                            Task.author_id == user.id, func.lower(Task.type) == "exam"
                        )
                        .options(
                            selectinload(Task.faculty),
                            selectinload(Task.department),
                            selectinload(Task.year),
                            selectinload(Task.subject),
                            selectinload(Task.author),
                        )
                        .order_by(Task.deadline.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["exams_published"] = [exam.to_dict() for exam in exams_published]
            exams = (
                (
                    await session.execute(
                        Select(Task)
                        .where(
                            Task.faculty_id == user.faculty_id,
                            Task.department_id == user.department_id,
                            Task.year_id == user.year_id,
                            func.lower(Task.type) == "exam",
                        )
                        .options(
                            selectinload(Task.faculty),
                            selectinload(Task.department),
                            selectinload(Task.year),
                            selectinload(Task.subject),
                            selectinload(Task.author),
                        )
                        .order_by(Task.deadline.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["exams"] = [exam.to_dict() for exam in exams]
            tasks_published = (
                (
                    await session.execute(
                        Select(Task)
                        .where(
                            Task.author_id == user.id, func.lower(Task.type) != "exam"
                        )
                        .options(
                            selectinload(Task.faculty),
                            selectinload(Task.department),
                            selectinload(Task.year),
                            selectinload(Task.subject),
                            selectinload(Task.author),
                        )
                        .order_by(Task.deadline.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["tasks_published"] = [task.to_dict() for task in tasks_published]
            tasks = (
                (
                    await session.execute(
                        Select(Task)
                        .where(
                            Task.faculty_id == user.faculty_id,
                            Task.department_id == user.department_id,
                            Task.year_id == user.year_id,
                            func.lower(Task.type) != "exam",
                        )
                        .options(
                            selectinload(Task.faculty),
                            selectinload(Task.department),
                            selectinload(Task.year),
                            selectinload(Task.subject),
                            selectinload(Task.author),
                        )
                        .order_by(Task.deadline.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["tasks"] = [task.to_dict() for task in tasks]
            announcements_published = (
                (
                    await session.execute(
                        Select(Announcement)
                        .where(Announcement.author_id == user.id)
                        .options(
                            selectinload(Announcement.faculty),
                            selectinload(Announcement.department),
                            selectinload(Announcement.year),
                            selectinload(Announcement.subject),
                            selectinload(Announcement.author),
                        )
                        .order_by(Announcement.created_at.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["announcements_published"] = [
                announcement.to_dict() for announcement in announcements_published
            ]
            materials_uploaded = (
                (
                    await session.execute(
                        Select(Material)
                        .options(
                            selectinload(Material.author),
                            selectinload(Material.subject),
                            selectinload(Material.parent),
                        )
                        .where(Material.author_id == user.id)
                        .order_by(Material.created_at.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["materials_uploaded"] = [
                material.to_dict() for material in materials_uploaded
            ]
            grades_uploaded = (
                (
                    await session.execute(
                        Select(Grade)
                        .options(
                            selectinload(Grade.author),
                            selectinload(Grade.subject),
                            selectinload(Grade.parent),
                        )
                        .where(Grade.author_id == user.id)
                        .order_by(Grade.created_at.desc())
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["grades_uploaded"] = [
                grade.to_dict() for grade in grades_uploaded
            ]
            subjects = (
                (
                    await session.execute(
                        Select(Subject)
                        .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                        .where(UserSubjectLink.user_id == user.id)
                        .options(
                            selectinload(Subject.faculty),
                            selectinload(Subject.department),
                            selectinload(Subject.year),
                            selectinload(Subject.users),
                        )
                        .order_by(Subject.name)
                        .limit(3)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["subjects"] = [subject.to_dict() for subject in subjects]
            logs = (
                (
                    await session.execute(
                        Select(Log)
                        .where(Log.user_id == user.id)
                        .options(selectinload(Log.user))
                        .order_by(Log.created_at.desc())
                        .limit(5)
                    )
                )
                .scalars()
                .all()
            )
            user_dict["logs"] = [log_record.to_dict() for log_record in logs]
            await log(
                request,
                "Get",
                "User",
                200,
                "info",
                "User Retrieved Successfully.",
                {"user_id": user_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "User retrieved successfully",
                    "data": user_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "User",
            500,
            "error",
            "An Error Occurred while Retrieving User.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving user"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/users/search")
@is_logged_in
@rate_limit
@is_authorized(["View Users"])
async def search_users(request: Request):
    """
    This route is used to search users by name, email, or phone.
    It will return a list of users matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Users",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        is_active = (
            data.get("is_active").lower() == "true" if data.get("is_active") else True
        )
        page = int(data.get("page", 1)) if data.get("page", "1").isdigit() else 1
        limit = int(data.get("limit", 50)) if data.get("limit", "50").isdigit() else 50
        if (
            (faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1))
            or (department_id and (not is_int(department_id) or int(department_id) < 1))
            or (year_id and (not is_int(year_id) or int(year_id) < 1))
        ):
            await log(
                request,
                "Search",
                "Users",
                400,
                "warning",
                "Invalid Faculty/Department/Year ID Provided for User Search.",
                {
                    "faculty_id": faculty_id,
                    "department_id": department_id,
                    "year_id": year_id,
                },
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid request was sent. Please provide Data correctly",
                },
                400,
            )
            return finalize_request(response)
        async with async_session() as session:
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Search",
                        "Users",
                        404,
                        "warning",
                        "Faculty Not Found for User Search.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if not department:
                    await log(
                        request,
                        "Search",
                        "Users",
                        404,
                        "warning",
                        "Department Not Found for User Search.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Department not found"}, 404
                    )
                    return finalize_request(response)
                if not faculty_id:
                    await log(
                        request,
                        "Search",
                        "Users",
                        400,
                        "warning",
                        "Faculty ID Must Be Provided with Department ID for User Search.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Can't choose department without faculty",
                        },
                        400,
                    )
                    return finalize_request(response)
                if department.faculty_id != int(faculty_id):
                    await log(
                        request,
                        "Search",
                        "Users",
                        400,
                        "warning",
                        "Department Does Not Belong to the Specified Faculty for User Search.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department does not belong to the specified faculty",
                        },
                        400,
                    )
                    return finalize_request(response)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Search",
                        "Users",
                        404,
                        "warning",
                        "Year Not Found for User Search.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
            query = Select(User).where(User.status == is_active)
            if faculty_id:
                query = query.where(User.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(User.department_id == int(department_id))
            if year_id:
                query = query.where(User.year_id == int(year_id))
            query = query.where(User.status == is_active)
            if not is_active:
                query = query.where(
                    User.faculty != None,
                    User.department != None,
                    User.year != None,
                    User.type != None,
                    User.type != "",
                )
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(User.name).startswith(query_search),
                        func.lower(User.email).startswith(query_search),
                        func.lower(User.phone).startswith(query_search),
                    )
                )
            if limit < 1:  # Allow Any Positive Number to accept Approve and Reject All
                await log(
                    request,
                    "Get",
                    "Users",
                    400,
                    "warning",
                    "Invalid Limit Provided for User Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(User.name)
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            users = result[:limit]
            if page < 1 or page > 1 and (not users or len(users) < 1):
                await log(
                    request,
                    "Get",
                    "Users",
                    400,
                    "warning",
                    "Invalid Page Number Provided for User Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            await log(
                request,
                "Search",
                "Users",
                200,
                "info",
                "Users Search Completed Successfully.",
                {"query": query_search, "data": dict(data), "users_count": len(users)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Users search completed successfully",
                    "data": [user.min_to_dict() for user in users],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Users",
            500,
            "error",
            "An Error Occurred while Searching Users.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while searching users"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/roles/permissions/count")
@is_logged_in
@rate_limit
@is_authorized(["View Roles"])
async def count_permissions(request: Request):
    """
    This route is used to count the total number of permissions.
    It will return the count of permissions.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            permissions_count = await session.scalar(Select(func.count(ExactRole.id)))
            await log(
                request,
                "Count",
                "Permissions",
                200,
                "info",
                "Permissions Count Retrieved Successfully.",
                {"permissions_count": permissions_count},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Permissions count retrieved successfully",
                    "data": permissions_count,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Count",
            "Permissions",
            500,
            "error",
            "An Error Occurred while Counting Permissions.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while counting permissions",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.post("/roles")
@is_logged_in
@rate_limit
@is_authorized(["Add Roles"])
async def create_role(request: Request):
    """
    This route is used to create a new role.
    It will return the created role data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Role",
            400,
            "warning",
            "No Data Provided for Creating Role.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Role",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    if not name:
        await log(
            request,
            "Add",
            "Role",
            400,
            "warning",
            "No Role Name Provided for Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Role name is required"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            existing_role = (
                await session.execute(
                    Select(Role).where(func.lower(Role.name) == name.lower())
                )
            ).scalar_one_or_none()
            if existing_role:
                await log(
                    request,
                    "Add",
                    "Role",
                    400,
                    "warning",
                    "Role with this name Already Exists.",
                    {"role_name": name},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Role with this name already exists",
                    },
                    400,
                )
                return finalize_request(response)
            role = Role(name=name, level=3)
            session.add(role)
            await session.flush()
            await log(
                request,
                "Add",
                "Role",
                201,
                "info",
                "Role Created Successfully.",
                {"role_name": name},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Role created successfully",
                    "data": role.min_to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Role",
                500,
                "error",
                "An Error Occurred while Creating Role.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while creating role"},
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/roles/{role_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Roles"])
async def update_role(request: Request, role_id: int):
    """
    This route is used to update an existing role.
    It will return the updated role data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Role",
            400,
            "warning",
            "No Data Provided for Updating Role.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Role",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    if not name:
        await log(
            request,
            "Edit",
            "Role",
            400,
            "warning",
            "No Role Name Provided for Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Role name is required"}, 400
        )
        return finalize_request(response)
    permissions = data.get("permissions", [])  # list of permission names
    if not isinstance(permissions, list):
        await log(
            request,
            "Edit",
            "Role",
            400,
            "warning",
            "Invalid Permissions Format Provided for Role Update.",
            {"permissions": permissions},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid permissions provided"}, 400
        )
        return finalize_request(response)
    current_user_permissions = (
        json.loads((await get_user_permissions(request)).body)
    ).get("data", [])
    missing_permissions = [
        permission
        for permission in permissions
        if permission not in current_user_permissions
    ]
    if missing_permissions and len(missing_permissions) > 0:
        await log(
            request,
            "Edit",
            "Role",
            403,
            "warning",
            "User Does Not Have All Required Permissions to Assign the Specified Permissions for Role Update.",
            {"missing_permissions": missing_permissions},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": f"You Cannot assign permissions you don't have.",
            },
            403,
        )
        return finalize_request(response)
    permissions_classified = {}
    for permission in permissions:
        if permission == "Is Admin":
            continue
        category = " ".join(permission.split(" ")[1:])  # Get the last word as category
        permission_name = permission.split(" ")[0]  # Get the rest as permission name
        if "All" in permission:
            category = " ".join(permission.split(" ")[2:])
            permission_name = " ".join(permission.split(" ")[:2])
        if category not in permissions_classified:
            permissions_classified[category] = []
        if permission_name in permissions_classified[category]:  # Avoid duplicates
            await log(
                request,
                "Edit",
                "Role",
                400,
                "warning",
                "Duplicate Permissions Provided in The Request Body for Role Update.",
                {"permission": permission},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": f"Duplicate permissions provided: {permission}",
                },
                400,
            )
            return finalize_request(response)
        permissions_classified[category].append(permission_name)
    for category, perms in permissions_classified.items():
        if "View" not in perms:
            await log(
                request,
                "Edit",
                "Role",
                400,
                "warning",
                "View Permission Missing for a Category in The Request Body for Role Update.",
                {"category": category},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": f"You can't assign permissions to '{category}' without assigning the 'View' permission",
                },
                400,
            )
            return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            role = (
                await session.execute(
                    Select(Role)
                    .where(Role.id == role_id)
                    .options(selectinload(Role.exact_roles), selectinload(Role.users))
                )
            ).scalar_one_or_none()
            if not role:
                await log(
                    request,
                    "Edit",
                    "Role",
                    404,
                    "warning",
                    "Role Not Found for Update.",
                    {"role_id": role_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Role not found"}, 404
                )
                return finalize_request(response)
            missing_permissions = [
                permission.name
                for permission in role.exact_roles
                if permission.name not in current_user_permissions
            ]
            if missing_permissions and len(missing_permissions) > 0:
                await log(
                    request,
                    "Edit",
                    "Role",
                    403,
                    "warning",
                    "User Does Not Have All Required Permissions to Update the Specified Role.",
                    {"role_id": role_id, "missing_permissions": missing_permissions},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": f"You Cannot update a role having permissions you don't have.",
                    },
                    403,
                )
                return finalize_request(response)
            existing_role = (
                await session.execute(
                    Select(Role).where(func.lower(Role.name) == name.lower())
                )
            ).scalar_one_or_none()
            if existing_role and existing_role.id != role_id:
                await log(
                    request,
                    "Edit",
                    "Role",
                    400,
                    "warning",
                    "Role with this name Already Exists for Update.",
                    {"role_name": name},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Role with this name already exists",
                    },
                    400,
                )
                return finalize_request(response)
            role.name = name
            for i in range(len(role.exact_roles) - 1, -1, -1):
                if role.exact_roles[i].name not in permissions:
                    role.exact_roles.remove(role.exact_roles[i])
            for permission in permissions:
                exact_role = (
                    await session.execute(
                        Select(ExactRole).where(
                            func.lower(ExactRole.name) == permission.lower()
                        )
                    )
                ).scalar_one_or_none()
                if not exact_role:
                    await log(
                        request,
                        "Edit",
                        "Role",
                        404,
                        "warning",
                        "Permission Not Found for Role Update.",
                        {"permission": permission},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": f"Permission '{permission}' not found",
                        },
                        404,
                    )
                    return finalize_request(response)
                if exact_role not in role.exact_roles:
                    role.exact_roles.append(exact_role)
            await session.flush()
            await log(
                request,
                "Edit",
                "Role",
                200,
                "info",
                "Role Updated Successfully.",
                {"role_id": role_id, "role_name": name},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Role updated successfully",
                    "data": role.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Role",
                500,
                "error",
                "An Error Occurred while Updating Role.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while updating role"},
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/roles/{role_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Roles"])
async def delete_role(request: Request, role_id: int):
    """
    This route is used to delete an existing role.
    It will return a success message if the role is deleted successfully.
    """
    current_user = request.state.current_user
    current_user_permissions = (
        json.loads((await get_user_permissions(request)).body)
    ).get("data", [])
    async with async_session() as session:
        await session.begin()
        try:
            role = (
                await session.execute(
                    Select(Role)
                    .where(Role.id == role_id)
                    .options(selectinload(Role.users), selectinload(Role.exact_roles))
                )
            ).scalar_one_or_none()
            if not role:
                await log(
                    request,
                    "Delete",
                    "Role",
                    404,
                    "warning",
                    "Role Not Found for Deletion.",
                    {"role_id": role_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Role not found"}, 404
                )
                return finalize_request(response)
            if role.users and len(role.users) > 0:
                await log(
                    request,
                    "Delete",
                    "Role",
                    400,
                    "warning",
                    "Role Cannot Be Deleted Because It Has Users Associated with It.",
                    {"role_id": role_id, "users_count": len(role.users)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Role cannot be deleted because it has users associated with it",
                    },
                    400,
                )
                return finalize_request(response)
            missing_permissions = [
                permission.name
                for permission in role.exact_roles
                if permission.name not in current_user_permissions
            ]
            if missing_permissions and len(missing_permissions) > 0:
                await log(
                    request,
                    "Delete",
                    "Role",
                    403,
                    "warning",
                    "User Does Not Have All Required Permissions to Delete the Specified Role.",
                    {"role_id": role_id, "missing_permissions": missing_permissions},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": f"You Cannot delete a role having permissions you don't have.",
                    },
                    403,
                )
                return finalize_request(response)
            role.exact_roles.clear()
            await session.flush()
            await session.delete(role)
            await log(
                request,
                "Delete",
                "Role",
                200,
                "info",
                "Role Deleted Successfully.",
                {"role_id": role_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Role deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Role",
                500,
                "error",
                "An Error Occurred while Deleting Role.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while deleting role"},
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/roles")
@is_logged_in
@rate_limit
@is_authorized(["View Roles"])
async def get_roles(request: Request):
    """
    This route is used to get all roles.
    It will return a list of roles.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Roles",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        async with async_session() as session:
            query = Select(Role).options(
                selectinload(Role.exact_roles), selectinload(Role.users)
            )
            query = query.where(Role.level >= current_user.role.level)
            if query_search:
                query = query.where(func.lower(Role.name).startswith(query_search))
            roles = (await session.execute(query.order_by(Role.name))).scalars().all()
            await log(
                request,
                "Get",
                "Roles",
                200,
                "info",
                "Roles Retrieved Successfully.",
                {"roles_count": len(roles)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Roles retrieved successfully",
                    "data": [role.to_dict() for role in roles],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Roles",
            500,
            "error",
            "An Error Occurred while Retrieving Roles.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving roles"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/roles/{role_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Roles"])
async def get_role(request: Request, role_id: int):
    """
    This route is used to get a specific role by its ID.
    It will return the role data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            role = (
                await session.execute(
                    Select(Role)
                    .where(Role.id == role_id)
                    .options(selectinload(Role.exact_roles), selectinload(Role.users))
                )
            ).scalar_one_or_none()
            if not role:
                await log(
                    request,
                    "Get",
                    "Role",
                    404,
                    "warning",
                    "Role Not Found for Retrieval.",
                    {"role_id": role_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Role not found"}, 404
                )
                return finalize_request(response)
            permissions = (json.loads((await get_user_permissions(request)).body)).get(
                "data", []
            )
            missing_permissions = [
                permission.name
                for permission in role.exact_roles
                if permission.name not in permissions
            ]
            if missing_permissions and len(missing_permissions) > 0:
                await log(
                    request,
                    "Get",
                    "Role",
                    403,
                    "warning",
                    "User Does Not Have All Required Permissions to View the Specified Role.",
                    {"role_id": role_id, "missing_permissions": missing_permissions},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": f"You Cannot view a role having permissions you don't have.",
                    },
                    403,
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Role",
                200,
                "info",
                "Role Retrieved Successfully.",
                {"role_id": role_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Role retrieved successfully",
                    "data": {
                        "role": role.full_to_dict(),
                        "permissions": permissions,
                    },
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Role",
            500,
            "error",
            "An Error Occurred while Retrieving Role.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving role"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/roles/search")
@is_logged_in
@rate_limit
@is_authorized(["View Roles"])
async def search_roles(request: Request):
    """
    This route is used to search roles by name.
    It will return a list of roles matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Roles",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        async with async_session() as session:
            roles = (
                (
                    await session.execute(
                        Select(Role)
                        .where(
                            Role.level >= current_user.role.level,
                            func.lower(Role.name).startswith(query_search),
                        )
                        .order_by(Role.name)
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Search",
                "Roles",
                200,
                "info",
                "Roles Search Completed Successfully.",
                {"query": query_search, "roles_count": len(roles)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Roles search completed successfully",
                    "data": [role.min_to_dict() for role in roles],
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Roles",
            500,
            "error",
            "An Error Occurred while Searching Roles.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while searching roles"},
            500,
        )
        return finalize_request(response)


@admin_prefix.post("/courses")
@is_logged_in
@rate_limit
@is_authorized(["Add Courses"])
async def create_course(request: Request):
    """
    This route is used to create a new course.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Course",
            400,
            "warning",
            "No Data Provided for Creating Course.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Course",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    code = data.get("code", "").strip().upper()
    description = data.get("description", "").strip()
    faculty_id = data.get("faculty_id", None)
    department_id = data.get("department_id", None)
    year_id = data.get("year_id", None)
    credits = data.get("credits", None)
    max_students = data.get("max_students", None)
    if (
        not name
        or not code
        or not faculty_id
        or not department_id
        or not year_id
        or not credits
    ):
        await log(
            request,
            "Add",
            "Course",
            400,
            "warning",
            "Missing Required Fields for Course Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if (
        (
            not is_int(faculty_id)
            or int(faculty_id) < 1
            or not is_int(department_id)
            or int(department_id) < 1
            or not is_int(year_id)
            or int(year_id) < 1
        )
        or not is_int(credits)
        or int(credits) < 1
        or (max_students and (not is_int(max_students) or int(max_students) < 1))
    ):
        await log(
            request,
            "Add",
            "Course",
            400,
            "warning",
            "Invalid Data Provided for Course Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Add",
                    "Course",
                    404,
                    "warning",
                    "Faculty Not Found for Course Creation.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == int(department_id))
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Add",
                    "Course",
                    404,
                    "warning",
                    "Department Not Found for Course Creation.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(
                    request,
                    "Add",
                    "Course",
                    400,
                    "warning",
                    "Department Does Not Belong to the Specified Faculty for Course Creation.",
                    {"department_id": department_id, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department does not belong to the specified faculty",
                    },
                    400,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == int(year_id)))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Add",
                    "Course",
                    404,
                    "warning",
                    "Year Not Found for Course Creation.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            existing_course = (
                await session.execute(
                    Select(Subject).where(
                        Subject.faculty_id == int(faculty_id),
                        Subject.department_id == int(department_id),
                        Subject.year_id == int(year_id),
                        func.lower(Subject.code) == code.lower(),
                    )
                )
            ).scalar_one_or_none()
            if existing_course:
                await log(
                    request,
                    "Add",
                    "Course",
                    400,
                    "warning",
                    "Course with this code Already Exists in the Specified Faculty, Department and Year.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course with this code already exists in the specified criteria",
                    },
                    400,
                )
                return finalize_request(response)
            course = Subject(
                name=name,
                code=code,
                faculty_id=faculty.id,
                department_id=department.id,
                year_id=year.id,
                credits=int(credits),
                details={
                    "max_students": int(max_students) if max_students else None,
                    "description": description,
                },
            )
            session.add(course)
            await session.flush()
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course created successfully",
                    "data": course.min_to_dict(),
                },
                201,
            )
            await log(
                request,
                "Add",
                "Course",
                201,
                "info",
                "Course Created Successfully.",
                {"course": course.min_to_dict()},
                current_user.id,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Course",
                500,
                "error",
                "An Error Occurred while Creating Course.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating course",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/courses/{course_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Courses"])
async def update_course(request: Request, course_id: int):
    """
    This route is used to update an existing course.
    It will return the updated course data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Course",
            400,
            "warning",
            "No Data Provided for Updating Course.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Course",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    code = data.get("code", "").strip().upper()
    description = data.get("description", "").strip()
    faculty_id = data.get("faculty_id", None)
    department_id = data.get("department_id", None)
    year_id = data.get("year_id", None)
    credits = data.get("credits", None)
    max_students = data.get("max_students", None)
    if (
        not name
        or not code
        or not faculty_id
        or not department_id
        or not year_id
        or not credits
    ):
        await log(
            request,
            "Edit",
            "Course",
            400,
            "warning",
            "Missing Required Fields for Course Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if (
        (
            not is_int(faculty_id)
            or int(faculty_id) < 1
            or not is_int(department_id)
            or int(department_id) < 1
            or not is_int(year_id)
            or int(year_id) < 1
        )
        or not is_int(credits)
        or int(credits) < 1
        or (max_students and (not is_int(max_students) or int(max_students) < 1))
    ):
        await log(
            request,
            "Edit",
            "Course",
            400,
            "warning",
            "Invalid Data Provided for Course Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            course = (
                await session.execute(Select(Subject).where(Subject.id == course_id))
            ).scalar_one_or_none()
            if not course:
                await log(
                    request,
                    "Edit",
                    "Course",
                    404,
                    "warning",
                    "Course Not Found for Update.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course not found"}, 404
                )
                return finalize_request(response)
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Edit",
                    "Course",
                    404,
                    "warning",
                    "Faculty Not Found for Course Update.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == int(department_id))
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Edit",
                    "Course",
                    404,
                    "warning",
                    "Department Not Found for Course Update.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(
                    request,
                    "Edit",
                    "Course",
                    400,
                    "warning",
                    "Department Does Not Belong to the Specified Faculty for Course Update.",
                    {"department_id": department_id, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department does not belong to the specified faculty",
                    },
                    400,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == int(year_id)))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Edit",
                    "Course",
                    404,
                    "warning",
                    "Year Not Found for Course Update.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            existing_course = (
                await session.execute(
                    Select(Subject).where(
                        Subject.faculty_id == int(faculty_id),
                        Subject.department_id == int(department_id),
                        Subject.year_id == int(year_id),
                        func.lower(Subject.code) == code.lower(),
                    )
                )
            ).scalar_one_or_none()
            if existing_course and existing_course.id != course.id:
                await log(
                    request,
                    "Edit",
                    "Course",
                    400,
                    "warning",
                    "Course with this code Already Exists in the Specified Faculty, Department and Year for Course Update.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course with this code already exists in the specified criteria",
                    },
                    400,
                )
                return finalize_request(response)
            course.name = name
            course.code = code
            course.faculty_id = faculty.id
            course.department_id = department.id
            course.year_id = year.id
            course.credits = int(credits)
            course.details["max_students"] = int(max_students) if max_students else None
            course.details["description"] = description
            await session.flush()
            await log(
                request,
                "Edit",
                "Course",
                200,
                "info",
                "Course Updated Successfully.",
                {"course": course.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course updated successfully",
                    "data": course.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course",
                500,
                "error",
                "An Error Occurred while Updating Course.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating course",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/courses/{course_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Courses"])
async def delete_course(request: Request, course_id: int):
    """
    This route is used to delete an existing course.
    It will return a success message if the course is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == course_id)
                    .options(selectinload(Subject.users))
                )
            ).scalar_one_or_none()
            if not course:
                await log(
                    request,
                    "Delete",
                    "Course",
                    404,
                    "warning",
                    "Course Not Found for Deletion.",
                    {"course_id": course_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course not found"}, 404
                )
                return finalize_request(response)
            if course.users and len(course.users) > 0:
                await log(
                    request,
                    "Delete",
                    "Course",
                    400,
                    "warning",
                    "Course Cannot Be Deleted Because It Has Users Associated with It.",
                    {"course_id": course_id, "users_count": len(course.users)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course cannot be deleted because it has users associated with it",
                    },
                    400,
                )
                return finalize_request(response)
            await session.delete(course)
            await log(
                request,
                "Delete",
                "Course",
                200,
                "info",
                "Course Deleted Successfully.",
                {"course_id": course_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Course deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Course",
                500,
                "error",
                "An Error Occurred while Deleting Course.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting course",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/courses")
@is_logged_in
@rate_limit
@is_authorized(["View Courses"])
async def get_courses(request: Request):
    """
    This route is used to get all courses.
    It will return a list of courses.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Courses",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        if (
            faculty_id
            and (not is_int(faculty_id) or int(faculty_id) < 1)
            or department_id
            and (not is_int(department_id) or int(department_id) < 1)
            or year_id
            and (not is_int(year_id) or int(year_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Courses",
                400,
                "warning",
                "Invalid Data Provided for Course Retrieval.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            query = Select(Subject)
            # if not current_user.role.level == 1:
            #     query = query.join(UserSubjectLink, Subject.id == UserSubjectLink.subject_id).where(UserSubjectLink.user_id == current_user.id)
            query = query.options(
                selectinload(Subject.faculty),
                selectinload(Subject.department),
                selectinload(Subject.year),
                selectinload(Subject.users),
            )
            if faculty_id:
                query = query.where(Subject.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Subject.department_id == int(department_id))
            if year_id:
                query = query.where(Subject.year_id == int(year_id))
            if query_search:
                query = query.where(
                    or_(
                        func.lower(Subject.name).startswith(query_search),
                        func.lower(Subject.code).startswith(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Courses",
                    400,
                    "warning",
                    "Invalid Limit Provided for Courses Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(Subject.name)
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Courses",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Courses " "Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            courses = result[:limit]
            await log(
                request,
                "Get",
                "Courses",
                200,
                "info",
                "Courses Retrieved Successfully.",
                {"courses_count": len(courses)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Courses retrieved successfully",
                    "data": [course.to_dict() for course in courses],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Courses",
            500,
            "error",
            "An Error Occurred while Retrieving Courses.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while retrieving courses",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/courses/view/{course_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Courses"])
async def get_course(request: Request, course_id: int):
    """
    This route is used to get a specific course by its ID.
    It will return the course data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course = (
                await session.execute(
                    Select(Subject)
                    .where(Subject.id == course_id)
                    .options(
                        selectinload(Subject.faculty),
                        selectinload(Subject.department),
                        selectinload(Subject.year),
                        selectinload(Subject.users),
                    )
                )
            ).scalar_one_or_none()
            if not course:
                await log(
                    request,
                    "Get",
                    "Course",
                    404,
                    "warning",
                    "Course Not Found for Retrieval.",
                    {"course_id": course_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Course not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Course",
                200,
                "info",
                "Course Retrieved Successfully.",
                {"course_id": course_id},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course retrieved successfully",
                    "data": course.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Course",
            500,
            "error",
            "An Error Occurred while Retrieving Course.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while retrieving course"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/courses/search")
@is_logged_in
@rate_limit
# @is_authorized(['View Courses'])
async def search_courses(request: Request):
    """
    This route is used to search courses by name or code.
    It will return a list of courses matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Courses",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        if (
            faculty_id
            and (not is_int(faculty_id) or int(faculty_id) < 1)
            or department_id
            and (not is_int(department_id) or int(department_id) < 1)
            or year_id
            and (not is_int(year_id) or int(year_id) < 1)
        ):
            await log(
                request,
                "Search",
                "Courses",
                400,
                "warning",
                "Invalid Data Provided for Course Search.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Search",
                        "Courses",
                        404,
                        "warning",
                        "Faculty Not Found for Course Search.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if not department:
                    await log(
                        request,
                        "Search",
                        "Courses",
                        404,
                        "warning",
                        "Department Not Found for Course Search.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Department not found"}, 404
                    )
                    return finalize_request(response)
                if not faculty_id:
                    await log(
                        request,
                        "Search",
                        "Courses",
                        400,
                        "warning",
                        "Faculty ID Must Be Provided When Department ID is Given for Course Search.",
                        {"department_id": department_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Faculty must be provided when department is given",
                        },
                        400,
                    )
                    return finalize_request(response)
                if department.faculty_id != int(faculty_id):
                    await log(
                        request,
                        "Search",
                        "Courses",
                        400,
                        "warning",
                        "Department Does Not Belong to the Specified Faculty for Course Search.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department does not belong to the specified faculty",
                        },
                        400,
                    )
                    return finalize_request(response)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Search",
                        "Courses",
                        404,
                        "warning",
                        "Year Not Found for Course Search.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
            query = Select(Subject)
            if not current_user.role.level == 1:
                query = query.join(
                    UserSubjectLink, Subject.id == UserSubjectLink.subject_id
                ).where(UserSubjectLink.user_id == current_user.id)
            if faculty_id:
                query = query.where(Subject.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Subject.department_id == int(department_id))
            if year_id:
                query = query.where(Subject.year_id == int(year_id))
            if query_search:
                query = query.where(
                    or_(
                        func.lower(Subject.name).startswith(query_search),
                        func.lower(Subject.code).startswith(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Search",
                    "Courses",
                    400,
                    "warning",
                    "Invalid Limit Provided for Courses Search.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(Subject.name)
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Search",
                    "Courses",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Courses " "Search.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            courses = result[:limit]
            await log(
                request,
                "Search",
                "Courses",
                200,
                "info",
                "Courses Search Completed Successfully.",
                {"query": query_search, "courses_count": len(courses)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Courses search completed successfully",
                    "data": [course.min_to_dict() for course in courses],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Courses",
            500,
            "error",
            "An Error Occurred while Searching Courses.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while searching courses"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/courses/search-registered")
@is_logged_in
@rate_limit
@is_authorized(["View Courses"])
async def search_registered_courses(request: Request):
    """
    This route is used to search registered courses by name or code.
    It will return a list of courses matching the search query.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Search",
                "Registered Courses",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower() if data else ""
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        async with async_session() as session:
            query = (
                Select(Subject)
                .join(UserSubjectLink, UserSubjectLink.subject_id == Subject.id)
                .where(UserSubjectLink.user_id == current_user.id)
            )
            if query_search:
                query = query.where(
                    or_(
                        func.lower(Subject.name).startswith(query_search),
                        func.lower(Subject.code).startswith(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Search",
                    "Registered Courses",
                    400,
                    "warning",
                    "Invalid Limit Provided for Registered Courses Search.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            result = (
                (
                    await session.execute(
                        query.order_by(Subject.name)
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Search",
                    "Registered Courses",
                    400,
                    "warning",
                    "Invalid Page Number Provided for " "Registered Courses Search.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            courses = result[:limit]
            await log(
                request,
                "Search",
                "Registered Courses",
                200,
                "info",
                "Registered Courses Search Completed Successfully.",
                {"query": query_search, "courses_count": len(courses)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Registered courses search completed successfully",
                    "data": [course.min_to_dict() for course in courses],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Search",
            "Registered Courses",
            500,
            "error",
            "An Error Occurred while Searching Registered Courses.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while searching registered courses",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.post("/course-maps")
@is_logged_in
@rate_limit
@is_authorized(["Add Course Maps"])
async def create_course_map(request: Request):
    """
    This route is used to create a new course map.
    :param request:
    :return:
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Course Map",
            400,
            "warning",
            "No Data Provided for Creating Course Map.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Course Map",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    faculty_id = data.get("faculty_id", None)
    department_id = data.get("department_id", None)
    year_id = data.get("year_id", None)
    years = data.get("years", None)
    terms = data.get("terms", None)
    if not faculty_id or not department_id or not year_id or not years or not terms:
        await log(
            request,
            "Add",
            "Course Map",
            400,
            "warning",
            "Missing Required Fields for Course Map Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if (
        (
            not is_int(faculty_id)
            or int(faculty_id) < 1
            or not is_int(department_id)
            or int(department_id) < 1
            or not is_int(year_id)
            or int(year_id) < 1
        )
        or not is_int(years)
        or int(years) < 1
        or not is_int(terms)
        or int(terms) < 1
    ):
        await log(
            request,
            "Add",
            "Course Map",
            400,
            "warning",
            "Invalid Data Provided for Course Map Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    if int(years) < 4 or int(years) > 7 or int(terms) < 1 or int(terms) > 4:
        await log(
            request,
            "Add",
            "Course Map",
            400,
            "warning",
            "Years or Terms Out of Allowed Range for Course Map Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Years must be between 4 and 7 and terms/year must be between 1 and 4",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Add",
                    "Course Map",
                    404,
                    "warning",
                    "Faculty Not Found for Course Map Creation.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == int(department_id))
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Add",
                    "Course Map",
                    404,
                    "warning",
                    "Department Not Found for Course Map Creation.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(
                    request,
                    "Add",
                    "Course Map",
                    400,
                    "warning",
                    "Department Does Not Belong to the Specified Faculty for Course Map Creation.",
                    {"department_id": department_id, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department does not belong to the specified faculty",
                    },
                    400,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == int(year_id)))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Add",
                    "Course Map",
                    404,
                    "warning",
                    "Year Not Found for Course Map Creation.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            existing_course_map = (
                await session.execute(
                    Select(Roadmap).where(
                        Roadmap.status == True,
                        Roadmap.faculty_id == int(faculty_id),
                        Roadmap.department_id == int(department_id),
                        Roadmap.year_id == int(year_id),
                        Roadmap.type == 2,
                    )
                )
            ).scalar_one_or_none()
            if existing_course_map:
                await log(
                    request,
                    "Add",
                    "Course Map",
                    400,
                    "warning",
                    "Course Map Already Exists in the Specified Faculty, Department and Year.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course map already exists in the specified criteria",
                    },
                    400,
                )
                return finalize_request(response)
            course_map = Roadmap(
                faculty_id=faculty.id,
                department_id=department.id,
                year_id=year.id,
                author_id=current_user.id,
                status=True,
                type=2,
                details={
                    "years": [f"Level {i+1}" for i in range(int(years))],
                    "terms": int(terms),
                },
            )
            session.add(course_map)
            await session.flush()
            await log(
                request,
                "Add",
                "Course Map",
                201,
                "info",
                "Course Map Created Successfully.",
                {"course_map": course_map.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course map created successfully",
                    "data": course_map.min_to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Creating Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/course-maps/{course_map_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Course Maps"])
async def update_course_map(request: Request, course_map_id: int):
    """
    This route is used to update an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "No Data Provided for Updating Course Map.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    faculty_id = data.get("faculty_id", None)
    department_id = data.get("department_id", None)
    year_id = data.get("year_id", None)
    years = data.get("years", None)
    terms = data.get("terms", None)
    if not faculty_id or not department_id or not year_id or not years or not terms:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Missing Required Fields for Course Map Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if (
        (
            not is_int(faculty_id)
            or int(faculty_id) < 1
            or not is_int(department_id)
            or int(department_id) < 1
            or not is_int(year_id)
            or int(year_id) < 1
        )
        or not is_int(years)
        or int(years) < 1
        or not is_int(terms)
        or int(terms) < 1
    ):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Invalid Data Provided for Course Map Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    if int(years) < 4 or int(years) > 7 or int(terms) < 1 or int(terms) > 4:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Years or Terms Out of Allowed Range for Course Map Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Years must be between 4 and 7 and terms/year must be between 1 and 4",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            current_user = await session.merge(current_user)
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(Roadmap.id == course_map_id)
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                        selectinload(Roadmap.courses),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Update.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Faculty Not Found for Course Map Update.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == int(department_id))
                )
            ).scalar_one_or_none()
            if not department:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Department Not Found for Course Map Update.",
                    {"department_id": department_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Department not found"}, 404
                )
                return finalize_request(response)
            if department.faculty_id != faculty.id:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Department Does Not Belong to the Specified Faculty for Course Map Update.",
                    {"department_id": department_id, "faculty_id": faculty_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department does not belong to the specified faculty",
                    },
                    400,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == int(year_id)))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Year Not Found for Course Map Update.",
                    {"year_id": year_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            existing_course_map = (
                await session.execute(
                    Select(Roadmap).where(
                        Roadmap.status == True,
                        Roadmap.faculty_id == int(faculty_id),
                        Roadmap.department_id == int(department_id),
                        Roadmap.year_id == int(year_id),
                        Roadmap.type == 2,
                    )
                )
            ).scalar_one_or_none()
            if existing_course_map and existing_course_map.id != course_map.id:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Course Map Already Exists in the Specified Faculty, Department and Year for Course Map Update.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course map already exists in the specified criteria",
                    },
                    400,
                )
                return finalize_request(response)
            courses_to_be_removed = [
                c
                for c in course_map.courses
                if c.year > int(years) or c.term > int(terms)
            ]
            if len(courses_to_be_removed) > 0:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Courses Exist in the Course Map That Exceed the New Years or Terms Limit for Course Map Update.",
                    {
                        "data": dict(data),
                        "courses_to_be_removed": [
                            c.min_to_dict() for c in courses_to_be_removed
                        ],
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Some Courses exist in the course map that exceed the new years or terms limit. Please remove those courses first.",
                    },
                    400,
                )
                return finalize_request(response)
            course_map.faculty_id = faculty.id
            course_map.department_id = department.id
            course_map.year_id = year.id
            course_map.author_id = current_user.id
            course_map.details["years"] = [f"Level {i+1}" for i in range(int(years))]
            course_map.details["terms"] = int(terms)
            await session.flush()
            await log(
                request,
                "Edit",
                "Course Map",
                200,
                "info",
                "Course Map Updated Successfully.",
                {"course_map": course_map.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course map updated successfully",
                    "data": course_map.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Updating Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/course-maps/{course_map_id}/years")
@is_logged_in
@rate_limit
@is_authorized(["Edit Course Maps"])
async def update_course_map_years(request: Request, course_map_id: int):
    """
    This route is used to update the years of an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "No Data Provided for Updating Course Map Years.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    year_index = data.get("year_index", None)
    year_name = data.get("year_name", "").strip()
    if (
        not year_index
        or not year_name
        or year_name == ""
        or not is_int(year_index)
        or int(year_index) < 1
    ):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Missing Required Fields for Course Map Years Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (
                await session.execute(
                    Select(Roadmap).where(Roadmap.id == course_map_id)
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Years Update.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            years = course_map.details.get("years", [])
            if int(year_index) > len(years):
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Year Index Out of Range for Course Map Years Update.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year index out of range"}, 400
                )
                return finalize_request(response)
            years[int(year_index) - 1] = year_name
            course_map.details["years"] = years
            await session.flush()
            await log(
                request,
                "Edit",
                "Course Map",
                200,
                "info",
                "Course Map Years Updated Successfully.",
                {"course_map": course_map.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course map years updated successfully",
                    "data": course_map.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Updating Course Map Years.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating course map years",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.post("/course-maps/{course_map_id}/courses")
@is_logged_in
@rate_limit
@is_authorized(["Edit Course Maps"])
async def add_course_to_course_map(request: Request, course_map_id: int):
    """
    This route is used to add a course to an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "No Data Provided for Adding Course to Course Map.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    subject_id = data.get("subject_id", None)
    year_index = data.get("year_index", None)
    term = data.get("term", None)
    rank = data.get("rank", None)
    if (
        not subject_id
        or not year_index
        or not term
        or not rank
        or not is_int(subject_id)
        or int(subject_id) < 1
        or not is_int(year_index)
        or int(year_index) < 1
        or not is_int(term)
        or int(term) < 1
        or not is_int(rank)
        or int(rank) < 1
    ):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Missing or Invalid Required Fields for Adding Course to Course Map.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(Roadmap.id == course_map_id)
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Adding Course.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            if int(year_index) > len(course_map.details.get("years", [])) or int(
                term
            ) > course_map.details.get("terms", 0):
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Year Index or Term Out of Range for Adding Course to Course Map.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year index or term out of range"},
                    400,
                )
                return finalize_request(response)
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Subject Not Found for Adding to Course Map.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if (
                subject.faculty_id != course_map.faculty_id
                or subject.department_id != course_map.department_id
                or subject.year_id != course_map.year_id
            ):
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Subject Does Not Belong to the Same Faculty, Department or Year as Course Map for Adding to Course Map.",
                    {"subject_id": subject_id, "course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject does not belong to the same criteria as course map",
                    },
                    400,
                )
                return finalize_request(response)
            existing_course = (
                await session.execute(
                    Select(RoadmapCourse).where(
                        RoadmapCourse.roadmap_id == course_map.id,
                        RoadmapCourse.subject_id == subject.id,
                    )
                )
            ).scalar_one_or_none()
            if existing_course:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Subject Already Added to Course Map.",
                    {"subject_id": subject_id, "course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject already added to course map",
                    },
                    400,
                )
                return finalize_request(response)
            courses = (
                (
                    await session.execute(
                        Select(RoadmapCourse).where(
                            RoadmapCourse.roadmap_id == course_map.id,
                            RoadmapCourse.year == int(year_index),
                            RoadmapCourse.term == int(term),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if int(rank) > len(courses) + 1:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Rank Out of Allowed Range for Adding Course to Course Map.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Rank out of range"}, 400
                )
                return finalize_request(response)
            for c in courses:
                if c.rank >= int(rank):
                    c.rank += 1
            course = RoadmapCourse(
                roadmap=course_map,
                subject=subject,
                year=int(year_index),
                term=int(term),
                rank=int(rank),
            )
            session.add(course)
            await log(
                request,
                "Edit",
                "Course Map",
                201,
                "info",
                "Course Added to Course Map Successfully.",
                {"course_map": course_map.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course added to course map successfully",
                    "data": course_map.to_dict(),
                },
                201,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Adding Course to Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while adding course to course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/course-maps/{course_map_id}/courses/{course_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Course Maps"])
async def update_course_in_course_map(
    request: Request, course_map_id: int, course_id: int
):
    """
    This route is used to update a course in an existing course map.
    It will return the updated course map data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "No Data Provided for Updating Course in Course Map.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    year_index = data.get("year_index", None)
    term = data.get("term", None)
    rank = data.get("rank", None)
    if (
        not year_index
        or not term
        or not rank
        or not is_int(year_index)
        or int(year_index) < 1
        or not is_int(term)
        or int(term) < 1
        or not is_int(rank)
        or int(rank) < 1
    ):
        await log(
            request,
            "Edit",
            "Course Map",
            400,
            "warning",
            "Missing or Invalid Required Fields for Updating Course in Course Map.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(Roadmap.id == course_map_id)
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Updating Course.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            if int(year_index) > len(course_map.details.get("years", [])) or int(
                term
            ) > course_map.details.get("terms", 0):
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Year Index or Term Out of Range for Updating Course in Course Map.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Year index or term out of range"},
                    400,
                )
                return finalize_request(response)
            course = (
                await session.execute(
                    Select(RoadmapCourse).where(RoadmapCourse.id == course_id)
                )
            ).scalar_one_or_none()
            if not course or course.roadmap_id != course_map.id:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Not Found in the Specified Course Map for Update.",
                    {"course_id": course_id, "course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course not found in the specified course map",
                    },
                    404,
                )
                return finalize_request(response)
            courses = (
                (
                    await session.execute(
                        Select(RoadmapCourse).where(
                            RoadmapCourse.roadmap_id == course_map.id,
                            RoadmapCourse.year == int(year_index),
                            RoadmapCourse.term == int(term),
                        )
                    )
                )
                .scalars()
                .all()
            )
            courses_length = len(courses)
            if course in courses:
                courses_length -= 1
            if int(year_index) != course.year or int(term) != course.term:
                courses_length += 1
            if int(rank) > courses_length:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    400,
                    "warning",
                    "Rank Out of Allowed Range for Updating Course in Course Map.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Rank out of range"}, 400
                )
                return finalize_request(response)
            for c in courses:
                if c.id == course.id:
                    continue
                if c.rank >= int(rank):
                    c.rank += 1
            course.year = int(year_index)
            course.term = int(term)
            course.rank = int(rank)
            await session.flush()
            await log(
                request,
                "Edit",
                "Course Map",
                200,
                "info",
                "Course in Course Map Updated Successfully.",
                {"course_map": course_map.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course in course map updated successfully",
                    "data": course_map.min_to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Updating Course in Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating course in course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/course-maps/{course_map_id}/courses/{course_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Course Maps"])
async def delete_course_from_course_map(
    request: Request, course_map_id: int, course_id: int
):
    """
    This route is used to delete a course from an existing course map.
    It will return a success message if the course is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(Roadmap.id == course_map_id)
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Deleting Course.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            course = (
                await session.execute(
                    Select(RoadmapCourse).where(RoadmapCourse.id == course_id)
                )
            ).scalar_one_or_none()
            if not course or course.roadmap_id != course_map.id:
                await log(
                    request,
                    "Edit",
                    "Course Map",
                    404,
                    "warning",
                    "Course Not Found in the Specified Course Map for Deletion.",
                    {"course_id": course_id, "course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Course not found in the specified course map",
                    },
                    404,
                )
                return finalize_request(response)
            rank = course.rank
            year = course.year
            term = course.term
            await session.delete(course)
            courses = (
                (
                    await session.execute(
                        Select(RoadmapCourse).where(
                            RoadmapCourse.roadmap_id == course_map.id,
                            RoadmapCourse.year == year,
                            RoadmapCourse.term == term,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for c in courses:
                if c.rank > rank:
                    c.rank -= 1
            await log(
                request,
                "Edit",
                "Course Map",
                200,
                "info",
                "Course Deleted from Course Map Successfully.",
                {"course_map": course_map.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course deleted from course map successfully",
                    "data": course_map.to_dict(),
                },
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Deleting Course from Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting course from course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/course-maps/{course_map_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Course Maps"])
async def delete_course_map(request: Request, course_map_id: int):
    """
    This route is used to delete an existing course map.
    It will return a success message if the course map is deleted successfully.
    """
    current_user = request.state.current_user
    async with async_session() as session:
        await session.begin()
        try:
            course_map = (
                await session.execute(
                    Select(Roadmap).where(Roadmap.id == course_map_id)
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Delete",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found for Deletion.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            await session.delete(course_map)
            await log(
                request,
                "Delete",
                "Course Map",
                200,
                "info",
                "Course Map Deleted Successfully.",
                {"course_map_id": course_map_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Course map deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Course Map",
                500,
                "error",
                "An Error Occurred while Deleting Course Map.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting course map",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/course-maps")
@is_logged_in
@rate_limit
@is_authorized(["View Course Maps"])
async def get_course_maps(request: Request):
    """
    This route is used to get all course maps.
    It will return a list of course maps.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Course Maps",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        if (
            (faculty_id and (not is_int(faculty_id) or int(faculty_id) < 1))
            or (department_id and (not is_int(department_id) or int(department_id) < 1))
            or (year_id and (not is_int(year_id) or int(year_id) < 1))
        ):
            await log(
                request,
                "Get",
                "Course Maps",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Course Maps.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        async with async_session() as session:
            query = (
                Select(Roadmap)
                .where(Roadmap.status == True, Roadmap.type == 2)
                .options(
                    selectinload(Roadmap.faculty),
                    selectinload(Roadmap.department),
                    selectinload(Roadmap.year),
                    selectinload(Roadmap.author),
                    selectinload(Roadmap.courses),
                )
            )
            if faculty_id:
                query = query.where(Roadmap.faculty_id == int(faculty_id))
            if department_id:
                query = query.where(Roadmap.department_id == int(department_id))
            if year_id:
                query = query.where(Roadmap.year_id == int(year_id))
            result = (
                (
                    await session.execute(
                        query.order_by(Roadmap.id.desc())
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Course Maps",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Course Maps " "Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Course Maps",
                    400,
                    "warning",
                    "Invalid Limit Provided for Course Maps Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            course_maps = result[:limit]
            await log(
                request,
                "Get",
                "Course Maps",
                200,
                "info",
                "Course Maps Retrieved Successfully.",
                {"filters": dict(data), "count": len(course_maps)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course maps retrieved successfully",
                    "data": [
                        {"roadmap": cm.to_dict(), "courses_count": len(cm.courses)}
                        for cm in course_maps
                    ],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Course Maps",
            500,
            "error",
            "An Error Occurred while Getting Course Maps.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting course maps",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/course-maps/{course_map_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Course Maps"])
async def get_course_map(request: Request, course_map_id: int):
    """
    This route is used to get a specific course map by its ID.
    It will return the course map data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            course_map = (
                await session.execute(
                    Select(Roadmap)
                    .where(
                        Roadmap.id == course_map_id,
                        Roadmap.status == True,
                        Roadmap.type == 2,
                    )
                    .options(
                        selectinload(Roadmap.faculty),
                        selectinload(Roadmap.department),
                        selectinload(Roadmap.year),
                        selectinload(Roadmap.author),
                    )
                )
            ).scalar_one_or_none()
            if not course_map:
                await log(
                    request,
                    "Get",
                    "Course Map",
                    404,
                    "warning",
                    "Course Map Not Found.",
                    {"course_map_id": course_map_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Course map not found"}, 404
                )
                return finalize_request(response)
            courses = (
                (
                    await session.execute(
                        Select(RoadmapCourse)
                        .where(RoadmapCourse.roadmap_id == course_map.id)
                        .order_by(
                            RoadmapCourse.year.asc(),
                            RoadmapCourse.term.asc(),
                            RoadmapCourse.rank.asc(),
                        )
                        .options(
                            selectinload(RoadmapCourse.subject),
                            selectinload(RoadmapCourse.roadmap),
                        )
                    )
                )
                .scalars()
                .all()
            )
            years = [
                [[] for term in range(course_map.details.get("terms", 0))]
                for _ in range(len(course_map.details.get("years", [])))
            ]
            for course in courses:
                if 1 <= course.year <= len(years) and 1 <= course.term <= len(
                    years[course.year - 1]
                ):
                    if not years[course.year - 1][course.term - 1]:
                        years[course.year - 1][course.term - 1] = []
                    years[course.year - 1][course.term - 1].append(course.to_dict())
            await log(
                request,
                "Get",
                "Course Map",
                200,
                "info",
                "Course Map Retrieved Successfully.",
                {"course_map": course_map.to_dict(), "courses_count": len(courses)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Course map retrieved successfully",
                    "data": {
                        "roadmap": course_map.to_dict(),
                        "courses": years,
                        "courses_count": len(courses),
                    },
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Course Map",
            500,
            "error",
            "An Error Occurred while Getting Course Map.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting course map",
            },
            500,
        )
        return finalize_request(response)


async def get_unique_material_name(session, query, base_name) -> str:
    """
    This function is used to get a unique material name.
    """
    if not base_name or base_name == "":
        base_name = "Untitled"
    base_name = base_name.strip()
    if (
        base_name.endswith(")")
        and base_name.rfind("(") != -1
        and is_int(base_name[base_name.rfind("(") + 1 : -1])
    ):
        base_name = base_name[: base_name.rfind("(")].strip()
    unique_name = base_name
    counter = 1
    while True:
        existing_material = (
            await session.execute(query.where(Material.name == unique_name))
        ).scalar_one_or_none()
        if not existing_material:
            return unique_name
        unique_name = f"{base_name} ({counter})"
        counter += 1


@admin_prefix.post("/materials")
@is_logged_in
@rate_limit
@is_authorized(["Add Materials"])
@has_registered_subjects
async def create_material(request: Request):
    """
    This route is used to create a new material.
    It will return the created material data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "No Data Provided for Material Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    url = data.get("url", "").strip()
    type = (
        data.get("type", "").strip().lower()
    )  # File or Folder or YouTube or Drive or External
    parent_id = data.get("parent_id", None)  # Parent Folder ID
    subject_id = data.get("subject_id", None)  # Subject ID
    # file_type = data.get('file_type', '').strip().lower() # pdf, docx, pptx, xlsx, txt, zip, rar, image, video,
    # audio, ...
    allowed_file_types = [
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
    ]
    file = None
    if not type or type not in ["file", "folder", "youtube", "drive", "external"]:
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Invalid or Missing Material Type Provided for Material Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Material type must be one of the available types",
            },
            400,
        )
        return finalize_request(response)
    if parent_id and (not is_int(parent_id) or int(parent_id) < 1):
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Invalid Parent ID Provided for Material Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid parent ID provided"}, 400
        )
        return finalize_request(response)
    if not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Invalid or Missing Subject ID Provided for Material Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid subject was provided."}, 400
        )
        return finalize_request(response)
    if type == "folder":
        if not name or name == "":
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Missing Required Fields for Folder Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Folder Name is required"}, 400
            )
            return finalize_request(response)
    elif type in ["youtube", "drive", "external"]:
        if not name or name == "" or not url or url == "":
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Missing Required Fields for Link Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Name and URL are required"}, 400
            )
            return finalize_request(response)
        if type == "youtube" and not is_youtube_url(url):
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Invalid YouTube URL Provided for Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid YouTube URL provided"}, 400
            )
            return finalize_request(response)
        if type == "drive" and not is_drive_url(url):
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Invalid Google Drive URL Provided for Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Google Drive URL provided"}, 400
            )
            return finalize_request(response)
        if type == "external" and not is_valid_url(url):
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Invalid External URL Provided for Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid External URL provided"}, 400
            )
            return finalize_request(response)
    else:
        if not url or url == "":
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Missing Required Fields for File Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "File is required"}, 400
            )
            return finalize_request(response)
        file = await get_file_from_drive(
            url, current_user.google_refresh_token, request
        )
        if not file:
            await log(
                request,
                "Add",
                "Material",
                400,
                "warning",
                "Invalid File URL Provided for Material Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid File Provided."}, 400
            )
            return finalize_request(response)
        # if get_file_type(file.get('mimeType')) not in allowed_file_types:
        #     await log(request, "Add", "Material", 400, 'warning', 'Unsupported File Type Provided for Material Creation.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
    if name and name != "" and len(name) > 200:
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Material Name Exceeds Maximum Length for Material Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Material name exceeds maximum length of 200 characters",
            },
            400,
        )
        return finalize_request(response)
    if url and url != "" and len(url) > 200:
        await log(
            request,
            "Add",
            "Material",
            400,
            "warning",
            "Material URL Exceeds Maximum Length for Material Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Material URL exceeds maximum length of 200 characters",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Material).where(Material.id == int(parent_id))
                    )
                ).scalar_one_or_none()
                if not parent or parent.type != "folder":
                    await log(
                        request,
                        "Add",
                        "Material",
                        404,
                        "warning",
                        "Parent Folder Not Found for Material Creation.",
                        {"parent_id": parent_id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Parent folder not found"}, 404
                    )
                    return finalize_request(response)
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Add",
                    "Material",
                    404,
                    "warning",
                    "Subject Not Found for Material Creation.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            material_name = name if name and name != "" else file.get("name")
            unique_name_query = Select(Material).where(
                Material.subject_id == subject.id,
                Material.parent_id == (parent.id if parent_id else None),
                Material.type == type,
            )
            material = Material(
                name=(
                    await get_unique_material_name(session, unique_name_query, name)
                    if name and name != ""
                    else await get_unique_material_name(
                        session, unique_name_query, file.get("name")
                    )
                ),
                type=type,
                url=url if url and url != "" else None,
                subject_id=subject.id,
                author_id=current_user.id,
                parent_id=parent.id if parent_id else None,
                details={
                    "description": (
                        description if description and description != "" else None
                    ),
                    "file_data": get_file_data(file) if file else None,
                    "fetched": False,
                },
            )
            if file:
                material.details["file_data"] = get_file_data(file)
            session.add(material)
            is_file = material.type != "folder"
            await session.flush()
            await log(
                request,
                "Add",
                "Material",
                201,
                "info",
                "Material Created Successfully.",
                {"material": material.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material created successfully",
                    "data": material.min_to_dict(),
                },
                201,
            )
            await session.commit()
            if is_file:
                share_link = None
                if material.type == "file":
                    share_link = f"{os.environ.get('FRONTEND_URL')}/user/materials?subject_id={subject.id}&parent_id={parent.id if parent_id else ''}&material_id={material.id}"
                else:
                    share_link = material.url
                await create_notification(
                    request,
                    "material",
                    material.id,
                    f'New material "{material.name}" has been '
                    f'uploaded for subject "{subject.name}".',
                    share_link,
                )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Material",
                500,
                "error",
                "An Error Occurred while Creating Material.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating material",
                },
                500,
            )
            return finalize_request(response)


async def recursive_create_materials(
    fetched: dict,
    subject_id: int,
    parent_id: int | None,
    author_id: int,
    request: Request,
    session,
) -> bool | JSONResponse:
    try:
        current_user = request.state.current_user
        if not fetched or type(fetched) != dict or "data" not in fetched:
            await log(
                request,
                "Fetch",
                "Materials",
                400,
                "warning",
                "Invalid Fetched Data Provided for Recursive Creation of Materials.",
                {"fetched": fetched},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid Fetched Data From Google Drive.",
                },
                400,
            )
            return finalize_request(response)
        if "id" not in fetched.get("data", {}):
            await log(
                request,
                "Fetch",
                "Materials",
                400,
                "warning",
                "Invalid Data Structure from Google Drive during Recursive Creation.",
                {"fetched": fetched},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid Fetched Data From Google Drive.",
                },
                400,
            )
            return finalize_request(response)
        if "children" in fetched:
            data = fetched.get("data", {})
            unique_name_query = Select(Material).where(
                Material.subject_id == subject_id,
                Material.parent_id == (parent_id if parent_id else None),
                Material.type == "folder",
            )
            folder = Material(
                name=(
                    await get_unique_material_name(
                        session, unique_name_query, data.get("name")
                    )
                    if data.get("name") and data.get("name") != ""
                    else await get_unique_material_name(
                        session, unique_name_query, "Untitled"
                    )
                ),
                subject_id=subject_id,
                parent_id=parent_id if parent_id else None,
                author_id=author_id,
                type="folder",
            )
            session.add(folder)
            await session.flush()
            for child in fetched.get("children", []):
                result = await recursive_create_materials(
                    child, subject_id, folder.id, author_id, request, session
                )
                if type(result) != bool:
                    return result
            return True
        else:
            data = fetched.get("data", {})
            unique_name_query = Select(Material).where(
                Material.subject_id == subject_id,
                Material.parent_id == (parent_id if parent_id else None),
                Material.type == "file",
            )
            material = Material(
                name=(
                    await get_unique_material_name(
                        session, unique_name_query, data.get("name")
                    )
                    if data.get("name") and data.get("name") != ""
                    else await get_unique_material_name(
                        session, unique_name_query, "Untitled"
                    )
                ),
                subject_id=subject_id,
                parent_id=parent_id if parent_id else None,
                author_id=author_id,
                type="file",
                url=get_drive_url(data.get("id")),
                details={"file_data": data, "fetched": True},
            )
            session.add(material)
            await session.flush()
            return True
    except Exception as e:
        await log(
            request,
            "Fetch",
            "Materials",
            500,
            "error",
            "An Error Occurred while Recursively Creating Materials.",
            {"error": str(e)},
            current_user.id,
        )
        await session.rollback()
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while recursively creating materials",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/materials/fetch-one-from-drive")
@is_logged_in
@rate_limit
@is_authorized(["Add Materials"])
async def fetch_one_material_from_drive(request: Request):
    """
    This route is used to fetch a single material from Google Drive.
    It will return the fetched material data.
    """
    current_user = request.state.current_user
    data = request.query_params
    if not data:
        await log(
            request,
            "Fetch",
            "Material",
            400,
            "warning",
            "No Data Provided for Fetching Material from Google Drive.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Fetch",
            "Material",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    drive_url = data.get("drive_url", "").strip()
    if not drive_url or drive_url == "" or not is_drive_url(drive_url):
        await log(
            request,
            "Fetch",
            "Material",
            400,
            "warning",
            "Invalid or Missing Google Drive URL Provided for Fetching Material.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid Google Drive URL provided"}, 400
        )
        return finalize_request(response)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://www.googleapis.com/drive/v3/files/{get_drive_id(drive_url)}?fields=id,name,mimeType,webContentLink,webViewLink",
            params={"key": os.environ.get("GOOGLE_TOKEN_API_KEY")},
        ) as resp:
            if resp.status != 200:
                await log(
                    request,
                    "Fetch",
                    "Material",
                    400,
                    "warning",
                    "Failed to Fetch Material from Google Drive.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Failed to fetch material from Google Drive",
                    },
                    400,
                )
                return finalize_request(response)
            file_data = await resp.json()
            await log(
                request,
                "Fetch",
                "Material",
                200,
                "info",
                "Material Fetched from Google Drive Successfully.",
                {"file_data": file_data},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material fetched successfully",
                    "data": file_data,
                }
            )
            return finalize_request(response)


@admin_prefix.get("/materials/fetch-from-drive")
@is_logged_in
@rate_limit
@is_authorized(["Add Materials"])
async def fetch_materials_from_drive(request: Request):
    """
    This route is used to fetch materials from Google Drive.
    It will return the fetched materials data.
    """
    current_user = request.state.current_user
    data = request.query_params
    if not data:
        await log(
            request,
            "Fetch",
            "Materials",
            400,
            "warning",
            "No Data Provided for Fetching Materials from Google Drive.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Fetch",
            "Materials",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    drive_url = data.get("drive_url", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    parent_id = data.get("parent_id", None)  # Parent Folder ID
    if not drive_url or drive_url == "" or not is_drive_url(drive_url):
        await log(
            request,
            "Fetch",
            "Materials",
            400,
            "warning",
            "Invalid or Missing Google Drive URL Provided for Fetching Materials.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid Google Drive URL provided"}, 400
        )
        return finalize_request(response)
    if not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(
            request,
            "Fetch",
            "Materials",
            400,
            "warning",
            "Invalid or Missing Subject ID Provided for Fetching Materials.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid subject was provided."}, 400
        )
        return finalize_request(response)
    if parent_id and (not is_int(parent_id) or int(parent_id) < 1):
        await log(
            request,
            "Fetch",
            "Materials",
            400,
            "warning",
            "Invalid Parent ID Provided for Fetching Materials.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid parent ID provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Fetch",
                    "Materials",
                    404,
                    "warning",
                    "Subject Not Found for Fetching Materials.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Material).where(Material.id == int(parent_id))
                    )
                ).scalar_one_or_none()
                if not parent or parent.type != "folder":
                    await log(
                        request,
                        "Fetch",
                        "Materials",
                        404,
                        "warning",
                        "Parent Folder Not Found for Fetching Materials.",
                        {"parent_id": parent_id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Parent folder not found"}, 404
                    )
                    return finalize_request(response)
            file_id = get_drive_id(drive_url)
            if not file_id:
                await log(
                    request,
                    "Fetch",
                    "Materials",
                    400,
                    "warning",
                    "Invalid Google Drive URL Provided for Fetching Materials.",
                    {"data": dict(data)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Invalid Google Drive URL provided"},
                    400,
                )
                return finalize_request(response)
            fetched_data = await fetch_public_drive(
                file_id, os.environ.get("GOOGLE_TOKEN_API_KEY"), request
            )
            result = await recursive_create_materials(
                fetched_data,
                subject.id,
                int(parent_id) if parent_id else None,
                current_user.id,
                request,
                session,
            )
            if type(result) != bool:
                await session.rollback()
                response = result
                return finalize_request(response)
            await log(
                request,
                "Fetch",
                "Materials",
                201,
                "info",
                "Materials Fetched from Google Drive and Created Successfully.",
                {
                    "subject_id": subject.id,
                    "parent_id": parent.id if parent_id else None,
                },
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Materials fetched and created successfully",
                },
                201,
            )
            await session.commit()
            share_link = f"{os.environ.get('FRONTEND_URL')}/user/materials?subject_id={subject.id}&parent_id={parent.id if parent_id else ''}"
            await create_notification(
                request,
                "material",
                parent.id if parent_id else None,
                f'New materials have been fetched from Google Drive for subject "{subject.name}".',
                share_link,
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Fetch",
                "Materials",
                500,
                "error",
                "An Error Occurred while Fetching Materials from Google Drive.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while fetching materials from google drive",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/materials/update/{material_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Materials"])
@has_registered_subjects
async def update_material(request: Request, material_id: int):
    """
    This route is used to update an existing material.
    It will return the updated material data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Material",
            400,
            "warning",
            "No Data Provided for Material Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Material",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    url = data.get("url", "").strip()
    file = None
    to_be_removed = False
    async with async_session() as session:
        await session.begin()
        try:
            material = (
                await session.execute(
                    Select(Material)
                    .where(Material.id == material_id)
                    .options(
                        selectinload(Material.author), selectinload(Material.subject)
                    )
                )
            ).scalar_one_or_none()
            if not material:
                await log(
                    request,
                    "Edit",
                    "Material",
                    404,
                    "warning",
                    "Material Not Found for Update.",
                    {"material_id": material_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Material not found"}, 404
                )
                return finalize_request(response)
            if (
                material.author_id != current_user.id
                and not "Manage All Materials" in permissions
            ):
                await log(
                    request,
                    "Edit",
                    "Material",
                    403,
                    "warning",
                    "Unauthorized Material Update Attempt by Non-Author User.",
                    {"material_id": material_id, "author_id": material.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to update this material",
                    },
                    403,
                )
                return finalize_request(response)
            if name and name != "":
                material.name = await get_unique_material_name(
                    session,
                    Select(Material).where(
                        Material.subject_id == material.subject_id,
                        Material.parent_id == material.parent_id,
                        Material.type == material.type,
                        Material.id != material.id,
                    ),
                    name,
                )
            if description and description != "":
                material.details["description"] = description
            if material.type == "file" and url and url != "" and url != material.url:
                file = await get_file_from_drive(
                    url, current_user.google_refresh_token, request
                )
                if not file:
                    await log(
                        request,
                        "Edit",
                        "Material",
                        400,
                        "warning",
                        "Invalid File URL Provided for Material Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid File Provided."}, 400
                    )
                    return finalize_request(response)
                # if get_file_type(file.get('mimeType')) not in ['image', 'pdf', 'doc', 'sheet', 'ppt', 'video', 'audio', 'text', 'archive', 'gdrive']:
                #     await log(request, "Edit", "Material", 400, 'warning', 'Unsupported File Type Provided for Material Update.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
                #     await session.rollback()
                #     response = JSONResponse({
                #         'status': 'error',
                #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
                #     }, 400)
                #     return finalize_request(response)
                to_be_removed = (
                    True if not material.details.get("fetched", False) else False
                )
                material.url = (
                    url if material.details.get("fetched", False) else material.url
                )
                material.details["file_data"] = get_file_data(file)
                material.details["fetched"] = False
            if (
                material.type in ["youtube", "drive", "external"]
                and url
                and url != ""
                and url != material.url
            ):
                if material.type == "youtube" and not is_youtube_url(url):
                    await log(
                        request,
                        "Edit",
                        "Material",
                        400,
                        "warning",
                        "Invalid YouTube URL Provided for Material Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid YouTube URL provided"},
                        400,
                    )
                    return finalize_request(response)
                if material.type == "drive" and not is_drive_url(url):
                    await log(
                        request,
                        "Edit",
                        "Material",
                        400,
                        "warning",
                        "Invalid Google Drive URL Provided for Material Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Invalid Google Drive URL provided",
                        },
                        400,
                    )
                    return finalize_request(response)
                if material.type == "external" and not is_valid_url(url):
                    await log(
                        request,
                        "Edit",
                        "Material",
                        400,
                        "warning",
                        "Invalid External URL Provided for Material Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid External URL provided"},
                        400,
                    )
                    return finalize_request(response)
                material.url = url
            if to_be_removed:
                removed = await remove_file_from_drive(
                    material.url, material.author.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Edit",
                        "Material",
                        500,
                        "error",
                        "Failed to Remove Old File from Drive During Material Update.",
                        {"material_id": material.id, "old_url": material.url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to update material. Please try again later.",
                        },
                        500,
                    )
                    return finalize_request(response)
                material.url = url
                material.details["file_data"] = get_file_data(file)
                material.details["fetched"] = False
            material.author_id = (
                current_user.id
            )  # Update the author to the user who made the update
            is_file = material.type != "folder"
            await session.flush()
            await log(
                request,
                "Edit",
                "Material",
                200,
                "info",
                "Material Updated Successfully.",
                {"material": material.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material updated successfully",
                    "data": material.min_to_dict(),
                },
                200,
            )
            subject_name = material.subject.name if material.subject else "N/A"
            await session.commit()
            if is_file:
                share_link = None
                if material.type == "file":
                    share_link = f"{os.environ.get('FRONTEND_URL')}/user/materials?subject_id={material.subject_id}&parent_id={material.parent_id if material.parent_id else ''}&material_id={material.id}"
                else:
                    share_link = material.url
                await create_notification(
                    request,
                    "material",
                    material.id,
                    f'Material "{material.name}" has been updated for subject "{subject_name}".',
                    share_link,
                )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Material",
                500,
                "error",
                "An Error Occurred while Updating Material.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating material",
                },
                500,
            )
            return finalize_request(response)


async def recursive_delete_materials(request: Request, material_id: int, session):
    try:
        current_user = request.state.current_user
        material = (
            await session.execute(
                Select(Material)
                .where(Material.id == material_id)
                .options(selectinload(Material.author))
            )
        ).scalar_one_or_none()
        if not material:
            return True  # If material not found, consider it deleted
        if material.type == "file" and not material.details.get("fetched", False):
            removed = await remove_file_from_drive(
                material.url, material.author.google_refresh_token, request
            )
            if not removed:
                await log(
                    request,
                    "Delete",
                    "Materials",
                    500,
                    "error",
                    "Failed to Remove File from Drive During Recursive Material Deletion.",
                    {"material_id": material.id, "url": material.url},
                    current_user.id,
                )
                return False
        if material.type == "folder":
            # If folder, check if it has any children and delete them recursively
            children = (
                (
                    await session.execute(
                        Select(Material).where(Material.parent_id == material.id)
                    )
                )
                .scalars()
                .all()
            )
            for child in children:
                deleted = await recursive_delete_materials(request, child.id, session)
                if not deleted:
                    return False
        await session.delete(material)
        await session.flush()
        return True
    except Exception as e:
        await log(
            request,
            "Delete",
            "Materials",
            500,
            "error",
            "An Error Occurred during Recursive Material Deletion.",
            {"error": str(e), "material_id": material_id},
            current_user.id,
        )
        return False


@admin_prefix.delete("/materials/{material_ids}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Materials"])
@has_registered_subjects
async def delete_materials(request: Request, material_ids: str):
    """
    This route is used to delete existing materials.
    It will return a success message if materials are deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    ids = material_ids.split(",") if "," in material_ids else [material_ids]
    if not ids or len(ids) == 0:
        await log(
            request,
            "Delete",
            "Material",
            400,
            "warning",
            "No Material IDs Provided for Deletion.",
            {},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Invalid Request."}, 400)
        return finalize_request(response)
    if any(not is_int(id) or int(id) < 1 for id in ids):
        await log(
            request,
            "Delete",
            "Material",
            400,
            "warning",
            "Invalid Material IDs Provided for Deletion.",
            {"material_ids": material_ids},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Invalid Request."}, 400)
        return finalize_request(response)
    if any(ids.count(id) > 1 for id in ids):
        await log(
            request,
            "Delete",
            "Material",
            400,
            "warning",
            "Duplicate Material IDs Provided for Deletion.",
            {"material_ids": material_ids},
            current_user.id,
        )
        response = JSONResponse({"status": "error", "message": "Invalid Request."}, 400)
        return finalize_request(response)
    ids = [int(id) for id in ids]
    async with async_session() as session:
        await session.begin()
        try:
            for material_id in ids:
                material = (
                    await session.execute(
                        Select(Material)
                        .where(Material.id == material_id)
                        .options(selectinload(Material.author))
                    )
                ).scalar_one_or_none()
                if not material:
                    await log(
                        request,
                        "Delete",
                        "Materials",
                        404,
                        "warning",
                        "Material Not Found for Deletion.",
                        {"material_id": material_id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Material(s) not found"}, 404
                    )
                    return finalize_request(response)
                if (
                    material.author_id != current_user.id
                    and not "Manage All Materials" in permissions
                ):
                    await log(
                        request,
                        "Delete",
                        "Materials",
                        403,
                        "warning",
                        "Unauthorized Material Deletion Attempt by Non-Author User.",
                        {"material_id": material_id, "author_id": material.author.id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": f"You are not authorized to delete this material {material.name}",
                        },
                        403,
                    )
                    return finalize_request(response)
                removed = await recursive_delete_materials(
                    request, material_id, session
                )
                if not removed:
                    await log(
                        request,
                        "Delete",
                        "Materials",
                        500,
                        "error",
                        f"Failed to Recursively Delete Material {material.name} and Its Contents.",
                        {"material_id": material_id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": f"Failed to delete material {material.name}. Please try again later.",
                        },
                        500,
                    )
                    return finalize_request(response)
            await log(
                request,
                "Delete",
                "Materials",
                200,
                "info",
                "Material(s) Deleted Successfully.",
                {"material_ids": ids},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Material(s) deleted successfully"},
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Materials",
                500,
                "error",
                "An Error Occurred while Deleting Materials.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting material(s)",
                },
                500,
            )
            return finalize_request(response)


async def recursive_copy_materials(
    request: Request,
    material_id: int,
    subject_id: int,
    parent_id: int | None,
    author_id: int,
    session,
) -> bool | dict:
    try:
        current_user = request.state.current_user
        material = (
            await session.execute(Select(Material).where(Material.id == material_id))
        ).scalar_one_or_none()
        if not material:
            await log(
                request,
                "Copy",
                "Materials",
                404,
                "warning",
                "Material Not Found for Copying.",
                {"material_id": material_id},
                current_user.id,
            )
            return {"code": 404, "message": "Material not found"}
        if material.subject_id != subject_id:
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "Material Subject Mismatch During Copying.",
                {
                    "material_id": material_id,
                    "source_subject_id": material.subject_id,
                    "destination_subject_id": subject_id,
                },
                current_user.id,
            )
            return {
                "code": 400,
                "message": "Materials from different subjects cannot be copied together",
            }
        # if parent_id and material.parent_id and parent_id == material.parent_id:
        #     await log(request, "Copy", "Materials", 400, 'warning', 'Material Parent ID Conflict During Copying.', {'material_id': material_id, 'parent_id': parent_id}, current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': 'Can\'t copy materials to the same folder they are in'
        #     }, 400)
        #     return finalize_request(response)
        # if parent_id and material.id == parent_id:
        #     await log(request, "Copy", "Materials", 400, 'warning', 'Material Self Parenting Conflict During Copying.', {'material_id': material_id, 'parent_id': parent_id}, current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': 'Can\'t copy materials to themselves'
        #     }, 400)
        #     return finalize_request(response)
        new_name = await get_unique_material_name(
            session,
            Select(Material).where(
                Material.subject_id == subject_id,
                Material.parent_id == (parent_id if parent_id else None),
                Material.type == material.type,
            ),
            material.name,
        )
        new_url = material.url
        file_data = (
            material.details.get("file_data", None) if material.details else None
        )
        details = material.details if material.details else {}
        if material.type == "file":
            # For files, we need to copy the file in Google Drive as well
            file_id = get_drive_id(material.url)
            if not file_id:
                await log(
                    request,
                    "Copy",
                    "File",
                    400,
                    "warning",
                    "Failed to get file ID from URL.",
                    {"url": material.url},
                    current_user.id,
                )
                return {"code": 400, "message": "Invalid Request."}
            new_file = await import_file_in_drive(
                file_id, current_user.google_refresh_token, request
            )
            if not new_file:
                await log(
                    request,
                    "Copy",
                    "File",
                    400,
                    "warning",
                    "Failed to copy file in Google Drive.",
                    {"file_id": file_id},
                    current_user.id,
                )
                return {"code": 400, "message": "Failed to copy material(s)."}
            new_url = get_drive_url(new_file.get("id"))
            file_data = get_file_data(new_file)
            details["file_data"] = file_data
        children = []
        if material.type == "folder":
            children = (
                (
                    await session.execute(
                        Select(Material).where(Material.parent_id == material.id)
                    )
                )
                .scalars()
                .all()
            )
        new_material = Material(
            name=new_name,
            type=material.type,
            subject_id=subject_id,
            parent_id=parent_id,
            author_id=author_id,
            url=new_url,
            details=details,
        )
        session.add(new_material)
        await session.flush()
        for child in children:
            result = await recursive_copy_materials(
                request, child.id, subject_id, new_material.id, author_id, session
            )
            if type(result) != bool:
                return result
        return True
    except Exception as e:
        await log(
            request,
            "Copy3",
            "Materials",
            500,
            "error",
            "An Error Occurred while Copying Materials.",
            {"error": str(e)},
            current_user.id,
        )
        return {"code": 500, "message": "An error occurred while copying materials."}


@admin_prefix.patch("/materials/copy")
@is_logged_in
@rate_limit
@is_authorized(["Edit Materials"])
@has_registered_subjects
async def copy_materials(request: Request):
    """
    This route is used to copy materials.
    It will create a copy of the specified materials.
    """
    try:
        current_user = request.state.current_user
        data = await request.json()
        if not data:
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "No Data Provided for Copying Materials.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "No data provided"}, 400
            )
            return finalize_request(response)
        if not is_sanitized(data):
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        material_ids = data.get("material_ids", [])
        destination_id = data.get("destination_id", None)  # Destination Folder ID
        permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if not material_ids:
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "No Material IDs Provided for Copying.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invaid Request."}, 400
            )
            return finalize_request(response)
        if destination_id and (not is_int(destination_id) or int(destination_id) < 1):
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "Invalid Destination ID Provided for Copying Materials.",
                {"destination_id": destination_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        if not isinstance(material_ids, list) or any(
            not is_int(id) or int(id) < 1 for id in material_ids
        ):
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "Invalid Material IDs Provided for Copying.",
                {"material_ids": material_ids},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        if any(material_ids.count(id) > 1 for id in material_ids):
            await log(
                request,
                "Copy",
                "Materials",
                400,
                "warning",
                "Duplicate Material IDs Provided for Copying.",
                {"material_ids": material_ids},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        material_ids = [int(id) for id in material_ids]
        destination_id = int(destination_id) if destination_id else None
        async with async_session() as session:
            await session.begin()
            try:
                if destination_id:
                    destination = (
                        await session.execute(
                            Select(Material).where(Material.id == destination_id)
                        )
                    ).scalar_one_or_none()
                    if not destination or destination.type != "folder":
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            400,
                            "warning",
                            "Invalid Destination ID Provided for Copying Materials.",
                            {"destination_id": destination_id},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Invalid destination provided",
                            },
                            400,
                        )
                        return finalize_request(response)
                parent_id = None
                subject_id = None
                for material_id in material_ids:
                    material = (
                        await session.execute(
                            Select(Material).where(Material.id == int(material_id))
                        )
                    ).scalar_one_or_none()
                    if not material:
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            400,
                            "warning",
                            "Invalid Material ID Provided for Copying.",
                            {"material_id": material_id},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {"status": "error", "message": "Material(s) not found"}, 400
                        )
                        return finalize_request(response)
                    if (
                        material.author_id != current_user.id
                        and not "Manage All Materials" in permissions
                    ):
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            403,
                            "warning",
                            "Unauthorized Material Copy Attempt by Non-Author User.",
                            {
                                "material_id": material_id,
                                "author_id": material.author.id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "You are not authorized to copy this/these material(s).",
                            },
                            403,
                        )
                        return finalize_request(response)
                    if not subject_id:
                        subject_id = material.subject_id
                    elif subject_id != material.subject_id:
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            400,
                            "warning",
                            "Materials from Different Subjects Provided for Copying.",
                            {
                                "material_id": material_id,
                                "subject_id": material.subject_id,
                                "expected_subject_id": subject_id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials from different subjects cannot be copied together",
                            },
                            400,
                        )
                        return finalize_request(response)
                    if not parent_id:
                        parent_id = material.parent_id
                    elif parent_id != material.parent_id:
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            400,
                            "warning",
                            "Materials from Different Parent Folders Provided for Copying.",
                            {
                                "material_id": material_id,
                                "parent_id": material.parent_id,
                                "expected_parent_id": parent_id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials from different parent folders cannot be copied together",
                            },
                            400,
                        )
                        return finalize_request(response)
                    # elif destination_id and parent_id == destination.id:
                    #     await log(request, "Copy", "Materials", 400, 'warning', 'Destination Folder is Same as Source Parent Folder for Copying Materials.', {'material_id': material_id, 'parent_id': parent_id, 'destination_id': destination.id}, current_user.id)
                    #     response = JSONResponse({
                    #         'status': 'error',
                    #         'message': 'Can\'t copy materials to the same folder they are in'
                    #     }, 400)
                    #     return finalize_request(response)
                    result = await recursive_copy_materials(
                        request,
                        material.id,
                        subject_id,
                        destination_id,
                        current_user.id,
                        session,
                    )
                    if type(result) != bool:
                        await log(
                            request,
                            "Copy",
                            "Materials",
                            500,
                            "error",
                            "An Error Occurred while Copying Materials.",
                            {"error": result.get("message")},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": result.get("message"),
                            },
                            result.get("code"),
                        )
                        return finalize_request(response)
                await log(
                    request,
                    "Copy",
                    "Materials",
                    201,
                    "info",
                    "Material(s) Copied Successfully.",
                    {
                        "material_ids": material_ids,
                        "destination_id": destination_id if destination_id else None,
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "success",
                        "message": "Material(s) Copied Successfully.",
                    },
                    201,
                )
                await session.commit()
                return finalize_request(response)
            except Exception as e:
                await log(
                    request,
                    "Copy",
                    "Materials",
                    500,
                    "error",
                    "An Error Occurred while Validating Materials for Copying.",
                    {"error": str(e)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An error occurred while copying material(s)",
                    },
                    500,
                )
                return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Copy",
            "Materials",
            500,
            "error",
            "An Error Occurred while Copying Materials.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while copying material(s)",
            },
            500,
        )
        return finalize_request(response)


async def fetch_parents(material_id: int):
    try:
        parents = []
        id = material_id
        async with async_session() as session:
            while id:
                material = (
                    await session.execute(Select(Material).where(Material.id == id))
                ).scalar_one_or_none()
                if material:
                    parents.append(material.min_to_dict())
                    id = material.parent_id
                else:
                    id = None
        parents.reverse()
        await log(
            None,
            "Fetch",
            "Material Parents",
            200,
            "info",
            "Material Parents Fetched Successfully.",
            {"material_id": material_id, "parents": [p["id"] for p in parents]},
            None,
        )
        return parents
    except Exception as e:
        await log(
            None,
            "Fetch",
            "Material Parents",
            500,
            "error",
            "An Error Occurred while Fetching Material Parents.",
            {"error": str(e), "material_id": material_id},
            None,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while fetching material parents",
            },
            500,
        )
        return response


@admin_prefix.patch("/materials/move")
@is_logged_in
@rate_limit
@is_authorized(["Edit Materials"])
@has_registered_subjects
async def move_materials(request: Request):
    """
    This route is used to move materials.
    """
    try:
        current_user = request.state.current_user
        data = await request.json()
        if not data:
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "No Data Provided for Moving Materials.",
                {},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "No data provided"}, 400
            )
            return finalize_request(response)
        if not is_sanitized(data):
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Body.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        material_ids = data.get("material_ids", [])
        destination_id = data.get("destination_id", None)
        permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if not material_ids:
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "Invalid Data Provided in The Request Body for Moving Materials.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        if not isinstance(material_ids, list) or any(
            not is_int(id) or int(id) < 1 for id in material_ids
        ):
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "Invalid Material IDs Provided for Moving Materials.",
                {"material_ids": material_ids},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        if any(material_ids.count(id) > 1 for id in material_ids):
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "Duplicate Material IDs Provided for Moving Materials.",
                {"material_ids": material_ids},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        material_ids = [int(id) for id in material_ids]
        if destination_id and (not is_int(destination_id) or int(destination_id) < 1):
            await log(
                request,
                "Move",
                "Materials",
                400,
                "warning",
                "Invalid Destination ID Provided for Moving Materials.",
                {"destination_id": destination_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Request."}, 400
            )
            return finalize_request(response)
        destination_id = int(destination_id) if destination_id else None
        async with async_session() as session:
            await session.begin()
            try:
                if destination_id:
                    destination = (
                        await session.execute(
                            Select(Material).where(Material.id == destination_id)
                        )
                    ).scalar_one_or_none()
                    if not destination or destination.type != "folder":
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Invalid Destination ID Provided for Moving Materials.",
                            {"destination_id": destination_id},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {"status": "error", "message": "Invalid Request."}, 400
                        )
                        return finalize_request(response)
                parent_id = None
                subject_id = None
                for material_id in material_ids:
                    material = (
                        await session.execute(
                            Select(Material).where(Material.id == int(material_id))
                        )
                    ).scalar_one_or_none()
                    if not material:
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Invalid Material ID Provided for Moving Materials.",
                            {"material_id": material_id},
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {"status": "error", "message": "Invalid Request."}, 400
                        )
                        return finalize_request(response)
                    if (
                        material.author_id != current_user.id
                        and not "Manage All Materials" in permissions
                    ):
                        await log(
                            request,
                            "Move",
                            "Materials",
                            403,
                            "warning",
                            "Unauthorized Material Move Attempt by Non-Author User.",
                            {
                                "material_id": material_id,
                                "author_id": material.author.id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "You are not authorized to move this/these material(s).",
                            },
                            403,
                        )
                        return finalize_request(response)
                    if not subject_id:
                        subject_id = material.subject_id
                    elif subject_id != material.subject_id:
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Materials from Different Subjects Provided for Moving.",
                            {
                                "material_id": material_id,
                                "subject_id": material.subject_id,
                                "expected_subject_id": subject_id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials from different subjects cannot be moved together",
                            },
                            400,
                        )
                        return finalize_request(response)
                    if not parent_id:
                        parent_id = material.parent_id
                    elif parent_id != material.parent_id:
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Materials from Different Parent Folders Provided for Moving.",
                            {
                                "material_id": material_id,
                                "parent_id": material.parent_id,
                                "expected_parent_id": parent_id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials from different folders cannot be moved together",
                            },
                            400,
                        )
                        return finalize_request(response)
                    if (
                        destination_id
                        and parent_id
                        and parent_id == destination_id
                        or not destination_id
                        and not parent_id
                    ):
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Destination Folder is Same as Source Parent Folder for Moving Materials.",
                            {
                                "material_id": material_id,
                                "parent_id": parent_id,
                                "destination_id": destination_id,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials can't be moved to the same folder they are in",
                            },
                            400,
                        )
                        return finalize_request(response)
                    material.name = await get_unique_material_name(
                        session,
                        Select(Material).where(
                            Material.subject_id == subject_id,
                            Material.parent_id
                            == (destination_id if destination_id else None),
                            Material.type == material.type,
                        ),
                        material.name,
                    )
                    response = (
                        await fetch_parents(destination_id) if destination_id else []
                    )
                    if type(response) == JSONResponse:
                        return finalize_request(response)
                    parent_ids = (
                        [parent["id"] for parent in response] if response else []
                    )
                    if material.id in parent_ids:
                        await log(
                            request,
                            "Move",
                            "Materials",
                            400,
                            "warning",
                            "Cannot Move Material Inside Its Own Subfolder.",
                            {
                                "material_id": material_id,
                                "destination_id": (
                                    destination_id if destination_id else None
                                ),
                                "parent_ids": parent_ids,
                            },
                            current_user.id,
                        )
                        await session.rollback()
                        response = JSONResponse(
                            {
                                "status": "error",
                                "message": "Materials can't be moved to a subfolder of themselves",
                            },
                            400,
                        )
                        return finalize_request(response)
                    material.parent_id = destination_id if destination_id else None
                    material.author_id = (
                        current_user.id
                    )  # Update the author to the user who made the move
                    await session.flush()
                await log(
                    request,
                    "Move",
                    "Materials",
                    200,
                    "info",
                    "Material(s) Moved Successfully.",
                    {
                        "material_ids": material_ids,
                        "destination_id": destination_id if destination_id else None,
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "success", "message": "Material(s) moved successfully"},
                    200,
                )
                await session.commit()
                return finalize_request(response)
            except Exception as e:
                await log(
                    request,
                    "Move",
                    "Materials",
                    500,
                    "error",
                    "An Error Occurred while Validating Materials for Moving.",
                    {"error": str(e)},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An error occurred while moving material(s)",
                    },
                    500,
                )
                return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Move",
            "Materials",
            500,
            "error",
            "An Error Occurred while Moving Materials.",
            {"error": str(e)},
            current_user.id,
        )
        await session.rollback()
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while moving material(s)",
            },
            500,
        )
        return finalize_request(response)


async def recursive_materials_count_descendants(
    request: Request, material_id: int, count_files=True
) -> int:
    count = 0
    current_user = request.state.current_user
    try:
        async with async_session() as session:
            material = (
                await session.execute(
                    Select(Material).where(Material.id == material_id)
                )
            ).scalar_one_or_none()
            if not material:
                return 0
            if material.type == "folder":
                children = (
                    (
                        await session.execute(
                            Select(Material).where(Material.parent_id == material.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                for child in children:
                    count += (
                        1
                        if count_files
                        and child.type != "folder"
                        or not count_files
                        and child.type == "folder"
                        else 0
                    )
                    count += await recursive_materials_count_descendants(
                        request, child.id, count_files
                    )  # Add descendants of the
                    # child
        return count
    except Exception as e:
        await log(
            request,
            "Count",
            "Materials",
            500,
            "error",
            "An Error Occurred during Recursive Descendant Material Counting.",
            {"error": str(e), "material_id": material_id},
            current_user.id,
        )
    return count


@admin_prefix.get("/materials")
@is_logged_in
@rate_limit
@is_authorized(["View Materials"])
@has_registered_subjects
async def get_materials(request: Request):
    """
    This route is used to get all materials.
    It will return a list of materials.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        material_type = data.get("type", "").strip().lower()
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        subject_id = data.get("subject_id", None)
        parent_id = data.get("parent_id", None)  # Parent Folder ID
        author_id = data.get("author_id", None)  # Author ID
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if (
            (
                faculty_id
                and (not is_int(faculty_id) or int(faculty_id) < 1)
                or department_id
                and (not is_int(department_id) or int(department_id) < 1)
                or year_id
                and (not is_int(year_id) or int(year_id) < 1)
                or subject_id
                and (not is_int(subject_id) or int(subject_id) < 1)
                or parent_id
                and (not is_int(parent_id) or int(parent_id) < 1)
            )
            or author_id
            and (not is_int(author_id) or int(author_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Materials.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if (
            faculty_id
            and "Access All Faculties" not in user_permissions
            or department_id
            and "Access All Departments" not in user_permissions
            or year_id
            and "Access All Years" not in user_permissions
        ):
            await log(
                request,
                "Get",
                "Tasks",
                403,
                "warning",
                "Unauthorized Access Attempt to Restricted Faculty, Department, or Year for Getting Tasks.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You are not authorized to access the specified criteria",
                },
                403,
            )
            return finalize_request(response)
        if not subject_id:
            await log(
                request,
                "Get",
                "Materials",
                400,
                "warning",
                "Missing Required Query Parameters for Getting Materials.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Please make sure to fill all filters correctly",
                },
                400,
            )
            return finalize_request(response)
        faculty_id = int(faculty_id) if faculty_id else None
        department_id = int(department_id) if department_id else None
        year_id = int(year_id) if year_id else None
        subject_id = int(subject_id) if subject_id else None
        parent_id = int(parent_id) if parent_id else None
        author_id = int(author_id) if author_id else None
        async with async_session() as session:
            query = Select(Material).options(
                selectinload(Material.author),
                selectinload(Material.subject),
                selectinload(Material.parent),
            )
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Material).where(Material.id == int(parent_id))
                    )
                ).scalar_one_or_none()
                if not parent or parent.type != "folder":
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Parent Folder Not Found for Getting Materials.",
                        {"parent_id": parent_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Parent folder not found"}, 404
                    )
                    return finalize_request(response)
            parent_id = int(parent_id) if parent_id else None
            query = query.where(Material.parent_id == parent_id)
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Faculty Not Found for Getting Materials.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Material.faculty_id == faculty.id)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if (
                    not department
                    or not faculty_id
                    or department.faculty_id != faculty_id
                ):
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Department Not Found or Does Not Belong to Specified Faculty for Getting Materials.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department not found in the specified faculty",
                        },
                        404,
                    )
                    return finalize_request(response)
                query = query.where(Material.department_id == department.id)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Year Not Found for Getting Materials.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Material.year_id == year.id)
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if (
                not subject
                or (faculty_id and subject.faculty_id != faculty_id)
                or (department_id and subject.department_id != department_id)
                or (year_id and subject.year_id != year_id)
            ):
                await log(
                    request,
                    "Get",
                    "Materials",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to Specified Faculty, Department, or Year for Getting Materials.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": faculty_id,
                        "department_id": department_id,
                        "year_id": year_id,
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in the specified criteria",
                    },
                    404,
                )
                return finalize_request(response)
            query = query.where(Material.subject_id == subject.id)
            if author_id:
                author = (
                    await session.execute(Select(User).where(User.id == int(author_id)))
                ).scalar_one_or_none()
                if not author:
                    await log(
                        request,
                        "Get",
                        "Materials",
                        404,
                        "warning",
                        "Author Not Found for Getting Materials.",
                        {"author_id": author_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Author not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Material.author_id == author.id)
            query = query.where(func.lower(Material.name).contains(query_search))
            query = (
                query.where(Material.type == material_type) if material_type else query
            )
            sort_order = case(
                (Material.type == "folder", 1),
                (Material.type == "file", 2),
                (Material.type == "drive", 3),
                (Material.type == "youtube", 4),
                (Material.type == "external", 5),
                else_=6,
            )
            query = query.order_by(sort_order, Material.modified_at.desc())
            materials = (
                (await session.execute(query.order_by(Material.modified_at.desc())))
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Materials",
                200,
                "info",
                "Materials Retrieved Successfully.",
                {"filters": dict(data), "count": len(materials)},
                current_user.id,
            )
            materials_dict = [m.to_dict() for m in materials]
            for m in materials_dict:
                m["details"]["files_count"] = (
                    await recursive_materials_count_descendants(request, m.get("id"))
                )
                m["details"]["folders_count"] = (
                    await recursive_materials_count_descendants(
                        request, m.get("id"), False
                    )
                )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Materials retrieved successfully",
                    "data": materials_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Materials",
            500,
            "error",
            "An Error Occurred while Getting Materials.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting materials"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/materials/{material_id}/parents")
@is_logged_in
@rate_limit
@is_authorized(["View Materials"])
@has_registered_subjects
async def get_material_parents(request: Request, material_id: int):
    """
    This route is used to get the parents of a specific material by its ID.
    It will return a list of parent materials.
    """
    try:
        current_user = request.state.current_user
        material = None
        async with async_session() as session:
            material = (
                await session.execute(
                    Select(Material).where(Material.id == material_id)
                )
            ).scalar_one_or_none()
            if not material:
                await log(
                    request,
                    "Get",
                    "Material Parents",
                    404,
                    "warning",
                    "Material Not Found for Fetching Parents.",
                    {"material_id": material_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Material not found"}, 404
                )
                return finalize_request(response)
            parents = await fetch_parents(material.id)
            if not parents or type(parents) != list:
                response = parents
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Material Parents",
                200,
                "info",
                "Material Parents Retrieved Successfully.",
                {"material_id": material_id, "parents": [p["id"] for p in parents]},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material parents retrieved successfully",
                    "data": parents,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Material Parents",
            500,
            "error",
            "An Error Occurred while Getting Material Parents.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting material parents",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/materials/{material_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Materials"])
@has_registered_subjects
async def get_material(request: Request, material_id: int):
    """
    This route is used to get a specific material by its ID.
    It will return the material data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            material = (
                await session.execute(
                    Select(Material)
                    .where(Material.id == material_id)
                    .options(
                        selectinload(Material.author),
                        selectinload(Material.subject),
                        selectinload(Material.parent),
                    )
                )
            ).scalar_one_or_none()
            if not material:
                await log(
                    request,
                    "Get",
                    "Material",
                    404,
                    "warning",
                    "Material Not Found.",
                    {"material_id": material_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Material not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Material",
                200,
                "info",
                "Material Retrieved Successfully.",
                {"material": material.to_dict()},
                current_user.id,
            )
            material_dict = material.to_dict()
            material_dict["details"]["files_count"] = (
                await recursive_materials_count_descendants(request, material.id)
            )
            material_dict["details"]["folders_count"] = (
                await recursive_materials_count_descendants(request, material.id, False)
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Material retrieved successfully",
                    "data": material_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Material",
            500,
            "error",
            "An Error Occurred while Getting Material.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting material"},
            500,
        )
        return finalize_request(response)


async def get_unique_grade_name(session, query, base_name) -> str:
    """
    This function is used to get a unique grade name.
    """
    if not base_name or base_name == "":
        base_name = "Untitled"
    base_name = base_name.strip()
    if (
        base_name.endswith(")")
        and base_name.rfind("(") != -1
        and is_int(base_name[base_name.rfind("(") + 1 : -1])
    ):
        base_name = base_name[: base_name.rfind("(")].strip()
    unique_name = base_name
    counter = 1
    while True:
        existing_grade = (
            await session.execute(query.where(Grade.name == unique_name))
        ).scalar_one_or_none()
        if not existing_grade:
            return unique_name
        unique_name = f"{base_name} ({counter})"
        counter += 1


@admin_prefix.post("/grades")
@is_logged_in
@rate_limit
@is_authorized(["Add Grades"])
@has_registered_subjects
async def create_grade(request: Request):
    """
    This route is used to create a new grade.
    It will return the created grade data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "No Data Provided for Grade Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    url = data.get("url", "").strip()
    type = (
        data.get("type", "").strip().lower()
    )  # File or Folder or YouTube or Drive or External
    parent_id = data.get("parent_id", None)  # Parent Folder ID
    subject_id = data.get("subject_id", None)  # Subject ID
    # file_type = data.get('file_type', '').strip().lower() # pdf, docx, pptx, xlsx, txt, zip, rar, image, video,
    # audio, ...
    allowed_file_types = [
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
    ]
    file = None
    if not type or type not in ["file", "folder", "youtube", "drive", "external"]:
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Invalid or Missing Grade Type Provided for Grade Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Grade type must be one of the available types",
            },
            400,
        )
        return finalize_request(response)
    if parent_id and (not is_int(parent_id) or int(parent_id) < 1):
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Invalid Parent ID Provided for Grade Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid parent ID provided"}, 400
        )
        return finalize_request(response)
    if not subject_id or not is_int(subject_id) or int(subject_id) < 1:
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Invalid or Missing Subject ID Provided for Grade Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid subject was provided."}, 400
        )
        return finalize_request(response)
    if type == "folder":
        if not name or name == "":
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Missing Required Fields for Folder Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Folder Name is required"}, 400
            )
            return finalize_request(response)
    elif type in ["youtube", "drive", "external"]:
        if not name or name == "" or not url or url == "":
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Missing Required Fields for Link Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Name and URL are required"}, 400
            )
            return finalize_request(response)
        if type == "youtube" and not is_youtube_url(url):
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Invalid YouTube URL Provided for Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid YouTube URL provided"}, 400
            )
            return finalize_request(response)
        if type == "drive" and not is_drive_url(url):
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Invalid Google Drive URL Provided for Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid Google Drive URL provided"}, 400
            )
            return finalize_request(response)
        if type == "external" and not is_valid_url(url):
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Invalid External URL Provided for Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid External URL provided"}, 400
            )
            return finalize_request(response)
    else:
        if not url or url == "":
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Missing Required Fields for File Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "File is required"}, 400
            )
            return finalize_request(response)
        file = await get_file_from_drive(
            url, current_user.google_refresh_token, request
        )
        if not file:
            await log(
                request,
                "Add",
                "Grade",
                400,
                "warning",
                "Invalid File URL Provided for Grade Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid File Provided."}, 400
            )
            return finalize_request(response)
        # if get_file_type(file.get('mimeType')) not in allowed_file_types:
        #     await log(request, "Add", "Grade", 400, 'warning', 'Unsupported File Type Provided for Grade Creation.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
    if name and name != "" and len(name) > 200:
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Grade Name Exceeds Maximum Length for Grade Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Grade name exceeds maximum length of 200 characters",
            },
            400,
        )
        return finalize_request(response)
    if url and url != "" and len(url) > 200:
        await log(
            request,
            "Add",
            "Grade",
            400,
            "warning",
            "Grade URL Exceeds Maximum Length for Grade Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Grade URL exceeds maximum length of 200 characters",
            },
            400,
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Grade).where(Grade.id == int(parent_id))
                    )
                ).scalar_one_or_none()
                if not parent or parent.type != "folder":
                    await log(
                        request,
                        "Add",
                        "Grade",
                        404,
                        "warning",
                        "Parent Folder Not Found for Grade Creation.",
                        {"parent_id": parent_id},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Parent folder not found"}, 404
                    )
                    return finalize_request(response)
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Add",
                    "Grade",
                    404,
                    "warning",
                    "Subject Not Found for Grade Creation.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            grade_name = name if name and name != "" else file.get("name")
            unique_name_query = Select(Grade).where(
                Grade.subject_id == subject.id,
                Grade.parent_id == (parent.id if parent_id else None),
                Grade.type == type,
            )
            grade = Grade(
                name=(
                    await get_unique_grade_name(session, unique_name_query, name)
                    if name and name != ""
                    else await get_unique_grade_name(
                        session, unique_name_query, file.get("name")
                    )
                ),
                type=type,
                url=url if url and url != "" else None,
                subject_id=subject.id,
                author_id=current_user.id,
                parent_id=parent.id if parent_id else None,
                details={
                    "description": (
                        description if description and description != "" else None
                    ),
                    "file_data": get_file_data(file) if file else None,
                    "fetched": False,
                },
            )
            if file:
                grade.details["file_data"] = get_file_data(file)
            session.add(grade)
            is_file = grade.type != "folder"
            await session.flush()
            await log(
                request,
                "Add",
                "Grade",
                201,
                "info",
                "Grade Created Successfully.",
                {"grade": grade.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade created successfully",
                    "data": grade.min_to_dict(),
                },
                201,
            )
            await session.commit()
            if is_file:
                share_link = None
                if grade.type == "file":
                    share_link = f"{os.environ.get('FRONTEND_URL')}/user/grades?subject_id={subject.id}&parent_id={parent.id if parent_id else ''}&grade_id={grade.id}"
                else:
                    share_link = grade.url
                await create_notification(
                    request,
                    "grade",
                    grade.id,
                    f'New grade "{grade.name}" has been '
                    f'uploaded for subject "{subject.name}".',
                    share_link,
                )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Grade",
                500,
                "error",
                "An Error Occurred while Creating Grade.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating grade",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/grades/{grade_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Grades"])
@has_registered_subjects
async def update_grade(request: Request, grade_id: int):
    """
    This route is used to update an existing grade.
    It will return the updated grade data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Grade",
            400,
            "warning",
            "No Data Provided for Grade Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Grade",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    url = data.get("url", "").strip()
    file = None
    to_be_removed = False
    async with async_session() as session:
        await session.begin()
        try:
            grade = (
                await session.execute(
                    Select(Grade)
                    .where(Grade.id == grade_id)
                    .options(
                        selectinload(Grade.author),
                        selectinload(Grade.subject),
                    )
                )
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Edit",
                    "Grade",
                    404,
                    "warning",
                    "Grade Not Found for Update.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            if (
                grade.author_id != current_user.id
                and not "Manage All Grades" in permissions
            ):
                await log(
                    request,
                    "Edit",
                    "Grade",
                    403,
                    "warning",
                    "Unauthorized Grade Update Attempt by Non-Author User.",
                    {"grade_id": grade_id, "author_id": grade.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to update this grade",
                    },
                    403,
                )
                return finalize_request(response)
            if name and name != "":
                grade.name = await get_unique_grade_name(
                    session,
                    Select(Grade).where(
                        Grade.subject_id == grade.subject_id,
                        Grade.parent_id == grade.parent_id,
                        Grade.type == grade.type,
                        Grade.id != grade.id,
                    ),
                    name,
                )
            if description and description != "":
                grade.details["description"] = description
            if grade.type == "file" and url and url != "" and url != grade.url:
                file = await get_file_from_drive(
                    url, current_user.google_refresh_token, request
                )
                if not file:
                    await log(
                        request,
                        "Edit",
                        "Grade",
                        400,
                        "warning",
                        "Invalid File URL Provided for Grade Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid File Provided."}, 400
                    )
                    return finalize_request(response)
                # if get_file_type(file.get('mimeType')) not in ['image', 'pdf', 'doc', 'sheet', 'ppt', 'video', 'audio', 'text', 'archive', 'gdrive']:
                #     await log(request, "Edit", "Grade", 400, 'warning', 'Unsupported File Type Provided for Grade Update.', {'data': dict(data), 'file_type': file.get('mimeType')}, current_user.id)
                #     await session.rollback()
                #     response = JSONResponse({
                #         'status': 'error',
                #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
                #     }, 400)
                #     return finalize_request(response)
                to_be_removed = (
                    True if not grade.details.get("fetched", False) else False
                )
                grade.url = url if grade.details.get("fetched", False) else grade.url
                grade.details["file_data"] = get_file_data(file)
                grade.details["fetched"] = False
            if (
                grade.type in ["youtube", "drive", "external"]
                and url
                and url != ""
                and url != grade.url
            ):
                if grade.type == "youtube" and not is_youtube_url(url):
                    await log(
                        request,
                        "Edit",
                        "Grade",
                        400,
                        "warning",
                        "Invalid YouTube URL Provided for Grade Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid YouTube URL provided"},
                        400,
                    )
                    return finalize_request(response)
                if grade.type == "drive" and not is_drive_url(url):
                    await log(
                        request,
                        "Edit",
                        "Grade",
                        400,
                        "warning",
                        "Invalid Google Drive URL Provided for Grade Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Invalid Google Drive URL provided",
                        },
                        400,
                    )
                    return finalize_request(response)
                if grade.type == "external" and not is_valid_url(url):
                    await log(
                        request,
                        "Edit",
                        "Grade",
                        400,
                        "warning",
                        "Invalid External URL Provided for Grade Update.",
                        {"data": dict(data)},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {"status": "error", "message": "Invalid External URL provided"},
                        400,
                    )
                    return finalize_request(response)
                grade.url = url
            if to_be_removed:
                removed = await remove_file_from_drive(
                    grade.url, grade.author.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Edit",
                        "Grade",
                        500,
                        "error",
                        "Failed to Remove Old File from Drive During Grade Update.",
                        {"grade_id": grade.id, "old_url": grade.url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to update grade. Please try again later.",
                        },
                        500,
                    )
                    return finalize_request(response)
                grade.url = url
                grade.details["file_data"] = get_file_data(file)
                grade.details["fetched"] = False
            grade.author_id = (
                current_user.id
            )  # Update the author to the user who made the update
            await session.flush()
            await log(
                request,
                "Edit",
                "Grade",
                200,
                "info",
                "Grade Updated Successfully.",
                {"grade": grade.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade updated successfully",
                    "data": grade.min_to_dict(),
                },
                200,
            )
            subject_name = grade.subject.name if grade.subject else "N/A"
            await session.commit()
            if is_file:
                share_link = None
                if grade.type == "file":
                    share_link = f"{os.environ.get('FRONTEND_URL')}/user/grades?subject_id={grade.subject_id}&parent_id={grade.parent_id if grade.parent_id else ''}&grade_id={grade.id}"
                else:
                    share_link = grade.url
                await create_notification(
                    request,
                    "grade",
                    grade.id,
                    f'Grade "{grade.name}" has been updated for subject "{subject_name}".',
                    share_link,
                )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Grade",
                500,
                "error",
                "An Error Occurred while Updating Grade.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating grade",
                },
                500,
            )
            return finalize_request(response)


async def recursive_delete_grades(request: Request, grade_id: int):
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            grade = (
                await session.execute(
                    Select(Grade)
                    .where(Grade.id == grade_id)
                    .options(selectinload(Grade.author))
                )
            ).scalar_one_or_none()
            if not grade:
                return True  # If grade not found, consider it deleted
            if grade.type == "file":
                removed = await remove_file_from_drive(
                    grade.url, grade.author.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Delete",
                        "Grades",
                        500,
                        "error",
                        "Failed to Remove File from Drive During Recursive Grade Deletion.",
                        {"grade_id": grade.id, "url": grade.url},
                        current_user.id,
                    )
                    return False
            if grade.type == "folder":
                # If folder, check if it has any children and delete them recursively
                children = (
                    (
                        await session.execute(
                            Select(Grade).where(Grade.parent_id == grade.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                for child in children:
                    deleted = await recursive_delete_grades(request, child.id)
                    if not deleted:
                        return False
            await session.delete(grade)
            await session.flush()
            return True
    except Exception as e:
        await log(
            request,
            "Delete",
            "Grades",
            500,
            "error",
            "An Error Occurred during Recursive Grade Deletion.",
            {"error": str(e), "grade_id": grade_id},
            current_user.id,
        )
        return False


@admin_prefix.delete("/grades/{grade_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Grades"])
@has_registered_subjects
async def delete_grade(request: Request, grade_id: int):
    """
    This route is used to delete an existing grade.
    It will return a success message if the grade is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    async with async_session() as session:
        await session.begin()
        try:
            grade = (
                await session.execute(
                    Select(Grade)
                    .where(Grade.id == grade_id)
                    .options(selectinload(Grade.author))
                )
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Delete",
                    "Grade",
                    404,
                    "warning",
                    "Grade Not Found for Deletion.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            if (
                grade.author_id != current_user.id
                and not "Manage All Grades" in permissions
            ):
                await log(
                    request,
                    "Delete",
                    "Grade",
                    403,
                    "warning",
                    "Unauthorized Grade Deletion Attempt by Non-Author User.",
                    {"grade_id": grade_id, "author_id": grade.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to delete this grade",
                    },
                    403,
                )
                return finalize_request(response)
            removed = await recursive_delete_grades(request, grade_id)
            if not removed:
                await log(
                    request,
                    "Delete",
                    "Grade",
                    500,
                    "error",
                    "Failed to Recursively Delete Grade and Its Contents.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Failed to delete grade. Please try again later.",
                    },
                    500,
                )
                return finalize_request(response)
            await log(
                request,
                "Delete",
                "Grade",
                200,
                "info",
                "Grade Deleted Successfully.",
                {"grade_id": grade_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Grade deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Grade",
                500,
                "error",
                "An Error Occurred while Deleting Grade.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting grade",
                },
                500,
            )
            return finalize_request(response)


async def recursive_grades_count_descendants(
    request: Request, grade_id: int, count_files=True
) -> int:
    count = 0
    current_user = request.state.current_user
    try:
        async with async_session() as session:
            grade = (
                await session.execute(Select(Grade).where(Grade.id == grade_id))
            ).scalar_one_or_none()
            if not grade:
                return 0
            if grade.type == "folder":
                children = (
                    (
                        await session.execute(
                            Select(Grade).where(Grade.parent_id == grade.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                for child in children:
                    count += (
                        1
                        if count_files
                        and child.type != "folder"
                        or not count_files
                        and child.type == "folder"
                        else 0
                    )
                    count += await recursive_grades_count_descendants(
                        request, child.id, count_files
                    )  # Add descendants of the
                    # child
        return count
    except Exception as e:
        await log(
            request,
            "Count",
            "Grades",
            500,
            "error",
            "An Error Occurred during Recursive Descendant Grade Counting.",
            {"error": str(e), "grade_id": grade_id},
            current_user.id,
        )
    return count


@admin_prefix.get("/grades")
@is_logged_in
@rate_limit
@is_authorized(["View Grades"])
@has_registered_subjects
async def get_grades(request: Request):
    """
    This route is used to get all grades.
    It will return a list of grades.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        subject_id = data.get("subject_id", None)
        parent_id = data.get("parent_id", None)  # Parent Folder ID
        author_id = data.get("author_id", None)  # Author ID
        if (
            (
                faculty_id
                and (not is_int(faculty_id) or int(faculty_id) < 1)
                or department_id
                and (not is_int(department_id) or int(department_id) < 1)
                or year_id
                and (not is_int(year_id) or int(year_id) < 1)
                or subject_id
                and (not is_int(subject_id) or int(subject_id) < 1)
                or parent_id
                and (not is_int(parent_id) or int(parent_id) < 1)
            )
            or author_id
            and (not is_int(author_id) or int(author_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Grades.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if not faculty_id or not department_id or not year_id or not subject_id:
            await log(
                request,
                "Get",
                "Grades",
                400,
                "warning",
                "Missing Required Query Parameters for Getting Grades.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Please make sure to fill all filters correctly",
                },
                400,
            )
            return finalize_request(response)
        faculty_id = int(faculty_id) if faculty_id else None
        department_id = int(department_id) if department_id else None
        year_id = int(year_id) if year_id else None
        subject_id = int(subject_id) if subject_id else None
        parent_id = int(parent_id) if parent_id else None
        author_id = int(author_id) if author_id else None
        async with async_session() as session:
            if parent_id:
                parent = (
                    await session.execute(
                        Select(Grade).where(Grade.id == int(parent_id))
                    )
                ).scalar_one_or_none()
                if not parent or parent.type != "folder":
                    await log(
                        request,
                        "Get",
                        "Grades",
                        404,
                        "warning",
                        "Parent Folder Not Found for Getting Grades.",
                        {"parent_id": parent_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Parent folder not found"}, 404
                    )
                    return finalize_request(response)
            parent_id = int(parent_id) if parent_id else None
            faculty = (
                await session.execute(
                    Select(Faculty).where(Faculty.id == int(faculty_id))
                )
            ).scalar_one_or_none()
            if not faculty:
                await log(
                    request,
                    "Get",
                    "Grades",
                    404,
                    "warning",
                    "Faculty Not Found for Getting Grades.",
                    {"faculty_id": faculty_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Faculty not found"}, 404
                )
                return finalize_request(response)
            department = (
                await session.execute(
                    Select(Department).where(Department.id == int(department_id))
                )
            ).scalar_one_or_none()
            if not department or department.faculty_id != faculty.id:
                await log(
                    request,
                    "Get",
                    "Grades",
                    404,
                    "warning",
                    "Department Not Found or Does Not Belong to Specified Faculty for Getting Grades.",
                    {"department_id": department_id, "faculty_id": faculty_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Department not found in the specified faculty",
                    },
                    404,
                )
                return finalize_request(response)
            year = (
                await session.execute(Select(Year).where(Year.id == int(year_id)))
            ).scalar_one_or_none()
            if not year:
                await log(
                    request,
                    "Get",
                    "Grades",
                    404,
                    "warning",
                    "Year Not Found for Getting Grades.",
                    {"year_id": year_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Year not found"}, 404
                )
                return finalize_request(response)
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if (
                not subject
                or subject.faculty_id != faculty.id
                or subject.department_id != department.id
                or subject.year_id != year.id
            ):
                await log(
                    request,
                    "Get",
                    "Grades",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to Specified Faculty, Department, or Year for Getting Grades.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": faculty_id,
                        "department_id": department_id,
                        "year_id": year_id,
                    },
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in the specified criteria",
                    },
                    404,
                )
                return finalize_request(response)
            sort_order = case(
                (Grade.type == "folder", 1),
                (Grade.type == "file", 2),
                (Grade.type == "drive", 3),
                (Grade.type == "youtube", 4),
                (Grade.type == "external", 5),
                else_=6,
            )
            query = (
                Select(Grade)
                .where(Grade.subject_id == subject.id, Grade.parent_id == parent_id)
                .options(
                    selectinload(Grade.author),
                    selectinload(Grade.subject),
                    selectinload(Grade.parent),
                )
                .order_by(sort_order, Grade.modified_at.desc())
            )
            if author_id:
                author = (
                    await session.execute(Select(User).where(User.id == int(author_id)))
                ).scalar_one_or_none()
                if not author:
                    await log(
                        request,
                        "Get",
                        "Grades",
                        404,
                        "warning",
                        "Author Not Found for Getting Grades.",
                        {"author_id": author_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Author not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Grade.author_id == author.id)
            query = query.where(func.lower(Grade.name).contains(query_search))
            grades = (
                (await session.execute(query.order_by(Grade.modified_at.desc())))
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Grades",
                200,
                "info",
                "Grades Retrieved Successfully.",
                {"filters": dict(data), "count": len(grades)},
                current_user.id,
            )
            grades_dict = [m.to_dict() for m in grades]
            for m in grades_dict:
                m["details"]["files_count"] = await recursive_grades_count_descendants(
                    request, m.get("id")
                )
                m["details"]["folders_count"] = (
                    await recursive_grades_count_descendants(
                        request, m.get("id"), False
                    )
                )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grades retrieved successfully",
                    "data": grades_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grades",
            500,
            "error",
            "An Error Occurred while Getting Grades.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting grades"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/grades/{grade_id}/parents")
@is_logged_in
@rate_limit
@is_authorized(["View Grades"])
@has_registered_subjects
async def get_grade_parents(request: Request, grade_id: int):
    """
    This route is used to get the parents of a specific grade by its ID.
    It will return a list of parent grades.
    """
    try:
        current_user = request.state.current_user
        grade = None
        async with async_session() as session:
            grade = (
                await session.execute(Select(Grade).where(Grade.id == grade_id))
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Get",
                    "Grade Parents",
                    404,
                    "warning",
                    "Grade Not Found for Fetching Parents.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            parents = await fetch_parents(grade.id)
            if not parents or type(parents) != list:
                response = parents
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Grade Parents",
                200,
                "info",
                "Grade Parents Retrieved Successfully.",
                {"grade_id": grade_id, "parents": [p["id"] for p in parents]},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade parents retrieved successfully",
                    "data": parents,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grade Parents",
            500,
            "error",
            "An Error Occurred while Getting Grade Parents.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting grade parents",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/grades/{grade_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Grades"])
@has_registered_subjects
async def get_grade(request: Request, grade_id: int):
    """
    This route is used to get a specific grade by its ID.
    It will return the grade data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            grade = (
                await session.execute(
                    Select(Grade)
                    .where(Grade.id == grade_id)
                    .options(
                        selectinload(Grade.author),
                        selectinload(Grade.subject),
                        selectinload(Grade.parent),
                    )
                )
            ).scalar_one_or_none()
            if not grade:
                await log(
                    request,
                    "Get",
                    "Grade",
                    404,
                    "warning",
                    "Grade Not Found.",
                    {"grade_id": grade_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Grade not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Grade",
                200,
                "info",
                "Grade Retrieved Successfully.",
                {"grade": grade.to_dict()},
                current_user.id,
            )
            grade_dict = grade.to_dict()
            grade_dict["details"]["files_count"] = (
                await recursive_grades_count_descendants(request, grade.id)
            )
            grade_dict["details"]["folders_count"] = (
                await recursive_grades_count_descendants(request, grade.id, False)
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Grade retrieved successfully",
                    "data": grade_dict,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Grade",
            500,
            "error",
            "An Error Occurred while Getting Grade.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting grade"}, 500
        )
        return finalize_request(response)


@admin_prefix.post("/tasks")
@is_logged_in
@rate_limit
@is_authorized(["Add Tasks"])
@is_ready
@has_registered_subjects
async def create_task(request: Request):
    """
    This route is used to create a new task.
    It will return the created task data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "No Data Provided for Task Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    submission_url = data.get("submission_url", "").strip()
    deadline = data.get("deadline", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    urls = data.get("urls", [])  # List of File URLs
    links = data.get("links", [])  # List of Links
    if (
        not title
        or title == ""
        or not deadline
        or deadline == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Missing Required Fields for Task Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    try:
        deadline_date = convert_to_utc(datetime.fromisoformat(deadline))
        due_date = deadline_date.date()
    except ValueError:
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Invalid Deadline Format Provided for Task Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid deadline format. Please provide a valid date.",
            },
            400,
        )
        return finalize_request(response)
    if deadline_date and deadline_date <= datetime.now(utc_tz):
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Past Deadline Provided for Task Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Deadline must be a future date."}, 400
        )
        return finalize_request(response)
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Invalid Data Type for URLs or Links Provided for Task Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided for files or links"},
            400,
        )
        return finalize_request(response)
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(
                request,
                "Add",
                "Task",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Task Creation.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = await fetch_public_drive(
            get_drive_id(url), os.environ.get("GOOGLE_TOKEN_API_KEY"), request
        )
        if not file:
            await log(
                request,
                "Add",
                "Task",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Task Creation.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = file.get("data")
        # if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
        #     await log(request, "Add", "Task", 400, 'warning', 'Unsupported File Type in URLs List Provided for Task Creation.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
        #               current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
        files.append(file)
    for link in links:
        if not is_valid_url(link.get("url")):
            await log(
                request,
                "Add",
                "Task",
                400,
                "warning",
                "Invalid Link URL in Links List Provided for Task Creation.",
                {"data": dict(data), "invalid_link": link},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid Link provided"}, 400
            )
            return finalize_request(response)
    if submission_url and submission_url != "" and not is_valid_url(submission_url):
        await log(
            request,
            "Add",
            "Task",
            400,
            "warning",
            "Invalid Submission URL Provided for Task Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid submission URL provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Add",
                    "Task",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Task Creation.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            task = Task(
                name=title,
                urls=urls if urls and len(urls) > 0 else [],
                links=links if links and len(links) > 0 else [],
                type="task",
                faculty_id=current_user.faculty_id,
                department_id=current_user.department_id,
                year_id=current_user.year_id,
                details={
                    "description": (
                        description if description and description != "" else None
                    ),
                    "files_data": files if files and len(files) > 0 else [],
                },
                deadline=deadline_date,
                due_date=due_date,
                subject_id=subject.id,
                author_id=current_user.id,
                url=submission_url if submission_url and submission_url != "" else None,
            )
            session.add(task)
            await session.flush()
            await log(
                request,
                "Add",
                "Task",
                201,
                "info",
                "Task Created Successfully.",
                {"task": task.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Task created successfully",
                    "data": task.min_to_dict(),
                },
                201,
            )
            diff_days = math.ceil(
                (task.deadline.date() - datetime.now(utc_tz).date()).total_seconds()
                / 86400
            )
            diff_string = (
                f"due in {diff_days} day{'s' if diff_days > 1 else ''}"
                if diff_days > 0
                else (
                    "due today"
                    if diff_days == 0
                    else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago"
                )
            )
            await session.commit()
            await create_notification(
                request,
                "task",
                task.id,
                f'New task "{task.name}" has been assigned for '
                f'subject "{subject.name}". {diff_string}.',
                f"{os.environ.get('FRONTEND_URL')}/user/tasks/{task.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Task",
                500,
                "error",
                "An Error Occurred while Creating Task.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while creating task"},
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/tasks/{task_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Tasks"])
@is_ready
@has_registered_subjects
async def update_task(request: Request, task_id: int):
    """
    This route is used to update an existing task.
    It will return the updated task data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Task",
            400,
            "warning",
            "No Data Provided for Task Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Task",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    submission_url = data.get("submission_url", "").strip()
    deadline = data.get("deadline", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    urls = data.get("urls", [])  # List of File URLs
    links = data.get("links", [])  # List of Links
    if (
        not title
        or title == ""
        or not deadline
        or deadline == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Edit",
            "Task",
            400,
            "warning",
            "Missing Required Fields for Task Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if deadline and deadline != "":
        try:
            deadline_date = convert_to_utc(datetime.fromisoformat(deadline))
            due_date = deadline_date.date()
        except ValueError:
            await log(
                request,
                "Edit",
                "Task",
                400,
                "warning",
                "Invalid Deadline Format Provided for Task Update.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid deadline format. Please provide a valid date.",
                },
                400,
            )
            return finalize_request(response)
        if deadline_date <= datetime.now(utc_tz):
            await log(
                request,
                "Edit",
                "Task",
                400,
                "warning",
                "Past Deadline Provided for Task Update.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Deadline must be a future date."}, 400
            )
            return finalize_request(response)
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(
            request,
            "Edit",
            "Task",
            400,
            "warning",
            "Invalid Data Type for URLs or Links Provided for Task Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided for files or links"},
            400,
        )
        return finalize_request(response)
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(
                request,
                "Edit",
                "Task",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Task Update.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = await fetch_public_drive(
            get_drive_id(url), os.environ.get("GOOGLE_TOKEN_API_KEY"), request
        )
        if not file:
            await log(
                request,
                "Edit",
                "Task",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Task Update.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = file.get("data")
        # if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
        #     await log(request, "Edit", "Task", 400, 'warning', 'Unsupported File Type in URLs List Provided for Task Update.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
        #               current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
        files.append(file)
    for link in links:
        if not is_valid_url(link.get("url")):
            await log(
                request,
                "Edit",
                "Task",
                400,
                "warning",
                "Invalid Link URL in Links List Provided for Task Update.",
                {"data": dict(data), "invalid_link": link},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid Link provided"}, 400
            )
            return finalize_request(response)
    if submission_url and submission_url != "" and not is_valid_url(submission_url):
        await log(
            request,
            "Edit",
            "Task",
            400,
            "warning",
            "Invalid Submission URL Provided for Task Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid submission URL provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            task = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == task_id)
                    .options(
                        selectinload(Task.author),
                        selectinload(Task.subject),
                    )
                )
            ).scalar_one_or_none()
            if not task or task.type == "exam":
                await log(
                    request,
                    "Edit",
                    "Task",
                    404,
                    "warning",
                    "Task Not Found for Update.",
                    {"task_id": task_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Task not found"}, 404
                )
                return finalize_request(response)
            if (
                task.author_id != current_user.id
                and not "Manage All Tasks" in permissions
            ):
                await log(
                    request,
                    "Edit",
                    "Task",
                    403,
                    "warning",
                    "Unauthorized Task Update Attempt by Non-Author User.",
                    {"task_id": task_id, "author_id": task.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to update this task",
                    },
                    403,
                )
                return finalize_request(response)
            task.name = title
            task.deadline = deadline_date
            task.due_date = due_date
            task.details["description"] = description
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Edit",
                    "Task",
                    404,
                    "warning",
                    "Subject Not Found for Task Update.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Edit",
                    "Task",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Task Update.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            task.subject_id = subject.id
            old_urls = [u for u in task.urls if u not in urls]
            for old_url in old_urls:
                removed = await remove_file_from_drive(
                    old_url, current_user.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Edit",
                        "Task",
                        500,
                        "error",
                        "Failed to Remove Old File from Drive during Task Update.",
                        {"task_id": task_id, "file_url": old_url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to update task. Please try again later.",
                        },
                        500,
                    )
                    return finalize_request(response)
            task.urls = urls if urls and len(urls) > 0 else []
            task.links = links if links and len(links) > 0 else []
            task.url = (
                submission_url if submission_url and submission_url != "" else None
            )
            task.details["files_data"] = files
            task.author_id = (
                current_user.id
            )  # Update the author to the user who made the update
            await session.flush()
            await log(
                request,
                "Edit",
                "Task",
                200,
                "info",
                "Task Updated Successfully.",
                {"task": task.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Task updated successfully",
                    "data": task.min_to_dict(),
                },
                200,
            )
            diff_days = math.ceil(
                (task.deadline.date() - datetime.now(utc_tz).date()).total_seconds()
                / 86400
            )
            diff_string = (
                f"due in {diff_days} day{'s' if diff_days > 1 else ''}"
                if diff_days > 0
                else (
                    "due today"
                    if diff_days == 0
                    else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago"
                )
            )
            await session.commit()
            await create_notification(
                request,
                "task",
                task.id,
                f'Task "{task.name}" has been updated for '
                f'subject "{subject.name}". {diff_string}.',
                f"{os.environ.get('FRONTEND_URL')}/user/tasks/{task.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Task",
                500,
                "error",
                "An Error Occurred while Updating Task.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while updating task"},
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/tasks/{task_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Tasks"])
@is_ready
@has_registered_subjects
async def delete_task(request: Request, task_id: int):
    """
    This route is used to delete an existing task.
    It will return a success message if the task is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    async with async_session() as session:
        await session.begin()
        try:
            task = (
                await session.execute(Select(Task).where(Task.id == task_id))
            ).scalar_one_or_none()
            if not task or task.type == "exam":
                await log(
                    request,
                    "Delete",
                    "Task",
                    404,
                    "warning",
                    "Task Not Found for Deletion.",
                    {"task_id": task_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Task not found"}, 404
                )
                return finalize_request(response)
            if (
                task.author_id != current_user.id
                and not "Manage All Tasks" in permissions
            ):
                await log(
                    request,
                    "Delete",
                    "Task",
                    403,
                    "warning",
                    "Unauthorized Task Deletion Attempt by Non-Author User.",
                    {"task_id": task_id, "author_id": task.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to delete this task",
                    },
                    403,
                )
                return finalize_request(response)
            for url in task.urls:
                removed = await remove_file_from_drive(
                    url, current_user.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Delete",
                        "Task",
                        500,
                        "error",
                        "Failed to Remove File from Drive during Task Deletion.",
                        {"task_id": task_id, "file_url": url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to delete task. Please try again later.",
                        },
                        500,
                    )
                    return finalize_request(response)
            await session.delete(task)
            await log(
                request,
                "Delete",
                "Task",
                200,
                "info",
                "Task Deleted Successfully.",
                {"task_id": task_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Task deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Task",
                500,
                "error",
                "An Error Occurred while Deleting Task.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while deleting task"},
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/tasks")
@is_logged_in
@rate_limit
@is_authorized(["View Tasks"])
@is_ready
@has_registered_subjects
async def get_tasks(request: Request):
    """
    This route is used to get all tasks.
    It will return a list of tasks.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Tasks",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        author_id = data.get("author_id", None)  # Author ID
        start_date = data.get("start_date", "").strip()
        end_date = data.get("end_date", "").strip()
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if start_date and start_date != "":
            try:
                start_date_obj = (
                    datetime.fromisoformat(start_date)
                    .replace(microsecond=0, tzinfo=cairo_tz)
                    .date()
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid Start Date Format Provided for Getting Tasks.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid start date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = (
                    datetime.fromisoformat(end_date)
                    .replace(microsecond=0, tzinfo=cairo_tz)
                    .date()
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid End Date Format Provided for Getting Tasks.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid end date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if (
            (
                subject_id
                and (not is_int(subject_id) or int(subject_id) < 1)
                or faculty_id
                and (not is_int(faculty_id) or int(faculty_id) < 1)
                or department_id
                and (not is_int(department_id) or int(department_id) < 1)
                or year_id
                and (not is_int(year_id) or int(year_id) < 1)
            )
            or author_id
            and (not is_int(author_id) or int(author_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Tasks",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Tasks.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if (
            faculty_id
            and "Access All Faculties" not in user_permissions
            or department_id
            and "Access All Departments" not in user_permissions
            or year_id
            and "Access All Years" not in user_permissions
        ):
            await log(
                request,
                "Get",
                "Tasks",
                403,
                "warning",
                "Unauthorized Access Attempt to Restricted Faculty, Department, or Year for Getting Tasks.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You are not authorized to access the specified criteria",
                },
                403,
            )
            return finalize_request(response)
        async with async_session() as session:
            query = (
                Select(Task)
                .options(
                    selectinload(Task.faculty),
                    selectinload(Task.department),
                    selectinload(Task.year),
                    selectinload(Task.subject),
                    selectinload(Task.author),
                )
                .where(Task.type != "exam")
            )
            if "Access All Faculties" not in user_permissions:
                faculty_id = current_user.faculty_id
            if "Access All Departments" not in user_permissions:
                department_id = current_user.department_id
            if "Access All Years" not in user_permissions:
                year_id = current_user.year_id
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Faculty Not Found for Getting Tasks.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.faculty_id == faculty.id)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if not department or (
                    faculty_id and department.faculty_id != faculty.id
                ):
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Department Not Found or Does Not Belong to Specified Faculty for Getting Tasks.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department not found in the specified faculty",
                        },
                        404,
                    )
                    return finalize_request(response)
                query = query.where(Task.department_id == department.id)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Year Not Found for Getting Tasks.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.year_id == year.id)
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject).where(Subject.id == int(subject_id))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Subject Not Found for Getting Tasks.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.subject_id == subject.id)
            if author_id:
                author = (
                    await session.execute(Select(User).where(User.id == int(author_id)))
                ).scalar_one_or_none()
                if not author:
                    await log(
                        request,
                        "Get",
                        "Tasks",
                        404,
                        "warning",
                        "Author Not Found for Getting Tasks.",
                        {"author_id": author_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Author not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.author_id == author.id)
            if start_date_obj:
                query = query.where(Task.due_date >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.due_date <= end_date_obj)
            if query_search and query_search != "":
                query = query.where(func.lower(Task.name).startswith(query_search))
            result = (
                (
                    await session.execute(
                        query.order_by(
                            (Task.deadline >= func.now()).desc(), Task.deadline.asc()
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Tasks " "Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Tasks",
                    400,
                    "warning",
                    "Invalid Limit Provided for Tasks Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            tasks = result[:limit]
            await log(
                request,
                "Get",
                "Tasks",
                200,
                "info",
                "Tasks Retrieved Successfully.",
                {"filters": dict(data), "count": len(tasks)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Tasks retrieved successfully",
                    "data": [t.to_dict() for t in tasks],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Tasks",
            500,
            "error",
            "An Error Occurred while Getting Tasks.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting tasks"}, 500
        )
        return finalize_request(response)


@admin_prefix.get("/tasks/{task_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Tasks"])
@is_ready
@has_registered_subjects
async def get_task(request: Request, task_id: int):
    """
    This route is used to get a specific task by its ID.
    It will return the task data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            task = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == task_id)
                    .options(
                        selectinload(Task.author),
                        selectinload(Task.subject),
                        selectinload(Task.faculty),
                        selectinload(Task.department),
                        selectinload(Task.year),
                    )
                )
            ).scalar_one_or_none()
            if not task or task.type == "exam":
                await log(
                    request,
                    "Get",
                    "Task",
                    404,
                    "warning",
                    "Task Not Found.",
                    {"task_id": task_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Task not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Task",
                200,
                "info",
                "Task Retrieved Successfully.",
                {"task": task.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Task retrieved successfully",
                    "data": task.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Task",
            500,
            "error",
            "An Error Occurred while Getting Task.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting task"}, 500
        )
        return finalize_request(response)


@admin_prefix.post("/exams")
@is_logged_in
@rate_limit
@is_authorized(["Add Exams"])
@is_ready
@has_registered_subjects
async def create_exam(request: Request):
    """
    This route is used to create a new exam.
    It will return the created exam data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "No Data Provided for Exam Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    instructions = data.get("instructions", "").strip()
    due_date = data.get("due_date", "").strip()
    start_time = data.get("start_time", "").strip()
    location = data.get("location", "").strip()
    duration = data.get("duration")
    exam_type = data.get("exam_type", "").strip().title()
    exam_format = data.get("exam_format", "").strip()
    exam_weight = data.get("exam_weight", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    if (
        not title
        or title == ""
        or not due_date
        or due_date == ""
        or not exam_type
        or exam_type == ""
        or not start_time
        or start_time == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "Missing Required Fields for Exam Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    try:
        deadline_date = convert_to_utc(
            datetime.fromisoformat(f"{due_date}T{start_time}")
        )
        due_date = deadline_date.date()
    except ValueError:
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "Invalid Deadline Format Provided for Exam Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid date format or start time format. Please provide a valid date and start time.",
            },
            400,
        )
        return finalize_request(response)
    if deadline_date and deadline_date <= datetime.now(utc_tz):
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "Past Deadline Provided for Exam Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Exam Date must be a future date."}, 400
        )
        return finalize_request(response)
    if duration and (not is_float(duration) or float(duration) < 0):
        await log(
            request,
            "Add",
            "Exam",
            400,
            "warning",
            "Invalid Duration Provided for Exam Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid duration provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Add",
                    "Exam",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Exam Creation.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            exam = Task(
                name=title,
                type="exam",
                faculty_id=current_user.faculty_id,
                department_id=current_user.department_id,
                year_id=current_user.year_id,
                details={
                    "description": (
                        description if description and description != "" else None
                    ),
                    "instructions": (
                        instructions if instructions and instructions != "" else None
                    ),
                    "location": location if location and location != "" else None,
                    "exam_type": exam_type if exam_type and exam_type != "" else None,
                    "exam_format": (
                        exam_format if exam_format and exam_format != "" else None
                    ),
                    "exam_weight": (
                        exam_weight if exam_weight and exam_weight != "" else None
                    ),
                    "duration": (
                        float(duration)
                        if duration and is_float(duration) and float(duration) > 0
                        else None
                    ),
                },
                deadline=deadline_date,
                due_date=due_date,
                subject_id=subject.id,
                author_id=current_user.id,
            )
            session.add(exam)
            await session.flush()
            await log(
                request,
                "Add",
                "Exam",
                201,
                "info",
                "Exam Created Successfully.",
                {"exam": exam.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exam created successfully",
                    "data": exam.min_to_dict(),
                },
                201,
            )
            diff_days = math.ceil(
                (exam.deadline.date() - datetime.now(utc_tz).date()).total_seconds()
                / 86400
            )
            diff_string = (
                f"due in {diff_days} day{'s' if diff_days > 1 else ''}"
                if diff_days > 0
                else (
                    "due today"
                    if diff_days == 0
                    else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago"
                )
            )
            await session.commit()
            await create_notification(
                request,
                "exam",
                exam.id,
                f'New exam "{exam.name}" has been assigned for '
                f'subject "{subject.name}". {diff_string}.',
                f"{os.environ.get('FRONTEND_URL')}/user/exams/{exam.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Exam",
                500,
                "error",
                "An Error Occurred while Creating Exam.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while creating exam"},
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/exams/{exam_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Exams"])
@is_ready
@has_registered_subjects
async def update_exam(request: Request, exam_id: int):
    """
    This route is used to update an existing exam.
    It will return the updated exam data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "No Data Provided for Exam Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    instructions = data.get("instructions", "").strip()
    due_date = data.get("due_date", "").strip()
    start_time = data.get("start_time", "").strip()
    location = data.get("location", "").strip()
    duration = data.get("duration")
    exam_type = data.get("exam_type", "").strip().title()
    exam_format = data.get("exam_format", "").strip()
    exam_weight = data.get("exam_weight", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    if (
        not title
        or title == ""
        or not due_date
        or due_date == ""
        or not exam_type
        or exam_type == ""
        or not start_time
        or start_time == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "Missing Required Fields for Exam Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    try:
        deadline_date = convert_to_utc(
            datetime.fromisoformat(f"{due_date}T{start_time}")
        )
        due_date = deadline_date.date()
    except ValueError:
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "Invalid Deadline Format Provided for Exam Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Invalid date format or start time format. Please provide a valid date and start time.",
            },
            400,
        )
        return finalize_request(response)
    if deadline_date and deadline_date <= datetime.now(utc_tz):
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "Past Deadline Provided for Exam Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Exam Date must be a future date."}, 400
        )
        return finalize_request(response)
    if duration and (not is_float(duration) or float(duration) < 0):
        await log(
            request,
            "Edit",
            "Exam",
            400,
            "warning",
            "Invalid Duration Provided for Exam Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid duration provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            exam = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == exam_id)
                    .options(
                        selectinload(Task.author),
                        selectinload(Task.subject),
                    )
                )
            ).scalar_one_or_none()
            if not exam or exam.type != "exam":
                await log(
                    request,
                    "Edit",
                    "Exam",
                    404,
                    "warning",
                    "Exam Not Found for Update.",
                    {"exam_id": exam_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Exam not found"}, 404
                )
                return finalize_request(response)
            if (
                exam.author_id != current_user.id
                and not "Manage All Exams" in permissions
            ):
                await log(
                    request,
                    "Edit",
                    "Exam",
                    403,
                    "warning",
                    "Unauthorized Exam Update Attempt by Non-Author User.",
                    {"exam_id": exam_id, "author_id": exam.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to update this exam",
                    },
                    403,
                )
                return finalize_request(response)
            exam.name = title
            exam.deadline = deadline_date
            exam.due_date = due_date
            exam.details["description"] = description
            exam.details["instructions"] = instructions
            exam.details["location"] = location
            exam.details["duration"] = (
                float(duration)
                if duration and is_float(duration) and float(duration) > 0
                else None
            )
            exam.details["exam_format"] = exam_format
            exam.details["exam_weight"] = exam_weight
            exam.details["exam_type"] = exam_type
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Edit",
                    "Exam",
                    404,
                    "warning",
                    "Subject Not Found for Exam Update.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Edit",
                    "Exam",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Exam Update.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            exam.subject_id = subject.id
            exam.author_id = (
                current_user.id
            )  # Update the author to the user who made the update
            await session.flush()
            await log(
                request,
                "Edit",
                "Exam",
                200,
                "info",
                "Exam Updated Successfully.",
                {"exam": exam.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exam updated successfully",
                    "data": exam.min_to_dict(),
                },
                200,
            )
            diff_days = math.ceil(
                (exam.deadline.date() - datetime.now(utc_tz).date()).total_seconds()
                / 86400
            )
            diff_string = (
                f"due in {diff_days} day{'s' if diff_days > 1 else ''}"
                if diff_days > 0
                else (
                    "due today"
                    if diff_days == 0
                    else f"was due {-diff_days} day{'s' if diff_days < -1 else ''} ago"
                )
            )
            await session.commit()
            await create_notification(
                request,
                "exam",
                exam.id,
                f'Exam "{exam.name}" has been updat for '
                f'subject "{subject.name}". {diff_string}.',
                f"{os.environ.get('FRONTEND_URL')}/user/exams/{exam.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Exam",
                500,
                "error",
                "An Error Occurred while Updating Exam.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while updating exam"},
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/exams/{exam_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Exams"])
@is_ready
@has_registered_subjects
async def delete_exam(request: Request, exam_id: int):
    """
    This route is used to delete an existing exam.
    It will return a success message if the exam is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    async with async_session() as session:
        await session.begin()
        try:
            exam = (
                await session.execute(Select(Task).where(Task.id == exam_id))
            ).scalar_one_or_none()
            if not exam or exam.type != "exam":
                await log(
                    request,
                    "Delete",
                    "Exam",
                    404,
                    "warning",
                    "Exam Not Found for Deletion.",
                    {"exam_id": exam_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Exam not found"}, 404
                )
                return finalize_request(response)
            if (
                exam.author_id != current_user.id
                and not "Manage All Tasks" in permissions
            ):
                await log(
                    request,
                    "Delete",
                    "Exam",
                    403,
                    "warning",
                    "Unauthorized Exam Deletion Attempt by Non-Author User.",
                    {"exam_id": exam_id, "author_id": exam.author.id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to delete this exam",
                    },
                    403,
                )
                return finalize_request(response)
            await session.delete(exam)
            await log(
                request,
                "Delete",
                "Exam",
                200,
                "info",
                "Exam Deleted Successfully.",
                {"exam_id": exam_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Exam deleted successfully"}, 200
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Exam",
                500,
                "error",
                "An Error Occurred while Deleting Exam.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {"status": "error", "message": "An error occurred while deleting exam"},
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/exams")
@is_logged_in
@rate_limit
@is_authorized(["View Exams"])
@is_ready
@has_registered_subjects
async def get_exams(request: Request):
    """
    This route is used to get all exams.
    It will return a list of exams.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Exams",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        author_id = data.get("author_id", None)  # Author ID
        start_date = data.get("start_date", "").strip()
        end_date = data.get("end_date", "").strip()
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if start_date and start_date != "":
            try:
                start_date_obj = (
                    datetime.fromisoformat(start_date)
                    .replace(microsecond=0, tzinfo=cairo_tz)
                    .date()
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid Start Date Format Provided for Getting Exams.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid start date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = (
                    datetime.fromisoformat(end_date)
                    .replace(microsecond=0, tzinfo=cairo_tz)
                    .date()
                )
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid End Date Format Provided for Getting Exams.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid end date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if (
            (
                subject_id
                and (not is_int(subject_id) or int(subject_id) < 1)
                or faculty_id
                and (not is_int(faculty_id) or int(faculty_id) < 1)
                or department_id
                and (not is_int(department_id) or int(department_id) < 1)
                or year_id
                and (not is_int(year_id) or int(year_id) < 1)
            )
            or author_id
            and (not is_int(author_id) or int(author_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Exams",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Exams.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if (
            faculty_id
            and "Access All Faculties" not in user_permissions
            or department_id
            and "Access All Departments" not in user_permissions
            or year_id
            and "Access All Years" not in user_permissions
        ):
            await log(
                request,
                "Get",
                "Exams",
                403,
                "warning",
                "Unauthorized Access Attempt to Restricted Faculty, Department, or Year for Getting Exams.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You are not authorized to access the specified criteria",
                },
                403,
            )
            return finalize_request(response)
        async with async_session() as session:
            query = (
                Select(Task)
                .options(
                    selectinload(Task.faculty),
                    selectinload(Task.department),
                    selectinload(Task.year),
                    selectinload(Task.subject),
                    selectinload(Task.author),
                )
                .where(Task.type == "exam")
            )
            if "Access All Faculties" not in user_permissions:
                faculty_id = current_user.faculty_id
            if "Access All Departments" not in user_permissions:
                department_id = current_user.department_id
            if "Access All Years" not in user_permissions:
                year_id = current_user.year_id
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Faculty Not Found for Getting Exams.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.faculty_id == faculty.id)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if not department or (
                    faculty_id and department.faculty_id != faculty.id
                ):
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Department Not Found or Does Not Belong to Specified Faculty for Getting Exams.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department not found in the specified faculty",
                        },
                        404,
                    )
                    return finalize_request(response)
                query = query.where(Task.department_id == department.id)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Year Not Found for Getting Exams.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.year_id == year.id)
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject).where(Subject.id == int(subject_id))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Subject Not Found for Getting Exams.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.subject_id == subject.id)
            if author_id:
                author = (
                    await session.execute(Select(User).where(User.id == int(author_id)))
                ).scalar_one_or_none()
                if not author:
                    await log(
                        request,
                        "Get",
                        "Exams",
                        404,
                        "warning",
                        "Author Not Found for Getting Exams.",
                        {"author_id": author_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Author not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Task.author_id == author.id)
            if start_date_obj:
                query = query.where(Task.due_date >= start_date_obj)
            if end_date_obj:
                query = query.where(Task.due_date <= end_date_obj)
            if query_search and query_search != "":
                query = query.where(func.lower(Task.name).startswith(query_search))
            result = (
                (
                    await session.execute(
                        query.order_by(
                            (Task.deadline >= func.now()).desc(), Task.deadline.asc()
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Exams " "Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Exams",
                    400,
                    "warning",
                    "Invalid Limit Provided for Exams Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            exams = result[:limit]
            await log(
                request,
                "Get",
                "Exams",
                200,
                "info",
                "Exams Retrieved Successfully.",
                {"filters": dict(data), "count": len(exams)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exams retrieved successfully",
                    "data": [e.to_dict() for e in exams],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Exams",
            500,
            "error",
            "An Error Occurred while Getting Exams.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting exams"}, 500
        )
        return finalize_request(response)


@admin_prefix.get("/exams/{exam_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Exams"])
@is_ready
@has_registered_subjects
async def get_exam(request: Request, exam_id: int):
    """
    This route is used to get a specific exam by its ID.
    It will return the exam data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            exam = (
                await session.execute(
                    Select(Task)
                    .where(Task.id == exam_id)
                    .options(
                        selectinload(Task.author),
                        selectinload(Task.subject),
                        selectinload(Task.faculty),
                        selectinload(Task.department),
                        selectinload(Task.year),
                    )
                )
            ).scalar_one_or_none()
            if not exam or exam.type != "exam":
                await log(
                    request,
                    "Get",
                    "Exam",
                    404,
                    "warning",
                    "Exam Not Found.",
                    {"exam_id": exam_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Exam not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Exam",
                200,
                "info",
                "Exam Retrieved Successfully.",
                {"exam": exam.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Exam retrieved successfully",
                    "data": exam.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Exam",
            500,
            "error",
            "An Error Occurred while Getting Exam.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting exam"}, 500
        )
        return finalize_request(response)


@admin_prefix.post("/announcements")
@is_logged_in
@rate_limit
@is_authorized(["Add Announcements"])
@is_ready
@has_registered_subjects
async def create_announcement(request: Request):
    """
    This route is used to create a new announcement.
    It will return the created announcement data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Add",
            "Announcement",
            400,
            "warning",
            "No Data Provided for Announcement Creation.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Add",
            "Announcement",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    date = data.get("date", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    urls = data.get("urls", [])  # List of File URLs
    links = data.get("links", [])  # List of Links
    if (
        not title
        or title == ""
        or not content
        or content == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Add",
            "Announcement",
            400,
            "warning",
            "Missing Required Fields for Announcement Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    date_date = None
    if date and date != "":
        try:
            date_date = convert_to_utc(datetime.fromisoformat(date))
        except ValueError:
            await log(
                request,
                "Add",
                "Announcement",
                400,
                "warning",
                "Invalid Date Format Provided for Announcement Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid date format. Please provide a valid date.",
                },
                400,
            )
            return finalize_request(response)
        if date_date and date_date <= datetime.now(utc_tz):
            await log(
                request,
                "Add",
                "Announcement",
                400,
                "warning",
                "Past Date Provided for Announcement Creation.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Date must be a future date."}, 400
            )
            return finalize_request(response)
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(
            request,
            "Add",
            "Announcement",
            400,
            "warning",
            "Invalid Data Type for URLs or Links Provided for Announcement Creation.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided for files or links"},
            400,
        )
        return finalize_request(response)
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(
                request,
                "Add",
                "Announcement",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Announcement Creation.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = await fetch_public_drive(
            get_drive_id(url), os.environ.get("GOOGLE_TOKEN_API_KEY"), request
        )
        if not file:
            await log(
                request,
                "Add",
                "Announcement",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Announcement Creation.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = file.get("data")
        # if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
        #     await log(request, "Add", "Announcement", 400, 'warning', 'Unsupported File Type in URLs List Provided for Announcement Creation.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
        #               current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
        files.append(file)
    for link in links:
        if not is_valid_url(link.get("url")):
            await log(
                request,
                "Add",
                "Announcement",
                400,
                "warning",
                "Invalid Link URL in Links List Provided for Announcement Creation.",
                {"data": dict(data), "invalid_link": link},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid Link provided"}, 400
            )
            return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Add",
                    "Announcement",
                    404,
                    "warning",
                    "Subject Not Found for Announcement Creation.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Edit",
                    "Announcement",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Announcement Update.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            announcement = Announcement(
                title=title,
                content=content,
                date=date_date,
                faculty_id=current_user.faculty_id,
                department_id=current_user.department_id,
                year_id=current_user.year_id,
                subject_id=subject.id,
                author_id=current_user.id,
                urls=urls if urls and len(urls) > 0 else [],
                links=links if links and len(links) > 0 else [],
                details={"files_data": files if files and len(files) > 0 else []},
            )
            session.add(announcement)
            await session.flush()
            await log(
                request,
                "Add",
                "Announcement",
                201,
                "info",
                "Announcement Created Successfully.",
                {"announcement": announcement.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcement created successfully",
                    "data": announcement.min_to_dict(),
                },
                201,
            )
            date_str = (
                f' on {announcement.date.strftime("%b %d, %Y")}'
                if announcement.date
                else ""
            )
            await session.commit()
            await create_notification(
                request,
                "announcement",
                announcement.id,
                f'New announcement "{announcement.title}" has been posted for subject "{subject.name}"{date_str}.',
                f"{os.environ.get('FRONTEND_URL')}/user/announcements/{announcement.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Add",
                "Announcement",
                500,
                "error",
                "An Error Occurred while Creating Announcement.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while creating announcement. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.patch("/announcements/{announcement_id}")
@is_logged_in
@rate_limit
@is_authorized(["Edit Announcements"])
@is_ready
@has_registered_subjects
async def update_announcement(request: Request, announcement_id: int):
    """
    This route is used to update an existing announcement.
    It will return the updated announcement data.
    """
    current_user = request.state.current_user
    data = await request.json()
    if not data:
        await log(
            request,
            "Edit",
            "Announcement",
            400,
            "warning",
            "No Data Provided for Announcement Update.",
            {},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Empty Request was sent. Please provide data correctly.",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(data):
        await log(
            request,
            "Edit",
            "Announcement",
            400,
            "warning",
            "Un Sanitized Data Provided in The Request Body.",
            {},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    date = data.get("date", "").strip()
    subject_id = data.get("subject_id", None)  # Subject ID
    urls = data.get("urls", [])  # List of File URLs
    links = data.get("links", [])  # List of Links
    if (
        not title
        or title == ""
        or not content
        or content == ""
        or not subject_id
        or not is_int(subject_id)
        or int(subject_id) < 1
    ):
        await log(
            request,
            "Edit",
            "Announcement",
            400,
            "warning",
            "Missing Required Fields for Announcement Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    date_date = None
    if date and date != "":
        try:
            date_date = convert_to_utc(datetime.fromisoformat(date))
        except ValueError:
            await log(
                request,
                "Edit",
                "Announcement",
                400,
                "warning",
                "Invalid Date Format Provided for Announcement Update.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "Invalid date format. Please provide a valid date.",
                },
                400,
            )
            return finalize_request(response)
        if date_date and date_date <= datetime.now(utc_tz):
            await log(
                request,
                "Edit",
                "Announcement",
                400,
                "warning",
                "Past Date Provided for Announcement Update.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Date must be a future date."}, 400
            )
            return finalize_request(response)
    if not isinstance(urls, list) or not isinstance(links, list):
        await log(
            request,
            "Edit",
            "Announcement",
            400,
            "warning",
            "Invalid Data Type for URLs or Links Provided for Announcement Update.",
            {"data": dict(data)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided for files or links"},
            400,
        )
        return finalize_request(response)
    files = []
    for url in urls:
        if not is_drive_url(url):
            await log(
                request,
                "Edit",
                "Announcement",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Announcement Update.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = await fetch_public_drive(
            get_drive_id(url), os.environ.get("GOOGLE_TOKEN_API_KEY"), request
        )
        if not file:
            await log(
                request,
                "Edit",
                "Announcement",
                400,
                "warning",
                "Invalid File URL in URLs List Provided for Announcement Update.",
                {"data": dict(data), "invalid_url": url},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid File provided"}, 400
            )
            return finalize_request(response)
        file = file.get("data")
        # if not is_allowed_file_type(get_file_type(file.get('mimeType'))):
        #     await log(request, "Edit", "Announcement", 400, 'warning', 'Unsupported File Type in URLs List Provided for Announcement Update.', {'data': dict(data), 'file_type': file.get('mimeType'), 'invalid_url': url},
        #               current_user.id)
        #     response = JSONResponse({
        #         'status': 'error',
        #         'message': f"Unsupported File Type {get_file_type(file.get('mimeType'))}."
        #     }, 400)
        #     return finalize_request(response)
        files.append(file)
    for link in links:
        if not is_valid_url(link.get("url")):
            await log(
                request,
                "Edit",
                "Announcement",
                400,
                "warning",
                "Invalid Link URL in Links List Provided for Announcement Update.",
                {"data": dict(data), "invalid_link": link},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": f"Invalid Link provided"}, 400
            )
            return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            current_user = await session.merge(current_user)
            announcement = (
                await session.execute(
                    Select(Announcement)
                    .where(Announcement.id == announcement_id)
                    .options(
                        selectinload(Announcement.author),
                        selectinload(Announcement.subject),
                    )
                )
            ).scalar_one_or_none()
            if not announcement:
                await log(
                    request,
                    "Edit",
                    "Announcement",
                    404,
                    "warning",
                    "Announcement Not Found for Update.",
                    {"announcement_id": announcement_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Announcement not found"}, 404
                )
                return finalize_request(response)
            if (
                announcement.author_id != current_user.id
                and not "Manage All Announcements" in permissions
            ):
                await log(
                    request,
                    "Edit",
                    "Announcement",
                    403,
                    "warning",
                    "Unauthorized Announcement Update Attempt by Non-Author User.",
                    {
                        "announcement_id": announcement_id,
                        "author_id": announcement.author.id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to update this announcement",
                    },
                    403,
                )
                return finalize_request(response)
            announcement.title = title
            announcement.content = content
            announcement.date = date_date
            subject = (
                await session.execute(
                    Select(Subject).where(Subject.id == int(subject_id))
                )
            ).scalar_one_or_none()
            if not subject:
                await log(
                    request,
                    "Edit",
                    "Announcement",
                    404,
                    "warning",
                    "Subject Not Found for Announcement Update.",
                    {"subject_id": subject_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Subject not found"}, 404
                )
                return finalize_request(response)
            if (
                not subject
                or subject.faculty_id != current_user.faculty_id
                or subject.department_id != current_user.department_id
                or subject.year_id != current_user.year_id
            ):
                await log(
                    request,
                    "Edit",
                    "Announcement",
                    404,
                    "warning",
                    "Subject Not Found or Does Not Belong to User's Faculty, Department, or Year for Announcement Update.",
                    {
                        "subject_id": subject_id,
                        "faculty_id": current_user.faculty_id,
                        "department_id": current_user.department_id,
                        "year_id": current_user.year_id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Subject not found in your criteria",
                    },
                    404,
                )
                return finalize_request(response)
            old_urls = [u for u in announcement.urls if u not in urls]
            for old_url in old_urls:
                removed = await remove_file_from_drive(
                    old_url, current_user.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Edit",
                        "Announcement",
                        400,
                        "warning",
                        "Failed to Remove Old File from Drive during Announcement Update.",
                        {"old_url": old_url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to update announcement. Please try again later.",
                        },
                        400,
                    )
                    return finalize_request(response)
            announcement.urls = urls if urls and len(urls) > 0 else []
            if files and len(files) > 0:
                announcement.details["files_data"] = files
            announcement.links = links if links and len(links) > 0 else []
            announcement.subject_id = subject.id
            announcement.author_id = (
                current_user.id
            )  # Update the author to the user who made the update
            await session.flush()
            await log(
                request,
                "Edit",
                "Announcement",
                200,
                "info",
                "Announcement Updated Successfully.",
                {"announcement": announcement.min_to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcement updated successfully",
                    "data": announcement.min_to_dict(),
                },
                200,
            )
            date_str = (
                f' on {announcement.date.strftime("%b %d, %Y")}'
                if announcement.date
                else ""
            )
            await session.commit()
            await create_notification(
                request,
                "announcement",
                announcement.id,
                f'Announcement "{announcement.title}" has been updated for subject "{subject.name}"{date_str}.',
                f"{os.environ.get('FRONTEND_URL')}/user/announcements/{announcement.id}",
            )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Edit",
                "Announcement",
                500,
                "error",
                "An Error Occurred while Updating Announcement.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while updating announcement. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.delete("/announcements/{announcement_id}")
@is_logged_in
@rate_limit
@is_authorized(["Delete Announcements"])
@is_ready
@has_registered_subjects
async def delete_announcement(request: Request, announcement_id: int):
    """
    This route is used to delete an existing announcement.
    It will return a success message if the announcement is deleted successfully.
    """
    current_user = request.state.current_user
    permissions = (json.loads((await get_user_permissions(request)).body)).get(
        "data", []
    )
    async with async_session() as session:
        await session.begin()
        try:
            announcement = (
                await session.execute(
                    Select(Announcement).where(Announcement.id == announcement_id)
                )
            ).scalar_one_or_none()
            if not announcement:
                await log(
                    request,
                    "Delete",
                    "Announcement",
                    404,
                    "warning",
                    "Announcement Not Found for Deletion.",
                    {"announcement_id": announcement_id},
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Announcement not found"}, 404
                )
                return finalize_request(response)
            if (
                announcement.author_id != current_user.id
                and not "Manage All Announcements" in permissions
            ):
                await log(
                    request,
                    "Delete",
                    "Announcement",
                    403,
                    "warning",
                    "Unauthorized Announcement Deletion Attempt by Non-Author User.",
                    {
                        "announcement_id": announcement_id,
                        "author_id": announcement.author.id,
                    },
                    current_user.id,
                )
                await session.rollback()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "You are not authorized to delete this announcement",
                    },
                    403,
                )
                return finalize_request(response)
            for url in announcement.urls or []:
                removed = await remove_file_from_drive(
                    url, current_user.google_refresh_token, request
                )
                if not removed:
                    await log(
                        request,
                        "Delete",
                        "Announcement",
                        400,
                        "warning",
                        "Failed to Remove File from Drive during Announcement Deletion.",
                        {"url": url},
                        current_user.id,
                    )
                    await session.rollback()
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Failed to delete announcement. Please try again later.",
                        },
                        400,
                    )
                    return finalize_request(response)
            await session.delete(announcement)
            await log(
                request,
                "Delete",
                "Announcement",
                200,
                "info",
                "Announcement Deleted Successfully.",
                {"announcement_id": announcement_id},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "success", "message": "Announcement deleted successfully"},
                200,
            )
            await session.commit()
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Delete",
                "Announcement",
                500,
                "error",
                "An Error Occurred while Deleting Announcement.",
                {"error": str(e)},
                current_user.id,
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while deleting announcement. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


@admin_prefix.get("/announcements")
@is_logged_in
@rate_limit
@is_authorized(["View Announcements"])
@is_ready
@has_registered_subjects
async def get_announcements(request: Request):
    """
    This route is used to get all announcements.
    It will return a list of announcements.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Announcements",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        subject_id = data.get("subject_id", None)  # Subject ID
        faculty_id = data.get("faculty_id", None)
        department_id = data.get("department_id", None)
        year_id = data.get("year_id", None)
        start_date = data.get("start_date", "").strip()
        end_date = data.get("end_date", "").strip()
        author_id = data.get("author_id", None)  # Author ID
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        start_date_obj = None
        end_date_obj = None
        user_permissions = (json.loads((await get_user_permissions(request)).body)).get(
            "data", []
        )
        if start_date and start_date != "":
            try:
                start_date_obj = convert_to_utc(datetime.fromisoformat(start_date))
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid Start Date Format Provided for Getting Announcements.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid start date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if end_date and end_date != "":
            try:
                end_date_obj = convert_to_utc(datetime.fromisoformat(end_date))
            except ValueError:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid End Date Format Provided for Getting Announcements.",
                    {"data": dict(data)},
                    current_user.id,
                )
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "Invalid end date format. Please provide a valid date.",
                    },
                    400,
                )
                return finalize_request(response)
        if (
            (
                subject_id
                and (not is_int(subject_id) or int(subject_id) < 1)
                or faculty_id
                and (not is_int(faculty_id) or int(faculty_id) < 1)
                or department_id
                and (not is_int(department_id) or int(department_id) < 1)
                or year_id
                and (not is_int(year_id) or int(year_id) < 1)
            )
            or author_id
            and (not is_int(author_id) or int(author_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Announcements",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Announcements.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        if (
            faculty_id
            and "Access All Faculties" not in user_permissions
            or department_id
            and "Access All Departments" not in user_permissions
            or year_id
            and "Access All Years" not in user_permissions
        ):
            await log(
                request,
                "Get",
                "Announcements",
                403,
                "warning",
                "Unauthorized Access Attempt to Restricted Faculty, Department, "
                "or Year for Getting Announcements.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "You are not authorized to access the specified criteria",
                },
                403,
            )
            return finalize_request(response)
        async with async_session() as session:
            query = (
                Select(Announcement)
                .options(
                    selectinload(Announcement.subject),
                    selectinload(Announcement.faculty),
                    selectinload(Announcement.department),
                    selectinload(Announcement.year),
                    selectinload(Announcement.author).selectinload(User.faculty),
                    selectinload(Announcement.author).selectinload(User.department),
                    selectinload(Announcement.author).selectinload(User.year),
                    selectinload(Announcement.author).selectinload(User.role),
                    selectinload(Announcement.author).selectinload(User.pending_user),
                    selectinload(Announcement.author).selectinload(User.notifications),
                )
                .order_by(Announcement.created_at.desc())
            )
            if "Access All Faculties" not in user_permissions:
                faculty_id = current_user.faculty_id
            if "Access All Departments" not in user_permissions:
                department_id = current_user.department_id
            if "Access All Years" not in user_permissions:
                year_id = current_user.year_id
            if faculty_id:
                faculty = (
                    await session.execute(
                        Select(Faculty).where(Faculty.id == int(faculty_id))
                    )
                ).scalar_one_or_none()
                if not faculty:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Faculty Not Found for Getting Announcements.",
                        {"faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Faculty not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Announcement.faculty_id == faculty.id)
            if department_id:
                department = (
                    await session.execute(
                        Select(Department).where(Department.id == int(department_id))
                    )
                ).scalar_one_or_none()
                if not department or (
                    faculty_id and department.faculty_id != int(faculty_id)
                ):
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Department Not Found or Does Not Belong to Specified Faculty for Getting Announcements.",
                        {"department_id": department_id, "faculty_id": faculty_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Department not found in the specified faculty",
                        },
                        404,
                    )
                    return finalize_request(response)
                query = query.where(Announcement.department_id == department.id)
            if year_id:
                year = (
                    await session.execute(Select(Year).where(Year.id == int(year_id)))
                ).scalar_one_or_none()
                if not year:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Year Not Found for Getting Announcements.",
                        {"year_id": year_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Year not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Announcement.year_id == year.id)
            if subject_id:
                subject = (
                    await session.execute(
                        Select(Subject).where(Subject.id == int(subject_id))
                    )
                ).scalar_one_or_none()
                if not subject:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Subject Not Found for Getting Announcements.",
                        {"subject_id": subject_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Subject not found"}, 404
                    )
                    return finalize_request(response)
                if not faculty_id or not department_id or not year_id:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "User tried to filter by subject without specifying other "
                        "criteria",
                        {
                            "subject_id": subject_id,
                            "faculty_id": faculty_id,
                            "department_id": department_id,
                            "year_id": year_id,
                        },
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "You can't filter by subject without specifying faculty, department, and year",
                        },
                        400,
                    )
                    return finalize_request(response)
                if (
                    subject.faculty_id != int(faculty_id)
                    or subject.department_id != int(department_id)
                    or subject.year_id != int(year_id)
                ):
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Subject Not Found or Does Not Belong to Specified Faculty, Department, or Year for Getting Announcements.",
                        {
                            "subject_id": subject_id,
                            "faculty_id": faculty_id,
                            "department_id": department_id,
                            "year_id": year_id,
                        },
                        current_user.id,
                    )
                    response = JSONResponse(
                        {
                            "status": "error",
                            "message": "Subject not found in the specified criteria",
                        },
                        404,
                    )
                    return finalize_request(response)
                query = query.where(Announcement.subject_id == subject.id)
            if author_id:
                author = (
                    await session.execute(Select(User).where(User.id == int(author_id)))
                ).scalar_one_or_none()
                if not author:
                    await log(
                        request,
                        "Get",
                        "Announcements",
                        404,
                        "warning",
                        "Author Not Found for Getting Announcements.",
                        {"author_id": author_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "Author not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Announcement.author_id == author.id)
            if start_date_obj:
                query = query.where(
                    Announcement.date.isnot(None)
                    & (Announcement.date >= start_date_obj)
                )
            if end_date_obj:
                query = query.where(
                    Announcement.date.isnot(None) & (Announcement.date <= end_date_obj)
                )
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(Announcement.title).contains(query_search),
                        func.lower(Announcement.content).contains(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid Limit Provided for Announcements Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            announcement_sort_group = case(
                (Announcement.date.is_(None), 2),
                (Announcement.date >= func.now(), 0),
                else_=1,
            )
            future_announcement_date = case(
                (
                    Announcement.date.is_not(None) & (Announcement.date >= func.now()),
                    Announcement.date,
                ),
                else_=None,
            )
            past_announcement_date = case(
                (
                    Announcement.date.is_not(None) & (Announcement.date < func.now()),
                    Announcement.date,
                ),
                else_=None,
            )
            result = (
                (
                    await session.execute(
                        query.order_by(
                            announcement_sort_group.asc(),
                            future_announcement_date.asc(),
                            past_announcement_date.desc(),
                            Announcement.created_at.desc(),
                        )
                        .offset((page - 1) * limit)
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Announcements",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Announcements " "Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            announcements = result[:limit]
            await log(
                request,
                "Get",
                "Announcements",
                200,
                "info",
                "Announcements Retrieved Successfully.",
                {"filters": dict(data), "count": len(announcements)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcements retrieved successfully",
                    "data": [a.to_dict() for a in announcements],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Announcements",
            500,
            "error",
            "An Error Occurred while Getting Announcements.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting announcements",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/announcements/{announcement_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Announcements"])
@is_ready
@has_registered_subjects
async def get_announcement(request: Request, announcement_id: int):
    """
    This route is used to get a specific announcement by its ID.
    It will return the announcement data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            announcement = (
                await session.execute(
                    Select(Announcement)
                    .where(Announcement.id == announcement_id)
                    .options(
                        selectinload(Announcement.author).selectinload(User.faculty),
                        selectinload(Announcement.author).selectinload(User.department),
                        selectinload(Announcement.author).selectinload(User.year),
                        selectinload(Announcement.author).selectinload(User.role),
                        selectinload(Announcement.author).selectinload(
                            User.pending_user
                        ),
                        selectinload(Announcement.author).selectinload(
                            User.notifications
                        ),
                        selectinload(Announcement.subject),
                        selectinload(Announcement.faculty),
                        selectinload(Announcement.department),
                        selectinload(Announcement.year),
                    )
                )
            ).scalar_one_or_none()
            if not announcement:
                await log(
                    request,
                    "Get",
                    "Announcement",
                    404,
                    "warning",
                    "Announcement Not Found.",
                    {"announcement_id": announcement_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Announcement not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Announcement",
                200,
                "info",
                "Announcement Retrieved Successfully.",
                {"announcement": announcement.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Announcement retrieved successfully",
                    "data": announcement.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Announcement",
            500,
            "error",
            "An Error Occurred while Getting Announcement.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting announcement",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/logs/actions")
@is_logged_in
@rate_limit
@is_authorized(["View Logs"])
async def get_log_actions(request: Request):
    """
    This route is used to get all unique actions from logs.
    It will return a list of unique actions.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            actions = (
                (
                    await session.execute(
                        Select(func.distinct(Log.action)).order_by(Log.action.asc())
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Log Actions",
                200,
                "info",
                "Log Actions Retrieved Successfully.",
                {"count": len(actions)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Log actions retrieved successfully",
                    "data": actions,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Log Actions",
            500,
            "error",
            "An Error Occurred while Getting Log Actions.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting log actions",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/logs/entities")
@is_logged_in
@rate_limit
@is_authorized(["View Logs"])
async def get_log_entities(request: Request):
    """
    This route is used to get all unique entities from logs.
    It will return a list of unique entities.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            entities = (
                (
                    await session.execute(
                        Select(func.distinct(Log.entity)).order_by(Log.entity.asc())
                    )
                )
                .scalars()
                .all()
            )
            await log(
                request,
                "Get",
                "Log Entities",
                200,
                "info",
                "Log Entities Retrieved Successfully.",
                {"count": len(entities)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Log entities retrieved successfully",
                    "data": entities,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Log Entities",
            500,
            "error",
            "An Error Occurred while Getting Log Entities.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while getting log entities",
            },
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/logs")
@is_logged_in
@rate_limit
@is_authorized(["View Logs"])
async def get_logs(request: Request):
    """
    This route is used to get all logs with optional filters.
    It will return a list of logs.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Logs",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        date_from = data.get("date_from", None)
        date_to = data.get("date_to", None)
        log_type = data.get("type", None)  # info, warning, error
        action = data.get("action", None)
        entity = data.get("entity", None)
        user_id = data.get("user_id", None)  # User ID
        query_search = data.get("query", "").strip().lower()
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        if (
            log_type
            and log_type not in ["info", "warning", "error"]
            or date_from
            and not is_date(date_from)
            or date_to
            and not is_date(date_to)
            or user_id
            and (not is_int(user_id) or int(user_id) < 1)
        ):
            await log(
                request,
                "Get",
                "Logs",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Logs.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        date_from = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
        date_to = datetime.strptime(date_to, "%Y-%m-%d") if date_to else None
        if date_from and date_to and date_from > date_to:
            await log(
                request,
                "Get",
                "Logs",
                400,
                "warning",
                "Invalid Date Range Provided in The Request Query Parameters for Getting Logs.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid date range"}, 400
            )
            return finalize_request(response)
        if (
            date_from
            and date_from.replace(tzinfo=cairo_tz) > datetime.now(cairo_tz)
            or date_to
            and date_to.replace(tzinfo=cairo_tz) > datetime.now(cairo_tz)
        ):
            await log(
                request,
                "Get",
                "Logs",
                400,
                "warning",
                "Future Date Provided in The Request Query Parameters for Getting Logs.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Dates cannot be in the future"}, 400
            )
            return finalize_request(response)
        if date_to:
            date_to = date_to + timedelta(days=1) - timedelta(seconds=1)
        async with async_session() as session:
            query = (
                Select(Log, User.name)
                .join(User, Log.user_id == User.id, isouter=True)
                .order_by(Log.created_at.desc())
            )
            if date_from:
                query = query.where(Log.created_at >= date_from)
            if date_to:
                query = query.where(Log.created_at <= date_to)
            if log_type:
                query = query.where(Log.level == log_type)
            if action:
                query = query.where(func.lower(Log.action) == action.strip().lower())
            if entity:
                query = query.where(func.lower(Log.entity) == entity.strip().lower())
            if user_id:
                user = (
                    await session.execute(Select(User).where(User.id == int(user_id)))
                ).scalar_one_or_none()
                if not user:
                    await log(
                        request,
                        "Get",
                        "Logs",
                        404,
                        "warning",
                        "User Not Found for Getting Logs.",
                        {"user_id": user_id},
                        current_user.id,
                    )
                    response = JSONResponse(
                        {"status": "error", "message": "User not found"}, 404
                    )
                    return finalize_request(response)
                query = query.where(Log.user_id == user.id)
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(User.name).contains(query_search),
                        func.lower(Log.route).contains(query_search),
                    )
                )
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Logs",
                    400,
                    "warning",
                    "Invalid Limit Provided for Logs Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            has_next = (
                await session.execute(query.offset((page - 1) * limit).limit(limit + 1))
            ).all()
            if page < 1 or (page > 1 and (not has_next or len(has_next) < 1)):
                await log(
                    request,
                    "Get",
                    "Logs",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Logs Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            result = has_next[:limit] if has_next and len(has_next) > 0 else []
            logs = []
            if result and len(result) > 0:
                for l, user_name in result:
                    l.user = User(name=user_name)
                    logs.append(l)
            await log(
                request,
                "Get",
                "Logs",
                200,
                "info",
                "Logs Retrieved Successfully.",
                {"filters": dict(data), "count": len(logs)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Logs retrieved successfully",
                    "data": [l.many_to_dict() for l in logs],
                    "next": has_next and len(has_next) > limit,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Logs",
            500,
            "error",
            "An Error Occurred while Getting Logs.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting logs"}, 500
        )
        return finalize_request(response)


@admin_prefix.get("/logs/{log_id}")
@is_logged_in
@rate_limit
@is_authorized(["View Logs"])
async def get_log(request: Request, log_id: int):
    """
    This route is used to get a specific log by its ID.
    It will return the log data.
    """
    try:
        current_user = request.state.current_user
        async with async_session() as session:
            log_entry = (
                await session.execute(
                    Select(Log)
                    .where(Log.id == log_id)
                    .options(
                        selectinload(Log.user).selectinload(User.faculty),
                        selectinload(Log.user).selectinload(User.department),
                        selectinload(Log.user).selectinload(User.year),
                        selectinload(Log.user).selectinload(User.role),
                        selectinload(Log.user).selectinload(User.pending_user),
                        selectinload(Log.user).selectinload(User.notifications),
                    )
                )
            ).scalar_one_or_none()
            if not log_entry:
                await log(
                    request,
                    "Get",
                    "Log",
                    404,
                    "warning",
                    "Log Entry Not Found.",
                    {"log_id": log_id},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Log entry not found"}, 404
                )
                return finalize_request(response)
            await log(
                request,
                "Get",
                "Log",
                200,
                "info",
                "Log Entry Retrieved Successfully.",
                {"log": log_entry.to_dict()},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Log entry retrieved successfully",
                    "data": log_entry.to_dict(),
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Log",
            500,
            "error",
            "An Error Occurred while Getting Log Entry.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting log entry"},
            500,
        )
        return finalize_request(response)


@admin_prefix.get("/messages")
@is_logged_in
@rate_limit
@is_authorized(["View Messages"])
async def get_messages(request: Request):
    """
    This route is used to get all contact us messages with optional filters.
    It will return a list of messages.
    """
    try:
        current_user = request.state.current_user
        data = request.query_params
        if not is_sanitized(data):
            await log(
                request,
                "Get",
                "Messages",
                400,
                "warning",
                "Un Sanitized Data Provided in The Request Query Parameters.",
                {},
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        query_search = data.get("query", "").strip().lower()
        date_from = data.get("date_from", None)
        date_to = data.get("date_to", None)
        page = int(data.get("page", 1)) if is_int(data.get("page", "1")) else 1
        limit = int(data.get("limit", 50)) if is_int(data.get("limit", "50")) else 50
        if date_from and not is_date(date_from) or date_to and not is_date(date_to):
            await log(
                request,
                "Get",
                "Messages",
                400,
                "warning",
                "Invalid Data Provided in The Request Query Parameters for Getting Messages.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid data provided"}, 400
            )
            return finalize_request(response)
        date_from = (
            datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=cairo_tz)
            if date_from
            else None
        )
        date_to = (
            datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=cairo_tz)
            if date_to
            else None
        )
        if date_from and date_to and date_from > date_to:
            await log(
                request,
                "Get",
                "Messages",
                400,
                "warning",
                "Invalid Date Range Provided in The Request Query Parameters for Getting Messages.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Invalid date range"}, 400
            )
            return finalize_request(response)
        if (
            date_from
            and date_from > datetime.now(cairo_tz)
            or date_to
            and date_to > datetime.now(cairo_tz)
        ):
            await log(
                request,
                "Get",
                "Messages",
                400,
                "warning",
                "Future Date Provided in The Request Query Parameters for Getting Messages.",
                {"data": dict(data)},
                current_user.id,
            )
            response = JSONResponse(
                {"status": "error", "message": "Dates cannot be in the future"}, 400
            )
            return finalize_request(response)
        if date_to:
            date_to = date_to + timedelta(days=1) - timedelta(seconds=1)
        async with async_session() as session:
            query = Select(Message).order_by(Message.created_at.desc())
            if date_from:
                query = query.where(Message.created_at >= date_from)
            if date_to:
                query = query.where(Message.created_at <= date_to)
            if query_search and query_search != "":
                query = query.where(
                    or_(
                        func.lower(Message.name).contains(query_search),
                        func.lower(Message.email).contains(query_search),
                        func.lower(Message.phone).contains(query_search),
                        func.lower(Message.content).contains(query_search),
                    )
                )
            result = (
                (
                    await session.execute(
                        query.offset((page - 1) * limit).limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            if page < 1 or page > 1 and (not result or len(result) < 1):
                await log(
                    request,
                    "Get",
                    "Messages",
                    400,
                    "warning",
                    "Invalid Page Number Provided for Messages Retrieval.",
                    {"page": page},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Invalid page number"}, 400
                )
                return finalize_request(response)
            if limit < 1 or limit > 100:
                await log(
                    request,
                    "Get",
                    "Messages",
                    400,
                    "warning",
                    "Invalid Limit Provided for Messages Retrieval.",
                    {"limit": limit},
                    current_user.id,
                )
                response = JSONResponse(
                    {"status": "error", "message": "Limit must be between 1 and 100"},
                    400,
                )
                return finalize_request(response)
            messages = result[:limit]
            await log(
                request,
                "Get",
                "Messages",
                200,
                "info",
                "Messages Retrieved Successfully.",
                {"filters": dict(data), "count": len(messages)},
                current_user.id,
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Messages retrieved successfully",
                    "data": [m.to_dict() for m in messages],
                    "next": True if len(result) > limit else False,
                },
                200,
            )
            return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Get",
            "Messages",
            500,
            "error",
            "An Error Occurred while Getting Messages.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while getting messages"},
            500,
        )
        return finalize_request(response)


@app.get("/update-roles")
@is_logged_in
@rate_limit
@is_authorized(["Is Admin"])
async def update_roles(request: Request):
    """
    This route is used to update roles.
    """
    try:
        current_user = request.state.current_user
        await updated_roles(request)
        response = JSONResponse(
            {"status": "success", "message": "Roles updated successfully"}, 200
        )
        return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Update",
            "Roles",
            500,
            "error",
            "An Error Occurred while Updating Roles.",
            {"error": str(e)},
            current_user.id,
        )
        response = JSONResponse(
            {"status": "error", "message": "An error occurred while updating roles"},
            500,
        )
        return finalize_request(response)


@v1.post("/drive/notifications")
@rate_limit
async def drive_notifications(
    request: Request, username: str = Depends(verify_notification_credentials)
):
    """
    This route is used to handle Google Drive notifications.
    It will process the notification and update the drive files accordingly.
    """
    try:
        data = request.headers
        channel_id = data.get("X-Goog-Channel-ID")
        resource_id = data.get("X-Goog-Resource-ID")  # ID of the file
        resource_state = data.get(
            "X-Goog-Resource-State"
        )  # "update", "delete", "trash", etc.
        if not channel_id or not resource_id or not resource_state:
            await log(
                request,
                "Drive",
                "Notification",
                400,
                "warning",
                "Missing Required Headers for Drive Notification.",
                {"headers": dict(data)},
            )
            response = JSONResponse(
                {"status": "error", "message": "Missing required headers"}, 400
            )
            return finalize_request(response)
        response = JSONResponse(
            {"status": "success", "message": "Notification received"}, 200
        )
        return finalize_request(response)
    except Exception as e:
        await log(
            request,
            "Drive",
            "Notification",
            500,
            "error",
            "An Error Occurred while Handling Drive Notification.",
            {"error": str(e)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "An error occurred while processing the notification",
            },
            500,
        )
        return finalize_request(response)


# Public Routes
@v1.post("/messages")
@rate_limit
async def contact_us(request: Request):
    data = await request.json()
    if not data:
        await log(
            request,
            "Contact Us",
            "Message",
            400,
            "warning",
            "No Data Provided for Contact Us.",
            {},
        )
        response = JSONResponse({"status": "error", "message": "No data provided"}, 400)
        return finalize_request(response)
    name = data.get("name").strip()
    email = data.get("email").strip().lower()
    phone = data.get("phone").strip()
    message = data.get("content").strip()
    if not name or not email or not phone or not message:
        await log(
            request,
            "Contact Us",
            "Message",
            400,
            "warning",
            "Missing Required Fields for Contact Us.",
            {"data": dict(data)},
        )
        response = JSONResponse(
            {
                "status": "error",
                "message": "Please make sure to fill all the required fields",
            },
            400,
        )
        return finalize_request(response)
    if not is_sanitized(name) or not is_sanitized(phone):
        await log(
            request,
            "Contact Us",
            "Message",
            400,
            "warning",
            "Un Sanitized Data Provided for Contact Us.",
            {"data": dict(data)},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid data provided"}, 400
        )
        return finalize_request(response)
    if not is_phone_number(phone):
        await log(
            request,
            "Contact Us",
            "Message",
            400,
            "warning",
            "Invalid Phone Number Provided for Contact Us.",
            {"phone": phone},
        )
        response = JSONResponse(
            {"status": "error", "message": "Invalid phone number provided"}, 400
        )
        return finalize_request(response)
    async with async_session() as session:
        await session.begin()
        try:
            try:
                email_info = validate_email(email, check_deliverability=True)
            except EmailNotValidError as e:
                await log(
                    request,
                    "Contact Us",
                    "Message",
                    400,
                    "warning",
                    "Invalid Email Provided for Contact Us.",
                    {"email": email, "error": str(e)},
                )
                await session.rollback()
                response = JSONResponse(
                    {"status": "error", "message": "Invalid email address provided"},
                    400,
                )
                return finalize_request(response)
            message = Message(
                name=name,
                email=email,
                phone=phone,
                content=message,
            )
            session.add(message)
            await log(
                request,
                "Contact Us",
                "Message",
                201,
                "info",
                "Contact Us message sent successfully.",
                {"data": dict(data)},
            )
            response = JSONResponse(
                {
                    "status": "success",
                    "message": "Your message has been sent successfully. We will get back to you soon.",
                },
                201,
            )
            await session.commit()
            email_response = await send_email(
                request,
                os.environ.get("QUICK_REPLY_EMAIL"),
                "new_message",
                {"name": os.environ.get("QUICK_REPLY_NAME")},
            )
            if email_response.status_code != 200:
                await log(
                    request,
                    "Contact Us",
                    "Message",
                    500,
                    "error",
                    "An Error Occurred while Sending Notification Email for Contact Us message.",
                    {"email_response": email_response.body},
                )
                await session.delete(message)
                await session.commit()
                response = JSONResponse(
                    {
                        "status": "error",
                        "message": "An error occurred while sending your message. Please try again later.",
                    },
                    500,
                )
            return finalize_request(response)
        except Exception as e:
            await log(
                request,
                "Contact Us",
                "Message",
                500,
                "error",
                "An Error Occurred while Sending Contact Us message.",
                {"error": str(e)},
            )
            await session.rollback()
            response = JSONResponse(
                {
                    "status": "error",
                    "message": "An error occurred while sending your message. Please try again later.",
                },
                500,
            )
            return finalize_request(response)


# Views
# Coming from views.py
from views import *

# For Development


async def start_deployment(request: Request):
    try:
        # Use asyncio subprocess to run command without blocking
        process = await asyncio.create_subprocess_shell(
            "cd /Users/MazenDev/PycharmProjects/StudentsPortalScripts && python3 main.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait for the process to complete (non-blocking)
        stdout, stderr = await process.communicate()
        request.session["deployed"] = True
    except Exception as e:
        request.session["deployed"] = False
        print("Deployment failed:", str(e))


@app.get("/deploy")
async def deploy(request: Request):
    if request.session.get("deployed"):
        request.session["deployed"] = None
        return "Deployed Successfully"
    asyncio.create_task(start_deployment(request))
    # Return a page that automatically refreshes
    return """
    <html>
        <head>
            <title>Deploying...</title>
            <meta http-equiv="refresh" content="5;url=/deploy">
        </head>
        <body>
            <h1>Started Deploying</h1>
            <p>This page will automatically refresh every 5 seconds until deployment is complete.</p>
        </body>
    </html>
    """


# @app.get('/')
# async def main(request: Request):
#     await updated_roles()
#     async with async_session() as session:
#         # deleted = await session.execute(Delete(User).where(User.id == 1))  # Clear the user with id 1 for testing
#         user = (await session.execute(Select(User).where(or_(User.id == 1, User.id == 2)))).scalars().all()
#         role = (await session.execute(Select(Role).where(Role.name == 'admin'))).scalar_one_or_none()
#         for u in user:
#             if u and role:
#                 u.role = role
#         await session.commit()
#         # purposes
#     return templates.TemplateResponse(
#         'index.html'
#     , {'request': request})
# @app.get('/login')
# async def login(request: Request):
#     """
#     This route is used to render the login page.
#     It will RedirectResponse to the login page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login.html'
#     , {'request': request})
# @app.get('/login-success')
# async def login_success(request: Request):
#     """
#     This route is used to render the login success page.
#     It will RedirectResponse to the login success page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'login_success.html',
#         {'request': request}
#     )
# @app.get('/createProfile')
# async def signup_page(request: Request):
#     """
#     This route is used to render the signup page.
#     It will RedirectResponse to the signup page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'createProfile.html',
#         {'request': request}
#     )
# @app.get('/dashboard')
# async def dashboard(request: Request):
#     """
#     This route is used to render the dashboard page.
#     It will RedirectResponse to the dashboard page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'dashboard.html',
#         {'request': request}
#     )
#
# @app.get('/faculties')
# async def faculties(request: Request):
#     """
#     This route is used to render the faculties page.
#     It will RedirectResponse to the faculties page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'faculties.html',
#         {'request': request}
#     )
#
# @app.get('/departments')
# async def departments(request: Request):
#     """
#     This route is used to render the departments page.
#     It will RedirectResponse to the departments page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'departments.html',
#         {'request': request}
#     )
#
# @app.get('/years')
# async def years(request: Request):
#     """
#     This route is used to render the years page.
#     It will RedirectResponse to the years page of the frontend.
#     """
#     return templates.TemplateResponse(
#         'years.html',
#         {'request': request}
#     )

# @app.route(f"{os.environ.get('UPLOAD_PREFIX')}/<filename>')
# async def get_uploaded_file(request: Request, filename):
#     """Endpoint to serve uploaded files"""
#     if not filename:
#         await log(request, request, 400, 'warning', 'No filename provided for file download.', {})
#         response = JSONResponse({
#             'status': 'error',
#             'message': 'No filename provided'
#         }, 400)
#     await log(request, 200, 'info', 'Serving uploaded file.', {'filename': filename, 'url': request.url, 'path': request.path})
#     return send_from_directory(os.environ.get('UPLOAD_FOLDER'), filename)

# @app.get('/get-template/{template_name}')
# async def get_template(request: Request, template_name: str):
#     """Endpoint to serve rendered templates"""
#     try:
#         response = templates.TemplateResponse(
#             f"components/{template_name}",
#             {"request": request}
#         )
#         return finalize_request(response)
#     except Exception as e:
#         await log(request, "Get", "Template", 500, 'error', 'An Error Occurred while Rendering Template.', {'error': str(e), 'template_name': template_name})
#         response = JSONResponse({
#             'status': 'error',
#             'message': 'An error occurred while rendering the template. Please make sure the template exists.'
#         }, 500)
#         return finalize_request(response)


# Register Blueprints with the Flask app
v1.include_router(auth)
v1.include_router(user_prefix)
v1.include_router(admin_prefix)
app.include_router(v1)

# Import remaining models after the route if needed
if __name__ == "__main__":
    # Explicitly push app context when running directly
    # uvicorn.run('app:app', host='0.0.0.0', port=3000, reload=True)
    uvicorn.run("app:app", host="0.0.0.0", port=3000)
