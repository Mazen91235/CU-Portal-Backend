import urllib.parse
from collections.abc import AsyncIterable, Iterable
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel


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
        if isinstance(data, BaseModel):
            data = data.model_dump(mode="json")
        return JSONResponse(
            status_code=code or (200 if success else 500),
            content={
                "success": success,
                "message": message,
                "data": data,
                "next_page": True if next_page else False,
                **kwargs,
            },
        )

    @staticmethod
    def generate_redirect_response(redirect_url: str):
        return RedirectResponse(redirect_url)

    @staticmethod
    def generate_streaming_response(
        content: bytes | Iterable[bytes] | AsyncIterable[bytes],
        filename: str,
        content_type: str = "application/octet-stream",
    ):
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
        return StreamingResponse(stream, media_type=content_type, headers=headers)
