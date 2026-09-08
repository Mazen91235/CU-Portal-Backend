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
from business.contextVars.sessionContext import session_context
from core.iMiddlewares.iRequestLimitMiddleware import IRequestLimitMiddleware
from core.iLoggers.iBaseLogger import IBaseLogger
from core.utils.cachingHandler import CachingHandler
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
    except Exception:
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
            asyncio.create_task(
                caching_handler.set(
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
            )
        elif (
            request.method.upper() in ["POST", "PATCH", "PUT", "DELETE"]
            and str(response.status_code)[0] == "2"
        ):
            module = _extract_module_from_path(request.url.path)
            if module:
                asyncio.create_task(caching_handler.invalidate_module_cache(module))
        return None
    except Exception:
        return None


def _extract_module_from_path(path: str) -> str:
    if "/user/" in path:
        if not "/" in path.split("/user/")[1]:
            return "user/"
        return path.split("/user/")[1].split("/")[0]
    elif "/admin/" in path:
        return path.split("/admin/")[1].split("/")[0]
    elif "/auth/" in path:
        return path.split("/auth/")[1].split("/")[0]
    else:
        return ""


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
                        raise HTTPException(
                            status_code=409,
                            detail="A similar request is already being processed. Please wait for it to complete.",
                        )
                response = await asyncio.wait_for(
                    original_route_handler(request), timeout=timeout_seconds
                )
                await _update_cache(request, response)
                return response
            except CacheHitException as ex:
                return ex.response
            except asyncio.TimeoutError:
                try:
                    logger: IBaseLogger = request.app.state.container.logger()
                    await logger.log(
                        action="Timeout",
                        entity="Request",
                        level="warning",
                        code=504,
                        message=f"Request timed out after {timeout_seconds}s",
                        details={"path": str(request.url.path)},
                        source="CustomRoute",
                    )
                except Exception:
                    pass
                raise HTTPException(
                    status_code=504,
                    detail="The request took too long to process. Please try again.",
                )
            finally:
                if lock_key and acquired:
                    await caching_handler.release_lock(lock_key)

        return custom_route_handler
