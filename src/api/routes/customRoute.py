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
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.cachingHandler import CachingHandler
from core.utils.stringHandler import StringHandler
from core.utils.validator import Validator
from core.utils.responseHandler import ResponseHandler

load_dotenv()  # Load environment variables from .env file

DEFAULT_TIMEOUT_SECONDS = int(
    os.environ.get("DEFAULT_TIMEOUT_SECONDS", "10")
)  # Default request timeout in seconds
CACHE_TTL = int(os.environ.get("CACHE_TTL", "120"))  # Default cache TTL in seconds

caching_handler = CachingHandler()


def set_timeout(seconds: float):
    """Route-level dependency marker: overrides the default request timeout."""

    async def _set_timeout_dependency():
        return None

    _set_timeout_dependency._is_timeout_marker = True
    _set_timeout_dependency._timeout_seconds = seconds
    return _set_timeout_dependency


def allow_inactive():
    """Route-level dependency marker: skips active-user enforcement."""

    async def _allow_inactive_dependency():
        return None

    _allow_inactive_dependency._is_allow_inactive_marker = True
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
    def __init__(self, response: JSONResponse):
        self.response = response


async def _check_cache(request: Request):
    try:
        if os.environ.get("TESTING", "false").lower() == "true":
            return None
        if request.method.upper() == "GET":
            token = request.cookies.get("token", "")
            cache_key = f"{token}:{request.url.path}?{request.url.query}"
            cached_response = await caching_handler.get(cache_key)
            if cached_response:
                response = ResponseHandler.generate_response(
                    success=cached_response["success"],
                    code=cached_response["code"],
                    message=cached_response["message"],
                    data=cached_response["data"],
                    next_page=cached_response["next_page"],
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
        if os.environ.get("TESTING", "false").lower() == "true":
            return None
        if (
            request.method.upper() == "GET"
            and str(response.status_code)[0] == "2"
            and issubclass(type(response), JSONResponse)
        ):
            token = request.cookies.get("token", "")
            cache_key = f"{token}:{request.url.path}?{request.url.query}"
            body_bytes = getattr(response, "body", b"{}")
            body = json.loads(body_bytes.decode("utf-8"))
            await caching_handler.set(
                cache_key,
                {
                    "success": body.get("success", True),
                    "code": response.status_code,
                    "message": body.get("message", ""),
                    "data": body.get("data", None),
                    "next_page": body.get("next_page", False),
                },
                expire=CACHE_TTL,
            )
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


def _extract_module_from_path(path: str) -> str:
    module = path.removeprefix("/user/").removeprefix("/admin/")
    if not module:
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
    await caching_handler.set(token, {"token": request.cookies.get("token", "")})
    query = (
        f"?token={token}"
        if request.url.query == ""
        else f"?{request.url.query}&token={token}"
    )
    redirect_url = f"{os.environ.get('BACKGROUND_WORKER_URL', 'http://localhost:8001')}{request.url.path}{query}"
    modules_to_redirect = ["material", "file"]
    if any(module in request.url.path for module in modules_to_redirect):
        return ResponseHandler.generate_redirect_response(redirect_url)
    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes) if body_bytes else {}
    except Exception:
        body_json = {}
    if hasattr(body_json, "url") and getattr(body_json, "url"):
        return ResponseHandler.generate_redirect_response(redirect_url)
    if hasattr(body_json, "details") and isinstance(
        getattr(body_json, "details"), dict
    ):
        details = getattr(body_json, "details")
        if (
            "url" in details
            and details["url"]
            and Validator.is_valid_drive_url(details["url"])
        ):
            return ResponseHandler.generate_redirect_response(redirect_url)
        if (
            "avatar" in details
            and details["avatar"]
            and Validator.is_valid_drive_url(details["avatar"])
        ):
            return ResponseHandler.generate_redirect_response(redirect_url)
        if (
            "urls" in details
            and isinstance(details["urls"], list)
            and any(Validator.is_valid_drive_url(url) for url in details["urls"])
        ):
            return ResponseHandler.generate_redirect_response(redirect_url)
    return None


class CustomRoute(APIRoute):
    def __init__(self, *args, dependencies=None, **kwargs):
        dependencies = list(dependencies) if dependencies else []

        timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        skip_active_check = False

        for dep in dependencies:
            func = getattr(dep, "dependency", None)
            if getattr(func, "_is_timeout_marker", False):
                timeout_seconds = func._timeout_seconds
            if getattr(func, "_is_allow_inactive_marker", False):
                skip_active_check = True

        if not skip_active_check:
            dependencies.append(Depends(_enforce_active_user))

        dependencies.append(Depends(_check_cache))

        self.timeout_seconds = timeout_seconds

        super().__init__(*args, dependencies=dependencies, **kwargs)

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        timeout_seconds = self.timeout_seconds

        async def custom_route_handler(request: Request) -> Response:
            def _get_rate_limit_middleware() -> IRequestLimitMiddleware:
                return request.app.state.container.request_limit_middleware()

            async def _rate_limit(
                request: Request,
            ):
                return await _get_rate_limit_middleware().throttle(request)

            lock_key = await _generate_inflight_key(request)
            acquired = False
            try:
                await _rate_limit(request)
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
                redirect_response = await _check_for_redirect(request)
                if redirect_response is not None:
                    return redirect_response
                if timeout_seconds == 0:
                    response = await original_route_handler(request)
                else:
                    response = await asyncio.wait_for(
                        original_route_handler(request), timeout=timeout_seconds
                    )
                asyncio.create_task(_update_cache(request, response))
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
                    asyncio.create_task(caching_handler.release_lock(lock_key))

        return custom_route_handler
