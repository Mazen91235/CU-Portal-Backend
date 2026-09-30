import os
import asyncio
import urllib.parse
from collections.abc import AsyncIterable, Iterable
from fastapi import Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
from business.contextVars.requestContext import request_context

BACKGROUND_TASKS: set[asyncio.Task] = set()


class ResponseHandler:
    @staticmethod
    def generate_response(
        success: bool,
        code: int | None,
        message: str | None = None,
        data=None,
        next_page: bool | None = None,
        **kwargs,
    ):
        request = request_context.get(None)
        if isinstance(data, BaseModel):
            data = data.model_dump(mode="json")
        response = JSONResponse(
            status_code=code or (200 if success else 500),
            content={
                "success": success,
                "message": message,
                "data": data,
                "next_page": True if next_page else False,
                **kwargs,
            },
        )
        if success and request and hasattr(request.state, "background"):
            task = asyncio.create_task(request.state.background)
            BACKGROUND_TASKS.add(task)
            task.add_done_callback(BACKGROUND_TASKS.discard)
        return response

    @staticmethod
    def generate_redirect_response(
        redirect_url: str | None = None, token: str | None = None
    ):
        request = request_context.get(None)
        if not redirect_url:
            if not request:
                raise ValueError("Either redirect_url or request must be provided.")
            else:
                if token:
                    query = (
                        f"?token={token}"
                        if request.url.query == ""
                        else f"?{request.url.query}&token={token}"
                    )
                else:
                    query = f"?{request.url.query}" if request.url.query else ""
                redirect_url = f"{os.environ.get('BACKGROUND_WORKER_URL', 'http://localhost:8001')}{request.url.path}{query}"
        response = RedirectResponse(redirect_url)
        if request and hasattr(request.state, "background"):
            task = asyncio.create_task(request.state.background)
            BACKGROUND_TASKS.add(task)
            task.add_done_callback(BACKGROUND_TASKS.discard)
        return response

    @staticmethod
    def generate_streaming_response(
        content: bytes | Iterable[bytes] | AsyncIterable[bytes],
        filename: str,
        content_type: str = "application/octet-stream",
    ):
        request = request_context.get(None)
        # 1. Percent-encode the filename for UTF-8 compatibility (RFC 5987)
        encoded_filename = urllib.parse.quote(filename)

        # 2. Create an ASCII-safe fallback for older HTTP parsers
        ascii_filename = (
            filename.encode("ascii", "ignore").decode("ascii") or "download"
        )

        headers = {
            "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}",
        }

        stream = content if not isinstance(content, bytes) else iter((content,))
        response = StreamingResponse(stream, media_type=content_type, headers=headers)
        if request and hasattr(request.state, "background"):
            task = asyncio.create_task(request.state.background)
            BACKGROUND_TASKS.add(task)
            task.add_done_callback(BACKGROUND_TASKS.discard)
        return response

    @classmethod
    def generate_preflight_response(cls, request: Request, allowed_origins: list[str]):
        response = Response(status_code=204)
        return cls.attach_cors_headers(request, response, allowed_origins)

    @classmethod
    def attach_cors_headers(
        cls,
        request: Request,
        response: Response | Exception,
        allowed_origins: list[str],
    ):
        origin = request.headers.get("origin")
        real_origin = origin
        if not real_origin or real_origin == "null":
            real_origin = request.headers.get("referer")
        real_origin = real_origin.rstrip("/") if real_origin else None
        if real_origin and real_origin not in allowed_origins:
            response = cls.generate_response(
                success=False,
                code=403,
                message=f"CORS Policy Violation: Origin '{real_origin}' is not allowed.",
            )
        if isinstance(response, Exception):
            status_code = getattr(response, "status_code", 500)
            detail = (
                response.detail
                if isinstance(response, HTTPException)
                else (repr(response) or str(response) or "Internal Server Error")
            )
            response = cls.generate_response(
                success=False,
                code=status_code,
                message=detail,
            )
        response.headers["Access-Control-Allow-Origin"] = origin or real_origin or "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "OPTIONS, GET, POST, PUT, DELETE, PATCH"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-API-Key"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
