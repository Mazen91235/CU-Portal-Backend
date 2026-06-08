from fastapi import Request, Response
from starlette.requests import ClientDisconnect
from starlette.datastructures import UploadFile
from business.contextVars.requestContext import request_context
from typing import Callable
import json
from io import BytesIO


class RequestMiddleware:
    @classmethod
    async def handle(cls, request: Request, call_next: Callable) -> Response:
        request_token = request_context.set(request)
        try:
            response: Response = await cls.convert_formdata_to_json(request, call_next)
            return response
        finally:
            request_context.reset(request_token)

    @classmethod
    async def convert_formdata_to_json(
        cls, request: Request, call_next: Callable
    ) -> Response:
        files: list[UploadFile] = []
        json_body = b"{}"
        content_type = request.headers.get("Content-Type", "").lower()

        async def receive() -> dict:
            return {
                "type": "http.request",
                "body": json_body,
                "more_body": False,
            }

        if content_type.startswith(
            "application/x-www-form-urlencoded"
        ) or content_type.startswith("multipart/form-data"):
            try:
                form_data = await request.form()
            except ClientDisconnect:
                return Response(status_code=400, content="client disconnected")
            except Exception:
                return await call_next(request)
            request._json = {}

            for key, value in form_data.multi_items():
                normalized_key = key.lower().strip()
                if isinstance(value, UploadFile):
                    files.append(value)
                    try:
                        await value.seek(0)
                    except Exception:
                        pass
                    continue

                normalized_value = value.strip() if isinstance(value, str) else value
                if normalized_key not in request._json:
                    request._json[normalized_key] = normalized_value
                else:
                    current_value = request._json[normalized_key]
                    if isinstance(current_value, list):
                        current_value.append(normalized_value)
                    else:
                        request._json[normalized_key] = [
                            current_value,
                            normalized_value,
                        ]

            # Rebuild request body as JSON so downstream `await request.json()` reads this payload.
            json_body = json.dumps(request._json, default=str).encode("utf-8")
            request._body = json_body

            request._receive = receive
        # Handle Binary File Uploads: Attach files to request.state for downstream access.
        elif content_type.startswith("application/octet-stream"):
            body = await request.body()
            if body:
                file = UploadFile(
                    filename=(
                        request.headers.get("x-file-name")
                        or request.headers.get("x-filename")
                        or "uploaded_file"
                    ),
                    file=BytesIO(body),
                    size=len(body),
                    headers=request.headers,
                )
                files.append(file)
            request._json = (
                {}
            )  # No JSON data, but we still want to set this for consistency.
            json_body = json.dumps(request._json).encode("utf-8")
            request._body = json_body
            request._receive = receive

        # call_next only accepts the Request object, so attach files on request.state.
        request.state.upload_files = files

        response: Response = await call_next(request)
        return response
