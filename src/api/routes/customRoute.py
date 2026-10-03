import os
import hashlib
import asyncio
import json
from dotenv import load_dotenv
from typing import Callable
from fastapi import Request, Response, Depends, HTTPException
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from business.contextVars.userContext import user_context
from business.contextVars.permissionsContext import permissions_context
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.cachingHandler import caching_handler
from core.utils.stringHandler import StringHandler
from core.utils.validator import Validator
from core.utils.responseHandler import ResponseHandler
from core.utils.authCacheHandler import build_auth_cache

load_dotenv()  # Load environment variables from .env file

DEFAULT_TIMEOUT_SECONDS = int(
    os.environ.get("DEFAULT_TIMEOUT_SECONDS", "10")
)  # Default request timeout in seconds
CACHE_TTL = int(os.environ.get("CACHE_TTL", "120"))  # Default cache TTL in seconds

MODULES = {
    "announcement": {
        "user": "{registered_subjects}:{path}",
        "admin": "{registered_subjects}-{restrict_courses}:{path}",
    },
    "calendar": {"user": "{token}:{path}"},
    "event": {
        "user": "{faculty}:{department}:{year}:{path}",
        "admin": "{faculty}-{restrict_faculties}:{department}-{restrict_departments}:{year}-{restrict_years}:{path}",
    },
    "exam": {
        "user": "{registered_subjects}:{path}",
        "admin": "{registered_subjects}-{restrict_courses}:{path}",
    },
    "note": {
        "user": "{token}:{path}",
    },
    "notification": {
        "user": "{token}:{path}",
    },
    "task": {
        "user": "{registered_subjects}:{path}",
        "admin": "{registered_subjects}-{restrict_courses}:{path}",
    },
    "user": {
        "user": "{token}:{path}",
        "admin": "{faculty}-{restrict_faculties}:{department}-{restrict_departments}:{year}-{restrict_years}:{path}",
    },
    "week": {
        "user": "{faculty}:{department}:{year}:{path}",
        "admin": "{faculty}-{restrict_faculties}:{department}-{restrict_departments}:{year}-{restrict_years}:{path}",
    },
}
CUSTOM_PATHS = {
    "courses/enrolled": "{token}:{path}",
    "courses/available": "{department}:{year}:{registered_subjects}:{path}",
}


def set_timeout(seconds: float):
    """Route-level dependency marker: overrides the default request timeout."""

    async def _set_timeout_dependency():
        return None

    setattr(_set_timeout_dependency, "_is_timeout_marker", True)
    setattr(_set_timeout_dependency, "_timeout_seconds", seconds)
    return _set_timeout_dependency


def allow_inactive():
    """Route-level dependency marker: skips active-user enforcement."""

    async def _allow_inactive_dependency():
        return None

    setattr(_allow_inactive_dependency, "_is_allow_inactive_marker", True)
    return _allow_inactive_dependency


async def _enforce_active_user(request: Request):
    user = user_context.get(None)
    if user and not user.status:
        try:
            logger: IBaseLogger = request.app.state.container.logger()
            await logger.log(
                action="ActiveCheck",
                entity="User",
                level="warning",
                code=403,
                message="Inactive user attempted request",
                details={"user_id": user.id},
                source="CustomRoute",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=403,
            detail="Your account is not active. Please contact an admin.",
        )
    return None


async def _log(
    request: Request,
    action: str,
    entity: str,
    level: str,
    code: int,
    message: str,
    details: dict,
):
    try:
        logger: IBaseLogger = request.app.state.container.logger()
        await logger.log(
            action=action,
            entity=entity,
            level=level,
            code=code,
            message=message,
            details=details,
            source="CustomRoute",
        )
    except Exception:
        pass


class CacheHitException(Exception):
    def __init__(self, response: Response):
        self.response = response


async def _generate_cache_key_from_template(
    request: Request, template: str, token: str, path: str
) -> str:
    try:
        SUBS = {
            "{token}": token,
            "{path}": path,
        }
        for key, value in SUBS.items():
            template = template.replace(key, str(value))
        if "{" not in template:
            return template

        user_cached_response = getattr(request.state, "cached_user_access", None)
        if user_cached_response is None:
            user_cached_response = await caching_handler.get(f"system:{token}")

        if not user_cached_response:
            setattr(request.state, "fetch_user_data", True)
            return ""

        request.state.cached_user_access = user_cached_response
        access_data = user_cached_response.get("access", user_cached_response)
        SUBS["{registered_subjects}"] = ",".join(
            str(subject_id) for subject_id in access_data.get("registered_subjects", [])
        )
        SUBS["{restrict_courses}"] = access_data.get("restrict_courses", "1")
        SUBS["{faculty}"] = access_data.get("faculty", "")
        SUBS["{restrict_faculties}"] = access_data.get("restrict_faculties", "1")
        SUBS["{department}"] = access_data.get("department", "")
        SUBS["{restrict_departments}"] = access_data.get("restrict_departments", "1")
        SUBS["{year}"] = access_data.get("year", "")
        SUBS["{restrict_years}"] = access_data.get("restrict_years", "1")
        for key, value in SUBS.items():
            template = template.replace(key, str(value))
        return template
    except Exception:
        return ""


async def _resolve_cache_key(request: Request) -> str:
    token = request.cookies.get("token", "")
    module = _extract_module_from_path(request.url.path).removesuffix("s")
    path = f"{request.url.path}?{request.url.query}"
    if module not in MODULES:
        for custom_path, template in CUSTOM_PATHS.items():
            if custom_path in request.url.path:
                return await _generate_cache_key_from_template(
                    request, template, token, path
                )
        return path
    module_keys = MODULES[module]
    sub_key = "admin" if "admin/" in request.url.path else "user"
    template = module_keys.get(sub_key, "{path}")
    return await _generate_cache_key_from_template(request, template, token, path)


async def _prepare_cache(request: Request):
    try:
        if request.method.upper() == "GET":
            request.state.cache_key = await _resolve_cache_key(request)
        return None
    except Exception as e:
        await _log(
            request,
            action="Prepare",
            entity="Cache",
            level="error",
            code=500,
            message="Failed to prepare cache",
            details={"error": repr(e)},
        )
        request.state.cache_key = ""
        return None


async def _check_cache(request: Request):
    try:
        if request.method.upper() == "GET":
            cache_key = getattr(request.state, "cache_key", None)
            if cache_key is None:
                cache_key = await _resolve_cache_key(request)
            if not cache_key:
                return None
            cached_body = await caching_handler.get_raw(cache_key)
            if cached_body:
                response = Response(
                    content=cached_body,
                    status_code=200,
                    media_type="application/json",
                )
                raise CacheHitException(response)
        return None
    except CacheHitException as ex:
        raise ex
    except Exception as e:
        await _log(
            request,
            action="Check",
            entity="Cache",
            level="error",
            code=500,
            message="Failed to check cache",
            details={"error": repr(e)},
        )
        return None


async def _update_cache(request: Request, response: Response):
    try:
        if (
            request.method.upper() == "GET"
            and str(response.status_code)[0] == "2"
            and issubclass(type(response), JSONResponse)
        ):
            if "logout" in request.url.path:
                module = "auth"
                await caching_handler.invalidate_module_cache(module)
                return None
            cache_key = getattr(request.state, "cache_key", None)
            if cache_key is None:
                cache_key = await _resolve_cache_key(request)
            if not cache_key:
                return None
            body_bytes = getattr(response, "body", b"{}")
            await caching_handler.set_raw(cache_key, body_bytes, expire=CACHE_TTL)
        elif (
            request.method.upper() in ["POST", "PATCH", "PUT", "DELETE"]
            and str(response.status_code)[0] == "2"
        ):
            module = _extract_module_from_path(request.url.path)
            if module:
                await caching_handler.invalidate_module_cache(module)
        return None
    except Exception as e:
        await _log(
            request,
            action="Update",
            entity="Cache",
            level="error",
            code=500,
            message="Failed to update cache",
            details={"error": repr(e)},
        )
        return None


async def _update_user_cache(request: Request):
    try:
        if (
            not getattr(request.state, "refresh_user_cache", False)
            or request.method.upper() != "GET"
        ):
            return None

        user = getattr(request.state, "user", None)
        user_permissions = getattr(request.state, "user_permissions", None)
        refresh_token = getattr(user, "refresh_token", None) if user else None
        if user is None or user_permissions is None or not refresh_token:
            return None

        registered_subjects = sorted(
            str(subject_id)
            for subject_id in getattr(request.state, "registered_subject_ids", set())
        )
        access = {
            "registered_subjects": registered_subjects,
            "restrict_courses": (
                "1" if "Access All Courses" in user_permissions else "0"
            ),
            "faculty": str(user.faculty_id or ""),
            "restrict_faculties": (
                "1" if "Access All Faculties" in user_permissions else "0"
            ),
            "department": str(user.department_id or ""),
            "restrict_departments": (
                "1" if "Access All Departments" in user_permissions else "0"
            ),
            "year": str(user.year_id or ""),
            "restrict_years": ("1" if "Access All Years" in user_permissions else "0"),
        }

        cached = build_auth_cache(user, user_permissions)
        cached["access"] = access
        await caching_handler.set(f"system:{refresh_token}", cached, expire=CACHE_TTL)
        return None
    except Exception as e:
        await _log(
            request,
            action="Update",
            entity="UserCache",
            level="error",
            code=500,
            message="Failed to update user cache",
            details={"error": repr(e)},
        )
        return None


def _extract_module_from_path(path: str) -> str:
    module = path.removeprefix("/user/").removeprefix("/admin/")
    if not module or "/" not in module:
        return "user"
    if "auth" in module:
        return "auth"
    return module.split("/")[0] if "/" in module else module


async def _generate_inflight_key(request: Request) -> str:
    if request.method.upper() not in ["POST", "PATCH", "PUT", "DELETE"]:
        return ""
    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes) if body_bytes else {}
        canonical_body = json.dumps(body_json, sort_keys=True, separators=(",", ":"))
    except Exception:
        canonical_body = body_bytes.decode("utf-8", errors="ignore")

    raw_key = f"inflight:{request.method}:{request.url.path}:{canonical_body}"
    lock_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return lock_key


async def _check_for_redirect(request: Request):
    if request.method.upper() not in ["POST", "PATCH", "PUT", "DELETE"]:
        return None
    if Validator.validate_hostname_is_background_worker(request.url.hostname or ""):
        return None
    if not request.cookies.get("token"):
        return None
    token = StringHandler.generate_random_string(32)
    response = ResponseHandler.generate_redirect_response(token=token)
    await caching_handler.set(token, {"token": request.cookies.get("token", "")})
    modules_to_redirect = ["material", "file", "attachment"]
    if any(module in request.url.path for module in modules_to_redirect):
        return response
    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        body_json = {}
    if "url" in body_json and Validator.is_valid_drive_url(body_json["url"]):
        return response
    if "details" in body_json and isinstance(body_json["details"], dict):
        details = body_json["details"]
        if (
            "url" in details
            and details["url"]
            and Validator.is_valid_drive_url(details["url"])
        ):
            return response
        if (
            "avatar" in details
            and details["avatar"]
            and Validator.is_valid_drive_url(details["avatar"])
        ):
            return response
        if (
            "urls" in details
            and isinstance(details["urls"], list)
            and any(Validator.is_valid_drive_url(url) for url in details["urls"])
        ):
            return response
    return None


class CustomRoute(APIRoute):
    def __init__(self, *args, dependencies=None, **kwargs):
        dependencies = list(dependencies) if dependencies else []

        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        skip_active_check = False

        for dep in dependencies:
            func = getattr(dep, "dependency", None)
            if getattr(func, "_is_timeout_marker", False):
                timeout_seconds = getattr(
                    func, "_timeout_seconds", DEFAULT_TIMEOUT_SECONDS
                )
            if getattr(func, "_is_allow_inactive_marker", False):
                skip_active_check = True

        dependencies.insert(0, Depends(_prepare_cache))

        if not skip_active_check:
            dependencies.append(Depends(_enforce_active_user))

        dependencies.append(Depends(_check_cache))

        self.timeout_seconds = timeout_seconds

        self._background_tasks: set[asyncio.Task] = set()

        super().__init__(*args, dependencies=dependencies, **kwargs)

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        timeout_seconds = self.timeout_seconds

        async def custom_route_handler(request: Request) -> Response:
            redirect_response = await _check_for_redirect(request)
            if redirect_response is not None:
                return redirect_response

            lock_key = await _generate_inflight_key(request)
            acquired = False
            try:
                if lock_key:
                    acquired = await caching_handler.acquire_lock(lock_key)
                    if not acquired:
                        await _log(
                            request,
                            action="InflightCheck",
                            entity="Request",
                            level="warning",
                            code=409,
                            message="A similar request is already being processed.",
                            details={},
                        )
                        return ResponseHandler.generate_response(
                            success=False,
                            code=409,
                            message="A similar request is already being processed. Please wait for it to complete.",
                        )
                if timeout_seconds == 0:
                    response = await original_route_handler(request)
                else:
                    response = await asyncio.wait_for(
                        original_route_handler(request), timeout=timeout_seconds
                    )
                await _update_user_cache(request)
                await _update_cache(request, response)
                return response
            except CacheHitException as ex:
                return ex.response
            except asyncio.TimeoutError:
                await _log(
                    request,
                    action="Timeout",
                    entity="Request",
                    level="error",
                    code=504,
                    message="The request took too long to process.",
                    details={},
                )
                raise HTTPException(
                    status_code=504,
                    detail="The request took too long to process. Please try again.",
                )
            except Exception:
                raise
            finally:
                if lock_key and acquired:
                    release_lock_task = asyncio.create_task(
                        caching_handler.release_lock(lock_key)
                    )
                    self._background_tasks.add(release_lock_task)
                    release_lock_task.add_done_callback(self._background_tasks.discard)

        return custom_route_handler
